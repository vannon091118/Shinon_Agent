"""KeyPool: capability-aware key selection, rate limit budgets, and atomic claims.

v2.1 — claim() now uses health-weighted smart selection instead of
round-robin. Optional model parameter enables CapabilityMatrix routing.
Budget checks and streaming affinity built into claim().

Backward-compatible: existing claim()/release() API unchanged.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from limen.resilience import FailureType
    from limen.resilience.rate_limiter import RateLimitTracker, TokenBudget, RequestBudget
    from limen.routing.capability import CapabilityMatrix, CapabilityEntry

logger = logging.getLogger(__name__)


@dataclass
class Key:
    """One API key in a deployment pool."""

    value: str
    deployment: str = ""       # deployment alias for capability routing (v2.0)
    status: str = "active"     # active | cooldown | dead
    cooldown_until: float | None = None
    # Rate limit budgets (v2.0)
    token_budget: Any = None    # TokenBudget
    request_budget: Any = None  # RequestBudget
    # Health tracking (v2.0)
    error_count: int = 0
    success_count: int = 0
    # Latency tracking (v2.2)
    total_latency_ms: float = 0.0
    latency_count: int = 0

    @property
    def is_ready(self) -> bool:
        return self.status == "active" and self.cooldown_until is None

    @property
    def total_requests(self) -> int:
        return self.error_count + self.success_count

    @property
    def error_rate(self) -> float:
        total = self.total_requests
        if total == 0:
            return 0.0
        return self.error_count / total

    @property
    def avg_latency_ms(self) -> float:
        """Average latency in milliseconds, or 0 if no requests yet."""
        if self.latency_count == 0:
            return 0.0
        return self.total_latency_ms / self.latency_count

    @property
    def health_score(self) -> float:
        """0.0 = dead, 1.0 = perfect. Based on error rate."""
        if self.status == "dead":
            return 0.0
        err = self.error_rate
        return max(0.0, 1.0 - (err * 5.0))  # 20% error rate = 0.0

    def has_token_budget(self, estimated_tokens: int = 0) -> bool:
        if self.token_budget is None:
            return True
        if estimated_tokens > 0:
            return self.token_budget.remaining() >= estimated_tokens
        return not self.token_budget.is_exhausted()

    def has_request_budget(self) -> bool:
        if self.request_budget is None:
            return True
        return not self.request_budget.is_exhausted()

    def token_remaining_ratio(self) -> float:
        """0.0 = exhausted, 1.0 = full budget."""
        if self.token_budget is None:
            return 1.0
        return 1.0 - self.token_budget.ratio()

    def request_remaining_ratio(self) -> float:
        if self.request_budget is None:
            return 1.0
        mx = self.request_budget.max_requests
        if mx == 0:
            return 1.0
        return 1.0 - (self.request_budget.current_usage() / mx)

    def can_serve(self, estimated_tokens: int = 0) -> bool:
        return (
            self.is_ready
            and self.has_token_budget(estimated_tokens)
            and self.has_request_budget()
        )


class KeyPool:
    """Key pool with capability-aware selection, rate limit budgets, and atomic claims.

    v2.1: claim() uses health-weighted smart selection.
    Optional model param enables CapabilityMatrix routing.
    Budget checks and streaming affinity built into claim().

    ``asyncio.Lock`` serialises ``claim`` / ``release`` so two coroutines
    never grab the same key simultaneously.
    """

    def __init__(
        self,
        deployment: str,
        keys: Iterable[str],
        *,
        clock: Callable[[], float] | None = None,
        capability_matrix: Optional[CapabilityMatrix] = None,
        rate_tracker: Optional[RateLimitTracker] = None,
        persist_callback: Optional[Callable[[str, str, str, Optional[str]], None]] = None,
        budget_persist_callback: Optional[Callable[[str, str, int, int, int, int], None]] = None,
        provider: str = "",
    ) -> None:
        self._keys: tuple[Key, ...] = tuple(Key(value=value) for value in keys)
        self._cursor: int = 0
        self._lock: asyncio.Lock | None = None
        self._clock = clock if clock is not None else _monotonic_float
        self.deployment = deployment
        self.provider = provider

        # v2.0: capability-aware routing
        self._capability_matrix = capability_matrix
        self._rate_tracker = rate_tracker
        self._persist_callback = persist_callback
        self._budget_persist_callback = budget_persist_callback
        self._tokens_since_persist = 0
        self._requests_since_persist = 0

        # Deployment-to-key mapping for capability routing
        self._deployment_map: Dict[str, Key] = {}

        # Initialize rate limit budgets for each key
        if rate_tracker is not None:
            for key in self._keys:
                fp = hashlib.sha256(key.value.encode()).hexdigest()[:16]
                key_id = f"{deployment}:{fp}"
                key.token_budget = rate_tracker.get_or_create_token_budget(key_id)
                key.request_budget = rate_tracker.get_or_create_request_budget(key_id)

    def set_deployment_names(self, names: Iterable[str]) -> None:
        """Assign deployment names to keys in order (for capability routing)."""
        name_list = list(names)
        for i, key in enumerate(self._keys):
            if i < len(name_list):
                key.deployment = name_list[i]
                self._deployment_map[name_list[i]] = key

    # ── properties ──────────────────────────────────────────────────

    @property
    def active_count(self) -> int:
        now = self._clock()
        return sum(
            1 for key in self._keys
            if key.status == "active"
            or (key.status == "cooldown" and key.cooldown_until is not None and key.cooldown_until <= now)
        )

    @property
    def cooldown_count(self) -> int:
        now = self._clock()
        return sum(
            1 for key in self._keys
            if key.status == "cooldown" and key.cooldown_until is not None and key.cooldown_until > now
        )

    @property
    def dead_count(self) -> int:
        return sum(1 for key in self._keys if key.status == "dead")

    @property
    def total_count(self) -> int:
        return len(self._keys)

    @property
    def keys(self) -> tuple[Key, ...]:
        return self._keys

    # ── persistence recovery ────────────────────────────────────────

    def apply_persisted_state(
        self, key_value: str, status: str, *, cooldown_until: float | None = None
    ) -> None:
        key = _find_key(self._keys, key_value)
        if key is None:
            return
        if key.status == "dead":
            return
        if status == "dead":
            key.status = "dead"
            key.cooldown_until = None
        elif status == "cooldown" and cooldown_until is not None:
            now = self._clock()
            if cooldown_until > now:
                key.status = "cooldown"
                key.cooldown_until = cooldown_until

    def restore_persisted_states(
        self, persisted: dict[str, object], *, deployment: str
    ) -> None:
        for key in self._keys:
            fp = hashlib.sha256(key.value.encode()).hexdigest()[:16]
            key_id = f"{deployment}:{fp}"
            state = persisted.get(key_id)
            if state is None:
                continue
            state_dict: dict[str, object] = state  # type: ignore[assignment]
            status = str(state_dict.get("status", "active"))
            cooldown_str = state_dict.get("cooldown_until")
            cooldown_val: float | None = None
            if cooldown_str:
                try:
                    from datetime import datetime as _dt
                    cooldown_val = _dt.fromisoformat(str(cooldown_str)).timestamp()
                except (ValueError, OSError):
                    cooldown_val = None
            self.apply_persisted_state(key.value, status, cooldown_until=cooldown_val)

    # ── locking helper ──────────────────────────────────────────────

    async def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    # ── claim (v2.1: capability-aware smart selection) ──────────────

    async def claim(
        self,
        model: Optional[str] = None,
        *,
        estimated_tokens: int = 0,
        prefer_streaming: bool = False,
    ) -> str | None:
        """Return the best ready key, or None if none available.

        v2.1: Uses health-weighted smart selection instead of round-robin.
        When model is provided and CapabilityMatrix exists, uses capability-aware
        routing. Otherwise, ranks all ready keys by health, budget, and error rate.

        Backward compatible: claim() without arguments still works.
        """
        lock = await self._get_lock()
        async with lock:
            self._advance_cooldowns()

            # ── Path A: Capability-aware routing (model + matrix) ──
            if model is not None and self._capability_matrix is not None:
                entry = self._capability_matrix.best_key(
                    model,
                    prefer_streaming=prefer_streaming,
                )
                if entry is not None:
                    key = self._deployment_map.get(entry.deployment)
                    if key is not None and key.can_serve(estimated_tokens):
                        return key.value

            # ── Path B: Health-weighted smart selection ──
            candidates = [k for k in self._keys if k.can_serve(estimated_tokens)]
            if not candidates:
                return None

            # max() is stable (first wins on tie) — deterministic, not random
            return max(candidates, key=_score_key).value

    # ── claim_for_model (delegates to claim) ────────────────────────

    async def claim_for_model(
        self,
        model: str,
        *,
        estimated_tokens: int = 0,
        prefer_streaming: bool = False,
    ) -> tuple[Optional[str], Optional[CapabilityEntry]]:
        """Select the best key for a specific model request.

        Delegates to claim() with model param. Returns (key_value, entry)
        where entry is the CapabilityEntry if capability routing was used.
        """
        entry = None
        if self._capability_matrix is not None:
            entry = self._capability_matrix.best_key(model, prefer_streaming=prefer_streaming)

        key_val = await self.claim(
            model=model,
            estimated_tokens=estimated_tokens,
            prefer_streaming=prefer_streaming,
        )
        return key_val, entry

    async def release(
        self,
        key_value: str,
        failure: FailureType | None,
        *,
        cooldown_seconds: float = 0.0,
        tokens_used: int = 0,
        latency_ms: float = 0.0,
    ) -> None:
        """Update key state after a provider call."""
        lock = await self._get_lock()
        async with lock:
            key = _find_key(self._keys, key_value)
            if key is None:
                return

            if failure is None:
                if tokens_used > 0 and key.token_budget is not None:
                    key.token_budget.record(tokens_used)
                if key.request_budget is not None:
                    key.request_budget.record()
                key.success_count += 1
                if latency_ms > 0:
                    key.total_latency_ms += latency_ms
                    key.latency_count += 1
                if key.status == "cooldown":
                    key.status = "active"
                    key.cooldown_until = None
                self._maybe_persist(key_value, "active", None)
                self._maybe_persist_budget(key)
                return

            key.error_count += 1
            self._apply_failure(key, failure, cooldown_seconds)

            cooldown_for_db: Optional[str] = None
            if key.status == "cooldown" and key.cooldown_until is not None:
                remaining = key.cooldown_until - self._clock()
                if remaining > 0:
                    from datetime import datetime, timedelta, timezone
                    cooldown_for_db = (
                        datetime.now(timezone.utc) + timedelta(seconds=remaining)
                    ).isoformat()
            self._maybe_persist(key_value, key.status, cooldown_for_db)

    # ── budget stats ────────────────────────────────────────────────

    def budget_stats(self, key_value: str) -> Dict[str, int]:
        key = _find_key(self._keys, key_value)
        if key is None:
            return {}
        result: Dict[str, int] = {}
        if key.token_budget is not None:
            result["tokens_used"] = key.token_budget.current_usage()
            result["tokens_remaining"] = key.token_budget.remaining()
        if key.request_budget is not None:
            result["requests_used"] = key.request_budget.current_usage()
            result["requests_remaining"] = key.request_budget.remaining()
        result["errors"] = key.error_count
        result["successes"] = key.success_count
        return result

    # ── health snapshot (for DB persistence) ────────────────────────

    def get_health_snapshot(self) -> dict[str, dict[str, object]]:
        """Return per-key health data for DB sync.

        Returns dict keyed by key_id (deployment:fingerprint).
        Each value: {error_count, success_count, health_score, status, cooldown_until}
        """
        snapshot: dict[str, dict[str, object]] = {}
        for key in self._keys:
            fp = hashlib.sha256(key.value.encode()).hexdigest()[:16]
            key_id = f"{self.deployment}:{fp}"
            cooldown: Optional[str] = None
            if key.cooldown_until is not None:
                from datetime import datetime, timedelta, timezone
                remaining = key.cooldown_until - self._clock()
                if remaining > 0:
                    cooldown = (
                        datetime.now(timezone.utc) + timedelta(seconds=remaining)
                    ).isoformat()
            snapshot[key_id] = {
                "error_count": key.error_count,
                "success_count": key.success_count,
                "health_score": round(key.health_score, 4),
                "avg_latency_ms": round(key.avg_latency_ms, 1),
                "status": key.status,
                "cooldown_until": cooldown,
            }
        return snapshot

    # ── internal ────────────────────────────────────────────────────

    def _advance_cooldowns(self) -> None:
        now = self._clock()
        for key in self._keys:
            if (
                key.status == "cooldown"
                and key.cooldown_until is not None
                and key.cooldown_until <= now
            ):
                key.status = "active"
                key.cooldown_until = None

    def _apply_failure(self, key: Key, failure: FailureType, cooldown_seconds: float) -> None:
        if failure == "key_revoked":
            key.status = "dead"
            key.cooldown_until = None
        elif failure in ("rate_limited", "key_quota_exhausted", "unhandled_error"):
            key.status = "cooldown"
            key.cooldown_until = self._clock() + max(cooldown_seconds, 1.0)

    def _maybe_persist(
        self, key_value: str, status: str, cooldown_str: Optional[str]
    ) -> None:
        if self._persist_callback is None:
            return
        try:
            self._persist_callback(key_value, status, cooldown_str)
        except Exception:
            logger.warning(
                "persist_callback failed for key %s (status=%s)",
                key_value[:12] + "...", status, exc_info=True,
            )

    def _maybe_persist_budget(self, key: Key) -> None:
        """Persist rate limit budgets to DB (called on every release with token usage).

        Sliding windows are ephemeral (60s). Persisting on every call keeps
        the DB budget state as close to in-memory state as possible.
        On recovery, budgets older than 60s are reset to zero.
        """
        if self._budget_persist_callback is None:
            return

        self._requests_since_persist += 1

        # Persist on every request with tokens, or every 10th without
        if (
            self._requests_since_persist % 10 == 0
            or (key.token_budget is not None and key.token_budget.current_usage() > 0)
        ):
            token_used = key.token_budget.current_usage() if key.token_budget else 0
            token_max = key.token_budget.max_tokens if key.token_budget else 1_000_000
            req_used = key.request_budget.current_usage() if key.request_budget else 0
            req_max = key.request_budget.max_requests if key.request_budget else 500

            try:
                self._budget_persist_callback(
                    key.value, key.deployment,
                    token_used, token_max, req_used, req_max,
                )
            except Exception:
                logger.warning(
                    "budget_persist_callback failed for key %s",
                    key.value[:12] + "...", exc_info=True,
                )


# ─── Key scoring (v2.1) ──────────────────────────────────────────────

def _score_key(key: Key) -> float:
    """Score a key for smart selection. Higher = better.

    Ranking: health (dominant, includes error rate) > token budget > request budget.
    Note: prefer_streaming is only honored via CapabilityMatrix (model-aware routing).
    """
    health = key.health_score * 10.0  # 0..10 (includes error_rate penalty with x50 weight)
    token_budget = key.token_remaining_ratio() * 3.0  # 0..3
    request_budget = key.request_remaining_ratio() * 2.0  # 0..2
    return health + token_budget + request_budget


def _find_key(keys: tuple[Key, ...], value: str) -> Key | None:
    for key in keys:
        if key.value == value:
            return key
    return None


def _monotonic_float() -> float:
    return time.monotonic()
