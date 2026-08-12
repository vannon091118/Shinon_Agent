"""
Pattern Engine — Regex-basierte Pattern-Erkennung (ported from patterns.ts)

Detects preference, relationship, commitment, and contradiction patterns
from personal facts extracted from user input.

Scope: 0.3.0  |  Source: ShinonLLM-main/character/src/experience/patterns.ts
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ─── Types ────────────────────────────────────────────────────────────

PatternType = str  # "preference" | "commitment" | "relationship" | "contradiction"


@dataclass
class PatternExample:
    fact_id: str
    content: str
    date: str


@dataclass
class Pattern:
    """A detected behavioral pattern from user input."""
    id: str
    anchor: str
    type: PatternType
    confidence: float
    examples: List[PatternExample] = field(default_factory=list)
    first_seen: str = ""
    last_reinforced: str = ""
    reinforcement_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "anchor": self.anchor,
            "type": self.type,
            "confidence": self.confidence,
            "examples": [{"factId": e.fact_id, "content": e.content, "date": e.date} for e in self.examples],
            "first_seen": self.first_seen,
            "last_reinforced": self.last_reinforced,
            "reinforcement_count": self.reinforcement_count,
        }


@dataclass
class PersonalFact:
    """A single fact about the user (Tier 1 memory)."""
    id: str
    content: str
    category: str  # "preference" | "event" | "commitment" | "relationship"
    created_at: str = ""
    session_id: str = "default"

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


# ─── Regex Patterns (ported from TypeScript) ──────────────────────────

_PREFERENCE_KEYWORDS = re.compile(
    r'(?:ich\s+)?(?:mag|liebe|hasse|nicht\s+leiden\s+kann|bevorzuge|hasst|magst|liebst)',
    re.IGNORECASE
)
_RELATIONSHIP_KEYWORDS = re.compile(
    r'(?:meine?|mein|mit|freund|freundin|partner|partnerin|beziehung|date|trifft|treffen)',
    re.IGNORECASE
)
_NAME_PATTERN = re.compile(
    r'(?:Freund|Freundin|Partner|Partnerin|mit|mit\s+der|mit\s+dem)\s+([A-Z][a-z]+)'
)


# ─── Extraction Functions ─────────────────────────────────────────────


def extract_pattern(fact: PersonalFact) -> Optional[Pattern]:
    """Extract a pattern from a personal fact.
    
    Supports preference and relationship types (MVP).
    """
    content_lower = fact.content.lower()
    now = fact.created_at

    # Check for preference patterns
    if _PREFERENCE_KEYWORDS.search(fact.content):
        anchor = _extract_preference_anchor(fact.content)
        return Pattern(
            id=f"pattern_pref_{fact.id}",
            anchor=anchor,
            type="preference",
            confidence=0.6,
            examples=[PatternExample(fact_id=fact.id, content=fact.content, date=now)],
            first_seen=now,
            last_reinforced=now,
            reinforcement_count=1,
        )

    # Check for relationship patterns
    if _RELATIONSHIP_KEYWORDS.search(fact.content):
        person_name = _extract_person_name(fact.content)
        if person_name:
            anchor = f"user-beziehung-{person_name.lower()}"
            return Pattern(
                id=f"pattern_rel_{fact.id}",
                anchor=anchor,
                type="relationship",
                confidence=0.7,
                examples=[PatternExample(fact_id=fact.id, content=fact.content, date=now)],
                first_seen=now,
                last_reinforced=now,
                reinforcement_count=1,
            )

    return None


def find_contradictions(fact_a: PersonalFact, fact_b: PersonalFact) -> bool:
    """Detect contradictions between two facts.
    
    Recognizes inconsistencies in relationship patterns (e.g. Anna vs Lisa).
    """
    if fact_a.category != "relationship" and fact_b.category != "relationship":
        return False

    pattern_a = extract_pattern(fact_a)
    pattern_b = extract_pattern(fact_b)

    if not pattern_a or not pattern_b:
        return False
    if pattern_a.type != "relationship" or pattern_b.type != "relationship":
        return False

    name_a = _extract_name_from_anchor(pattern_a.anchor)
    name_b = _extract_name_from_anchor(pattern_b.anchor)

    if name_a and name_b and name_a != name_b:
        # Check temporal proximity (within 30 days)
        try:
            date_a = datetime.fromisoformat(fact_a.created_at.replace("Z", "+00:00"))
            date_b = datetime.fromisoformat(fact_b.created_at.replace("Z", "+00:00"))
            days_diff = abs((date_a - date_b).total_seconds()) / (60 * 60 * 24)
            if days_diff < 30:
                return True
        except (ValueError, TypeError):
            pass

    return False


def score_confidence(pattern: Pattern) -> float:
    """Calculate pattern confidence based on frequency, recency, and consistency."""
    now = datetime.now(timezone.utc)

    try:
        last_reinforced = datetime.fromisoformat(pattern.last_reinforced.replace("Z", "+00:00"))
        first_seen = datetime.fromisoformat(pattern.first_seen.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return pattern.confidence

    # Factor 1: Frequency (max 0.4)
    frequency_score = min(0.4, pattern.reinforcement_count * 0.1)

    # Factor 2: Recency (max 0.3, decays over time)
    days_since = (now - last_reinforced).total_seconds() / (60 * 60 * 24)
    recency_score = max(0.0, 0.3 - (days_since * 0.01))

    # Factor 3: Consistency (max 0.3, grows with pattern age)
    pattern_age = (last_reinforced - first_seen).total_seconds() / (60 * 60 * 24)
    consistency_score = min(0.3, pattern_age * 0.05)

    base = 0.5
    total = base + frequency_score + recency_score + consistency_score
    return max(0.0, min(1.0, total))


# ─── Helper Functions ─────────────────────────────────────────────────


def _extract_preference_anchor(content: str) -> str:
    match = re.search(
        r'(?:mag|liebe|hasse|bevorzuge)\s+(?:die|das|den|dem)?\s*([a-zäöüß]+(?:\s+[a-zäöüß]+)?)',
        content, re.IGNORECASE
    )
    if match:
        return f"user-pref-{match.group(1).lower().strip()}"
    return f"user-pref-{content[:20].lower().replace(' ', '-')}"


def _extract_person_name(content: str) -> Optional[str]:
    matches = list(_NAME_PATTERN.finditer(content))
    if matches:
        return matches[0].group(1).strip()

    fallback = re.search(r'(?:mit|Freund|Freundin)\s+([A-Z][a-z]+)', content)
    if fallback:
        return fallback.group(1).strip()

    return None


def _extract_name_from_anchor(anchor: str) -> Optional[str]:
    match = re.search(r'user-beziehung-(.+)', anchor)
    return match.group(1).lower() if match else None


# ─── Batch Extraction: Input Text → Patterns ──────────────────────────


def extract_patterns_from_input(
    user_text: str,
    session_id: str = "default",
) -> List[Pattern]:
    """Extract ALL patterns from raw user input in one call.

    Splits input into sentences, creates PersonalFacts with category
    classification, then runs extract_pattern() on each fact.
    Returns only non-None patterns, sorted by confidence descending.

    This is the combined entry point that replaces the two-step:
      1. _extract_facts(text) → List[PersonalFact]
      2. extract_pattern(fact) → Optional[Pattern]

    Args:
        user_text: Raw user input text
        session_id: Session identifier for fact ownership

    Returns:
        List of extracted patterns, sorted by confidence (highest first)
    """
    facts = _extract_facts_from_text(user_text, session_id)
    patterns = []
    for fact in facts:
        pattern = extract_pattern(fact)
        if pattern:
            scored = score_confidence(pattern)
            pattern.confidence = scored
            patterns.append(pattern)
    return sorted(patterns, key=lambda p: p.confidence, reverse=True)


def extract_facts_from_input(
    user_text: str,
    session_id: str = "default",
) -> List[PersonalFact]:
    """Extract PersonalFacts from raw user input.

    Sentence-level extraction with keyword-based category classification.
    Returns all facts, not just those with extractable patterns.

    Args:
        user_text: Raw user input text
        session_id: Session identifier for fact ownership

    Returns:
        List of PersonalFacts
    """
    return _extract_facts_from_text(user_text, session_id)


def _extract_facts_from_text(user_text: str, session_id: str) -> List[PersonalFact]:
    """Internal: sentence-level fact extraction with category classification."""
    import uuid
    facts = []
    sentences = re.split(r'[.!?]+', user_text)
    for sentence in sentences:
        stripped = sentence.strip()
        if len(stripped) < 5:
            continue

        lowered = stripped.lower()

        # Category classification (Ported from TypeScript keyword sets)
        if any(w in lowered for w in ("mag", "liebe", "hasse", "bevorzuge", "mögen",
                                       "liebst", "hasst", "magst")):
            category = "preference"
        elif any(w in lowered for w in ("freund", "freundin", "partner", "partnerin",
                                          "beziehung", "date", "meine", "mein", "trifft",
                                          "treffen")):
            category = "relationship"
        elif any(w in lowered for w in ("versprechen", "versprochen", "werde", "mache",
                                          "muss", "soll", "garantiere", "schwöre")):
            category = "commitment"
        else:
            category = "event"

        facts.append(PersonalFact(
            id=f"fact_{uuid.uuid4().hex[:12]}",
            content=stripped[:200],
            category=category,
            session_id=session_id,
        ))

    return facts
