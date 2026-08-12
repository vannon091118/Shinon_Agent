"""Anthropic Messages API route — translates between Anthropic and OpenAI wire formats."""

from __future__ import annotations

import asyncio
import json as _json
from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from limen.api.dispatch import durable_dispatch
from limen.schemas import ChatCompletionRequest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
from limen.schemas.anthropic import (
    AnthropicRequest,
    anthropic_to_chat_request,
    chat_to_anthropic_response,
)

router = APIRouter()


def _anthropic_error_body(error_type: str, message: str) -> dict[str, object]:
    """Build an Anthropic-shaped error envelope for HTTPException detail."""
    return {"type": "error", "error": {"type": error_type, "message": message}}


def _resolve_anthropic_model(requested: str, aliases: dict[str, str]) -> str:
    """Resolve an Anthropic model name through the [anthropic] config.

    The ``[anthropic]`` section is a free-form ``dict[str, str]`` mapping
    any model name the client sends to a LIMEN model.  No hardcoded
    Claude model IDs — users define their own aliases.

    An empty or missing value routes through the generic fallback pool
    (same as ``model: auto``).
    """
    mapped = aliases.get(requested, "")
    return mapped if mapped else requested


# ── POST /v1/messages ─────────────────────────────────────────────────


async def _anthropic_stream(
    chat_req: ChatCompletionRequest,
    requested_model: str,
    request_id: str,
    app_state: Any,
) -> StreamingResponse:
    """Streaming Anthropic Messages — translate OpenAI SSE to Anthropic SSE.

    Uses the existing stream_completion path, then re-wraps the byte
    iterator to emit Anthropic-shaped SSE events.
    """
    from limen.api.dispatch import stream_completion as _sc

    try:
        openai_stream = await _sc(
            chat_req,
            app_state.registry,
            app_state.transport,
            app_state.database,
            ui_event=None,
            correlation_id=request_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=_anthropic_error_body("api_error", str(exc)),
        ) from exc

    message_id = f"msg_{request_id}"

    async def _translate() -> AsyncIterator[bytes]:  # noqa: F821
        """Parse OpenAI SSE chunks → Anthropic SSE events."""
        started = False
        content_index = 0
        text_buf: list[str] = []
        input_tokens = 0

        async for chunk in openai_stream.body_iterator:
            decoded: str = (
                chunk.decode("utf-8", errors="replace") if isinstance(chunk, bytes) else str(chunk)
            )
            for line in decoded.split("\n"):
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    payload = _json.loads(data_str)
                except _json.JSONDecodeError:
                    continue

                choices = payload.get("choices", [])
                if not choices:
                    continue

                choice = choices[0]
                delta = choice.get("delta", {})
                text_delta = delta.get("content", "") or ""

                usage = payload.get("usage") or payload.get("x_groq", {}).get("usage", {})
                if usage:
                    input_tokens = int(usage.get("prompt_tokens", input_tokens or 0))

                if not started and text_delta:
                    # first chunk — emit message_start + content_block_start
                    started = True
                    yield _sse_event(
                        "message_start",
                        {
                            "type": "message_start",
                            "message": {
                                "id": message_id,
                                "type": "message",
                                "role": "assistant",
                                "content": [],
                                "model": requested_model,
                                "stop_reason": None,
                                "stop_sequence": None,
                                "usage": {"input_tokens": input_tokens, "output_tokens": 1},
                            },
                        },
                    )
                    yield _sse_event(
                        "content_block_start",
                        {
                            "type": "content_block_start",
                            "index": content_index,
                            "content_block": {"type": "text", "text": ""},
                        },
                    )

                if text_delta:
                    text_buf.append(text_delta)
                    yield _sse_event(
                        "content_block_delta",
                        {
                            "type": "content_block_delta",
                            "index": content_index,
                            "delta": {"type": "text_delta", "text": text_delta},
                        },
                    )

                finish = choice.get("finish_reason")
                if finish:
                    for ev in _anthropic_stop_events(content_index, text_buf, finish):
                        yield ev
                    break

        # Stream ended without an explicit finish_reason — still close cleanly.
        if started:
            for ev in _anthropic_stop_events(content_index, text_buf, "end_turn"):
                yield ev

    return StreamingResponse(_translate(), media_type="text/event-stream")


def _sse_event(event_type: str, payload: object) -> bytes:
    """Encode one SSE event as bytes."""
    body = _json.dumps(payload, separators=(",", ":"))
    return f"event: {event_type}\ndata: {body}\n\n".encode()


def _anthropic_stop_events(
    content_index: int, text_buf: list[str], finish_reason: str
) -> list[bytes]:
    """Return the terminal Anthropic SSE events as a list of byte chunks."""
    output_tokens = len(text_buf)
    stop_reason = (
        "end_turn"
        if finish_reason == "stop"
        else ("max_tokens" if finish_reason == "length" else "end_turn")
    )
    return [
        _sse_event("content_block_stop", {"type": "content_block_stop", "index": content_index}),
        _sse_event(
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                "usage": {"output_tokens": output_tokens},
            },
        ),
        _sse_event("message_stop", {"type": "message_stop"}),
    ]


# ── POST /v1/messages ─────────────────────────────────────────────────


@router.post("/v1/messages", response_model=None)
async def messages(
    request: AnthropicRequest,
    req: Request,
) -> JSONResponse | StreamingResponse:
    """Anthropic Messages API — translated to LIMEN's internal pipeline.

    Non-streaming: returns ``AnthropicResponse`` with text content blocks.
    Streaming: returns SSE with Anthropic event types (Slice 3).

    The ``x-api-key`` header is ignored — LIMEN uses its own key store.
    """
    app_state = req.app.state
    app_state.last_request_at = datetime.now(UTC).isoformat()

    request_id = uuid4().hex[:12]
    messages_tuple = anthropic_to_chat_request(request)

    # ── Resolve model alias through [anthropic] config ──
    resolved_model = _resolve_anthropic_model(request.model, req.app.state.config.anthropic)

    # ── Build internal ChatCompletionRequest ──
    chat_req = ChatCompletionRequest(
        model=resolved_model,
        messages=list(messages_tuple),
        stream=request.stream,
        temperature=request.temperature,
        top_p=request.top_p,
        max_tokens=request.max_tokens,
    )

    ui_event = partial(app_state.broadcast_ui_event, request_id=request_id)

    # ── Admission control ──
    queue_cfg = app_state.queue_config
    queue_depth = await asyncio.to_thread(app_state.database.queue_depth)
    if queue_depth >= queue_cfg.max_pending:
        raise HTTPException(
            status_code=503,
            detail=_anthropic_error_body("overloaded_error", "Queue full"),
            headers={"Retry-After": str(int(queue_cfg.max_wait_seconds))},
        )

    # ── Streaming path ──
    if request.stream:
        return await _anthropic_stream(chat_req, request.model, request_id, app_state)

    # ── Non-streaming path ──
    try:
        response = await durable_dispatch(
            chat_req,
            app_state.database,
            app_state.dispatcher,
            ui_event=ui_event,
            correlation_id=request_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=_anthropic_error_body("api_error", "Upstream provider error"),
        ) from exc

    anthropic_resp = chat_to_anthropic_response(response, model=request.model)
    return JSONResponse(
        content=anthropic_resp.model_dump(),
        headers={"X-Request-Id": request_id},
    )
