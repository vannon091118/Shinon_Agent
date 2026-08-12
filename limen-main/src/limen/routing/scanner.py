"""Local request analysis used by LIMEN's future automatic routing policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from limen.schemas import ChatCompletionRequest


@dataclass(frozen=True)
class RequestScan:
    """Bounded, provider-independent measurements of one chat request."""

    estimated_input_tokens: int
    estimated_output_tokens: int
    context_tokens: int
    message_count: int
    code_ratio: float
    json_or_tool_complexity: float
    score: int
    category: str

    def to_event_payload(self) -> dict[str, object]:
        """Return the redacted fields used by the audit event."""
        return {
            "estimated_input_tokens": self.estimated_input_tokens,
            "estimated_output_tokens": self.estimated_output_tokens,
            "context_tokens": self.context_tokens,
            "message_count": self.message_count,
            "code_ratio": self.code_ratio,
            "json_or_tool_complexity": self.json_or_tool_complexity,
            "score": self.score,
            "category": self.category,
        }


def scan_request(request: ChatCompletionRequest) -> RequestScan:
    """Estimate request size and complexity without making another API call.

    The estimator intentionally uses character counts rather than a provider
    tokenizer. It is deterministic, cheap, and suitable for observability;
    it does not yet select or override the explicitly requested model.
    """
    text = "\n".join(message.content for message in request.messages)
    characters = len(text)
    estimated_input_tokens = max(1, (characters + 3) // 4)
    estimated_output_tokens = request.max_tokens or 256
    context_tokens = estimated_input_tokens + estimated_output_tokens
    code_markers = ("```", "def ", "class ", "import ", "function ", "SELECT ")
    code_hits = sum(text.count(marker) for marker in code_markers)
    code_ratio = min(1.0, code_hits / max(1, len(request.messages)))
    structured_hits = sum(text.count(marker) for marker in ("{", "}", "[", "]", '"'))
    json_or_tool_complexity = min(1.0, structured_hits / max(12, characters))
    size_score = min(60, context_tokens * 60 // 128_000)
    complexity_score = round((code_ratio * 20) + (json_or_tool_complexity * 20))
    score = min(100, size_score + complexity_score)
    category = (
        "large" if context_tokens > 32_000 else
        "reasoning" if score >= 60 else
        "medium" if context_tokens > 4_000 or score >= 30 else
        "small"
    )
    return RequestScan(
        estimated_input_tokens=estimated_input_tokens,
        estimated_output_tokens=estimated_output_tokens,
        context_tokens=context_tokens,
        message_count=len(request.messages),
        code_ratio=round(code_ratio, 3),
        json_or_tool_complexity=round(json_or_tool_complexity, 3),
        score=score,
        category=category,
    )
