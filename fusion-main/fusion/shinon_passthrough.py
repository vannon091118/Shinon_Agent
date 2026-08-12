"""
Shinon Passthrough — Minimal Character Layer (Python)

MVP mode: No Pattern Engine, no full Two-Tier Memory.
Default neutral attitudes, pass-through handoff to Promtguard via HOFF-0002.

Contract: shinon.contract.json v1.0.0
Position: 0 (user-facing personality layer)
Asks: "How does it sound?"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ─── Attitude State ──────────────────────────────────────────────────


@dataclass
class AttitudeState:
    """Character attitude dimensions (-10 .. +10). MVP: neutral defaults."""

    warmth: float = 0.0
    respect: float = 0.0
    patience: float = 0.0
    trust: float = 0.0
    emotional_state: str = "neutral"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "warmth": self.warmth,
            "respect": self.respect,
            "patience": self.patience,
            "trust": self.trust,
            "emotional_state": self.emotional_state,
        }

    @classmethod
    def neutral(cls) -> "AttitudeState":
        return cls()


# ─── Character Context ───────────────────────────────────────────────


@dataclass
class CharacterContext:
    """Character-injected context for downstream (Promtguard)."""

    attitudes: AttitudeState = field(default_factory=AttitudeState.neutral)
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    facts: List[str] = field(default_factory=list)
    should_confront: bool = False
    tone_directive: str = "neutral"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attitudes": self.attitudes.to_dict(),
            "emotional_state": self.attitudes.emotional_state,
            "patterns": self.patterns,
            "facts": self.facts,
            "should_confront": self.should_confront,
            "tone_directive": self.tone_directive,
        }


# ─── Shinon Input / Output ──────────────────────────────────────────


@dataclass
class ShinonInput:
    """Raw user input per shinon.contract.json input schema."""

    user_text: str
    session_id: str
    conversation_id: str = ""
    history: List[Dict[str, str]] = field(default_factory=list)
    memory_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ShinonOutput:
    """Character-contextualized output ready for Promtguard handoff.

    ANNOTATION-ONLY: ``reply`` is always empty — the character layer never
    generates text. LIMEN generates the reply from handoff_to_promtguard.
    """

    reply: str
    character_context: CharacterContext
    handoff_to_promtguard: Dict[str, Any]
    model: str = "passthrough"
    guardrail_status: str = "validated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reply": self.reply,
            "character_context": self.character_context.to_dict(),
            "handoff_to_promtguard": self.handoff_to_promtguard,
            "model": self.model,
            "guardrail_status": self.guardrail_status,
        }


# ─── Identity ────────────────────────────────────────────────────────

DEFAULT_IDENTITY = {
    "name": "Buffy",
    "role": "strategic coding assistant",
    "tone": "precise, direct, helpful",
    "style": "minimalist, no filler",
}


# ─── Passthrough Engine ─────────────────────────────────────────────


class ShinonPassthrough:
    """Minimal character layer. Passes user_text through with neutral context.

    MVP mode: No Pattern Engine. No Two-Tier Memory.
    Neutral attitudes. Default identity. Produces HOFF-0002 handoff.
    """

    def __init__(self, identity: Optional[Dict[str, str]] = None):
        self.identity = identity or DEFAULT_IDENTITY
        self._session_attitudes: Dict[str, AttitudeState] = {}

    def process(self, input: ShinonInput) -> ShinonOutput:
        """Process user input through character layer → handoff to Promtguard.

        Args:
            input: Raw user input with session context.

        Returns:
            ShinonOutput with character_context and handoff_to_promtguard payload.
        """
        # Get or create session attitude
        attitude = self._session_attitudes.get(
            input.session_id, AttitudeState.neutral()
        )

        # Build character context (MVP: neutral, no patterns, no facts from memory)
        character_context = CharacterContext(
            attitudes=attitude,
            patterns=[],
            facts=[],
            should_confront=False,
            tone_directive="neutral",
        )

        # Annotation-only: the passthrough never generates text either.
        reply = ""

        # Build HOFF-0002 handoff payload
        handoff = {
            "handoff_id": "HOFF-0002",
            "from": "shinon",
            "to": "promtguard",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processed_input": input.user_text,
            "character_annotations": {
                "attitude": attitude.to_dict(),
                "identity": self.identity,
                "session_id": input.session_id,
            },
            "contract_version": "1.0.0",
        }

        return ShinonOutput(
            reply=reply,
            character_context=character_context,
            handoff_to_promtguard=handoff,
        )

    def update_attitude(self, session_id: str, delta: Dict[str, float]) -> None:
        """Adjust attitude for a session (e.g., +0.5 warmth)."""
        current = self._session_attitudes.get(
            session_id, AttitudeState.neutral()
        )
        for attr, val in delta.items():
            if hasattr(current, attr):
                new_val = max(-10.0, min(10.0, getattr(current, attr) + val))
                setattr(current, attr, new_val)
        self._session_attitudes[session_id] = current

    def get_attitude(self, session_id: str) -> AttitudeState:
        return self._session_attitudes.get(
            session_id, AttitudeState.neutral()
        )
