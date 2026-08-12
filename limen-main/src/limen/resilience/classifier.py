"""Typed failure classification for LIMEN dispatch and adapters.

``ProviderFailure`` is the single concrete error type adapters and the
dispatcher share. ``classify_http_failure`` folds an upstream HTTP outcome
into that type, while ``encode_failure_payload`` produces a redacted
observation suitable for the audit trail. No exceptions are swallowed
here; classification either returns a typed error or propagates input
problems.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from collections.abc import Mapping

FailureType = Literal[
    "rate_limited",
    "provider_unreachable",
    "key_quota_exhausted",
    "key_revoked",
    "request_invalid",
    "request_too_large",
    "unhandled_error",
]

FAILURE_TYPES: Final[tuple[FailureType, ...]] = (
    "rate_limited",
    "provider_unreachable",
    "key_quota_exhausted",
    "key_revoked",
    "request_invalid",
    "request_too_large",
    "unhandled_error",
)


@dataclass(frozen=True)
class ProviderFailure(Exception):  # noqa: N818 — Intentional short name for an internal value+error type.
    """Concrete provider-facing failure with retry hints."""

    failure_type: FailureType
    message: str
    http_code: int | None
    retry_after_seconds: float | None = None
    raw_body: str | None = None

    def __post_init__(self) -> None:
        if self.failure_type not in FAILURE_TYPES:
            raise ValueError(f"unknown failure type: {self.failure_type}")

    @property
    def is_retryable(self) -> bool:
        return self.failure_type in (
            "rate_limited",
            "provider_unreachable",
            "unhandled_error",
        )


def parse_retry_after(header_value: str | None) -> float | None:
    """Convert a Retry-After header value to a positive number of seconds."""
    if header_value is None:
        return None
    text = header_value.strip()
    if not text:
        return None
    try:
        seconds = float(text)
    except ValueError:
        return None
    return seconds if seconds > 0 else None


def classify_http_failure(
    status: int,
    body: bytes | str | None = None,
    headers: Mapping[str, str] | None = None,
) -> ProviderFailure:
    """Map a provider HTTP error into the typed failure vocabulary.

    Body keywords are conservative. Unknown bodies fall back to a
    transport-level failure so the dispatcher never accidentally treats a
    real 5xx as a client error and skips retry.
    """
    text = _normalize_body(body)
    if status == 429:
        retry_after = parse_retry_after((headers or {}).get("retry-after"))
        # Sub-classify 429 using rate_limiter intelligence
        try:
            from limen.resilience.rate_limiter import classify_429 as _classify_429
            detail = _classify_429(body=text, headers=dict(headers) if headers else None, status=status)
            message = f"rate_limited [{detail.limit_type.value}]: {detail.details}"
            cooldown = detail.cooldown_seconds if retry_after is None else retry_after
        except ImportError:
            message = text or "provider returned 429"
            cooldown = retry_after
        return ProviderFailure(
            failure_type="rate_limited",
            message=message,
            http_code=status,
            retry_after_seconds=cooldown,
            raw_body=text,
        )
    if status in (401, 403):
        return ProviderFailure(
            failure_type="key_revoked",
            message=text or f"provider returned {status}",
            http_code=status,
            raw_body=text,
        )
    if status == 402 or _contains_any(
        text, ("quota", "billing", "insufficient_quota", "payment")
    ):
        return ProviderFailure(
            failure_type="key_quota_exhausted",
            message=text or "provider reports quota/billing",
            http_code=status,
            raw_body=text,
        )
    if status == 413 or _contains_any(
        text, ("context length", "too large", "maximum context")
    ):
        return ProviderFailure(
            failure_type="request_too_large",
            message=text or "provider reports request too large",
            http_code=status,
            raw_body=text,
        )
    if status in (408, 425) or status >= 500:
        return ProviderFailure(
            failure_type="provider_unreachable",
            message=text or f"provider transport failure ({status})",
            http_code=status,
            raw_body=text,
        )
    if 400 <= status < 500:
        return ProviderFailure(
            failure_type="request_invalid",
            message=text or f"provider rejected request ({status})",
            http_code=status,
            raw_body=text,
        )
    return ProviderFailure(
        failure_type="unhandled_error",
        message=text or f"unexpected provider status {status}",
        http_code=status,
        raw_body=text,
    )


def _normalize_body(body: bytes | str | None) -> str:
    if body is None:
        return ""
    if isinstance(body, bytes):
        try:
            return body.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            return ""
    return body


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    if not haystack:
        return False
    lower = haystack.lower()
    return any(needle.lower() in lower for needle in needles)


def encode_failure_payload(failure: ProviderFailure) -> dict[str, object]:
    """Redact a failure into a JSON-safe dict suitable for Audit events."""
    body_preview = failure.raw_body or ""
    truncated = body_preview[:512]
    try:
        decoded = json.loads(body_preview)
        truncated_preview = _safe_preview(decoded)
    except (ValueError, TypeError):
        truncated_preview = truncated
    return {
        "failure_type": failure.failure_type,
        "message": failure.message,
        "http_code": failure.http_code,
        "retry_after_seconds": failure.retry_after_seconds,
        "body_preview": truncated_preview,
    }


def _safe_preview(value: object, *, depth: int = 0) -> object:
    if depth > 3:
        return "..."
    if isinstance(value, dict):
        return {
            str(key): _safe_preview(item, depth=depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_safe_preview(item, depth=depth + 1) for item in value[:8]]
    return value
