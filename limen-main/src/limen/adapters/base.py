"""Provider adapter abstraction for LIMEN dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import httpx

    from limen.resilience.classifier import FailureType
    from limen.schemas import ChatCompletionRequest, ChatCompletionResponse


class AdapterRequestError(Exception):
    """Non-HTTP failure produced inside an adapter before reaching the provider."""

    def __init__(self, failure_type: FailureType, message: str) -> None:
        super().__init__(message)
        self.failure_type = failure_type


@dataclass(frozen=True)
class ProviderCallResult:
    """Successful provider response plus redacted observation metadata."""

    response: ChatCompletionResponse
    deployment: str
    provider: str
    model: str
    upstream_status: int
    raw_payload: dict[str, Any]


class ProviderAdapter(Protocol):
    """Single dispatch entry: one adapter per provider deployment."""

    provider: str
    deployment: str
    model: str

    async def dispatch(
        self,
        request: ChatCompletionRequest,
        request_id: str,
        correlation_id: str,
        http_client: httpx.AsyncClient,
    ) -> ProviderCallResult: ...
