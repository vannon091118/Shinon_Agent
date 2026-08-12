"""Durable dispatch lifecycle for chat completions."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from limen.adapters.base import AdapterRequestError
from limen.resilience import ProviderFailure
from limen.routing import (
    NoAvailableDeployment,
    UnknownRequestedModel,
    to_http_exception,
)
from limen.routing.pipeline import PipelineExhausted, run_pipeline
from limen.routing.scanner import scan_request

if TYPE_CHECKING:
    from collections.abc import Callable

    from limen.api.schemas import ChatCompletionRequest, ChatCompletionResponse
    from limen.persistence.database import Database
    from limen.routing import Dispatcher
    from limen.routing.registry import ProviderRegistry
    from limen.transport import HttpTransport

# Conservative stand-in for the per-call budget when stream_completion is
# invoked without one. The non-streaming path uses 10 (Dispatcher's default);
# streaming is user-facing and stricter, but still high enough to walk one
# key per active deployment in a typical multi-provider setup.
_DEFAULT_STREAM_MAX_ATTEMPTS = 5


def _idempotency_fingerprint(request: ChatCompletionRequest) -> str:
    """Build a deterministic content fingerprint for idempotency.

    Uses (model, sorted message content, temperature, top_p, max_tokens,
    user) so that identical requests produce the same key — regardless of
    correlation_id.
    """
    messages_digest = ",".join(
        f"{m.role}:{m.content or ''}"
        for m in sorted(request.messages, key=lambda m: (m.role or "", m.content or ""))
    )
    raw = "|".join(
        [
            request.model,
            messages_digest,
            str(request.temperature),
            str(request.top_p),
            str(request.max_tokens),
            request.user or "",
        ]
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _extract_attempts(exc: BaseException) -> int:
    """Read the real attempt count from a PipelineExhausted, even when
    it has been wrapped in HTTPException via to_http_exception."""
    if isinstance(exc, PipelineExhausted):
        return exc.attempts
    if isinstance(exc, HTTPException) and isinstance(exc.__cause__, PipelineExhausted):
        return exc.__cause__.attempts
    return 1


def _failure_type_label(exc: BaseException) -> str:
    """Map a dispatcher-raised exception to a stable audit vocabulary.

    Typed dispatch failures surface as ``HTTPException`` after ``to_http_exception``
    packing; we read the original failure-type back out of the envelope when
    present so the audit log records ``rate_limited`` rather than ``HTTPException``.
    Falls back to the Python class name for unexpected exceptions.
    """
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            inner = detail.get("error")
            if isinstance(inner, dict):
                inner_type = inner.get("type")
                if isinstance(inner_type, str):
                    return inner_type
    if isinstance(exc, (ProviderFailure, AdapterRequestError, PipelineExhausted)):
        return getattr(exc, "failure_type", type(exc).__name__)
    return type(exc).__name__


async def durable_dispatch(
    request: ChatCompletionRequest,
    database: Database,
    dispatcher: Dispatcher,
    *,
    ui_event: Callable[..., None] | None = None,
    correlation_id: str | None = None,
) -> ChatCompletionResponse:
    """Enqueue, claim, dispatch, and finish a chat completion with durability.

    On crash mid-flight the entry is left ``in_flight`` with a lease;
    the worker recovers it on next startup. ``correlation_id`` ties the
    durable row, audit events, and external trace IDs together; a fresh
    12-char hex token is generated when the caller does not supply one.
    """
    if correlation_id is None:
        correlation_id = uuid4().hex[:12]
    request_id = uuid4().hex
    body_json = request.model_dump_json()

    entry = database.emplace(
        request_id, body_json, request.model, correlation_id, stream_flag=False
    )
    task_id = str(entry["id"])
    database.write_event(
        "task.started",
        {
            "id": task_id,
            "correlation_id": correlation_id,
        },
        correlation_id=correlation_id,
    )

    def write_event(event_type: str, payload: dict[str, object]) -> None:
        # Pipeline emits only (type, payload); inject correlation_id and the
        # durable task_id so audit log rows join to the queue table.
        merged = {**payload, "correlation_id": correlation_id, "task_id": task_id}
        database.write_event(event_type, merged, correlation_id=correlation_id)

    if ui_event:
        ui_event("request.enqueued", task_id=correlation_id)
        ui_event("worker.claimed", task_id=correlation_id)
        ui_event("dispatch.started", model=request.model, task_id=correlation_id)

    request_scan = scan_request(request)
    database.write_event(
        "request.scanned",
        {**request_scan.to_event_payload(), "correlation_id": correlation_id},
        correlation_id=correlation_id,
    )

    auto_route = request.model == "auto"
    min_context_tokens = request_scan.context_tokens if auto_route else 0
    if auto_route and ui_event:
        ui_event(
            "routing.auto",
            category=request_scan.category,
            score=request_scan.score,
            context_tokens=request_scan.context_tokens,
        )

    started_at = datetime.now(UTC).timestamp()
    try:
        outcome = await dispatcher.dispatch(
            request,
            ui_event=ui_event,
            write_event=write_event,
            min_context_tokens=min_context_tokens,
            persist_key_state=database.persist_key_state,
        )
    except Exception as exc:
        # ``dispatcher.dispatch`` already wraps typed dispatch failures
        # (``ProviderFailure``, ``AdapterRequestError``, ``PipelineExhausted``)
        # into ``HTTPException`` via ``to_http_exception``; HTTPException reaches
        # this branch too. The catch-all is bounded to ``Exception`` so signals
        # (``SystemExit``, ``KeyboardInterrupt``) propagate cleanly without
        # touching the durable ledger. ``fail_task`` runs first so the row is
        # recovered next start; ``task.failed`` carries the actual failure-type
        # vocabulary so audit-tracing can group errors by name.
        database.fail_task(task_id)
        elapsed = datetime.now(UTC).timestamp() - started_at
        failure_type = _failure_type_label(exc)
        database.write_event(
            "task.failed",
            {
                "id": task_id,
                "model": request.model,
                "stream_flag": False,
                "failure_type": failure_type,
                "attempts": _extract_attempts(exc),
                "waited_seconds": round(elapsed, 3),
                "correlation_id": correlation_id,
            },
            correlation_id=correlation_id,
        )
        if ui_event:
            ui_event(
                "dispatch.failed",
                failure_type=failure_type,
                latency_ms=round(elapsed * 1000, 3),
            )
        raise

    elapsed = datetime.now(UTC).timestamp() - started_at

    if ui_event:
        ui_event(
            "provider.responded",
            deployment=outcome.deployment,
            provider=outcome.provider,
            duration_seconds=round(elapsed, 3),
            upstream_status=outcome.upstream_status,
        )

    database.finish_task(task_id)
    result_json = outcome.response.model_dump_json()
    fingerprint = _idempotency_fingerprint(request)
    cached = database.check_idempotent(fingerprint, "chat.completion")
    if cached is None:
        database.store_idempotent(fingerprint, "chat.completion", result_json)
    database.write_event(
        "task.completed",
        {
            "id": task_id,
            "provider_deployment": outcome.deployment,
            "duration_seconds": round(elapsed, 3),
            "correlation_id": correlation_id,
        },
        correlation_id=correlation_id,
    )

    if ui_event:
        ui_event("db.lock_acquired", duration_seconds=round(elapsed, 3))

    return outcome.response


async def stream_completion(
    request: ChatCompletionRequest,
    registry: ProviderRegistry,
    transport: HttpTransport,
    database: Database,
    *,
    ui_event: Callable[..., None] | None = None,
    max_attempts: int | None = None,
    correlation_id: str | None = None,
) -> StreamingResponse:
    """Streaming dispatch: walk candidates, claim a key, stream from provider.

    Retries across keys/deployments on retryable connection failures
    BEFORE the first byte reaches the client. Once streaming begins,
    no further retry is possible.

    ``max_attempts`` caps the total number of key claims per call so that a
    retryable failure (``provider_unreachable``) cannot burn an indefinite
    amount of time waiting for a key whose pool never exhausts; defaults to
    ``dispatcher.max_attempts`` when not supplied.

    ``correlation_id`` ties audit events, the durable queue row, and the
    ``X-Request-Id`` header; a fresh 12-char hex token is generated when
    the caller does not supply one.
    """

    if correlation_id is None:
        correlation_id = uuid4().hex[:12]
    request_id = uuid4().hex
    body_json = request.model_dump_json()

    database.emplace(request_id, body_json, request.model, correlation_id, stream_flag=True)
    database.write_event(
        "task.started",
        {
            "id": request_id,
            "correlation_id": correlation_id,
        },
        correlation_id=correlation_id,
    )

    if ui_event:
        ui_event("request.enqueued", task_id=correlation_id)
        ui_event("worker.claimed", task_id=correlation_id)
        ui_event("dispatch.started", model=request.model, task_id=correlation_id)

    request_scan = scan_request(request)
    database.write_event(
        "request.scanned",
        {**request_scan.to_event_payload(), "correlation_id": correlation_id},
        correlation_id=correlation_id,
    )

    auto_route = request.model == "auto"
    min_context_tokens = request_scan.context_tokens if auto_route else 0
    if auto_route and ui_event:
        ui_event(
            "routing.auto",
            category=request_scan.category,
            score=request_scan.score,
            context_tokens=request_scan.context_tokens,
        )

    candidates = registry.resolve(request.model, min_context_tokens=min_context_tokens)
    if not candidates:
        database.write_event(
            "task.failed",
            {
                "id": request_id,
                "model": request.model,
                "stream_flag": True,
                "failure_type": "unknown_model",
                "attempts": 1,
                "waited_seconds": 0.0,
                "correlation_id": correlation_id,
            },
            correlation_id=correlation_id,
        )
        database.dead_task(request_id)
        raise UnknownRequestedModel(request.model)

    # ── Delegate to run_pipeline in stream mode ──
    # run_pipeline handles key claiming, failure classification, cooldown,
    # and attempt budgeting. We only wrap the streaming result.
    if max_attempts is None:
        max_attempts = _DEFAULT_STREAM_MAX_ATTEMPTS

    attempts_used = 0

    try:
        result = await run_pipeline(
            request,
            candidates,
            transport.client,
            max_attempts=max_attempts,
            write_event=None,  # we write audit below, after stream closes
            ui_event=ui_event,
            stream=True,
        )
    except ProviderFailure as exc:
        database.write_event(
            "task.failed",
            {
                "id": request_id,
                "model": request.model,
                "stream_flag": True,
                "failure_type": exc.failure_type,
                "attempts": _extract_attempts(exc),
                "waited_seconds": 0.0,
                "correlation_id": correlation_id,
            },
            correlation_id=correlation_id,
        )
        database.fail_task(request_id)
        if ui_event:
            ui_event("dispatch.failed", failure_type=exc.failure_type, latency_ms=0.0)
        raise to_http_exception(exc) from exc
    except PipelineExhausted as exc:
        failure_type = exc.failure_type
        database.write_event(
            "task.failed",
            {
                "id": request_id,
                "model": request.model,
                "stream_flag": True,
                "failure_type": failure_type,
                "attempts": exc.attempts,
                "waited_seconds": 0.0,
                "correlation_id": correlation_id,
            },
            correlation_id=correlation_id,
        )
        database.fail_task(request_id)
        if ui_event:
            ui_event("dispatch.failed", failure_type=failure_type, latency_ms=0.0)
        raise NoAvailableDeployment(request.model) from exc

    # Unpack streaming result tuple from run_pipeline
    if isinstance(result, dict):  # type narrowing for mypy
        raise RuntimeError("run_pipeline(stream=True) must return tuple, not dict")
    content_type, byte_iter, deployment_name, provider_name, attempts_used, key_value = result

    # ── Record key claim (factually correct — claim already happened) ──
    database.write_event(
        "key.claimed",
        {
            "deployment": deployment_name,
            "correlation_id": correlation_id,
        },
        correlation_id=correlation_id,
    )

    # ── Resolve the deployment for key release on stream close ──
    stream_deployment = None
    for d in candidates:
        if d.deployment == deployment_name:
            stream_deployment = d
            break
    if stream_deployment is None:
        # Should never happen; release defensively so the key isn't leaked.
        for d in candidates:
            await d.pool.release(key_value, None)
            break

    stream_started_at = datetime.now(UTC).timestamp()

    async def _wrapped_stream(
        _byte_iter: Any = byte_iter,
        _deployment: Any = stream_deployment,
        _key_value: str = key_value,
    ) -> Any:
        try:
            async for chunk in _byte_iter:
                yield chunk
        finally:
            elapsed = datetime.now(UTC).timestamp() - stream_started_at
            try:
                database.write_event(
                    "key.released",
                    {
                        "deployment": deployment_name,
                        "failure_type": "success",
                    },
                    correlation_id=correlation_id,
                )
                database.finish_task(request_id)
                database.write_event(
                    "task.completed",
                    {
                        "id": request_id,
                        "provider_deployment": deployment_name,
                        "duration_seconds": round(elapsed, 3),
                        "attempts": attempts_used,
                        "correlation_id": correlation_id,
                    },
                    correlation_id=correlation_id,
                )
                if ui_event:
                    ui_event(
                        "provider.responded",
                        deployment=deployment_name,
                        provider=provider_name,
                        duration_seconds=round(elapsed, 3),
                        upstream_status=0,
                    )
            except Exception:  # noqa: BLE001, S110 — audit must never block key release
                pass
            if _deployment is not None:
                await _deployment.pool.release(_key_value, None)

    return StreamingResponse(
        _wrapped_stream(),
        media_type=content_type or "text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-Id": correlation_id,
        },
    )
