"""
Emotional State Machine — 6 states, transitions, tone modifiers (ported from emotional.ts)

Scope: 0.3.0  |  Source: ShinonLLM-main/character/src/state/emotional.ts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Literal


# ─── Types ────────────────────────────────────────────────────────────

EmotionalState = Literal["neutral", "amused", "annoyed", "concerned", "curious", "confrontational"]

EMOTIONAL_STATES: List[EmotionalState] = [
    "neutral", "amused", "annoyed", "concerned", "curious", "confrontational",
]


@dataclass
class EmotionalTransition:
    state: EmotionalState
    triggered_by: str
    timestamp: str


@dataclass
class SessionEmotionalContext:
    session_id: str
    current_state: EmotionalState = "neutral"
    previous_states: List[EmotionalTransition] = field(default_factory=list)
    state_since: str = ""

    def __post_init__(self):
        if not self.state_since:
            self.state_since = datetime.now(timezone.utc).isoformat()


# ─── Functions ────────────────────────────────────────────────────────


def create_emotional_context(session_id: str) -> SessionEmotionalContext:
    return SessionEmotionalContext(session_id=session_id)


def transition_state(
    context: SessionEmotionalContext,
    new_state: EmotionalState,
    reason: str,
) -> SessionEmotionalContext:
    now = datetime.now(timezone.utc).isoformat()
    return SessionEmotionalContext(
        session_id=context.session_id,
        current_state=new_state,
        previous_states=context.previous_states + [
            EmotionalTransition(state=context.current_state, triggered_by=reason, timestamp=now)
        ],
        state_since=now,
    )


def get_tone_modifier(state: EmotionalState) -> str:
    modifiers: dict[EmotionalState, str] = {
        "neutral": "behalte deinen normalen, trockenen Ton bei",
        "amused": "zeige leichte Belustigung, aber bleib reserviert",
        "annoyed": "sei direkter und kürzer, zeige leichte Irritation",
        "concerned": "zeige vorsichtiges Interesse ohne zu kuschen",
        "curious": "sei offener, aber behalte Skepsis bei",
        "confrontational": "stelle die harte Frage direkt, keine Umschweife",
    }
    return modifiers.get(state, modifiers["neutral"])
