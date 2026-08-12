"""
Replay Bridge — Event-Replay → DispatchGate-Actions → State-Replay

Bridges the EventBus ReplayBus (event-level fingerprint comparison) with
KARMA's ReplayEngine (state-level hash chain verification). Runs both
and produces a combined audit report.

Flow:
    EventBus.events (JSON log or in-memory)
        ↓
    ReplayBus.replay()
        → ReplayReport (identical/diverged/errors per event)
        ↓
    Extract dispatch.executed events → Action objects
        ↓
    ReplayEngine.replay_from_seed(actions)
        → DriftReport (state hash matches after replay)
        ↓
    AuditTrailVerifier.verify()
        → AuditReport (hash chain integrity)
        ↓
    CombinedAuditReport (all three reports merged)

Usage:
    bridge = ReplayBridge(event_bus, persistence, seed="ci-run-42")
    report = await bridge.full_audit()
    print(report.summary())
    # → CombinedAudit: events=✅ state=✅ hash_chain=✅
"""

from __future__ import annotations

import asyncio
import json
import logging
import time as _time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Lazy imports (avoid circular deps) ─────────────────────────────

def _import_event_bus():
    from fusion.event_bus import (
        AsyncEventBus,
        Event,
        ReplayBus,
        ReplayReport,
        set_replay_report_path,
    )
    return AsyncEventBus, Event, ReplayBus, ReplayReport, set_replay_report_path


def _import_karma_replay():
    from karma.core.replay import (
        ActionJournal,
        AuditReport,
        AuditTrailVerifier,
        DriftReport,
        ReplayEngine,
        replay_from_seed,
    )
    from karma.core.dispatch import Action, DispatchGate
    return (
        ActionJournal,
        AuditReport,
        AuditTrailVerifier,
        DriftReport,
        ReplayEngine,
        replay_from_seed,
        Action,
        DispatchGate,
    )


# ─── Combined Audit Report ──────────────────────────────────────────


@dataclass
class CombinedAuditReport:
    """Unified audit result: event replay + state replay + hash chain."""

    # Event-level
    events_total: int = 0
    events_identical: int = 0
    events_diverged: int = 0
    events_errors: int = 0

    # State-level
    actions_extracted: int = 0
    actions_replayed: int = 0
    state_hash_matches: int = 0
    state_hash_mismatches: int = 0

    # Hash chain
    hash_chain_verified: int = 0
    hash_chain_tampered: int = 0
    hash_chain_gaps: int = 0

    # Meta
    seed: str = ""
    project: str = ""
    elapsed_ms: float = 0.0
    passed: bool = False

    # Detailed sub-reports
    event_report: Optional[Any] = None   # ReplayReport
    drift_report: Optional[Any] = None   # DriftReport
    audit_report: Optional[Any] = None   # AuditReport

    # Failure details
    failures: List[Dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "═══════════════════════════════════════════════════════",
            f"  COMBINED AUDIT: {'✅ PASSED' if self.passed else '❌ FAILED'}",
            "═══════════════════════════════════════════════════════",
            f"  Events:   {self.events_identical}/{self.events_total} identical"
            + (f", {self.events_diverged} diverged" if self.events_diverged else "")
            + (f", {self.events_errors} errors" if self.events_errors else ""),
            f"  State:    {self.state_hash_matches}/{self.actions_replayed} matched"
            + (f", {self.state_hash_mismatches} mismatches" if self.state_hash_mismatches else ""),
            f"  Chain:    {self.hash_chain_verified} verified"
            + (f", {self.hash_chain_tampered} tampered" if self.hash_chain_tampered else "")
            + (f", {self.hash_chain_gaps} gaps" if self.hash_chain_gaps else ""),
            f"  Seed:     {self.seed or 'none'}",
            f"  Project:  {self.project or 'ALL'}",
            f"  Time:     {self.elapsed_ms:.1f}ms",
        ]
        if self.failures:
            lines.append("  Failures:")
            for f in self.failures[:5]:
                lines.append(f"    - {f.get('layer', '?')}: {f.get('reason', '?')[:120]}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "events_total": self.events_total,
            "events_identical": self.events_identical,
            "events_diverged": self.events_diverged,
            "events_errors": self.events_errors,
            "actions_extracted": self.actions_extracted,
            "actions_replayed": self.actions_replayed,
            "state_hash_matches": self.state_hash_matches,
            "state_hash_mismatches": self.state_hash_mismatches,
            "hash_chain_verified": self.hash_chain_verified,
            "hash_chain_tampered": self.hash_chain_tampered,
            "hash_chain_gaps": self.hash_chain_gaps,
            "seed": self.seed,
            "project": self.project,
            "elapsed_ms": self.elapsed_ms,
            "event_report": (
                {
                    "identical": self.event_report.identical,
                    "diverged": self.event_report.diverged,
                    "errors": self.event_report.errors,
                    "deterministic": self.event_report.deterministic,
                }
                if self.event_report else None
            ),
            "drift_report": self.drift_report.to_dict() if self.drift_report else None,
            "audit_report": self.audit_report.to_dict() if self.audit_report else None,
            "failures": self.failures[:20],
        }


