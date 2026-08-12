"""OpenAI-compatible provider adapter used as the LIMEN reference implementation."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from limen.adapters.base import AdapterRequestError, ProviderCallResult
from limen.resilience import ProviderFailure, classify_http_failure
from limen.schemas import ChatCompletionRequest, ChatCompletionResponse


@dataclass(frozen=True)
class OpenAIDeployment:
    """Configuration for one OpenAI-compatible deployment."""

    provider: str
    deployment: str
    base_url: str
    model: str
    api_keys: tuple[str, ...]
    capabilities: tuple[str, ...]

    def validate(self) -> None:
        if not self.base_url:
            raise AdapterRequestError(
                "request_invalid", f"deployment {self.deployment} has no base_url"
            )
        if not self.api_keys:
            raise AdapterRequestError(
                "key_revoked", f"deployment {self.deployment} has no configured API keys"
            )
        if "chat" not in self.capabilities:
            raise AdapterRequestError(
                "request_invalid",
                f"deployment {self.deployment} does not list the chat capability",
            )


class OpenAICompatibleAdapter:
    """Adapter for OpenAI-compatible chat completions endpoints."""

    def __init__(
        self,
        *,
        provider: str,
        deployment_name: str,
        model: str,
        base_url: str,
        api_keys: list[str],
        capabilities: list[str],
    ) -> None:
        self._deployment = OpenAIDeployment(
            provider=provider,
            deployment=deployment_name,
            base_url=base_url.rstrip("/"),
            model=model,
            api_keys=tuple(api_keys),
            capabilities=tuple(capabilities),
        )
        self.provider = provider
        self.deployment = deployment_name
        self.model = model

    def _select_key(self, offset: int = 0) -> str:
        if not self._deployment.api_keys:
            raise AdapterRequestError(
                "key_revoked", f"deployment {self.deployment} has no configured API keys"
            )
        index = offset % len(self._deployment.api_keys)
        return self._deployment.api_keys[index]

    async def dispatch(
        self,
        request: ChatCompletionRequest,
        request_id: str,
        correlation_id: str,
        http_client: httpx.AsyncClient,
    ) -> ProviderCallResult:
        """Phase-1 backwards-compat: iterate all keys internally."""
        self._deployment.validate()
        attempts = 0
        last_failure: ProviderFailure | None = None
        while attempts < len(self._deployment.api_keys):
            key_value = self._select_key(attempts)
            try:
                return await self.dispatch_single(
                    request, http_client, key_value=key_value
                )
            except ProviderFailure as exc:
                last_failure = exc
                if not exc.is_retryable:
                    raise exc
                attempts += 1
        if last_failure is None:
            raise AdapterRequestError(
                "unhandled_error",
                "provider adapter exhausted without a recorded failure",
            )
        raise last_failure

    async def dispatch_single(
        self,
        request: ChatCompletionRequest,
        http_client: httpx.AsyncClient,
        *,
        key_value: str,
    ) -> ProviderCallResult:
        """Issue exactly one provider call with the given key."""
        self._deployment.validate()
        url = f"{self._deployment.base_url}/chat/completions"
        payload = _build_payload(request, self._deployment.model)
        headers = _build_headers(
            _request_id(), _correlation_id(), key_value
        )
        try:
            response = await http_client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise ProviderFailure(
                failure_type="provider_unreachable",
                message=str(exc),
                http_code=None,
            ) from exc
        if 200 <= response.status_code < 300:
            return _build_result(
                response,
                self._deployment.provider,
                self._deployment.deployment,
                self._deployment.model,
            )
        raise classify_http_failure(
            response.status_code, response.content, response.headers
        )

    async def dispatch_stream(
        self,
        request: ChatCompletionRequest,
        http_client: httpx.AsyncClient,
        *,
        key_value: str,
    ) -> tuple[str, Any]:
        """Make a streaming provider call and return an async byte iterator.

        Returns ``(content_type, byte_iterator)``. The caller wraps the
        iterator in a ``StreamingResponse``.

        No retry — streaming can't be safely repeated after the first chunk.
        """
        self._deployment.validate()
        url = f"{self._deployment.base_url}/chat/completions"
        payload = _build_stream_payload(request, self._deployment.model)
        headers = _build_headers(
            _request_id(), _correlation_id(), key_value
        )
        try:
            response = await http_client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise ProviderFailure(
                failure_type="provider_unreachable",
                message=str(exc),
                http_code=None,
            ) from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise classify_http_failure(
                response.status_code,
                response.content,
                dict(response.headers),
            )
        return response.headers.get("content-type", "text/event-stream"), response.aiter_bytes()


def _build_payload(request: ChatCompletionRequest, model: str) -> dict[str, Any]:
    return _build_payload_common(request, model, stream=False)


def _build_stream_payload(request: ChatCompletionRequest, model: str) -> dict[str, Any]:
    return _build_payload_common(request, model, stream=True)


def _build_payload_common(
    request: ChatCompletionRequest, model: str, *, stream: bool
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [message.model_dump(exclude_none=True) for message in request.messages],
        "stream": stream,
    }
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.top_p is not None:
        payload["top_p"] = request.top_p
    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens
    if request.user is not None:
        payload["user"] = request.user
    return payload


def _request_id() -> str:
    return uuid.uuid4().hex


def _correlation_id() -> str:
    return uuid.uuid4().hex


def _redact_user(value: str) -> str:
    if len(value) <= 4:
        return "***"
    return f"{value[:2]}***{value[-2:]}"


def _build_headers(request_id: str, correlation_id: str, api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Proxy-Request-Id": request_id,
        "X-Proxy-Correlation-Id": correlation_id,
    }


def _build_result(
    response: httpx.Response,
    provider: str,
    deployment: str,
    model: str,
) -> ProviderCallResult:
    try:
        payload = json.loads(response.text or "{}")
    except json.JSONDecodeError as exc:
        raise ProviderFailure(
            failure_type="unhandled_error",
            message=f"provider returned non-JSON payload: {exc}",
            http_code=response.status_code,
            raw_body=response.text,
        ) from exc
    if not isinstance(payload, dict):
        raise ProviderFailure(
            failure_type="unhandled_error",
            message="provider payload is not a JSON object",
            http_code=response.status_code,
            raw_body=response.text,
        )
    if response.status_code == 200 and "choices" not in payload:
        raise ProviderFailure(
            failure_type="unhandled_error",
            message="200 response missing required 'choices' field",
            http_code=response.status_code,
            raw_body=response.text,
        )
    model_name = str(payload.get("model") or model)
    created_value = payload.get("created")
    if isinstance(created_value, (int, float)):
        created_int = int(created_value)
    else:
        created_int = int(datetime.now(UTC).timestamp())
    response_id = str(payload.get("id") or f"limen-{created_int}")
    completion = _parse_choices(payload.get("choices", []), response_id)
    usage = _parse_usage(payload.get("usage"))
    bounded_data: dict[str, Any] = {
        "id": response_id,
        "object": "chat.completion",
        "created": created_int,
        "model": model_name,
        "choices": [
            {
                "index": choice["index"],
                "message": choice["message"],
                "finish_reason": choice.get("finish_reason"),
            }
            for choice in completion["choices"]
        ],
    }
    if usage is not None:
        bounded_data["usage"] = usage
    return ProviderCallResult(
        response=ChatCompletionResponse.model_validate(bounded_data),
        deployment=deployment,
        provider=provider,
        model=model_name,
        upstream_status=response.status_code,
        raw_payload={key: value for key, value in payload.items() if key != "choices"},
    )


def _parse_choices(value: object, response_id: str) -> dict[str, Any]:
    if not isinstance(value, list) or not value:
        raise ProviderFailure(
            failure_type="unhandled_error",
            message=f"provider responded without valid choices ({response_id})",
            http_code=None,
            raw_body=str(value),
        )
    choices: list[dict[str, Any]] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise ProviderFailure(
                failure_type="unhandled_error",
                message=f"choice {index} is not a JSON object ({response_id})",
                http_code=None,
                raw_body=str(entry),
            )
        message = entry.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ProviderFailure(
                failure_type="unhandled_error",
                message=f"choice {index} missing message.content ({response_id})",
                http_code=None,
                raw_body=str(entry),
            )
        choices.append(
            {
                "index": entry.get("index", index),
                "message": {
                    "role": message.get("role", "assistant"),
                    "content": message["content"],
                },
                "finish_reason": entry.get("finish_reason"),
            }
        )
    return {"choices": choices}


def _parse_usage(value: object) -> dict[str, int] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        return None
    return {
        key: int(value[key])
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        if isinstance(value.get(key), int)
    }
