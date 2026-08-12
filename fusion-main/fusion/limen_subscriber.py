"""
LIMEN Subscriber — EventBus bridge for LIMEN rate-limit and key-state events

Bridges LIMEN's internal rate-limit/key-pool state to the Control Plane
EventBus. When LIMEN hits a 429, exhausts a key pool, or detects budget
warnings, events are published so goal-chain can trigger mitigation TIDs.

Architecture:
    LIMEN pipeline.py (run_pipeline)
        │  _emit() / write_event() callback
        ▼
    LIMENSubscriber (this module)
        │  classify → enrich → publish
        ▼
    EventBus:
      ├── limen.rate_limited    (429 hit → TPM/RPD/RPM/MONTHLY/CONCURRENT)
      ├── limen.key_cooldown    (key entered cooldown)
      ├── limen.key_exhausted   (all keys for deployment dead/cooldown)
      ├── limen.budget_warning  (token/request budget >80% used)
      ├── limen.key_recovered   (key returned from cooldown)
      └── limen.api_error       (non-429 API errors)

Position: 4 (infrastructure layer, between KARMA and goal-chain)
Subscribes to: N/A (publishes only — driven by LIMEN pipeline)
Publishes: limen.* events

WIRING.md: LIMEN sits between goal-chain and the external API providers.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fusion.event_bus import (
    AsyncEventBus,
    Event,
    EVENT_LIMEN_RATE_LIMITED,
    EVENT_LIMEN_KEY_COOLDOWN,
    EVENT_LIMEN_KEY_EXHAUSTED,
    EVENT_LIMEN_BUDGET_WARNING,
    EVENT_LIMEN_KEY_RECOVERED,
    EVENT_LIMEN_API_ERROR,
)

logger = logging.getLogger(__name__)

# ─── Budget Thresholds ────────────────────────────────────────────────

BUDGET_WARNING_RATIO = 0.80   # Warn when 80%+ of budget is consumed
BUDGET_CRITICAL_RATIO = 0.95  # Critical when 95%+ consumed


# ─── Data Classes ─────────────────────────────────────────────────────


@dataclass
class RateLimitEvent:
    """A rate-limit event with full 429 classification."""

    limit_type: str           # tpm | rpd | rpm | monthly | concurrent | unknown
    cooldown_seconds: float
    deployment: str
    provider: str
    key_id_redacted: str = ""
    retry_after: Optional[float] = None
    strategy: str = ""
    details: str = ""
    correlation_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "limit_type": self.limit_type,
            "cooldown_seconds": self.cooldown_seconds,
            "deployment": self.deployment,
            "provider": self.provider,
            "key_id_redacted": self.key_id_redacted,
            "retry_after": self.retry_after,
            "strategy": self.strategy,
            "details": self.details,
        }


@dataclass
class KeyStateEvent:
    """A key entering cooldown or recovering."""

    event_type: str           # cooldown | recovered | exhausted | dead
    deployment: str
    provider: str
    key_id_redacted: str = ""
    failure_type: str = ""    # rate_limited | key_quota_exhausted | key_revoked | ...
    cooldown_until: Optional[str] = None
    active_count: int = 0
    cooldown_count: int = 0
    dead_count: int = 0
    correlation_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "deployment": self.deployment,
            "provider": self.provider,
            "key_id_redacted": self.key_id_redacted,
            "failure_type": self.failure_type,
            "cooldown_until": self.cooldown_until,
            "active_count": self.active_count,
            "cooldown_count": self.cooldown_count,
            "dead_count": self.dead_count,
        }


@dataclass
class BudgetWarning:
    """A token/request budget warning."""

    deployment: str
    provider: str
    key_id_redacted: str = ""
    budget_type: str = ""     # token | request
    used: int = 0
    max_budget: int = 0
    ratio: float = 0.0
    severity: str = "warning"  # warning | critical
    correlation_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deployment": self.deployment,
            "provider": self.provider,
            "key_id_redacted": self.key_id_redacted,
            "budget_type": self.budget_type,
            "used": self.used,
            "max_budget": self.max_budget,
            "ratio": round(self.ratio, 3),
            "severity": self.severity,
        }


# ─── LIMEN Subscriber ─────────────────────────────────────────────────


class LIMENSubscriber:
    """Bridges LIMEN pipeline events to the Control Plane EventBus.

    Provides callback functions compatible with LIMEN's ``run_pipeline``
    ``write_event`` and ``ui_event`` parameters. These callbacks publish
    structured events to the EventBus that goal-chain can react to.

    Modes:
      - ``mode=\"eventbus\"``: Publish to EventBus (default, for production).
      - ``mode=\"passthrough\"``: Log only, no publishing (for testing).

    Usage:
        limen_bridge = LIMENSubscriber(bus)
        limen_bridge.wire(bus)

        # Then pass limen_bridge.write_event as LIMEN's event callback:
        await run_pipeline(request, candidates, http_client,
                          write_event=limen_bridge.write_event,
                          ui_event=limen_bridge.ui_event)
    """

    def __init__(
        self,
        bus: Optional[AsyncEventBus] = None,
        *,
        mode: str = "eventbus",
        budget_warning_ratio: float = BUDGET_WARNING_RATIO,
        budget_critical_ratio: float = BUDGET_CRITICAL_RATIO,
    ):
        self.bus = bus
        self._mode = mode
        self._budget_warning_ratio = budget_warning_ratio
        self._budget_critical_ratio = budget_critical_ratio

        # Cooldown tracking (key_id_redacted → cooldown_count)
        self._cooldowns: Dict[str, int] = {}

        # Budget tracking per deployment (deployment → {tokens_used, requests_used})
        self._budgets: Dict[str, Dict[str, int]] = {}

        # Stats
        self._events_published: int = 0
        self._rate_limits_detected: int = 0
        self._key_cooldowns: int = 0
        self._key_exhaustions: int = 0

    def wire(self, bus: Optional[AsyncEventBus] = None) -> None:
        """Register LIMEN events with the EventBus (no subscriptions needed)."""
        b = bus or self.bus
        if b is None:
            logger.warning("LIMENSubscriber: no EventBus available — events will be logged only")
            return
        self.bus = b
        logger.info("LIMENSubscriber wired to EventBus (mode=%s)", self._mode)

    # ── LIMEN Pipeline Callbacks ──────────────────────────────────────

    def write_event(self, event_type: str, payload: Dict[str, object]) -> None:
        """Callback for LIMEN's ``write_event`` parameter.

        Receives raw pipeline events (key.claimed, key.released,
        key.cooldown_set, key.dead, etc.) and publishes structured
        events to the EventBus.

        Args:
            event_type: LIMEN event type string (key.claimed, key.released, ...).
            payload: Event payload dict from LIMEN pipeline.
        """
        if event_type == "key.claimed":
            self._on_key_claimed(payload)
        elif event_type == "key.released":
            self._on_key_released(payload)
        elif event_type == "key.cooldown_set":
            self._on_key_cooldown_set(payload)
        elif event_type == "key.dead":
            self._on_key_dead(payload)
        else:
            logger.debug("LIMEN event (unhandled): %s", event_type)

    def ui_event(self, *args: Any, **kwargs: Any) -> None:
        """Callback for LIMEN's ``ui_event`` parameter.

        Handles UI-oriented events like provider.rate_limited and
        provider.dispatched.
        """
        event_type = args[0] if args else kwargs.get("event_type", "")

        if event_type == "provider.rate_limited":
            self._on_provider_rate_limited(kwargs)
        elif event_type == "provider.dispatched":
            self._on_provider_dispatched(kwargs)
        else:
            logger.debug("LIMEN ui_event (unhandled): %s", event_type)

    # ── Event Handlers ────────────────────────────────────────────────

    def _on_key_claimed(self, payload: Dict[str, object]) -> None:
        """Key claimed — reset cooldown counter if recovering."""
        key_id = str(payload.get("key_id", ""))
        if key_id in self._cooldowns:
            self._cooldowns.pop(key_id, None)
            self._publish_key_recovered(payload)

    def _on_key_released(self, payload: Dict[str, object]) -> None:
        """Key released — check if it was a failure release."""
        failure_type = str(payload.get("failure_type", "success"))
        if failure_type == "success":
            return
        # Non-success releases are handled by key.cooldown_set / key.dead

    def _on_key_cooldown_set(self, payload: Dict[str, object]) -> None:
        """Key entered cooldown — publish rate limit event."""
        deployment = str(payload.get("deployment", "unknown"))
        provider = str(payload.get("provider", deployment))
        key_id = str(payload.get("key_id", ""))
        reason = str(payload.get("reason", "rate_limited"))
        until = str(payload.get("until", ""))

        self._key_cooldowns += 1
        self._cooldowns[key_id] = self._cooldowns.get(key_id, 0) + 1

        # Track repeated cooldowns (key may be unreliable)
        repeat_cooldown = self._cooldowns.get(key_id, 1) >= 3

        # Determine limit type from reason
        limit_type = self._reason_to_limit_type(reason)

        # Publish rate_limited event
        rate_event = RateLimitEvent(
            limit_type=limit_type,
            cooldown_seconds=float(until) if until.replace(".", "").isdigit() else 60.0,
            deployment=deployment,
            provider=provider,
            key_id_redacted=key_id,
            retry_after=float(until) if until.replace(".", "").isdigit() else None,
            strategy=f"cooldown set by pipeline: {reason}" + (
                " (REPEAT: key may be unreliable)" if repeat_cooldown else ""
            ),
            details=f"Key {key_id} in cooldown until {until}. Reason: {reason}. "
                     f"Repeat cooldowns: {self._cooldowns.get(key_id, 1)}.",
        )
        self._publish(EVENT_LIMEN_RATE_LIMITED, rate_event.to_dict())

        # Also publish key_cooldown event
        key_event = KeyStateEvent(
            event_type="cooldown",
            deployment=deployment,
            provider=provider,
            key_id_redacted=key_id,
            failure_type=reason,
            cooldown_until=until if until else None,
        )
        self._publish(EVENT_LIMEN_KEY_COOLDOWN, key_event.to_dict())

        self._rate_limits_detected += 1

    def _on_key_dead(self, payload: Dict[str, object]) -> None:
        """Key marked dead — publish api_error event."""
        deployment = str(payload.get("deployment", "unknown"))
        provider = str(payload.get("provider", deployment))
        key_id = str(payload.get("key_id", ""))
        reason = str(payload.get("reason", "key_revoked"))

        key_event = KeyStateEvent(
            event_type="dead",
            deployment=deployment,
            provider=provider,
            key_id_redacted=key_id,
            failure_type=reason,
            active_count=0,
            cooldown_count=0,
            dead_count=1,
        )
        self._publish(EVENT_LIMEN_API_ERROR, {
            "error_type": "key_dead",
            **key_event.to_dict(),
        })

    def _on_provider_rate_limited(self, kwargs: Dict[str, Any]) -> None:
        """Provider hit 429 — publish detailed rate-limit event."""
        deployment = str(kwargs.get("deployment", "unknown"))
        provider = str(kwargs.get("provider", deployment))
        retry_after = kwargs.get("retry_after", 60)

        rate_event = RateLimitEvent(
            limit_type="unknown",  # Will be refined by classify_429
            cooldown_seconds=float(retry_after) if isinstance(retry_after, (int, float)) else 60.0,
            deployment=deployment,
            provider=provider,
            retry_after=float(retry_after) if isinstance(retry_after, (int, float)) else None,
            strategy="rotate to next available key",
            details=f"Provider {provider}/{deployment} returned 429. Retry-After: {retry_after}s",
        )
        self._publish(EVENT_LIMEN_RATE_LIMITED, rate_event.to_dict())
        self._rate_limits_detected += 1

    def _on_provider_dispatched(self, kwargs: Dict[str, Any]) -> None:
        """Provider dispatched — track budget usage."""
        deployment = str(kwargs.get("deployment", "unknown"))
        provider = str(kwargs.get("provider", deployment))
        key_index = int(kwargs.get("key_index", 0))

        if deployment not in self._budgets:
            self._budgets[deployment] = {"tokens_used": 0, "requests_used": 0}
        self._budgets[deployment]["requests_used"] += 1

        # Check budget thresholds
        self._check_budget(deployment, provider)

    # ── Public API ────────────────────────────────────────────────────

    def notify_key_exhausted(
        self,
        deployment: str,
        provider: str = "",
        *,
        active: int = 0,
        cooldown: int = 0,
        dead: int = 0,
        correlation_id: str = "",
    ) -> None:
        """Notify that all keys in a deployment are exhausted.

        Call this when ``KeyPool.claim()`` returns None (pool empty).
        Publishes ``limen.key_exhausted`` with CRITICAL priority.
        """
        self._key_exhaustions += 1

        key_event = KeyStateEvent(
            event_type="exhausted",
            deployment=deployment,
            provider=provider or deployment,
            active_count=active,
            cooldown_count=cooldown,
            dead_count=dead,
            correlation_id=correlation_id,
        )
        self._publish(EVENT_LIMEN_KEY_EXHAUSTED, {
            **key_event.to_dict(),
            "severity": "critical",
            "message": (
                f"ALL keys exhausted for {deployment}/{provider}: "
                f"active={active} cooldown={cooldown} dead={dead}. "
                f"External intervention required."
            ),
        })

    def notify_budget_warning(
        self,
        deployment: str,
        provider: str = "",
        *,
        key_id_redacted: str = "",
        budget_type: str = "",
        used: int = 0,
        max_budget: int = 0,
        correlation_id: str = "",
    ) -> None:
        """Notify that a token or request budget is near exhaustion.

        Publishes ``limen.budget_warning`` for proactive rate limit avoidance.
        """
        ratio = used / max_budget if max_budget > 0 else 1.0
        severity = "critical" if ratio >= self._budget_critical_ratio else "warning"

        warning = BudgetWarning(
            deployment=deployment,
            provider=provider or deployment,
            key_id_redacted=key_id_redacted,
            budget_type=budget_type,
            used=used,
            max_budget=max_budget,
            ratio=ratio,
            severity=severity,
            correlation_id=correlation_id,
        )
        self._publish(EVENT_LIMEN_BUDGET_WARNING, warning.to_dict())

    def record_token_usage(
        self, deployment: str, tokens: int, *, max_tokens: int = 1_000_000
    ) -> None:
        """Record token usage for budget tracking."""
        if deployment not in self._budgets:
            self._budgets[deployment] = {"tokens_used": 0, "requests_used": 0}
        self._budgets[deployment]["tokens_used"] += tokens
        self._check_budget(deployment, "", max_tokens=max_tokens)

    # ── Internal ──────────────────────────────────────────────────────

    def _reason_to_limit_type(self, reason: str) -> str:
        """Map a pipeline failure reason to a rate limit type."""
        reason_lower = reason.lower()
        if "quota" in reason_lower or "monthly" in reason_lower:
            return "monthly"
        if "rpd" in reason_lower or "daily" in reason_lower:
            return "rpd"
        if "tpm" in reason_lower or "token" in reason_lower:
            return "tpm"
        if "rpm" in reason_lower or "request" in reason_lower:
            return "rpm"
        if "concurrent" in reason_lower:
            return "concurrent"
        if "rate" in reason_lower:
            return "rpm"  # Generic "rate_limited" → RPM (most common default)
        return "unknown"

    def _check_budget(
        self, deployment: str, provider: str, *, max_tokens: int = 1_000_000
    ) -> None:
        """Check budget thresholds and publish warnings if needed."""
        budget = self._budgets.get(deployment, {})
        tokens_used = budget.get("tokens_used", 0)
        requests_used = budget.get("requests_used", 0)

        # Token budget check
        token_ratio = tokens_used / max_tokens if max_tokens > 0 else 0
        if token_ratio >= self._budget_warning_ratio:
            self.notify_budget_warning(
                deployment=deployment,
                provider=provider,
                budget_type="token",
                used=tokens_used,
                max_budget=max_tokens,
            )

        # Request budget check (max 500/minute per key)
        request_ratio = requests_used / 500
        if request_ratio >= self._budget_warning_ratio:
            self.notify_budget_warning(
                deployment=deployment,
                provider=provider,
                budget_type="request",
                used=requests_used,
                max_budget=500,
            )

    def _publish_key_recovered(self, payload: Dict[str, object]) -> None:
        """Publish key.recovered event."""
        deployment = str(payload.get("deployment", "unknown"))
        provider = str(payload.get("provider", deployment))
        key_id = str(payload.get("key_id", ""))

        key_event = KeyStateEvent(
            event_type="recovered",
            deployment=deployment,
            provider=provider,
            key_id_redacted=key_id,
        )
        self._publish(EVENT_LIMEN_KEY_RECOVERED, key_event.to_dict())

    def _publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish to EventBus or log depending on mode."""
        self._events_published += 1

        if self._mode == "eventbus" and self.bus is not None:
            try:
                # Fire-and-forget to avoid blocking LIMEN's hot path
                self.bus.publish_fire_and_forget(Event(
                    event_type=event_type,
                    source="limen",
                    payload=payload,
                ))
                logger.debug("LIMEN → EventBus: %s (total: %d)", event_type, self._events_published)
            except Exception:
                logger.exception("LIMENSubscriber: failed to publish %s", event_type)
        else:
            logger.info(
                "LIMEN [%s]: %s",
                event_type,
                {k: v for k, v in payload.items() if k != "key_id_redacted"} if payload else {},
            )

    # ── Stats ─────────────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "events_published": self._events_published,
            "rate_limits_detected": self._rate_limits_detected,
            "key_cooldowns": self._key_cooldowns,
            "key_exhaustions": self._key_exhaustions,
            "deployments_tracked": len(self._budgets),
        }
