"""Codex / OpenAI Responses API route — translated to LIMEN's pipeline."""

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
from limen.schemas import ChatCompletionRequest, ChatMessage
from limen.schemas.codex import (
    CodexRequest,
    chat_to_codex_response,
    codex_input_to_text,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

router = APIRouter()


def _sse_event(event_type: str, payload: object) -> bytes:
    body = _json.dumps(payload, separators=(",", ":"))
    return f"event: {event_type}\ndata: {body}\n\n".encode()


async def _codex_stream(
    chat_req: ChatCompletionRequest,
    requested_model: str,
    request_id: str,
    app_state: Any,
) -> StreamingResponse:
    """Streaming Codex Responses — translate OpenAI SSE to response.output_text.delta."""
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
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    response_id = f"resp_{request_id}"

    async def _translate() -> AsyncIterator[bytes]:  # noqa: F821
        started = False
        async for chunk in openai_stream.body_iterator:
            decoded = chunk.decode("utf-8", errors="replace") if isinstance(chunk, bytes) else str(chunk)
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
                delta = choices[0].get("delta", {})
                text_delta = delta.get("content", "") or ""
                if not text_delta:
                    continue
                if not started:
                    started = True
                    yield _sse_event("response.created", {
                        "type": "response.created",
                        "response": {
                            "id": response_id,
                            "object": "response",
                            "model": requested_model,
                            "output": [],
                        },
                    })
                yield _sse_event("response.output_text.delta", {
                    "type": "response.output_text.delta",
                    "item_id": response_id,
                    "output_index": 0,
                    "content_index": 0,
                    "delta": text_delta,
                })
                finish = choices[0].get("finish_reason")
                if finish:
                    yield _sse_event("response.completed", {
                        "type": "response.completed",
                        "response": {"id": response_id, "object": "response"},
                    })

    return StreamingResponse(_translate(), media_type="text/event-stream")


@router.post("/v1/responses", response_model=None)
async def responses(
    request: CodexRequest,
    req: Request,
) -> JSONResponse | StreamingResponse:
    """OpenAI Responses API (Codex) — translated to LIMEN's pipeline.

    Non-streaming: ``CodexResponse`` with output_text blocks.
    Streaming: SSE with ``response.output_text.delta`` events.
    """
    app_state = req.app.state
    app_state.last_request_at = datetime.now(UTC).isoformat()

    request_id = uuid4().hex[:12]

    # ── Build internal ChatCompletionRequest ──
    text_input = codex_input_to_text(request.input)
    messages = [ChatMessage(role="user", content=text_input)]
    if request.instructions:
        messages.insert(0, ChatMessage(role="system", content=request.instructions))

    chat_req = ChatCompletionRequest(
        model=request.model,
        messages=messages,
        stream=request.stream,
        temperature=request.temperature,
        top_p=request.top_p,
        max_tokens=request.max_output_tokens,
    )

    # ── Admission control ──
    queue_cfg = app_state.queue_config
    queue_depth = await asyncio.to_thread(app_state.database.queue_depth)
    if queue_depth >= queue_cfg.max_pending:
        raise HTTPException(
            status_code=503,
            detail={"error": {"message": "Queue full", "type": "queue_full", "code": "503", "param": None}},
            headers={"Retry-After": str(int(queue_cfg.max_wait_seconds))},
        )

    # ── Streaming path ──
    if request.stream:
        return await _codex_stream(chat_req, request.model, request_id, app_state)

    # ── Non-streaming path ──
    ui_event = partial(app_state.broadcast_ui_event, request_id=request_id)
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
            detail={"error": {"message": "Upstream error", "type": "api_error", "code": "502", "param": None}},
        ) from exc

    codex_resp = chat_to_codex_response(response, model=request.model)
    return JSONResponse(content=codex_resp.model_dump(), headers={"X-Request-Id": request_id})
