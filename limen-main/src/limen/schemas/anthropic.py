"""Anthropic Messages API schemas for request/response translation.

Translates between the Anthropic-native API shape and LIMEN's internal
OpenAI-compatible ``ChatCompletionRequest`` / ``ChatCompletionResponse``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from limen.schemas import ChatCompletionResponse, ChatMessage


class AnthropicTextBlock(BaseModel):
    """A text content block in the Anthropic response."""
    type: Literal["text"] = "text"
    text: str


class AnthropicMessage(BaseModel):
    """An Anthropic message (user or assistant turn)."""
    role: Literal["user", "assistant"]
    content: str | list[AnthropicTextBlock]


class AnthropicRequest(BaseModel):
    """POST /v1/messages request body."""

    model_config = ConfigDict(extra="ignore")

    model: str = Field(min_length=1)
    messages: list[AnthropicMessage] = Field(min_length=1)
    max_tokens: int = Field(ge=1)
    system: str | list[dict[str, Any]] | None = None
    stop_sequences: list[str] | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    stream: bool = False


class AnthropicUsage(BaseModel):
    """Token usage block in the Anthropic response."""
    input_tokens: int = 0
    output_tokens: int = 0


class AnthropicResponse(BaseModel):
    """Non-streaming Anthropic Messages API response."""

    model_config = ConfigDict(extra="ignore")

    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    content: list[AnthropicTextBlock]
    model: str
    stop_reason: str = "end_turn"
    stop_sequence: str | None = None
    usage: AnthropicUsage


class AnthropicErrorDetail(BaseModel):
    """Anthropic error payload."""
    type: str
    message: str


class AnthropicErrorResponse(BaseModel):
    """Anthropic error envelope."""
    type: Literal["error"] = "error"
    error: AnthropicErrorDetail


# ── Translation helpers ───────────────────────────────────────────────


def _extract_text(content: str | list[AnthropicTextBlock]) -> str:
    if isinstance(content, str):
        return content
    return "".join(block.text for block in content if block.type == "text")


def anthropic_to_chat_request(ar: AnthropicRequest) -> tuple[ChatMessage, ...]:
    """Convert Anthropic messages to LIMEN ChatMessages.

    Returns a tuple of ChatMessages suitable for ``ChatCompletionRequest.messages``.
    The Anthropic ``system`` field becomes a leading system message.
    """
    messages: list[ChatMessage] = []

    # system prompt → ChatMessage(role="system", ...)
    if ar.system is not None:
        if isinstance(ar.system, str):
            messages.append(ChatMessage(role="system", content=ar.system))
        else:
            # system as list of text blocks (Claude extended format)
            parts = [
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in ar.system
            ]
            messages.append(ChatMessage(role="system", content="\n".join(p for p in parts if p)))

    for msg in ar.messages:
        text = _extract_text(msg.content)
        role: Literal["system", "user", "assistant", "tool", "function"] = (
            "user" if msg.role == "user" else "assistant"
        )
        messages.append(ChatMessage(role=role, content=text))

    return tuple(messages)


FINISH_REASON_MAP: dict[str, str] = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
    "content_filter": "end_turn",
}


def chat_to_anthropic_response(
    cr: ChatCompletionResponse,
    *,
    model: str,
) -> AnthropicResponse:
    """Convert a LIMEN ChatCompletionResponse to Anthropic format."""
    choice = cr.choices[0] if cr.choices else None
    text = choice.message.content if choice else ""
    finish = choice.finish_reason if choice else None

    stop_reason = FINISH_REASON_MAP.get(str(finish), "end_turn") if finish else "end_turn"

    return AnthropicResponse(
        id=cr.id,
        content=[AnthropicTextBlock(text=text)],
        model=model,
        stop_reason=stop_reason,
        usage=AnthropicUsage(
            input_tokens=cr.usage.prompt_tokens or 0 if cr.usage else 0,
            output_tokens=cr.usage.completion_tokens or 0 if cr.usage else 0,
        ),
    )
