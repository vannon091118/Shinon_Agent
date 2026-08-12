"""Dispatcher that runs the Phase-2 fallback pipeline over registry candidates."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

from fastapi import HTTPException

from limen.adapters.base import AdapterRequestError, ProviderCallResult
from limen.resilience import ProviderFailure
from limen.routing.pipeline import PipelineExhausted, run_pipeline
from limen.routing.registry import NoMatchingDeployment, ProviderRegistry
from limen.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ErrorEnvelope,
    ErrorResponse,
)

if TYPE_CHECKING:
    from limen.transport import HttpTransport


class NoAvailableDeployment(HTTPException):
    """Raised when no enabled deployment exists in the registry."""

    def __init__(self, model: str) -> None:
        envelope = ErrorResponse(
            error=ErrorEnvelope(
                message=f"no enabled deployment advertises model {model!r}",
                type="no_available_deployment",
                param=None,
                code=None,
            )
        ).to_dict()
        super().__init__(status_code=503, detail=envelope)


class UnknownRequestedModel(HTTPException):
    """Raised when the requested model is not offered by any deployment."""

    def __init__(self, model: str) -> None:
        envelope = ErrorResponse(
            error=ErrorEnvelope(
                message=f"unknown model {model!r}",
                type="unknown_model",
                param="model",
                code=None,
            )
        ).to_dict()
        super().__init__(status_code=400, detail=envelope)


@dataclass(frozen=True)
class DispatchOutcome:
    """Successful return shape including route decisions."""

    response: ChatCompletionResponse
    correlation_id: str
    request_id: str
    deployment: str
    provider: str
    upstream_status: int = 0
    routed_via: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)


class Dispatcher:
    """Phase 2 dispatcher: multi-candidate pipeline with key rotation and cooldown."""

    def __init__(
        self,
        registry: ProviderRegistry,
        transport: HttpTransport,
        *,
        audit_writer: Callable[[str, dict[str, object]], None] | None = None,
        max_attempts: int = 10,
    ) -> None:
        self._registry = registry
        self._transport = transport
        self._audit_writer = audit_writer
        self.max_attempts = max_attempts

    async def dispatch(
        self,
        request: ChatCompletionRequest,
        *,
        ui_event: Callable[..., None] | None = None,
        write_event: Callable[[str, dict[str, object]], None] | None = None,
        min_context_tokens: int = 0,
        persist_key_state: Callable[..., None] | None = None,
    ) -> DispatchOutcome:
        """Walk the pipeline. ``write_event`` (per-call) overrides the
        constructor-bound ``audit_writer`` so the dispatch layer can bind
        per-call context such as correlation_id.
        """
        if not self._registry.deployments:
            raise NoAvailableDeployment(request.model)
        try:
            candidates = self._registry.resolve(
                request.model, min_context_tokens=min_context_tokens
            )
        except NoMatchingDeployment as exc:
            raise UnknownRequestedModel(exc.requested_model) from exc

        correlation_id = uuid.uuid4().hex
        request_id = uuid.uuid4().hex
        max_attempts = self._resolve_max_attempts()
        pipeline_writer = write_event if write_event is not None else self._audit_writer

        try:
            result = await run_pipeline(
                request,
                candidates,
                self._transport.client,
                max_attempts=max_attempts,
                write_event=pipeline_writer,
                ui_event=ui_event,
                persist_key_state=persist_key_state,
            )
        except PipelineExhausted as exc:
            raise to_http_exception(exc) from exc
        except ProviderFailure as exc:
            raise to_http_exception(exc) from exc
        except AdapterRequestError as exc:
            raise to_http_exception(exc) from exc

        result_dict = cast("dict[str, Any]", result)
        call_result: ProviderCallResult = result_dict["response"]
        return DispatchOutcome(
            response=call_result.response,
            correlation_id=correlation_id,
            request_id=request_id,
            deployment=str(result_dict["deployment"]),
            provider=str(result_dict["provider"]),
            upstream_status=call_result.upstream_status,
            routed_via=f"{result_dict['provider']}:{result_dict['deployment']}",
            notes=(f"attempts={result_dict['attempts']}",),
        )

    def _resolve_max_attempts(self) -> int:
        """Return the maximum number of key attempts across the pipeline."""
        total_keys = sum(d.pool.total_count for d in self._registry.deployments)
        raw_max = max(self.max_attempts, 1)
        return min(total_keys, raw_max) if total_keys > 0 else 1


def to_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, PipelineExhausted):
        envelope = ErrorResponse(
            error=ErrorEnvelope(
                message=str(exc),
                type=exc.failure_type,
                code=str(exc.http_code) if exc.http_code is not None else None,
                param=None,
            )
        ).to_dict()
        return HTTPException(status_code=503, detail=envelope)
    if isinstance(exc, AdapterRequestError):
        envelope = ErrorResponse(
            error=ErrorEnvelope(
                message=str(exc),
                type=exc.failure_type,
                code=None,
                param=None,
            )
        ).to_dict()
        status = status_for_failure(exc.failure_type)
        return HTTPException(status_code=status, detail=envelope)
    if isinstance(exc, ProviderFailure):
        envelope = ErrorResponse(
            error=ErrorEnvelope(
                message=exc.message,
                type=exc.failure_type,
                code=str(exc.http_code) if exc.http_code is not None else None,
                param=None,
            )
        ).to_dict()
        status = status_for_failure(exc.failure_type)
        extra_headers: dict[str, str] = {"X-LIMEN-Failure": exc.failure_type}
        if exc.failure_type == "rate_limited" and exc.retry_after_seconds is not None:
            extra_headers["Retry-After"] = f"{exc.retry_after_seconds:.0f}"
        return HTTPException(status_code=status, detail=envelope, headers=extra_headers)
    raise exc


def status_for_failure(failure_type: str) -> int:
    mapping = {
        "request_invalid": 400,
        "request_too_large": 413,
        "key_revoked": 401,
        "key_quota_exhausted": 402,
        "provider_unreachable": 502,
        "rate_limited": 429,
        "unhandled_error": 500,
    }
    return mapping.get(failure_type, 500)


__all__ = [
    "Dispatcher",
    "DispatchOutcome",
    "NoAvailableDeployment",
    "UnknownRequestedModel",
    "status_for_failure",
    "to_http_exception",
]
