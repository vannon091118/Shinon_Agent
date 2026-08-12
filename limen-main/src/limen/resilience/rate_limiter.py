"""
LIMEN 429 Intelligence — Rate Limit Detection & Cooldown

Classifies 429 responses into TPM / RPD / RPM / MONTHLY / CONCURRENT.
Computes precise cooldowns from Retry-After headers and body inspection.
Tracks token budgets with sliding windows for proactive rate limit avoidance.

Contract: limen.contract.json § intelligence
Spec: 5 rate limit types with distinct detection and cooldown strategies.
"""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple


class RateLimitType(str, Enum):
    """The 5 rate limit types from limen.contract.json."""

    TPM = "tpm"            # Tokens Per Minute
    RPD = "rpd"            # Requests Per Day
    RPM = "rpm"            # Requests Per Minute
    MONTHLY = "monthly"    # Monthly quota exceeded
    CONCURRENT = "concurrent"  # Concurrent request limit
    UNKNOWN = "unknown"    # Unclassified 429


@dataclass
class RateLimitInfo:
    """Result of 429 classification with cooldown and strategy."""

    limit_type: RateLimitType
    cooldown_seconds: float
    retry_after: Optional[float] = None
    strategy: str = ""
    details: str = ""
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class TokenBudget:
    """Track token usage in a sliding window for one key."""

    window_seconds: float = 60.0
    max_tokens: int = 1_000_000
    _events: deque = field(default_factory=deque)

    def record(self, tokens: int, *, now: Optional[float] = None) -> None:
        now = now if now is not None else time.monotonic()
        self._events.append((now, tokens))
        self._purge(now)

    def current_usage(self, *, now: Optional[float] = None) -> int:
        now = now if now is not None else time.monotonic()
        self._purge(now)
        return sum(tokens for _, tokens in self._events)

    def remaining(self, *, now: Optional[float] = None) -> int:
        return max(0, self.max_tokens - self.current_usage(now=now))

    def is_exhausted(self, *, now: Optional[float] = None) -> bool:
        return self.remaining(now=now) <= 0

    def ratio(self, *, now: Optional[float] = None) -> float:
        used = self.current_usage(now=now)
        return used / self.max_tokens if self.max_tokens > 0 else 1.0

    def _purge(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()


@dataclass
class RequestBudget:
    """Track request counts in a sliding window."""

    window_seconds: float = 60.0
    max_requests: int = 500
    _events: deque = field(default_factory=deque)

    def record(self, *, now: Optional[float] = None) -> None:
        now = now if now is not None else time.monotonic()
        self._events.append(now)
        self._purge(now)

    def current_usage(self, *, now: Optional[float] = None) -> int:
        now = now if now is not None else time.monotonic()
        self._purge(now)
        return len(self._events)

    def remaining(self, *, now: Optional[float] = None) -> int:
        return max(0, self.max_requests - self.current_usage(now=now))

    def is_exhausted(self, *, now: Optional[float] = None) -> bool:
        return self.remaining(now=now) <= 0

    def _purge(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._events and self._events[0] < cutoff:
            self._events.popleft()


# ─── 429 Classification ──────────────────────────────────────────────


# Patterns for body-based classification
_BODY_PATTERNS: Dict[RateLimitType, List[str]] = {
    RateLimitType.TPM: [
        "tokens per minute", "tpm", "token rate limit",
        "tokens_per_min", "rate limit reached.*tokens",
    ],
    RateLimitType.RPD: [
        "requests per day", "rpd", "daily limit",
        "requests per 24", "per day",
    ],
    RateLimitType.RPM: [
        "requests per minute", "rpm", "rate limit.*requests",
        "too many requests", "request limit",
    ],
    RateLimitType.MONTHLY: [
        "quota exceeded", "billing", "monthly limit",
        "insufficient_quota", "payment required",
        "upgrade your plan",
    ],
    RateLimitType.CONCURRENT: [
        "concurrent", "parallel", "simultaneous",
        "too many connections",
    ],
}

# Header-based detection
_HEADER_PATTERNS: Dict[RateLimitType, List[str]] = {
    RateLimitType.TPM: [
        "x-ratelimit-reset-tokens", "x-ratelimit-remaining-tokens",
    ],
    RateLimitType.RPD: [
        "x-ratelimit-reset-requests", "x-ratelimit-limit-requests",
    ],
    RateLimitType.RPM: [
        "x-ratelimit-limit-requests",
    ],
}


def classify_429(
    body: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    status: int = 429,
) -> RateLimitInfo:
    """Classify a 429 response into one of the 5 rate limit types.

    Priority: headers > body keywords > heuristics.
    Computes cooldown from Retry-After or type-specific defaults.

    Args:
        body: Response body text (lowercased for matching).
        headers: Response headers dict (case-insensitive keys).
        status: HTTP status code (default 429).

    Returns:
        RateLimitInfo with type, cooldown, and strategy.
    """
    headers_lower: Dict[str, str] = {}
    if headers:
        headers_lower = {k.lower(): v for k, v in headers.items()}

    body_lower = (body or "").lower()

    # Extract Retry-After (highest priority)
    retry_after = _parse_retry_after(headers_lower.get("retry-after"))

    # ── Header-based detection (strong signal) ──
    for limit_type, header_names in _HEADER_PATTERNS.items():
        for name in header_names:
            if name in headers_lower:
                cooldown = _cooldown_for(limit_type, retry_after)
                return RateLimitInfo(
                    limit_type=limit_type,
                    cooldown_seconds=cooldown,
                    retry_after=retry_after,
                    strategy=_strategy_for(limit_type),
                    details=f"detected via header {name}",
                    headers=headers or {},
                )

    # ── Body-keyword detection ──
    scores: List[Tuple[RateLimitType, int]] = []
    for limit_type, patterns in _BODY_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, body_lower))
        if score > 0:
            scores.append((limit_type, score))

    if scores:
        scores.sort(key=lambda x: -x[1])
        best_type, _ = scores[0]
        cooldown = _cooldown_for(best_type, retry_after)
        return RateLimitInfo(
            limit_type=best_type,
            cooldown_seconds=cooldown,
            retry_after=retry_after,
            strategy=_strategy_for(best_type),
            details=f"body matched: {best_type.value}",
            headers=headers or {},
        )

    # ── Fallback: generic 429 with RPM behavior ──
    cooldown = retry_after if retry_after else 60.0
    return RateLimitInfo(
        limit_type=RateLimitType.UNKNOWN,
        cooldown_seconds=cooldown,
        retry_after=retry_after,
        strategy="rotate key, short wait",
        details="unclassified 429 — treating as generic rate limit",
        headers=headers or {},
    )


