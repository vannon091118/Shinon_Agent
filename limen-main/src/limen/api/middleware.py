"""ASGI middleware for the LIMEN HTTP layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodySizeLimitMiddleware:
    """Reject oversized declared or streamed HTTP request bodies."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = _content_length(scope)
        if content_length == -1:
            await _send_client_error_response(send)
            return
        if content_length is not None and content_length > self.max_bytes:
            await _send_body_limit_response(send)
            return

        messages: list[Message] = []
        received = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    await _send_body_limit_response(send)
                    return
                if not message.get("more_body", False):
                    break
            else:
                break

        position = 0

        async def buffered_receive() -> Message:
            nonlocal position
            if position < len(messages):
                message = messages[position]
                position += 1
                return message
            return {"type": "http.disconnect"}

        await self.app(scope, buffered_receive, send)


def _content_length(scope: Scope) -> int | None:
    """Parse Content-Length, using -1 for malformed or negative values."""
    for name, value in scope.get("headers", []):
        if name.lower() == b"content-length":
            try:
                parsed = int(value)
            except ValueError:
                return -1
            return parsed if parsed >= 0 else -1
    return None


async def _send_client_error_response(send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 400,
            "headers": [(b"content-type", b"text/plain; charset=utf-8")],
        }
    )
    await send({"type": "http.response.body", "body": b"Invalid Content-Length"})


async def _send_body_limit_response(send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [(b"content-type", b"text/plain; charset=utf-8")],
        }
    )
    await send({"type": "http.response.body", "body": b"Request body too large"})
