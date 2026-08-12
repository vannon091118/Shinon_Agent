"""Domain types for LIMEN — no HTTP/FastAPI dependency.

Adapters, routing, workers, and scanners import from here instead of
``limen.api.schemas`` so the domain model sits below the presentation layer.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """Single OpenAI chat message entry."""

    model_config = ConfigDict(extra="ignore")

    role: Literal["system", "user", "assistant", "tool", "function"]
    content: str
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    """Public OpenAI-compatible request body."""

    model_config = ConfigDict(extra="ignore")

    model: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, ge=1)
    user: str | None = None

    @property
    def is_streaming(self) -> bool:
        return self.stream


class ChatCompletionChoice(BaseModel):
    """One completion alternative in the response."""

    index: int
    message: ChatMessage
    finish_reason: str | None = None


class ChatCompletionUsage(BaseModel):
    """Optional OpenAI-style usage block, passthrough if reported by provider."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ChatCompletionResponse(BaseModel):
    """Successful OpenAI-compatible completion response shape."""

    model_config = ConfigDict(extra="ignore")

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage | None = None
    system_fingerprint: str | None = None


class ErrorEnvelope(BaseModel):
    """OpenAI-compatible error payload used for every public 4xx/5xx response."""

    message: str
    type: str
    param: str | None = None
    code: str | None = None


class ErrorResponse(BaseModel):
    """Wrapper carrying an error envelope."""

    error: ErrorEnvelope

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-compatible dict preserving optional fields."""
        payload: dict[str, Any] = {
            "message": self.error.message,
            "type": self.error.type,
        }
        if self.error.param is not None:
            payload["param"] = self.error.param
        if self.error.code is not None:
            payload["code"] = self.error.code
        return {"error": payload}