def _cooldown_for(limit_type: RateLimitType, retry_after: Optional[float]) -> float:
    """Compute cooldown duration for a rate limit type."""
    if retry_after is not None and retry_after > 0:
        return retry_after

    defaults = {
        RateLimitType.TPM: _seconds_until_next_minute(),
        RateLimitType.RPD: _seconds_until_next_utc_day(),
        RateLimitType.RPM: 60.0,
        RateLimitType.MONTHLY: _seconds_until_next_month(),
        RateLimitType.CONCURRENT: 1.0,  # start with 1s, exponential backoff
        RateLimitType.UNKNOWN: 60.0,
    }
    return defaults.get(limit_type, 60.0)


def _strategy_for(limit_type: RateLimitType) -> str:
    strategies = {
        RateLimitType.TPM: "rotate to next key with TPM budget remaining",
        RateLimitType.RPD: "rotate key, queue if all exhausted",
        RateLimitType.RPM: "rotate key, short wait",
        RateLimitType.MONTHLY: "mark key exhausted, alert",
        RateLimitType.CONCURRENT: "retry with backoff on same key (1s→2s→4s→8s max 30s)",
        RateLimitType.UNKNOWN: "rotate key, generic cooldown",
    }
    return strategies.get(limit_type, "unknown strategy")


def _parse_retry_after(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    try:
        return float(raw.strip())
    except ValueError:
        return None


def _seconds_until_next_minute() -> float:
    now = datetime.now(timezone.utc)
    next_minute = now.replace(second=0, microsecond=0)
    if next_minute <= now:
        from datetime import timedelta
        next_minute += timedelta(minutes=1)
    return (next_minute - now).total_seconds()


def _seconds_until_next_utc_day() -> float:
    now = datetime.now(timezone.utc)
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    tomorrow += timedelta(days=1)
    return (tomorrow - now).total_seconds()


def _seconds_until_next_month() -> float:
    now = datetime.now(timezone.utc)
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1)
    else:
        next_month = now.replace(month=now.month + 1, day=1)
    next_month = next_month.replace(hour=0, minute=0, second=0, microsecond=0)
    return (next_month - now).total_seconds()


# ─── Proactive Rate Limit Avoidance ──────────────────────────────────


class RateLimitTracker:
    """Track token and request budgets per deployment key.

    Used BEFORE making API calls to avoid hitting rate limits.
    After each call, record token usage and check remaining budgets.
    """

    def __init__(self):
        self._token_budgets: Dict[str, TokenBudget] = {}
        self._request_budgets: Dict[str, RequestBudget] = {}

    def get_or_create_token_budget(
        self, key_id: str, *, max_tokens: int = 1_000_000, window_seconds: float = 60.0
    ) -> TokenBudget:
        if key_id not in self._token_budgets:
            self._token_budgets[key_id] = TokenBudget(
                max_tokens=max_tokens, window_seconds=window_seconds
            )
        return self._token_budgets[key_id]

    def get_or_create_request_budget(
        self, key_id: str, *, max_requests: int = 500, window_seconds: float = 60.0
    ) -> RequestBudget:
        if key_id not in self._request_budgets:
            self._request_budgets[key_id] = RequestBudget(
                max_requests=max_requests, window_seconds=window_seconds
            )
        return self._request_budgets[key_id]

    def record_tokens(self, key_id: str, tokens: int) -> None:
        budget = self.get_or_create_token_budget(key_id)
        budget.record(tokens)

    def record_request(self, key_id: str) -> None:
        budget = self.get_or_create_request_budget(key_id)
        budget.record()

    def can_send(self, key_id: str, estimated_tokens: int = 0) -> bool:
        """Check if a key has budget remaining."""
        if key_id in self._token_budgets and estimated_tokens > 0:
            return self._token_budgets[key_id].remaining() >= estimated_tokens
        if key_id in self._request_budgets:
            return not self._request_budgets[key_id].is_exhausted()
        return True  # no budget tracked = assume OK

    def stats(self, key_id: str) -> Dict[str, int]:
        """Return current usage stats for a key."""
        result: Dict[str, int] = {}
        if key_id in self._token_budgets:
            tb = self._token_budgets[key_id]
            result["tokens_used"] = tb.current_usage()
            result["tokens_remaining"] = tb.remaining()
        if key_id in self._request_budgets:
            rb = self._request_budgets[key_id]
            result["requests_used"] = rb.current_usage()
            result["requests_remaining"] = rb.remaining()
        return result
