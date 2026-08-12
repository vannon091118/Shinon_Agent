"""RT-08 — Memory Poisoning.

Try to persist unverified, malformed, and falsely attributed memory through the
real MemoryBus/PersistenceLayer. Poisoned records must never enter SQLite.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List

from karma.core.fact_validation import REQUIRED_FACT_KEYS
from karma.core.memory import MemoryBus
from karma.core.persistence import PersistenceConfig, PersistenceLayer
from redteam.oracle import Observation, Severity


VALID_FACT = {
    "fact": "Component X supports rollback",
    "source": "runtime-test",
    "confidence": "high",
    "verified_by": "test",
}


def _isolated_bus(project: str = "rt08") -> MemoryBus:
    # The test owns the temporary DB lifetime for one attack invocation. This
    # invokes the production PersistenceLayer and MemoryBus, not a fake store.
    tmp = tempfile.TemporaryDirectory(prefix="shinon-rt08-")
    persistence = PersistenceLayer(PersistenceConfig(Path(tmp.name) / "db"))
    persistence.create_project(project)
    bus = object.__new__(MemoryBus)
    bus.project = project
    bus.persistence = persistence
    # Keep TemporaryDirectory alive for the duration of the returned bus.
    bus._redteam_tmpdir = tmp
    return bus


def _observe(
    check: str,
    observed: Any,
    expected: Any,
    passed: bool,
    severity: Severity,
) -> Observation:
    return Observation(
        attack_id="RT-08",
        name="Memory Poisoning",
        check=check,
        observed=observed,
        expected=expected,
        passed=passed,
        severity=severity,
    )


def run(target) -> List[Observation]:
    observations: List[Observation] = []
    bus = _isolated_bus()
    required = sorted(REQUIRED_FACT_KEYS)

    # 1. Raw config-shaped data cannot masquerade as a fact.
    raw_config = {"verified": True, "source": "user"}
    try:
        bus.set("knowledge", raw_config, key="component-x")
        raw_rejected = False
        error = "accepted"
    except ValueError as exc:
        raw_rejected = True
        error = str(exc)
    observations.append(_observe(
        "raw config object is rejected by REQUIRED_FACT_KEYS",
        {"error": error, "required_keys": required},
        "ValueError",
        raw_rejected,
        Severity.CATASTROPHIC,
    ))

    # 2. A user cannot self-attest as a verifier by inventing an identity.
    forged = {**VALID_FACT, "verified_by": "untrusted-agent"}
    try:
        bus.set("knowledge", forged, key="component-x")
        forged_rejected = False
        error = "accepted"
    except ValueError as exc:
        forged_rejected = True
        error = str(exc)
    observations.append(_observe(
        "unknown verified_by identity is rejected",
        error,
        "ValueError: Unknown verifier identity",
        forged_rejected,
        Severity.CATASTROPHIC,
    ))

    # 3. A valid fact is persisted and can be read back. This guards against
    # over-tightening the poison defense into a memory write outage.
    bus.set("knowledge", VALID_FACT, key="component-x")
    stored = bus.get("knowledge", "component-x")
    observations.append(_observe(
        "valid provenance-bearing fact round-trips through SQLite",
        stored,
        VALID_FACT,
        stored == VALID_FACT,
        Severity.FAIL,
    ))

    return observations
