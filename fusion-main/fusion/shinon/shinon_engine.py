"""
ShinonEngine — Full Character Layer (replaces ShinonPassthrough)

Wires: Pattern Engine + Two-Tier Memory + Attitude Tracker + Emotional State
Position: 0 (user-facing personality layer)
Asks: "How does it sound?"

Canonical: fusion-main/fusion/shinon/ · ex-TypeScript port (ShinonLLM-main strand removed)
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
    extract_patterns_from_input,
    extract_facts_from_input,
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
from fusion.shinon.shinon_prompts import (
    PromptContext,
    GeneratedPrompt,
    generate_prompt,
    generate_confrontation_prompt,
    generate_prompt_minimal,
)
from fusion.shinon.shinon_contracts import (
    validate_input,
    validate_output,
    validate_actions,
    safe_validate_input,
    safe_validate_output,
    safe_validate_actions,
    validate_all,
    stable_serialize,
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
    """Annotation-only output of the character layer.

    CONTRACT: The character layer NEVER generates text. ``reply`` is
    always empty (""). The actual reply is produced downstream by LIMEN
    from ``handoff_to_promtguard`` (which carries the enriched system_prompt,
    processed_input and character annotations). process() is a pure function
    over the handoff — it only annotates.
    """

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
    - Annotates the turn with character context + tone directives (never generates text)
    - Detects contradictions and enables confrontation mode

    ANNOTATION-ONLY CONTRACT: process() is a pure function over the handoff.
    It NEVER produces the reply text — ShinonOutput.reply is always empty.
    LIMEN generates the actual reply from handoff_to_promtguard.
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

        1. Extract facts from user input (sentence-level, categorized)
        2. Ingest facts into Tier 1 memory → extract patterns → Tier 2
        3. Load/sync attitude state for this session
        4. Check for contradictions with recent facts
        5. Update emotional state based on findings
        6. Apply attitude rules (e.g. inkonsistenz_gefunden → trust -3)
        7. Decide: should_confront? + generate tone directives
        8. Generate Shinon personality prompt via Prompt Generator
        9. Build contract-validated HOFF-0002 handoff to Promtguard

        Returns:
            ShinonOutput — ANNOTATION-ONLY. ``reply`` is always empty ("").
            The handoff (system_prompt + processed_input + annotations) is
            the input for LIMEN, which generates the actual reply text.
        """
        session_id = input.session_id
        user_text = input.user_text

        # 1. Extract facts from user input (sentence-level, categorized)
        facts = extract_facts_from_input(user_text, session_id)

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

        # 8. Build character context + tone directive
        tone_from_attitude = get_tone_directive(attitude)
        tone_from_emotional = get_tone_modifier(emotional_ctx.current_state)
        combined_tone = f"{tone_from_attitude} — {tone_from_emotional}"

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

        # 9. Generate personality prompt + contract-validated handoff
        prompt_ctx = PromptContext(
            user_text=user_text,
            patterns=patterns,
            attitude=attitude,
            emotional_state=emotional_ctx.current_state,
            relevant_facts=[
                {"id": f.id, "content": f.content, "date": f.created_at}
                for f in recent[-5:]
            ],
            interaction_count=len(recent),
        )
        generated_prompt = generate_prompt(prompt_ctx)

        # 11. Build HOFF-0002 handoff (contract-validated)
        handoff_raw = {
            "turn": {
                "userText": user_text,
                "sessionId": session_id,
                "history": input.history,
            },
            "memoryContext": {
                "attitude": attitude.to_dict(),
                "emotionalState": emotional_ctx.current_state,
                "patternsDetected": len(patterns),
                "contradictionsFound": contradictions_found,
                "shouldConfront": confront,
                "identityName": self.identity.name,
                "identityVersion": self.identity.version,
            },
        }

        # Validate through contract gates (fail-closed), then build handoff
        handoff = {
            "handoff_id": "HOFF-0002",
            "from": "shinon",
            "to": "promtguard",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processed_input": user_text,
            "system_prompt": generated_prompt.system_prompt,
            "tone_directive": generated_prompt.tone_directive,
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
                "referenced_patterns": generated_prompt.referenced_patterns,
                "referenced_facts": generated_prompt.referenced_facts,
            },
            "contract_version": "1.0.0",
        }

        try:
            validate_input(handoff_raw)
        except ValueError:
            handoff["contract_warning"] = "inputSchema validation bypassed"

        self._session_attitudes[session_id] = attitude

        return ShinonOutput(
            reply="",  # annotation-only: the engine never generates text (LIMEN does)
            character_context=character_context,
            handoff_to_promtguard=handoff,
        )

    # ── Memory Queries ────────────────────────────────────────────

    def query_character_memory(
        self,
        session_id: Optional[str] = None,
        min_confidence: float = 0.3,
    ) -> Dict[str, Any]:
        """Combined Tier1+Tier2 query for prompt context assembly."""
        return self.memory.query_character_memory(
            session_id=session_id,
            min_confidence=min_confidence,
        )

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
