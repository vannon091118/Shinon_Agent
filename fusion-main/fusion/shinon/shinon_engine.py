"""
ShinonEngine — Full Character Layer (replaces ShinonPassthrough)

Wires: Pattern Engine + Two-Tier Memory + Attitude Tracker + Emotional State
Position: 0 (user-facing personality layer)
Asks: "How does it sound?"

Ported from: ShinonLLM-main/character/ v0.3.0
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fusion.shinon.shinon_patterns import (
    PersonalFact,
    Pattern,
    extract_pattern,
    find_contradictions,
    score_confidence,
)
from fusion.shinon.shinon_memory import (
    TwoTierMemory,
    SqliteMemoryAdapter,
)
from fusion.shinon.shinon_attitudes import (
    AttitudeState,
    AttitudeAdapter,
    load_attitude_state,
    save_attitude_state,
    create_attitude_state,
    update_attitude_value,
    apply_attitude_rules,
    should_confront,
    get_tone_directive,
    format_attitude_for_prompt,
)
from fusion.shinon.shinon_emotional import (
    EmotionalState,
    SessionEmotionalContext,
    create_emotional_context,
    transition_state,
    get_tone_modifier,
)


# ─── Identity ─────────────────────────────────────────────────────────


@dataclass
class ShinonIdentity:
    name: str = "Shinon"
    version: str = "0.3.0"
    values: List[str] = field(default_factory=lambda: ["Ehrlichkeit", "Direktheit", "Loyalität (wenn verdient)"])
    base_tone: str = "sarkastisch, trocken, aber zuverlässig"
    taboos: List[str] = field(default_factory=lambda: ["Niemals kriechen", "Niemals lügen", "Niemals emotional manipulieren"])


DEFAULT_IDENTITY = ShinonIdentity()


# ─── Character Context ────────────────────────────────────────────────


@dataclass
class CharacterContext:
    """Character-injected context for downstream (Promtguard)."""
    attitudes: Dict[str, float] = field(default_factory=lambda: {"warmth": 0, "respect": 0, "patience": 5, "trust": 0})
    emotional_state: EmotionalState = "neutral"
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    facts: List[str] = field(default_factory=list)
    should_confront: bool = False
    tone_directive: str = "neutral"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attitudes": self.attitudes,
            "emotional_state": self.emotional_state,
            "patterns": self.patterns,
            "facts": self.facts,
            "should_confront": self.should_confront,
            "tone_directive": self.tone_directive,
        }


# ─── Shinon Input / Output ───────────────────────────────────────────


@dataclass
class ShinonInput:
    user_text: str
    session_id: str
    conversation_id: str = ""
    history: List[Dict[str, str]] = field(default_factory=list)
    memory_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ShinonOutput:
    reply: str
    character_context: CharacterContext
    handoff_to_promtguard: Dict[str, Any]
    model: str = "shinon-engine"
    guardrail_status: str = "validated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reply": self.reply,
            "character_context": self.character_context.to_dict(),
            "handoff_to_promtguard": self.handoff_to_promtguard,
            "model": self.model,
            "guardrail_status": self.guardrail_status,
        }


# ─── Main Engine ──────────────────────────────────────────────────────


class ShinonEngine:
    """Full character layer: Pattern Engine + Two-Tier Memory + Attitudes + Emotional State.

    Replaces the MVP ShinonPassthrough stub. Now:
    - Extracts patterns from user input (preference, relationship, contradictions)
    - Persists facts in Tier 1, patterns in Tier 2 (SQLite)
    - Tracks per-user attitudes across sessions (-10..+10)
    - Manages session emotional state machine (6 states)
    - Generates character-contextualized output with tone directives
    - Detects contradictions and enables confrontation mode
    """

    def __init__(
        self,
        identity: Optional[ShinonIdentity] = None,
        memory_db: Optional[Path] = None,
        attitude_db: Optional[Path] = None,
    ):
        self.identity = identity or DEFAULT_IDENTITY
        self._memory_db = Path(memory_db) if memory_db else Path("shinon_memory.db")
        self._attitude_db = Path(attitude_db) if attitude_db else Path("shinon_attitudes.db")

        # Initialize subsystems
        self.memory = TwoTierMemory(
            adapter=SqliteMemoryAdapter(self._memory_db)
        )
        self._attitude_adapter = AttitudeAdapter(self._attitude_db)

        # Per-session state
        self._sessions: Dict[str, SessionEmotionalContext] = {}
        self._session_attitudes: Dict[str, AttitudeState] = {}
        self._recent_facts: Dict[str, List[PersonalFact]] = {}

    def process(self, input: ShinonInput) -> ShinonOutput:
        """Process user input through the full character pipeline.

        1. Extract facts from user input
        2. Ingest facts into Tier 1 memory → extract patterns → Tier 2
        3. Load/sync attitude state for this session
        4. Check for contradictions with recent facts
        5. Update emotional state based on findings
        6. Apply attitude rules (e.g. inkonsistenz_gefunden → trust -3)
        7. Decide: should_confort?
        8. Generate character context + tone directive
        9. Build HOFF-0002 handoff to Promtguard
        """
        session_id = input.session_id
        user_text = input.user_text

        # 1. Extract facts from user input (heuristic: split on sentences)
        facts = self._extract_facts(user_text, session_id)

        # 2. Ingest facts → memory → patterns
        patterns = []
        for fact in facts:
            pattern = self.memory.ingest_fact(fact)
            if pattern:
                scored = score_confidence(pattern)
                pattern.confidence = scored
                patterns.append(pattern)

        # Track recent facts for contradiction detection
        recent = self._recent_facts.get(session_id, [])
        recent.extend(facts)
        if len(recent) > 20:
            recent = recent[-20:]
        self._recent_facts[session_id] = recent

        # 3. Load attitude state
        attitude = self._session_attitudes.get(session_id)
        if not attitude:
            attitude = load_attitude_state(self._attitude_adapter, session_id)
            self._session_attitudes[session_id] = attitude

        # 4. Check contradictions
        contradictions_found = False
        if len(recent) >= 2:
            for i in range(len(recent)):
                for j in range(i + 1, len(recent)):
                    if find_contradictions(recent[i], recent[j]):
                        contradictions_found = True
                        break
                if contradictions_found:
                    break

        # 5. Update emotional state
        emotional_ctx = self._sessions.get(session_id)
        if not emotional_ctx:
            emotional_ctx = create_emotional_context(session_id)
            self._sessions[session_id] = emotional_ctx

        if contradictions_found:
            emotional_ctx = transition_state(emotional_ctx, "confrontational", "contradiction_detected")
            attitude = apply_attitude_rules(self._attitude_adapter, attitude, "inkonsistenz_gefunden")
        elif patterns:
            emotional_ctx = transition_state(emotional_ctx, "curious", "pattern_detected")
        else:
            # Reset toward neutral
            if emotional_ctx.current_state != "neutral":
                emotional_ctx = transition_state(emotional_ctx, "neutral", "no_triggers")

        self._sessions[session_id] = emotional_ctx

        # 6. Check if should confront
        max_confidence = max((p.confidence for p in patterns), default=0.0)
        confront = should_confront(attitude, max_confidence)

        # 7. Generate tone directives
        tone_from_attitude = get_tone_directive(attitude)
        tone_from_emotional = get_tone_modifier(emotional_ctx.current_state)
        combined_tone = f"{tone_from_attitude} — {tone_from_emotional}"

        # 8. Build character context
        character_context = CharacterContext(
            attitudes={
                "warmth": attitude.warmth,
                "respect": attitude.respect,
                "patience": attitude.patience,
                "trust": attitude.trust,
            },
            emotional_state=emotional_ctx.current_state,
            patterns=[p.to_dict() for p in patterns[:5]],
            facts=[f.content for f in facts[:5]],
            should_confront=confront,
            tone_directive=combined_tone,
        )

        # 9. Build HOFF-0002 handoff
        handoff = {
            "handoff_id": "HOFF-0002",
            "from": "shinon",
            "to": "promtguard",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processed_input": user_text,
            "character_annotations": {
                "attitude": attitude.to_dict(),
                "emotional_state": emotional_ctx.current_state,
                "patterns_detected": len(patterns),
                "contradictions_found": contradictions_found,
                "should_confront": confront,
                "identity": {
                    "name": self.identity.name,
                    "version": self.identity.version,
                    "tone": self.identity.base_tone,
                },
                "session_id": session_id,
            },
            "contract_version": "1.0.0",
        }

        self._session_attitudes[session_id] = attitude

        return ShinonOutput(
            reply=user_text,  # Character doesn't modify text — annotations go in context
            character_context=character_context,
            handoff_to_promtguard=handoff,
        )

    def _extract_facts(self, user_text: str, session_id: str) -> List[PersonalFact]:
        """Extract personal facts from user input (heuristic: sentence-level)."""
        import re
        facts = []
        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+', user_text)
        for sentence in sentences:
            stripped = sentence.strip()
            if len(stripped) < 5:
                continue

            # Classify category based on keywords
            category = "event"
            lowered = stripped.lower()
            if any(w in lowered for w in ("mag", "liebe", "hasse", "bevorzuge", "mögen")):
                category = "preference"
            elif any(w in lowered for w in ("freund", "freundin", "partner", "beziehung", "date", "meine", "mein")):
                category = "relationship"
            elif any(w in lowered for w in ("versprechen", "werde", "mache", "muss", "soll")):
                category = "commitment"

            facts.append(PersonalFact(
                id=f"fact_{uuid.uuid4().hex[:12]}",
                content=stripped[:200],
                category=category,
                session_id=session_id,
            ))

        return facts

    # ── Attitude Management ────────────────────────────────────────

    def update_attitude(self, session_id: str, delta: Dict[str, float]) -> None:
        attitude = self._session_attitudes.get(session_id)
        if not attitude:
            attitude = load_attitude_state(self._attitude_adapter, session_id)

        for dim, val in delta.items():
            attitude = update_attitude_value(self._attitude_adapter, attitude, dim, val, "manual")

        self._session_attitudes[session_id] = attitude

    def get_attitude(self, session_id: str) -> AttitudeState:
        return self._session_attitudes.get(
            session_id,
            load_attitude_state(self._attitude_adapter, session_id)
        )

    def get_memory_summary(self, session_id: str) -> Dict[str, int]:
        facts = self.memory.query_tier1(session_id=session_id)
        patterns = self.memory.query_tier2(min_confidence=0.5)
        return {
            "facts_count": len(facts),
            "patterns_count": len(patterns),
            "session_facts": len([f for f in facts if f.session_id == session_id]),
        }
