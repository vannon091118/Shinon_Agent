"""Mock provider transport used by Phase 1 integration tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

ResponseFactory = Callable[[httpx.Request], httpx.Response]


def build_mock_transport(respond: ResponseFactory) -> httpx.MockTransport:
    """Wrap a request handler into an httpx MockTransport."""
    return httpx.MockTransport(respond)


def make_success_response(
    *,
    model: str,
    content: str,
    usage: dict[str, int] | None = None,
    request: httpx.Request | None = None,
) -> httpx.Response:
    """Build an OpenAI-shape completion response."""
    payload: dict[str, Any] = {
        "id": "chatcmpl-mock-001",
        "object": "chat.completion",
        "created": 1_700_000_000,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }
    if usage is not None:
        payload["usage"] = usage
    return httpx.Response(200, json=payload)


def make_error_response(status: int, payload: dict[str, Any]) -> httpx.Response:
    """Build a provider-style error response."""
    return httpx.Response(status, json=payload)


def encode_response(response: httpx.Response) -> bytes:
    return response.content
