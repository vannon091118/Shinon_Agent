"""
LLM Middleware — Core Package
"""

from .memory import MemoryBus
from .index import FactIndex, TokenEstimator
from .cache import CacheManager
from .persistence import (
    PersistenceLayer,
    PersistenceConfig,
    create_persistence,
    create_project_persistence,
    migrate_from_json,
)
from .replay import (
    ActionJournal,
    DispatchGateRecorder,
    ReplayEngine,
    AuditTrailVerifier,
    AuditReport,
    DriftReport,
    replay_from_seed,
    replay_from_journal,
    full_audit,
    verify_replay,
)
from .dispatch import (
    Action,
    DispatchGate,
    DeterministicRng,
    Patch,
    MUTATION_MATRIX,
    stable_stringify,
    hash32,
)

__all__ = [
    # Persistence
    "MemoryBus",
    "FactIndex",
    "TokenEstimator",
    "CacheManager",
    "PersistenceLayer",
    "PersistenceConfig",
    "create_persistence",
    "create_project_persistence",
    "migrate_from_json",
    # Replay / Audit
    "ActionJournal",
    "DispatchGateRecorder",
    "ReplayEngine",
    "AuditTrailVerifier",
    "AuditReport",
    "DriftReport",
    "replay_from_seed",
    "replay_from_journal",
    "full_audit",
    "verify_replay",
    # Dispatch
    "Action",
    "DispatchGate",
    "DeterministicRng",
    "Patch",
    "MUTATION_MATRIX",
    "stable_stringify",
    "hash32",
]

__version__ = "0.3.0"
