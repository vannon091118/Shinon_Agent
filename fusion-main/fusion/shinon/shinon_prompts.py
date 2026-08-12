"""
Shinon Prompt Generator — Template-basierte Prompt-Assembly (ported from generator.ts)

Generates "Shinons Gedanken"-prompts for the LLM by rendering a template
with current attitude, patterns, facts, and emotional state context.

Scope: 0.3.0  |  Canonical: fusion-main/fusion/shinon/ (ex-TypeScript port)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from fusion.shinon.shinon_patterns import Pattern, PersonalFact
from fusion.shinon.shinon_attitudes import AttitudeState, get_tone_directive
from fusion.shinon.shinon_emotional import EmotionalState, get_tone_modifier


# ─── Types ────────────────────────────────────────────────────────────


@dataclass
class PromptContext:
    """All context needed to generate a Shinon personality prompt."""
    user_text: str
    patterns: List[Pattern] = field(default_factory=list)
    attitude: Optional[AttitudeState] = None
    emotional_state: EmotionalState = "neutral"
    relevant_facts: List[Dict[str, str]] = field(default_factory=list)
    interaction_count: int = 1


@dataclass
class GeneratedPrompt:
    """A fully rendered prompt with metadata about what was referenced."""
    system_prompt: str
    user_prompt: str
    tone_directive: str
    referenced_patterns: List[str] = field(default_factory=list)
    referenced_facts: List[str] = field(default_factory=list)


# ─── Template ─────────────────────────────────────────────────────────

SHINON_PROMPT_TEMPLATE = """Du bist Shinon. Du hast mit diesem User {interaction_count} Interaktionen.

Deine aktuelle Haltung:
- Wärme: {warmth}/10 ({warmth_description})
- Respekt: {respect}/10 ({respect_description})
- Geduld: {patience}/10 ({patience_description})
- Vertrauen: {trust}/10 ({trust_description})

Erkannte Muster:
{patterns}

Relevante Erinnerungen:
{facts}

Deine aktuelle Stimmung: {emotional_state}
{tone_directive}

User Input: {user_text}

Antworte als Shinon. Dein Ton sollte deine Haltung widerspiegeln.
Wenn Geduld < 4, sei direkter/sarkastischer.
Wenn ein Muster mit Konfidenz > 0.8 erkannt wurde, adressiere es explizit."""

SHINON_PROMPT_TEMPLATE_EN = """You are Shinon. You have had {interaction_count} interactions with this user.

Your current stance:
- Warmth: {warmth}/10 ({warmth_description})
- Respect: {respect}/10 ({respect_description})
- Patience: {patience}/10 ({patience_description})
- Trust: {trust}/10 ({trust_description})

Detected patterns:
{patterns}

Relevant memories:
{facts}

Your current mood: {emotional_state}
{tone_directive}

User Input: {user_text}

