"""
Shinon Engine — Full Character Layer (Python, ported from TypeScript v0.3.0)

Components:
  - shinon_patterns.py   — Pattern Engine: regex-based extraction, contradictions, confidence
  - shinon_memory.py     — Two-Tier Memory: SQLite-backed facts (T1) + patterns (T2)
  - shinon_attitudes.py  — Attitude Tracker: -10..+10 dimensions, update rules, tone directives
  - shinon_emotional.py  — Emotional State Machine: 6 states, transitions, tone modifiers
  - shinon_engine.py     — Main Engine: wires all components, replaces passthrough stub

Ported from:
  ShinonLLM-main/character/src/experience/patterns.ts
  ShinonLLM-main/character/src/experience/twoTierMemory.ts
  ShinonLLM-main/character/src/attitudes/tracker.ts
  ShinonLLM-main/character/src/state/emotional.ts
  ShinonLLM-main/character/src/core/identity.ts
"""

from fusion.shinon.shinon_patterns import (
    Pattern,
    PersonalFact,
    PatternType,
    extract_pattern,
    extract_patterns_from_input,
    extract_facts_from_input,
    find_contradictions,
    score_confidence,
)
from fusion.shinon.shinon_memory import (
    TwoTierMemory,
    TwoTierMemoryConfig,
    MemoryAdapter,
    SqliteMemoryAdapter,
)
from fusion.shinon.shinon_attitudes import (
    AttitudeState,
    AttitudeDimension,
    AttitudeUpdateRule,
    ATTITUDE_UPDATE_RULES,
    load_attitude_state,
    save_attitude_state,
    create_attitude_state,
    update_attitude,
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
from fusion.shinon.shinon_engine import (
    ShinonEngine,
    ShinonInput,
    ShinonOutput,
    CharacterContext,
    ShinonIdentity,
    DEFAULT_IDENTITY,
)
from fusion.shinon.shinon_prosa import (
    NarrativeSpec,
    RenderedProsa,
    CritiquePoint,
    CritiqueResult,
    MOODS,
    normalize_tone,
    spec_hash,
    pick_block,
    build_prompt,
    build_fallback,
    build_model_command,
    render,
    render_critique,
    clamp_sentences,
    count_sentences,
)

__all__ = [
    # Patterns
    "Pattern", "PersonalFact", "PatternType",
    "extract_pattern", "extract_patterns_from_input", "extract_facts_from_input",
    "find_contradictions", "score_confidence",
    # Memory
    "TwoTierMemory", "TwoTierMemoryConfig", "MemoryAdapter", "SqliteMemoryAdapter",
    # Attitudes
    "AttitudeState", "AttitudeDimension", "AttitudeUpdateRule",
    "ATTITUDE_UPDATE_RULES", "load_attitude_state", "save_attitude_state",
    "create_attitude_state", "update_attitude", "apply_attitude_rules",
    "should_confront", "get_tone_directive", "format_attitude_for_prompt",
    # Emotional
    "EmotionalState", "SessionEmotionalContext",
    "create_emotional_context", "transition_state", "get_tone_modifier",
    # Prompts
    "PromptContext", "GeneratedPrompt",
    "generate_prompt", "generate_confrontation_prompt", "generate_prompt_minimal",
    # Contracts
    "validate_input", "validate_output", "validate_actions",
    "safe_validate_input", "safe_validate_output", "safe_validate_actions",
    "validate_all", "stable_serialize",
    # Engine
    "ShinonEngine", "ShinonInput", "ShinonOutput", "CharacterContext",
    "ShinonIdentity", "DEFAULT_IDENTITY",
    # Prosa (pure NarrativeSpec -> Text renderer)
    "NarrativeSpec", "RenderedProsa", "CritiquePoint", "CritiqueResult",
    "MOODS", "normalize_tone", "spec_hash", "pick_block", "build_prompt",
    "build_fallback", "build_model_command", "render", "render_critique",
    "clamp_sentences", "count_sentences",
]
