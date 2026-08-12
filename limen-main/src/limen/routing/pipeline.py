"""FallbackPipeline: deployment/key traversal with cooldown and retry budget.

Walks candidates from ``ProviderRegistry.resolve()`` in priority order.
For each candidate it claims keys from the ``KeyPool``. Retryable
failures (rate_limited, key_quota_exhausted) may fall through to the
next key; provider_unreachable skips to the next deployment. Non-
retryable failures (request_invalid, request_too_large, key_revoked)
stop immediately or — if more keys exist — try the next key for
key_revoked.
"""

from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from limen.adapters.base import AdapterRequestError
from limen.resilience import ProviderFailure

if TYPE_CHECKING:
    from collections.abc import Callable

    import httpx

    from limen.routing.registry import ProviderDeployment
    from limen.schemas import ChatCompletionRequest


class PipelineExhausted(ProviderFailure):
    """Raised when all deployments and keys have been tried without success."""

    def __init__(self, attempts: int, last: ProviderFailure | None = None) -> None:
        msg = f"all {attempts} attempts exhausted"
        if last is not None:
            msg += f"; last failure: {last.failure_type}: {last.message}"
        super().__init__(
            failure_type=last.failure_type if last else "provider_unreachable",
            message=msg,
            http_code=last.http_code if last else None,
        )
        self.attempts = attempts


async def run_pipeline(
    request: ChatCompletionRequest,
    candidates: list[ProviderDeployment],
    http_client: httpx.AsyncClient,
    *,
    max_attempts: int = 10,
    backoff_floor: float = 1.0,
    write_event: Callable[[str, dict[str, object]], None] | None = None,
    ui_event: Callable[..., None] | None = None,
    stream: bool = False,
    persist_key_state: Callable[..., None] | None = None,
) -> dict[str, Any] | tuple[str, Any, str, str, int, str]:
    """Walk candidates and their key pools until a response is produced.

    Non-streaming (default):
      Returns ``{"response": ProviderCallResult, "deployment": ...,
      "provider": ..., "attempts": ...}``.

    Streaming (``stream=True``):
      Returns ``(content_type, byte_iter, deployment, provider,
      attempts, key_value)``. The caller owns the key release and audit
      writes so they happen *after* the stream closes.
    """
    total_attempts = 0
    last_failure: ProviderFailure | None = None

    for deployment in candidates:
        while total_attempts < max_attempts:
            key_value = await deployment.pool.claim()
            if key_value is None:
                break  # pool exhausted → next deployment

            total_attempts += 1
            _emit(
                write_event,
                "key.claimed",
                {
                    "deployment": deployment.deployment,
                    "key_id": _redact_key(key_value),
                    "account_id": deployment.account_id,
                },
            )
            if ui_event is not None:
                ui_event(
                    "key.selected",
                    deployment=deployment.deployment,
                    provider=deployment.provider,
                    key_index=total_attempts,
                )
                ui_event(
                    "provider.dispatched",
                    deployment=deployment.deployment,
                    provider=deployment.provider,
                    key_index=total_attempts,
                )
            try:
                if stream:
                    content_type, byte_iter = await deployment.adapter.dispatch_stream(
                        request, http_client, key_value=key_value
                    )
                    # Caller owns key release + audit writes after stream closes.
                    return (
                        content_type,
                        byte_iter,
                        deployment.deployment,
                        deployment.provider,
                        total_attempts,
                        key_value,
                    )
                result = await deployment.adapter.dispatch_single(
                    request, http_client, key_value=key_value
                )
                await deployment.pool.release(key_value, None)
                if persist_key_state is not None:
                    persist_key_state(
                        deployment=deployment.deployment, key_value=key_value, status="active"
                    )
                _emit(
                    write_event,
                    "key.released",
                    {
                        "deployment": deployment.deployment,
                        "key_id": _redact_key(key_value),
                        "failure_type": "success",
                    },
                )
                return {
                    "response": result,
                    "deployment": deployment.deployment,
                    "provider": deployment.provider,
                    "attempts": total_attempts,
                }
            except ProviderFailure as exc:
                last_failure = exc
                cooldown = _cooldown_for(exc, backoff_floor)
                await deployment.pool.release(
                    key_value, exc.failure_type, cooldown_seconds=cooldown
                )
                if persist_key_state is not None:
                    _persist_key_after_failure(
                        persist_key_state,
                        deployment=deployment.deployment,
                        key_value=key_value,
                        failure_type=exc.failure_type,
                        cooldown_seconds=cooldown,
                    )
                _emit(
                    write_event,
                    "key.released",
                    {
                        "deployment": deployment.deployment,
                        "key_id": _redact_key(key_value),
                        "failure_type": exc.failure_type,
                    },
                )
                if exc.failure_type in ("request_invalid", "request_too_large"):
                    raise exc

                if exc.failure_type == "key_revoked":
                    _emit(
                        write_event,
                        "key.dead",
                        {
                            "deployment": deployment.deployment,
                            "key_id": _redact_key(key_value),
                            "reason": "key_revoked",
                        },
                    )
                    if deployment.pool.active_count > 0:
                        continue
                    break

                if exc.failure_type == "provider_unreachable":
                    break

                if exc.failure_type in ("rate_limited", "key_quota_exhausted"):
                    _emit(
                        write_event,
                        "key.cooldown_set",
                        {
                            "deployment": deployment.deployment,
                            "key_id": _redact_key(key_value),
                            "until": cooldown,
                            "reason": exc.failure_type,
                        },
                    )
                    if ui_event is not None and exc.failure_type == "rate_limited":
                        ui_event(
                            "provider.rate_limited",
                            deployment=deployment.deployment,
                            provider=deployment.provider,
                            key_index=total_attempts,
                            retry_after=cooldown,
                        )
                if deployment.pool.active_count > 0:
                    continue
                break

            except AdapterRequestError as exc:
                last_failure = ProviderFailure(
                    failure_type=exc.failure_type,
                    message=str(exc),
                    http_code=None,
                )
                await deployment.pool.release(key_value, exc.failure_type, cooldown_seconds=0.0)
                if persist_key_state is not None:
                    _persist_key_after_failure(
                        persist_key_state,
                        deployment=deployment.deployment,
                        key_value=key_value,
                        failure_type=exc.failure_type,
                        cooldown_seconds=0.0,
                    )
                _emit(
                    write_event,
                    "key.released",
                    {
                        "deployment": deployment.deployment,
                        "key_id": _redact_key(key_value),
                        "failure_type": exc.failure_type,
                    },
                )
                if exc.failure_type in ("request_invalid", "request_too_large"):
                    raise exc
                continue

    if last_failure is not None:
        raise last_failure
    raise PipelineExhausted(total_attempts, None)


