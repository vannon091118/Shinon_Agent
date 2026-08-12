"""OpenAI Responses API schemas — used by Codex CLI.

Translates between the Responses API shape and LIMEN's internal
OpenAI-compatible ``ChatCompletionRequest`` / ``ChatCompletionResponse``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from limen.schemas import ChatCompletionResponse


class CodexRequest(BaseModel):
    """POST /v1/responses request body (subset)."""

    model_config = ConfigDict(extra="ignore")

    model: str = Field(min_length=1)
    input: str | list[dict[str, Any]] = Field(min_length=1)
    instructions: str | None = None
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = Field(default=None, ge=1)


class CodexOutputText(BaseModel):
    """Text output block in the Responses response."""
    type: Literal["output_text"] = "output_text"
    text: str
    annotations: list[Any] = []


class CodexOutputMessage(BaseModel):
    """Message output block wrapping text content."""
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    content: list[CodexOutputText]


class CodexUsage(BaseModel):
    """Token usage in Responses API format."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class CodexResponse(BaseModel):
    """Non-streaming Responses API response."""

    model_config = ConfigDict(extra="ignore")

    id: str
    object: Literal["response"] = "response"
    model: str
    output: list[CodexOutputMessage]
    usage: CodexUsage | None = None


# ── Translation ────────────────────────────────────────────────────────


def codex_input_to_text(input_val: str | list[dict[str, Any]]) -> str:
    """Extract plain text from Codex input."""
    if isinstance(input_val, str):
        return input_val
    parts: list[str] = []
    for item in input_val:
        if isinstance(item, dict):
            text = item.get("text", "") or ""
            parts.append(str(text))
    return "\n".join(parts)


def chat_to_codex_response(cr: ChatCompletionResponse, *, model: str) -> CodexResponse:
    """Convert LIMEN ChatCompletionResponse → Codex Responses format."""
    choice = cr.choices[0] if cr.choices else None
    text = choice.message.content if choice else ""

    return CodexResponse(
        id=cr.id,
        model=model,
        output=[
            CodexOutputMessage(
                content=[CodexOutputText(text=text)],
            )
        ],
        usage=CodexUsage(
            input_tokens=cr.usage.prompt_tokens or 0 if cr.usage else 0,
            output_tokens=cr.usage.completion_tokens or 0 if cr.usage else 0,
            total_tokens=cr.usage.total_tokens or 0 if cr.usage else 0,
        ),
    )
