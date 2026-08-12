"""
Shinon + Promtguard + KARMA Fusion — Event-Driven Control Plane Runtime

Flow (event-driven, non-linear):
    User → runtime.input event
         → Shinon (subscriber) → shinon.output event
         → Promtguard (subscriber) → promtguard.claims event
         → KARMA (subscriber) → karma.falsified event
         → runtime.completed event

Each component subscribes to events and publishes results asynchronously.
Replaces the linear HOFF-0001→HOFF-0002→... handoff sequence.
"""

# ── Shinon Engine (NEW — Pattern Engine + Two-Tier Memory + Attitudes) ─
from fusion.shinon import (
    ShinonEngine,
    ShinonInput,
    ShinonOutput,
    CharacterContext,
    AttitudeState,
    TwoTierMemory,
)

# ── Legacy (sync) ─────────────────────────────────────────────────
from fusion.shinon_passthrough import ShinonPassthrough
from fusion.promtguard_claims import (
    PromtguardClaims,
    Claim,
    ClaimStatus,
    Handoff,
    ContextToken,
)
from fusion.fusion_bridge import (
    FusionBridge,
    FusionResult,
)

# ── Event-Driven Runtime (NEW) ────────────────────────────────────
from fusion.event_bus import (
    AsyncEventBus,
    Event,
    ReplayBus,
    ReplayReport,
    get_event_bus,
    EVENT_RUNTIME_INPUT,
    EVENT_SHINON_OUTPUT,
    EVENT_PROMTGUARD_CLAIMS,
    EVENT_PROMTGUARD_HANDOFF,
    EVENT_KARMA_FALSIFIED,
    EVENT_KARMA_EXPERIENCE,
    EVENT_RUNTIME_ERROR,
    EVENT_RUNTIME_COMPLETED,
    EVENT_GOAL_CHAIN_TRIGGERED,
    EVENT_GOAL_CHAIN_SKILL_CHAIN,
    EVENT_GOAL_CHAIN_REWORK,
)
from fusion.karma_subscriber import (
    KARMASubscriber,
    FalsificationResult,
    ExperienceRecord,
)
from fusion.goal_chain_subscriber import (
    GoalChainSubscriber,
    SkillChainTrigger,
    ReworkTrigger,
)
from fusion.limen_subscriber import (
    LIMENSubscriber,
    RateLimitEvent,
    KeyStateEvent,
    BudgetWarning,
)
from fusion.sanitize_schema import (
    sanitize,
    sanitize_by_schema_name,
    assert_patches_allowed,
    CLAIM_SCHEMA,
    DISPATCH_PATCH_SCHEMA,
)
from fusion.event_runtime import (
    ControlPlaneRuntime,
    RuntimeResult,
    run_pipeline,
)

__all__ = [
    # Shinon Engine (NEW)
    "ShinonEngine", "ShinonInput", "ShinonOutput",
    "CharacterContext", "AttitudeState", "TwoTierMemory",
    # Legacy
    "ShinonPassthrough",
    "PromtguardClaims", "Claim", "ClaimStatus", "Handoff", "ContextToken",
    "FusionBridge", "FusionResult",
    # Event Bus
    "AsyncEventBus", "Event", "get_event_bus",
    "EVENT_RUNTIME_INPUT", "EVENT_SHINON_OUTPUT",
    "EVENT_PROMTGUARD_CLAIMS", "EVENT_PROMTGUARD_HANDOFF",
    "EVENT_KARMA_FALSIFIED", "EVENT_KARMA_EXPERIENCE",
    "EVENT_RUNTIME_ERROR", "EVENT_RUNTIME_COMPLETED",
    # Subscribers
    "KARMASubscriber", "FalsificationResult", "ExperienceRecord",
    # Goal-Chain Subscriber
    "GoalChainSubscriber", "SkillChainTrigger", "ReworkTrigger",
    # LIMEN Subscriber
    "LIMENSubscriber", "RateLimitEvent", "KeyStateEvent", "BudgetWarning",
    # Schema Sanitization
    "sanitize", "sanitize_by_schema_name", "assert_patches_allowed",
    "CLAIM_SCHEMA", "DISPATCH_PATCH_SCHEMA",
    # Replay
    "ReplayBus", "ReplayReport",
    # Event constants (all)
    "EVENT_GOAL_CHAIN_TRIGGERED", "EVENT_GOAL_CHAIN_SKILL_CHAIN", "EVENT_GOAL_CHAIN_REWORK",
    # Runtime
    "ControlPlaneRuntime", "RuntimeResult", "run_pipeline",
]