Respond as Shinon. Your tone should reflect your stance.
If patience < 4, be more direct/sarcastic.
If a pattern with confidence > 0.8 was detected, address it explicitly."""


# ─── Description Helpers ──────────────────────────────────────────────


def _describe_dimension(value: float, dimension: str) -> str:
    """Convert a -10..+10 attitude value to a human-readable description."""
    if dimension == "patience":
        # Patience has neutral at 5
        if value >= 8:
            return "sehr geduldig"
        if value >= 5:
            return "normal geduldig"
        if value >= 3:
            return "leicht genervt"
        if value >= 0:
            return "genervt"
        return "extrem ungeduldig"

    # Warmth, Respect, Trust: neutral at 0
    abs_val = abs(value)
    direction = "positiv" if value >= 0 else "negativ"

    if abs_val >= 8:
        return f"extrem {direction}"
    if abs_val >= 5:
        return f"deutlich {direction}"
    if abs_val >= 2:
        return f"leicht {direction}"
    return "neutral"


def _format_patterns(patterns: List[Pattern]) -> str:
    """Format patterns as a readable bullet list."""
    if not patterns:
        return "  (keine Muster erkannt)"

    lines = []
    for p in patterns[:10]:  # Max 10 patterns in prompt
        pct = int(p.confidence * 100)
        type_label = {
            "preference": "Präferenz",
            "commitment": "Commitment",
            "relationship": "Beziehung",
            "contradiction": "Widerspruch",
        }.get(p.type, p.type)

        examples_str = ""
        if p.examples:
            latest = p.examples[-1]
            examples_str = f' — z.B. "{latest.content[:80]}"'

        lines.append(f"  [{type_label}] {p.anchor} ({pct}% sicher, "
                    f"{p.reinforcement_count}x bestätigt){examples_str}")

    return "\n".join(lines)


def _format_facts(facts: List[Dict[str, str]]) -> str:
    """Format facts as a readable bullet list."""
    if not facts:
        return "  (keine relevanten Erinnerungen)"

    lines = []
    for f in facts[:10]:  # Max 10 facts
        content = f.get("content", "")
        date = f.get("date", "unbekannt")
        lines.append(f'  [{date[:10]}] "{content[:120]}"')

    return "\n".join(lines)


# ─── Prompt Generation ────────────────────────────────────────────────


def generate_prompt(context: PromptContext, language: str = "de") -> GeneratedPrompt:
    """Generate a Shinon personality prompt from context.

    Renders the SHINON_PROMPT_TEMPLATE with actual values substituted
    for all {{placeholders}}. Produces a system prompt (Shinon's
    internal monologue) and a user prompt (the actual user input).

    Args:
        context: All context needed for prompt generation
        language: "de" or "en" for template language

    Returns:
        GeneratedPrompt with rendered system_prompt, user_prompt, tone directives
    """
    att = context.attitude
    if att is None:
        # Default neutral attitude
        from fusion.shinon.shinon_attitudes import create_attitude_state
        att = create_attitude_state("default")

    # Build descriptions
    warmth_desc = _describe_dimension(att.warmth, "warmth")
    respect_desc = _describe_dimension(att.respect, "respect")
    patience_desc = _describe_dimension(att.patience, "patience")
    trust_desc = _describe_dimension(att.trust, "trust")

    # Format patterns and facts
    patterns_str = _format_patterns(context.patterns)
    facts_str = _format_facts(context.relevant_facts)

    # Tone directives
    tone_from_attitude = get_tone_directive(att)
    tone_from_emotional = get_tone_modifier(context.emotional_state)
    combined_tone = f"{tone_from_attitude} — {tone_from_emotional}"

    # Select template
    template = SHINON_PROMPT_TEMPLATE if language == "de" else SHINON_PROMPT_TEMPLATE_EN

    # Render
    system_prompt = template.format(
        interaction_count=context.interaction_count,
        warmth=f"{att.warmth:+.0f}",
        warmth_description=warmth_desc,
        respect=f"{att.respect:+.0f}",
        respect_description=respect_desc,
        patience=f"{att.patience:+.0f}",
        patience_description=patience_desc,
        trust=f"{att.trust:+.0f}",
        trust_description=trust_desc,
        patterns=patterns_str,
        facts=facts_str,
        emotional_state=context.emotional_state,
        tone_directive=combined_tone,
        user_text=context.user_text,
    )

    return GeneratedPrompt(
        system_prompt=system_prompt,
        user_prompt=context.user_text,
        tone_directive=combined_tone,
        referenced_patterns=[p.anchor for p in context.patterns],
        referenced_facts=[f.get("id", "") for f in context.relevant_facts],
    )


def generate_confrontation_prompt(
    pattern: Pattern,
    contradiction: Dict[str, Dict[str, str]],
) -> str:
    """Generate a direct confrontation prompt when a contradiction is detected.

    Args:
        pattern: The pattern that contains the contradiction
        contradiction: Dict with 'older' and 'newer' entries,
                       each having 'date' and 'content'

    Returns:
        Confrontation prompt string
    """
    older = contradiction.get("older", {})
    newer = contradiction.get("newer", {})

    older_date = older.get("date", "?")
    older_content = older.get("content", "?")
    newer_date = newer.get("date", "?")
    newer_content = newer.get("content", "?")

    return (
        f"Ich muss dich auf etwas ansprechen. "
        f"Am {older_date} hast du gesagt: \"{older_content}\". "
        f"Jetzt ({newer_date}) sagst du: \"{newer_content}\". "
        f"Was ist da los?"
    )


def generate_prompt_minimal(
    user_text: str,
    attitude: Optional[AttitudeState] = None,
    emotional_state: EmotionalState = "neutral",
) -> GeneratedPrompt:
    """Generate a minimal Shinon prompt — fast path when no patterns/facts exist.

    Useful for first interactions or when memory is cold.
    """
    return generate_prompt(PromptContext(
        user_text=user_text,
        patterns=[],
        attitude=attitude,
        emotional_state=emotional_state,
        relevant_facts=[],
        interaction_count=1,
    ))
