"""Re-export domain schemas for backward compatibility.

Prefer importing from ``limen.schemas`` directly in non-HTTP modules
(adapters, routing, workers).  This module exists so existing callers
in the API layer don't break.
"""

from limen.schemas.domain import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
    ErrorEnvelope,
    ErrorResponse,
)

__all__ = [
    "ChatCompletionChoice",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatCompletionUsage",
    "ChatMessage",
    "ErrorEnvelope",
    "ErrorResponse",
]
