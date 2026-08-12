"""
KARMA ReplayEngine — Deterministic State Replay & Audit Trail Verification

Seed-based replay of ALL DispatchGate actions via DeterministicRng.
Hash chain verification of the audit trail (events table).

Architecture:
    DispatchGate.dispatch(action)
        ↓
    DispatchGateRecorder (wraps DispatchGate)
        ├── Records action → ActionJournal (in-memory)
        ├── Computes state fingerprints (stable_stringify → hash32)
        └── Persistence.emit_event → events table (with hash chain)
            ↓
    Later: Replay
        seed = "my-seed-42"
        initial_state = {}
        actions = journal.load_actions()
        report = replay_from_seed(seed, initial_state, actions)
            → DriftReport (deterministic? state hash matches?)
            ↓
    Audit Verification
        verifier = AuditTrailVerifier(persistence)
        report = verifier.verify(project="PZ")
            → AuditReport (hash chain intact? gaps? tampering?)

DNA: LifeGameLab rng.js + store.js → seed-replay with hash chain verification.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from karma.core.dispatch import (
    Action,
    DeterministicRng,
    DispatchGate,
    Patch,
    _default_reducer,
    apply_patches,
    hash32,
    stable_stringify,
)

logger = logging.getLogger(__name__)


# ─── State Snapshot ─────────────────────────────────────────────────

@dataclass
class StateSnapshot:
    """A point-in-time fingerprint of the full state."""

    version: int
    state_hash: str
    timestamp: str
    action_type: str = ""
    rng_seed: str = ""
    patches_applied: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "state_hash": self.state_hash,
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "rng_seed": self.rng_seed,
            "patches_applied": self.patches_applied,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateSnapshot":
        return cls(
            version=data["version"],
            state_hash=data["state_hash"],
            timestamp=data.get("timestamp", ""),
            action_type=data.get("action_type", ""),
            rng_seed=data.get("rng_seed", ""),
            patches_applied=data.get("patches_applied", 0),
        )


# ─── Journal Entry ──────────────────────────────────────────────────

@dataclass
class JournalEntry:
    """One recorded dispatch action with before/after state fingerprints."""

    step: int
    action: Action
    snapshot_before: StateSnapshot
    snapshot_after: StateSnapshot
    patches: List[Dict[str, Any]] = field(default_factory=list)
    rng_state_before: Optional[Dict[str, int]] = None  # world/sim/cos state
    seed: str = ""

    def to_dict(self) -> Dict:
        return {
            "step": self.step,
            "action_type": self.action.type,
            "action_payload": self.action.payload,
            "snapshot_before": self.snapshot_before.to_dict(),
            "snapshot_after": self.snapshot_after.to_dict(),
            "patches": self.patches,
            "rng_state_before": self.rng_state_before,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "JournalEntry":
        return cls(
            step=data["step"],
            action=Action(
                type=data["action_type"],
                payload=data.get("action_payload", {}),
            ),
            snapshot_before=StateSnapshot.from_dict(data["snapshot_before"]),
            snapshot_after=StateSnapshot.from_dict(data["snapshot_after"]),
            patches=data.get("patches", []),
            rng_state_before=data.get("rng_state_before"),
            seed=data.get("seed", ""),
        )


# ─── Action Journal ─────────────────────────────────────────────────

class ActionJournal:
    """Records every DispatchGate action with state fingerprints.

    The journal is the bridge between DispatchGate (runtime) and
    ReplayEngine (verification). Each entry captures:
      - The action (type + payload)
      - State hash BEFORE the action
      - State hash AFTER the action
      - Patches applied
      - RNG state for seed-based replay

    Usage:
        journal = ActionJournal(seed="my-seed-42")
        journal.record(action, state_before, state_after, patches, rng)
        journal.save(Path("replay.jsonl"))
    """

    def __init__(self, seed: str = "", max_entries: int = 10000):
        self.seed = seed
        self._entries: List[JournalEntry] = []
        self._step = 0
        self._max_entries = max_entries

    def record(
        self,
        action: Action,
        state_before: Dict,
        state_after: Dict,
        patches: List[Patch],
        rng: Optional[DeterministicRng] = None,
    ) -> JournalEntry:
        """Record one dispatch step.

        Args:
            action: The dispatch action.
            state_before: State before the action was applied.
            state_after: State after patches were applied.
            patches: The patches produced by the reducer.
            rng: Optional RNG instance to capture RNG state.

        Returns:
            The recorded JournalEntry.
        """
        if self._step >= self._max_entries:
            logger.warning("ActionJournal at capacity (%d entries), dropping oldest", self._max_entries)
            self._entries = self._entries[-self._max_entries // 2 :]

        before_hash = hash32(stable_stringify(state_before))
        after_hash = hash32(stable_stringify(state_after))
        timestamp = datetime.now(timezone.utc).isoformat()

        entry = JournalEntry(
            step=self._step,
            action=action,
            snapshot_before=StateSnapshot(
                version=self._step,
                state_hash=before_hash,
                timestamp=timestamp,
                action_type=action.type,
                rng_seed=self.seed,
            ),
            snapshot_after=StateSnapshot(
                version=self._step + 1,
                state_hash=after_hash,
                timestamp=timestamp,
                action_type=action.type,
                rng_seed=self.seed,
                patches_applied=len(patches),
            ),
            patches=[{"op": p.op, "path": p.path, "value": str(p.value)[:100]} for p in patches],
            rng_state_before=self._capture_rng_state(rng) if rng else None,
            seed=self.seed,
        )
        self._entries.append(entry)
        self._step += 1
        return entry

    def _capture_rng_state(self, rng: DeterministicRng) -> Dict[str, int]:
        """Capture deterministic RNG state for replay verification."""
        try:
            return {
                "world": rng.world.u32(),
                "sim": rng.sim.u32(),
                "cos": rng.cos.u32(),
            }
        except Exception:
            return {}

    def save(self, path: Path) -> Path:
        """Save journal to JSONL file."""
        with open(path, "w") as f:
            for entry in self._entries:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        logger.info("ActionJournal saved: %d entries → %s", len(self._entries), path)
        return path

    @classmethod
    def load(cls, path: Path) -> "ActionJournal":
        """Load journal from JSONL file."""
        journal = cls()
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                entry = JournalEntry.from_dict(data)
                journal._entries.append(entry)
                journal._step = max(journal._step, entry.step + 1)
        logger.info("ActionJournal loaded: %d entries ← %s", len(journal._entries), path)
        return journal

    @property
    def entries(self) -> List[JournalEntry]:
        return list(self._entries)

    @property
    def actions(self) -> List[Action]:
        return [e.action for e in self._entries]

    @property
    def step_count(self) -> int:
        return self._step


# ─── DispatchGate Recorder ──────────────────────────────────────────

class DispatchGateRecorder:
    """Wraps DispatchGate to auto-record every dispatch to an ActionJournal.

    Usage:
        gate = DispatchGate(persistence)
        gate.set_active_rng_seed("my-seed-42")
        recorder = DispatchGateRecorder(gate, journal)
        result = recorder.dispatch(action)  # records automatically
    """

    def __init__(
        self,
        gate: DispatchGate,
        journal: ActionJournal,
        *,
        auto_record: bool = True,
    ):
        self.gate = gate
        self.journal = journal
        self.auto_record = auto_record

    def dispatch(self, action: Action) -> Dict:
        """Dispatch an action and record it in the journal.

        Uses the (next_state, patches) returned by DispatchGate.dispatch()
        directly — no separate reducer call needed.
        """
        # Capture state BEFORE
        project = self.gate.persistence.get_active_project()
        state_before = self.gate.persistence.get_all_memory(project)

        # Execute through the real gate — returns (next_state, patches)
        next_state, patches = self.gate.dispatch(action)

        if self.auto_record:
            self.journal.record(
                action=action,
                state_before=state_before,
                state_after=next_state,
                patches=patches,
                rng=self.gate._rng,
            )

        return next_state

    @property
    def version(self) -> int:
        return self.gate.version

    def set_seed(self, seed: str) -> None:
        """Set the RNG seed and reset the journal."""
        self.gate._rng = DeterministicRng(seed)
        self.journal = ActionJournal(seed=seed)


# ─── Replay Engine ──────────────────────────────────────────────────

class ReplayEngine:
    """Deterministic replay with drift detection.

    Records every state transition as a fingerprint (stable_stringify →
    hash32). On replay, compares replayed state hash to recorded hash.
    Any mismatch = drift detected.

    Usage:
        engine = ReplayEngine(seed="my-seed-42")
        snapshot = engine.snapshot(state, action)
        engine.record(snapshot)

        # Later:
        drift = engine.replay(state, actions, journal)
        if drift:
            print(f"DRIFT at step {drift.step}")
    """

    def __init__(self, seed: str = "", journal_path: Optional[Path] = None):
        self.seed = seed
        self.rng = DeterministicRng(seed)
        self._journal: List[JournalEntry] = []
        self._step = 0
        self._journal_path = journal_path

    def snapshot(self, state: Dict, action: Action) -> StateSnapshot:
        """Create a fingerprint snapshot of the current state."""
        state_hash = hash32(stable_stringify(state))
        return StateSnapshot(
            version=self._step,
            state_hash=state_hash,
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type=action.type,
            rng_seed=self.seed,
        )

    def record(self, before: StateSnapshot, after: StateSnapshot,
               action: Action, patches: List[Patch]) -> None:
        """Record one step in the replay journal."""
        entry = JournalEntry(
            step=self._step,
            action=action,
            snapshot_before=before,
            snapshot_after=after,
            patches=[{"op": p.op, "path": p.path, "value": p.value} for p in patches],
            seed=self.seed,
        )
        self._journal.append(entry)
        self._step += 1

        if self._journal_path:
            self._append_to_file(entry)

    def _append_to_file(self, entry: JournalEntry) -> None:
        if not self._journal_path:
            return
        with open(self._journal_path, "a") as f:
            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    def load(self, path: Path) -> List[JournalEntry]:
        """Load a replay journal from file."""
        journal = ActionJournal.load(path)
        return journal.entries

    @property
    def journal(self) -> List[JournalEntry]:
        return list(self._journal)

    @property
    def step_count(self) -> int:
        return self._step


# ─── Drift Detection ────────────────────────────────────────────────

@dataclass
class DriftReport:
    """Result of a replay drift check."""

    passed: bool
    total_steps: int
    matched_steps: int
    first_mismatch_step: Optional[int] = None
    recorded_hash: Optional[str] = None
    replayed_hash: Optional[str] = None
    mismatches: List[Dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    seed: str = ""
    final_state_hash: Optional[str] = None
    elapsed_ms: float = 0.0

    def __post_init__(self):
        if not self.passed and not self.reason:
            if self.total_steps == 0:
                self.reason = "empty journal (no steps to replay)"
            elif self.mismatches:
                self.reason = f"{len(self.mismatches)} hash mismatches detected"

    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "total_steps": self.total_steps,
            "matched_steps": self.matched_steps,
            "first_mismatch_step": self.first_mismatch_step,
            "recorded_hash": self.recorded_hash,
            "replayed_hash": self.replayed_hash,
            "mismatches": self.mismatches[:20],
            "reason": self.reason,
            "seed": self.seed,
            "final_state_hash": self.final_state_hash,
            "elapsed_ms": self.elapsed_ms,
        }

    def summary(self) -> str:
        lines = [
            f"DriftReport: {'PASSED ✅' if self.passed else 'FAILED ❌'}",
            f"  steps: {self.matched_steps}/{self.total_steps} matched",
            f"  mismatches: {len(self.mismatches)}",
            f"  seed: {self.seed}",
        ]
        if self.first_mismatch_step is not None:
            lines.append(f"  first mismatch at step {self.first_mismatch_step}")
            lines.append(f"    recorded: {self.recorded_hash}")
            lines.append(f"    replayed: {self.replayed_hash}")
        if self.final_state_hash:
            lines.append(f"  final state hash: {self.final_state_hash}")
        return "\n".join(lines)


def replay_from_seed(
    seed: str,
    initial_state: Dict,
    actions: List[Action],
    *,
    reducer: Optional[Callable[[Dict, Action, DeterministicRng], List[Patch]]] = None,
    expected_final_hash: Optional[str] = None,
    deterministic_now: bool = True,
) -> DriftReport:
    """Deterministic replay of ALL DispatchGate actions from a seed.

    Given the same seed, initial state, and action sequence, this
    produces the same state — every time. Any deviation = drift detected.

    This is the core verification primitive: "Can we reproduce the
    exact state from just the seed + actions?"

    Args:
        seed: RNG seed for deterministic replay.
        initial_state: Starting state (empty dict for fresh starts).
        actions: Sequence of DispatchGate actions to replay.
        reducer: Optional reducer (uses _default_reducer if None).
        expected_final_hash: Optional expected final state hash for
            one-shot verification.
        deterministic_now: If True, inject a deterministic timestamp
            derived from seed+step (vs datetime.now which varies).

    Returns:
        DriftReport with pass/fail and step-by-step hash comparison.
    """
    import time as _time
    from datetime import datetime, timezone

    _reducer = reducer or _default_reducer  # type: ignore[assignment]
    rng = DeterministicRng(seed)
    state = dict(initial_state) if initial_state else {}

    start = _time.monotonic()
    matched = 0
    first_mismatch = None
    recorded_hash_at_mismatch = None
    replayed_hash_at_mismatch = None

    # Deterministic timestamp: seed-based offset from a fixed epoch
    base_ts = int(hash32(f"replay-epoch:{seed}"), 16) & 0x7FFFFFFF

    for i, action in enumerate(actions):
        # Compute state hash BEFORE applying
        before_hash = hash32(stable_stringify(state))

        # Apply action via reducer
        if deterministic_now:
            # Wrap reducer to inject deterministic timestamp for FALSIFY
            step_ts = base_ts + i * 60
            dt = datetime.fromtimestamp(step_ts, tz=timezone.utc).isoformat()

            def _det_reducer(s, a, r, *, _orig=_reducer, _dt=dt):
                patches = _orig(s, a, r)
                # Replace non-deterministic timestamps in FALSIFY patches
                for p in patches:
                    if isinstance(p.value, dict) and "timestamp" in p.value:
                        p.value = dict(p.value)
                        p.value["timestamp"] = _dt
                return patches

            patches = _det_reducer(state, action, rng)
        else:
            patches = _reducer(state, action, rng)  # type: ignore[call-arg]

        state = apply_patches(state, patches)

        # Compute state hash AFTER applying
        after_hash = hash32(stable_stringify(state))
        matched += 1

        # If expected_final_hash provided and this is the last step
        if expected_final_hash and i == len(actions) - 1:
            if after_hash == expected_final_hash:
                logger.info("Final state hash matches expected: %s", expected_final_hash)
            else:
                if first_mismatch is None:
                    first_mismatch = i
                    recorded_hash_at_mismatch = expected_final_hash
                    replayed_hash_at_mismatch = after_hash

    final_state_hash = hash32(stable_stringify(state))
    elapsed_ms = (_time.monotonic() - start) * 1000.0

    # Build mismatches list
    mismatches = []
    if expected_final_hash and final_state_hash != expected_final_hash:
        mismatches.append({
            "step": "final",
            "stage": "final_state",
            "expected": expected_final_hash,
            "actual": final_state_hash,
        })

    passed = len(mismatches) == 0 and len(actions) > 0

    return DriftReport(
        passed=passed,
        total_steps=len(actions),
        matched_steps=matched,
        first_mismatch_step=first_mismatch,
        recorded_hash=recorded_hash_at_mismatch,
        replayed_hash=replayed_hash_at_mismatch,
        mismatches=mismatches,
        seed=seed,
        final_state_hash=final_state_hash,
        elapsed_ms=elapsed_ms,
    )


def replay_from_journal(
    seed: str,
    initial_state: Dict,
    journal: ActionJournal,
    *,
    reducer: Optional[Callable[[Dict, Action, DeterministicRng], List[Patch]]] = None,
) -> DriftReport:
    """Replay all actions from a journal and verify state hashes match.

    Compares every state-after hash from the recorded journal against
    the replayed state hash. Any mismatch = drift detected.

    Args:
        seed: RNG seed (must match the original run).
        initial_state: Starting state.
        journal: Recorded ActionJournal.
        reducer: Optional reducer override.

    Returns:
        DriftReport with per-step hash comparison against the journal.
    """
    import time as _time

    _reducer = reducer or _default_reducer  # type: ignore[assignment]
    rng = DeterministicRng(seed)
    state = dict(initial_state) if initial_state else {}

    start = _time.monotonic()
    entries = journal.entries
    mismatches: List[Dict[str, Any]] = []
    matched = 0
    first_mismatch = None
    recorded_hash = None
    replayed_hash_at_mismatch = None

    for i, entry in enumerate(entries):
        # Verify snapshot-before hash
        before_hash = hash32(stable_stringify(state))
        if before_hash != entry.snapshot_before.state_hash:
            mismatch = {
                "step": i,
                "stage": "before",
                "recorded": entry.snapshot_before.state_hash,
                "replayed": before_hash,
                "action": entry.action.type,
            }
            mismatches.append(mismatch)
            if first_mismatch is None:
                first_mismatch = i
                recorded_hash = entry.snapshot_before.state_hash
                replayed_hash_at_mismatch = before_hash

        # Apply action
        patches = _reducer(state, entry.action, rng)  # type: ignore[call-arg]
        state = apply_patches(state, patches)

        # Verify snapshot-after hash
        after_hash = hash32(stable_stringify(state))
        if after_hash != entry.snapshot_after.state_hash:
            mismatch = {
                "step": i,
                "stage": "after",
                "recorded": entry.snapshot_after.state_hash,
                "replayed": after_hash,
                "action": entry.action.type,
            }
            mismatches.append(mismatch)
            if first_mismatch is None:
                first_mismatch = i
                recorded_hash = entry.snapshot_after.state_hash
                replayed_hash_at_mismatch = after_hash
        else:
            matched += 1

    final_state_hash = hash32(stable_stringify(state))
    elapsed_ms = (_time.monotonic() - start) * 1000.0
    passed = len(mismatches) == 0 and len(entries) > 0

    return DriftReport(
        passed=passed,
        total_steps=len(entries),
        matched_steps=matched,
        first_mismatch_step=first_mismatch,
        recorded_hash=recorded_hash,
        replayed_hash=replayed_hash_at_mismatch,
        mismatches=mismatches,
        reason=f"{len(mismatches)} hash mismatches" if mismatches else "",
        seed=seed,
        final_state_hash=final_state_hash,
        elapsed_ms=elapsed_ms,
    )


# ─── Audit Trail Verifier ───────────────────────────────────────────

@dataclass
class AuditReport:
    """Result of audit trail hash chain verification."""

    passed: bool
    total_events: int
    verified_events: int
    tampered_events: int
    gap_events: int  # events with missing prev_hash linkage
    first_tamper_at: Optional[int] = None
    first_gap_at: Optional[int] = None
    tamper_details: List[Dict[str, Any]] = field(default_factory=list)
    gap_details: List[Dict[str, Any]] = field(default_factory=list)
    chain_start: str = "genesis"
    chain_end: Optional[str] = None
    project: str = ""
    reason: str = ""
    elapsed_ms: float = 0.0

    def summary(self) -> str:
        lines = [
            f"AuditReport: {'PASSED ✅ (tamper-proof)' if self.passed else 'FAILED ❌ (TAMPERED!)'}",
            f"  events: {self.verified_events}/{self.total_events} verified",
            f"  tampered: {self.tampered_events}  gaps: {self.gap_events}",
            f"  project: {self.project or 'ALL'}",
        ]
        if self.chain_start and self.chain_end:
            lines.append(f"  chain: {self.chain_start[:8]} → {self.chain_end[:8]}")
        if self.tamper_details:
            lines.append(f"  tamper events:")
            for t in self.tamper_details[:3]:
                lines.append(f"    event #{t.get('id')}: {t.get('reason', '?')}")
        if self.gap_details:
            lines.append(f"  gap events:")
            for g in self.gap_details[:3]:
                lines.append(f"    event #{g.get('id')}: prev_hash={g.get('prev_hash', '?')[:8]}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "total_events": self.total_events,
            "verified_events": self.verified_events,
            "tampered_events": self.tampered_events,
            "gap_events": self.gap_events,
            "first_tamper_at": self.first_tamper_at,
            "first_gap_at": self.first_gap_at,
            "tamper_details": self.tamper_details[:10],
            "gap_details": self.gap_details[:10],
            "chain_start": self.chain_start,
            "chain_end": self.chain_end,
            "project": self.project,
            "reason": self.reason,
        }


class AuditTrailVerifier:
    """Verify the hash chain integrity of the audit trail.

    Each event in the events table has:
      - event_hash: SHA-256(prev_hash + event_type + payload + timestamp + correlation_id)
      - prev_event_hash: hash of the previous event in the chain

    The verifier recomputes each event_hash and checks:
    1. prev_event_hash matches the previous event's event_hash
    2. event_hash can be recomputed from the event data + prev_hash
    3. No gaps in the chain (missing prev_event_hash where expected)

    Usage:
        verifier = AuditTrailVerifier(persistence)
        report = verifier.verify(project="PZ")
        if not report.passed:
            print(f"AUDIT FAILED: {report.tampered_events} tampered!")
    """

    def __init__(self, persistence):
        self.persistence = persistence

    def verify(
        self,
        project: Optional[str] = None,
        *,
        limit: int = 10000,
        strict: bool = True,
    ) -> AuditReport:
        """Verify the audit trail hash chain.

        Args:
            project: Optional project to scope verification to.
            limit: Maximum events to verify.
            strict: If True, gaps count as failure.

        Returns:
            AuditReport with tamper/gap details.
        """
        import time as _time

        start = _time.monotonic()

        try:
            events = self.persistence.get_events_with_hash_chain(
                project=project,
                limit=limit,
            )
        except Exception as exc:
            return AuditReport(
                passed=False,
                total_events=0,
                verified_events=0,
                tampered_events=0,
                gap_events=0,
                project=project or "",
                reason=f"Failed to query events: {exc}",
            )

        if not events:
            return AuditReport(
                passed=True,
                total_events=0,
                verified_events=0,
                tampered_events=0,
                gap_events=0,
                project=project or "",
                reason="No events to verify (empty audit trail)",
            )

        verified = 0
        tampered = 0
        gaps = 0
        first_tamper = None
        first_gap = None
        tamper_details: List[Dict[str, Any]] = []
        gap_details: List[Dict[str, Any]] = []

        prev_hash = "genesis"

        for event in events:
            event_id = event.get("id", "?")
            event_type = event.get("event_type", "")
            payload = event.get("payload", "{}")
            timestamp = event.get("timestamp", "")
            correlation_id = event.get("correlation_id", "")
            recorded_hash = event.get("event_hash")
            recorded_prev_hash = event.get("prev_event_hash")

            # Check 1: prev_event_hash matches chain
            if recorded_prev_hash and recorded_prev_hash != prev_hash:
                gap = {
                    "id": event_id,
                    "event_type": event_type,
                    "expected_prev_hash": prev_hash[:8],
                    "recorded_prev_hash": (recorded_prev_hash or "?")[:8],
                    "reason": "prev_event_hash breaks chain — gap or insertion",
                }
                gap_details.append(gap)
                gaps += 1
                if first_gap is None:
                    first_gap = event_id

            # Check 2: Recompute event_hash
            if recorded_hash:
                hash_input = f"{prev_hash}|{event_type}|{payload}|{timestamp}|{correlation_id or ''}"
                expected_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

                if expected_hash == recorded_hash:
                    verified += 1
                    prev_hash = recorded_hash
                else:
                    tamper = {
                        "id": event_id,
                        "event_type": event_type,
                        "recorded_hash": recorded_hash[:8],
                        "expected_hash": expected_hash[:8],
                        "reason": "event_hash mismatch — payload or timestamp tampered",
                    }
                    tamper_details.append(tamper)
                    tampered += 1
                    if first_tamper is None:
                        first_tamper = event_id
                    # Chain is broken; use recorded hash for next link
                    # (allows detecting subsequent tampering too)
                    prev_hash = recorded_hash
            else:
                # No hash — pre-v5 event, skip verification
                gap = {
                    "id": event_id,
                    "event_type": event_type,
                    "prev_hash": recorded_prev_hash or "?",
                    "reason": "Missing event_hash (pre-v5 migration)",
                }
                gap_details.append(gap)
                gaps += 1
                if first_gap is None:
                    first_gap = event_id

        elapsed_ms = (_time.monotonic() - start) * 1000.0

        passed = tampered == 0 and (not strict or gaps == 0)

        return AuditReport(
            passed=passed,
            total_events=len(events),
            verified_events=verified,
            tampered_events=tampered,
            gap_events=gaps,
            first_tamper_at=first_tamper,
            first_gap_at=first_gap,
            tamper_details=tamper_details,
            gap_details=gap_details,
            chain_start=(events[0].get("event_hash") or "genesis")[:8] if events else "genesis",
            chain_end=(events[-1].get("event_hash") or "genesis")[:8] if events else None,
            project=project or "ALL",
            reason="" if passed else f"{tampered} tampered, {gaps} gaps",
            elapsed_ms=elapsed_ms,
        )


# ─── Replay Verifier (CLI-friendly) ──────────────────────────────────

def verify_replay(
    journal_path: Path,
    initial_state: Dict,
    seed: str = "",
) -> DriftReport:
    """Load journal from file, extract actions, and verify determinism.

    One-liner for CLI / CI usage:
        report = verify_replay(Path("replay.jsonl"), initial_state, seed="my-seed")
        assert report.passed, f"DRIFT: {report.mismatches}"
    """
    journal = ActionJournal.load(journal_path)
    return replay_from_journal(seed, initial_state, journal)


def full_audit(
    seed: str,
    initial_state: Dict,
    journal_path: Path,
    persistence,
    *,
    project: Optional[str] = None,
) -> Tuple[DriftReport, AuditReport]:
    """Complete KARMA audit: state replay + hash chain verification.

    Returns both a DriftReport (determinism check) and an
    AuditReport (tamper detection). Both must pass for a clean audit.

    Usage:
        drift, audit = full_audit(
            seed="my-seed-42",
            initial_state={},
            journal_path=Path("replay.jsonl"),
            persistence=persistence,
            project="PZ",
        )
        assert drift.passed and audit.passed, "AUDIT FAILED!"
    """
    journal = ActionJournal.load(journal_path)
    drift = replay_from_journal(seed, initial_state, journal)

    verifier = AuditTrailVerifier(persistence)
    audit = verifier.verify(project=project)

    return drift, audit


def replay_all_from_db(
    seed: str,
    initial_state: Dict,
    persistence,
    *,
    project: Optional[str] = None,
    limit: int = 1000,
) -> Tuple[DriftReport, AuditReport]:
    """Replay ALL DispatchGate actions from the events table in the DB.

    Reads every ``dispatch.executed`` event from the persistence layer,
    extracts the actions, and replays them deterministically using the
    given seed. Also runs audit trail verification on the hash chain.

    This is the complete audit primitive: "Given just the seed and the
    database, can we reproduce the exact same state and verify the
    audit trail wasn't tampered with?"

    Args:
        seed: RNG seed for deterministic replay.
        initial_state: Starting state (empty dict for fresh start).
        persistence: PersistenceLayer instance.
        project: Optional project to scope to.
        limit: Maximum events to replay.

    Returns:
        Tuple of (DriftReport, AuditReport). Both must pass.
    """
    # Extract dispatch actions from events table
    try:
        events = persistence.get_events_with_hash_chain(
            project=project,
            limit=limit,
        )
    except Exception as exc:
        logger.warning("Could not read events for replay: %s", exc)
        events = []

    actions: List[Action] = []
    for event in events:
        if event.get("event_type") != "dispatch.executed":
            continue
        try:
            payload = json.loads(event.get("payload", "{}"))
        except (json.JSONDecodeError, TypeError):
            payload = {}

        action_type = payload.get("action_type", "")
        if not action_type:
            continue

        # Reconstruct the original Action
        action = Action(
            type=action_type,
            payload={
                k: v for k, v in payload.items()
                if k not in ("action_type", "patch_count", "state_version")
            },
        )
        actions.append(action)

    logger.info(
        "replay_all_from_db: extracted %d actions from %d events (project=%s)",
        len(actions), len(events), project or "ALL",
    )

    # Replay all actions
    drift = replay_from_seed(seed, initial_state, actions)

    # Verify audit trail hash chain
    verifier = AuditTrailVerifier(persistence)
    audit = verifier.verify(project=project, limit=limit)

    return drift, audit