def _persist_key_after_failure(
    persist_key_state: Callable[..., None],
    *,
    deployment: str,
    key_value: str,
    failure_type: str,
    cooldown_seconds: float,
) -> None:
    """Map a pipeline failure type to a persisted key status."""
    if failure_type == "key_revoked":
        persist_key_state(deployment=deployment, key_value=key_value, status="dead")
    elif failure_type in ("rate_limited", "key_quota_exhausted"):
        until_ts = datetime.fromtimestamp(
            time.time() + max(cooldown_seconds, 1.0), tz=UTC
        ).isoformat()
        persist_key_state(
            deployment=deployment,
            key_value=key_value,
            status="cooldown",
            cooldown_until=until_ts,
        )
    elif failure_type == "provider_unreachable":
        # Key stays active in memory (transient provider issue), don't persist.
        pass
    elif failure_type == "unhandled_error":
        # Memory may cooldown; persist with a 1s floor to stay in sync.
        until_ts = datetime.fromtimestamp(time.time() + max(cooldown_seconds, 1.0), tz=UTC).isoformat()
        persist_key_state(
            deployment=deployment,
            key_value=key_value,
            status="cooldown",
            cooldown_until=until_ts,
        )
    # request_invalid / request_too_large: don't persist;
    # the key itself is healthy, the request is bad or it was a transient hiccup.


def _cooldown_for(failure: ProviderFailure, backoff_floor: float) -> float:
    """Return cooldown duration in seconds for a failure type."""
    if failure.failure_type == "rate_limited":
        if failure.retry_after_seconds is not None:
            return max(failure.retry_after_seconds, backoff_floor)
        return backoff_floor
    if failure.failure_type == "key_quota_exhausted":
        return 3600.0  # 1 hour default for quota
    if failure.failure_type == "unhandled_error":
        return backoff_floor
    return 0.0


def _emit(
    writer: Callable[[str, dict[str, object]], None] | None,
    event_type: str,
    payload: dict[str, object],
) -> None:
    if writer is None:
        return
    try:
        writer(event_type, payload)
    except Exception:  # noqa: BLE001, S110 — audit must never block the request path
        pass


def _redact_key(key_value: str) -> str:
    """Redact a key value: SHA-256 hash of first 16 chars + '***' suffix."""
    if not key_value:
        return "***"
    prefix = key_value[:16] if len(key_value) > 16 else key_value
    hashed = hashlib.sha256(prefix.encode()).hexdigest()[:12]
    return f"{hashed}***"