# ─── Replay Bridge ──────────────────────────────────────────────────


class ReplayBridge:
    """Orchestrates combined event + state + hash-chain replay audit.

    Bridges the two replay systems:
      - EventBus ReplayBus: fingerprint-based event comparison
      - KARMA ReplayEngine: state hash + hash chain verification

    Usage:
        bridge = ReplayBridge(
            event_bus,          # AsyncEventBus with events logged
            persistence,        # KARMA PersistenceLayer
            seed="ci-run-42",
        )
        report = await bridge.full_audit()
        assert report.passed, report.summary()
    """

    def __init__(
        self,
        event_bus: Any,          # AsyncEventBus
        persistence: Any,        # PersistenceLayer
        *,
        seed: str = "",
        project: str = "PZ",
        state_dir: Optional[Path] = None,
    ):
        self._event_bus = event_bus
        self._persistence = persistence
        self._seed = seed
        self._project = project
        self._state_dir = Path(state_dir) if state_dir else Path(".freebuff")

    # ── Full Audit Pipeline ─────────────────────────────────────────

    async def full_audit(self) -> CombinedAuditReport:
        """Run the complete audit pipeline.

        1. Replay events through ReplayBus (event-level)
        2. Extract DispatchGate actions from events
        3. Replay actions through ReplayEngine (state-level)
        4. Verify hash chain integrity
        5. Combine all results

        Returns:
            CombinedAuditReport with pass/fail and all three sub-reports.
        """
        start = _time.monotonic()
        failures: List[Dict[str, Any]] = []

        # ── Layer 1: Event Replay ──────────────────────────────────
        _, _, ReplayBus, ReplayReport, set_replay_report_path = _import_event_bus()

        # Set up replay report persistence
        report_path = self._state_dir / "last-replay-report.json"
        set_replay_report_path(report_path)

        # Replay only the trigger event (runtime.input) through wired subscribers
        events = self._event_bus.event_log()
        trigger_events = [e for e in events if e.event_type == "runtime.input"]

        event_report = None
        if trigger_events:
            replay = ReplayBus(trigger_events)
            # Wire subscribers for meaningful replay (not just echo)
            try:
                from fusion.event_runtime import ControlPlaneRuntime as CRT
                rt_replay = CRT(bus=replay.bus)
                rt_replay.goal_chain._dispatch_mode = "event"
                rt_replay.wire()
            except Exception as exc:
                logger.warning("Could not wire replay subscribers: %s", exc)
                failures.append({
                    "layer": "event_replay",
                    "reason": f"Subscriber wiring failed: {exc}",
                })

            event_report = await replay.replay()

            if not event_report.deterministic:
                failures.append({
                    "layer": "event_replay",
                    "reason": f"{event_report.diverged} diverged, {event_report.errors} errors",
                })

        # ── Layer 2: Extract Actions from Events ───────────────────
        (
            ActionJournal,
            AuditReport,
            AuditTrailVerifier,
            DriftReport,
            ReplayEngine,
            replay_from_seed,
            Action,
            DispatchGate,
        ) = _import_karma_replay()

        actions = self._extract_actions_from_events(events)

        # ── Layer 3: State Replay ──────────────────────────────────
        drift_report = None
        if actions:
            initial_state = self._persistence.get_all_memory(self._project) or {}
            drift_report = replay_from_seed(
                self._seed,
                initial_state,
                actions,
                deterministic_now=True,
            )

            if not drift_report.passed:
                failures.append({
                    "layer": "state_replay",
                    "reason": drift_report.reason or f"{len(drift_report.mismatches)} hash mismatches",
                })

        # ── Layer 4: Hash Chain Verification ───────────────────────
        audit_report = None
        try:
            verifier = AuditTrailVerifier(self._persistence)
            audit_report = verifier.verify(project=self._project)

            if not audit_report.passed:
                failures.append({
                    "layer": "hash_chain",
                    "reason": audit_report.reason or f"{audit_report.tampered_events} tampered",
                })
        except Exception as exc:
            logger.warning("Hash chain verification failed: %s", exc)
            failures.append({
                "layer": "hash_chain",
                "reason": f"Verification error: {exc}",
            })

        # ── Combine ────────────────────────────────────────────────
        passed = len(failures) == 0

        report = CombinedAuditReport(
            events_total=event_report.total_events if event_report else 0,
            events_identical=event_report.identical if event_report else 0,
            events_diverged=event_report.diverged if event_report else 0,
            events_errors=event_report.errors if event_report else 0,
            actions_extracted=len(actions),
            actions_replayed=drift_report.total_steps if drift_report else 0,
            state_hash_matches=drift_report.matched_steps if drift_report else 0,
            state_hash_mismatches=len(drift_report.mismatches) if drift_report else 0,
            hash_chain_verified=audit_report.verified_events if audit_report else 0,
            hash_chain_tampered=audit_report.tampered_events if audit_report else 0,
            hash_chain_gaps=audit_report.gap_events if audit_report else 0,
            seed=self._seed,
            project=self._project,
            elapsed_ms=(_time.monotonic() - start) * 1000.0,
            passed=passed,
            event_report=event_report,
            drift_report=drift_report,
            audit_report=audit_report,
            failures=failures,
        )

        # Persist combined report for dashboard
        self._save_combined_report(report)

        logger.info(
            "Combined audit: %s (events=%s state=%s chain=%s, %.1fms)",
            "PASSED" if passed else "FAILED",
            "✅" if report.events_diverged == 0 else "❌",
            "✅" if report.state_hash_mismatches == 0 else "❌",
            "✅" if report.hash_chain_tampered == 0 else "❌",
            report.elapsed_ms,
        )

        return report

    # ── Action Extraction ──────────────────────────────────────────

    def _extract_actions_from_events(self, events: List[Any]) -> List[Any]:
        """Extract DispatchGate Action objects from EventBus events.

        Looks for ``dispatch.executed`` events in the bus event log
        and converts them to KARMA Action objects.

        Also extracts actions from related events:
          - ``karma.falsified`` → UPDATE_CLAIM + FALSIFY actions
          - ``promtguard.claims`` → UPDATE_CLAIM actions
        """
        _, _, _, _, _, _, Action, _ = _import_karma_replay()

        actions: List[Any] = []

        for event in events:
            etype = event.event_type
            payload = event.payload

            if etype == "dispatch.executed":
                action_type = payload.get("action_type", "")
                if action_type:
                    actions.append(Action(
                        type=action_type,
                        payload={
                            k: v for k, v in payload.items()
                            if k not in ("action_type", "patch_count", "state_version")
                        },
                    ))

            elif etype == "promtguard.claims":
                for claim_data in payload.get("claims", []):
                    claim_id = claim_data.get("id", claim_data.get("claim_id", "UNKNOWN"))
                    claim_text = claim_data.get("claim", "")
                    claim_status = claim_data.get("status", "unverified")
                    actions.append(Action(
                        type="UPDATE_CLAIM",
                        payload={
                            "claim_id": claim_id,
                            "claim": claim_text,
                            "status": claim_status,
                        },
                    ))

            elif etype == "karma.falsified":
                for result in payload.get("results", []):
                    claim_id = result.get("claim_id", "UNKNOWN")
                    actions.append(Action(
                        type="FALSIFY",
                        payload={
                            "claim_id": claim_id,
                            "result": result.get("result", "unverified"),
                            "confidence": result.get("confidence", 0.5),
                            "evidence": result.get("evidence", []),
                        },
                    ))

        return actions

    # ── Persistence for Dashboard ──────────────────────────────────

    def _save_combined_report(self, report: CombinedAuditReport) -> None:
        """Persist the combined audit report for dashboard visualization."""
        path = self._state_dir / "combined-audit-report.json"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = report.to_dict()
            data["saved_at"] = datetime.now(timezone.utc).isoformat()
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            logger.debug("Combined audit report saved: %s", path)
        except Exception as exc:
            logger.warning("Failed to persist combined audit report: %s", exc)


# ─── Quick Entry Point ──────────────────────────────────────────────


async def run_combined_audit(
    bus: Any,
    persistence: Any,
    *,
    seed: str = "",
    project: str = "PZ",
) -> CombinedAuditReport:
    """One-liner: run the full combined audit.

    Usage:
        report = await run_combined_audit(bus, persistence, seed="ci")
        assert report.passed, report.summary()
    """
    bridge = ReplayBridge(bus, persistence, seed=seed, project=project)
    return await bridge.full_audit()
