"""
KARMA Subscriber — Real DispatchGate + FalsificationGate integration

Receives CLAIM-GEN-NNN claims from Promtguard via EventBus and routes
them through KARMA's DispatchGate for deterministic write-gated mutation
AND through FalsificationGate for LLM-grade claim verification.

Architecture:
    promtguard.claims event
        ↓
    KARMASubscriber.on_claims_received()
        ↓
    For each claim:
        1. UPDATE_CLAIM → DispatchGate.dispatch(action)
        2. FALSIFY → FalsificationGate.run(claim_file)
           → 6 probes: assumptions, test_coverage, contradictions,
              regressions, idempotency, determinism
           → Map probe results → claim verdict
        3. FALSIFY dispatch → DispatchGate.dispatch(action)
        4. Publish karma.falsified

Position: 2 (cognition layer)
Subscribes to: "promtguard.claims"
Publishes: "karma.falsified", "karma.experience"
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fusion.event_bus import (
    AsyncEventBus,
    Event,
    EVENT_PROMTGUARD_CLAIMS,
    EVENT_KARMA_FALSIFIED,
    EVENT_KARMA_EXPERIENCE,
    EVENT_RUNTIME_COMPLETED,
    EVENT_RUNTIME_ERROR,
)

logger = logging.getLogger(__name__)


# ─── Falsification Result ─────────────────────────────────────────────


@dataclass
class FalsificationResult:
    """Result of a single claim's falsification."""

    claim_id: str
    result: str  # supported | confirmed | refuted | conflicted | unverified
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.5
    gate_version: str = "1.0.0"
    falsified_at: str = ""

    def __post_init__(self):
        if not self.falsified_at:
            self.falsified_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "result": self.result,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "gate_version": self.gate_version,
            "falsified_at": self.falsified_at,
        }


@dataclass
class ExperienceRecord:
    """Immutable experience entry in KARMA's Experience Store."""

    experience_id: str
    action: str
    outcome: str
    reward: float
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "action": self.action,
            "outcome": self.outcome,
            "reward": self.reward,
            "context_snapshot": self.context_snapshot,
            "timestamp": self.timestamp,
        }


# ─── KARMA Subscriber (Real DispatchGate) ────────────────────────────


class KARMASubscriber:
    """Async KARMA subscriber — integrates with real DispatchGate + FalsificationGate.

    Receives Promtguard claims, evaluates them through KARMA's
    FalsificationGate (6 deterministic probes), dispatches results
    through DispatchGate for write-gated persistence, and publishes
    falsification results back to the EventBus.

    Graceful degradation:
      - FalsificationGate available → real probe-based verification
      - FalsificationGate unavailable → heuristic fallback (regex)
      - DispatchGate available → write-gated persistence
      - DispatchGate unavailable → EventBus-only (testing mode)

    Usage:
        # With real gates:
        from karma.core.falsification_gate import FalsificationGate
        from karma.core.dispatch import DispatchGate
        from karma.core.persistence import create_persistence
        persistence = create_persistence()
        fgate = FalsificationGate(persistence, "PZ")
        dgate = DispatchGate(persistence)
        karma = KARMASubscriber(bus, dispatch_gate=dgate, falsification_gate=fgate)

        # Fallback (heuristic only):
        karma = KARMASubscriber(bus)
        karma.wire(bus)
    """

    VALID_RESULTS = {"supported", "confirmed", "refuted", "conflicted", "unverified"}

    def __init__(
        self,
        bus: AsyncEventBus,
        dispatch_gate: Optional[Any] = None,
        falsification_gate: Optional[Any] = None,
        persistence: Optional[Any] = None,
        state_dir: Optional[Path] = None,
        project: str = "PZ",
    ):
        self.bus = bus
        self._state_dir = Path(state_dir) if state_dir else Path("karma-main/state")
        self._state_dir.mkdir(parents=True, exist_ok=True)

        # Real gates (optional — fall back to heuristic)
        self._gate = dispatch_gate
        self._falsification_gate = falsification_gate
        self._persistence = persistence
        self._project = project

        # Temp dir for claim files (used by FalsificationGate)
        self._tmp_dir = self._state_dir / "claims_tmp"
        self._tmp_dir.mkdir(parents=True, exist_ok=True)

        # Claim evidence source: claim-log.jsonl from Promtguard
        self._claim_log_paths = [
            Path(".promtset/state/claim-log.jsonl"),
            Path("Promtguard-main/.promtset/state/claim-log.jsonl"),
        ]
        self._claim_evidence_cache: Optional[Dict[str, Any]] = None
        self._claim_evidence_loaded_at: float = 0.0

        # Preprocessor evidence: StructuredInput from LLMPreProcessor
        # Populated by ControlPlaneRuntime before process() runs
        self._preprocess_evidence: Optional[Dict[str, Any]] = None
        self._preprocess_evidence_requirements: List[str] = []
        self._preprocess_evidence_tests: List[str] = []
        self._preprocess_evidence_goal: str = ""

        # Counters
        self._falsification_count = 0
        self._experience_count = 0
        self._gate_falsifications = 0  # via FalsificationGate
        self._heuristic_falsifications = 0  # via regex fallback
        self._evidence_hits = 0  # claims where evidence was found in claim-log
        self._cross_reference_hits = 0  # claims matched against preprocessor evidence

        # Import DispatchGate lazily to avoid hard dependency
        self._Action = None
        self._DispatchGate = None
        self._dispatch_available = False
        self._try_import_dispatch()

        # FalsificationGate availability
        self._falsification_gate_available = falsification_gate is not None
        if self._falsification_gate_available:
            logger.info("KARMA FalsificationGate connected — real probe-based verification")
        else:
            logger.info("KARMA FalsificationGate not provided — heuristic fallback active")

    def set_preprocess_evidence(self, structured_input: Optional[Any]) -> None:
        """Set LLMPreProcessor output as falsification evidence.

        Called by ControlPlaneRuntime after preprocessing. The structured
        input's requirements, tests, and goal are used to cross-reference
        claims during falsification — replacing the empty evidence pool.

        Args:
            structured_input: StructuredInput from LLMPreProcessor.structure()
        """
        if structured_input is None:
            self._preprocess_evidence = None
            self._preprocess_evidence_requirements = []
            self._preprocess_evidence_tests = []
            self._preprocess_evidence_goal = ""
            return

        # Extract evidence from StructuredInput
        reqs = getattr(structured_input, 'requirements', [])
        tests = getattr(structured_input, 'tests', [])
        goal = getattr(structured_input, 'goal', '')
        arch = getattr(structured_input, 'architecture_components', [])

        self._preprocess_evidence = {
            "requirements": list(reqs),
            "tests": list(tests),
            "goal": goal,
            "architecture": list(arch),
            "mode": getattr(structured_input, 'mode', 'unknown'),
        }
        self._preprocess_evidence_requirements = list(reqs)
        self._preprocess_evidence_tests = list(tests)
        self._preprocess_evidence_goal = goal

        logger.info(
            "KARMA preprocess evidence set: %d requirements, %d tests, goal='%s'",
            len(reqs), len(tests), goal[:60],
        )

    def _cross_reference_claim(
        self, claim_text: str
    ) -> Dict[str, Any]:
        """Cross-reference a claim against the LLM's structured requirements and tests.

        Returns a dict with:
          - matched_requirement: the best-matching requirement text (or None)
          - matched_test: the best-matching test text (or None)
          - req_overlap: keyword overlap with requirements (0.0-1.0)
          - test_overlap: keyword overlap with tests (0.0-1.0)
          - goal_overlap: keyword overlap with the goal statement (0.0-1.0)
        """
        if not self._preprocess_evidence_requirements and not self._preprocess_evidence_tests:
            return {"matched_requirement": None, "matched_test": None,
                    "req_overlap": 0.0, "test_overlap": 0.0, "goal_overlap": 0.0}

        # Extract significant words from the claim
        stopwords = {"this", "that", "with", "from", "have", "been", "were", "they",
                     "will", "would", "could", "should", "must", "shall", "also", "then",
                     "the", "and", "for", "are", "has", "had", "not", "its", "all"}
        claim_words = set(
            w.lower().rstrip(".,;:!?)\"'")
            for w in claim_text.split()
            if len(w) >= 3 and w.lower() not in stopwords
        )

        if not claim_words:
            return {"matched_requirement": None, "matched_test": None,
                    "req_overlap": 0.0, "test_overlap": 0.0, "goal_overlap": 0.0}

        # Best requirement match
        best_req = None
        best_req_score = 0.0
        for req in self._preprocess_evidence_requirements:
            req_words = set(
                w.lower().rstrip(".,;:!?)\"'")
                for w in req.split()
                if len(w) >= 3 and w.lower() not in stopwords
            )
            if not req_words:
                continue
            overlap = len(claim_words & req_words) / max(len(req_words), 1)
            if overlap > best_req_score:
                best_req_score = overlap
                best_req = req

        # Best test match
        best_test = None
        best_test_score = 0.0
        for test in self._preprocess_evidence_tests:
            test_words = set(
                w.lower().rstrip(".,;:!?)\"'")
                for w in test.split()
                if len(w) >= 3 and w.lower() not in stopwords
            )
            if not test_words:
                continue
            overlap = len(claim_words & test_words) / max(len(test_words), 1)
            if overlap > best_test_score:
                best_test_score = overlap
                best_test = test

        # Goal overlap
        goal_words = set(
            w.lower().rstrip(".,;:!?)\"'")
            for w in self._preprocess_evidence_goal.split()
            if len(w) >= 3 and w.lower() not in stopwords
        )
        goal_overlap = len(claim_words & goal_words) / max(len(goal_words), 1) if goal_words else 0.0

        return {
            "matched_requirement": best_req,
            "matched_test": best_test,
            "req_overlap": round(best_req_score, 2),
            "test_overlap": round(best_test_score, 2),
            "goal_overlap": round(goal_overlap, 2),
        }

    def _try_import_dispatch(self) -> None:
        """Try to import KARMA's Action class. Sets _dispatch_available flag."""
        try:
            from karma.core.dispatch import Action as A
            self._Action = A
            self._dispatch_available = True
            logger.info("KARMA DispatchGate imported — real write-gated dispatch available")
        except ImportError:
            logger.info("KARMA DispatchGate not available — falling back to heuristic falsifier")
            self._dispatch_available = False

    def wire(self, bus: Optional[AsyncEventBus] = None) -> None:
        """Wire KARMA subscriptions to the EventBus."""
        b = bus or self.bus
        b.subscribe(EVENT_PROMTGUARD_CLAIMS, self.on_claims_received)
        b.subscribe(EVENT_RUNTIME_COMPLETED, self.on_run_completed)
        logger.info(
            "KARMA wired to EventBus — dispatch=%s falsification=%s",
            "real" if self._dispatch_available else "heuristic",
            "gate" if self._falsification_gate_available else "heuristic",
        )

    # ── Event Handlers ───────────────────────────────────────────────

    async def on_claims_received(self, event: Event) -> None:
        """Handle 'promtguard.claims' event — falsify via DispatchGate.

        For each CLAIM-GEN-NNN claim:
        1. UPDATE_CLAIM: register claim in KARMA state
        2. FALSIFY: evaluate claim, persist result
        3. Publish karma.falsified with results
        """
        payload = event.payload
        claims = payload.get("claims", [])
        logger.info(
            "KARMA received %d claims (cid=%s, dispatch=%s)",
            len(claims), event.correlation_id,
            "real" if self._dispatch_available else "heuristic",
        )

        results: List[FalsificationResult] = []

        for claim_data in claims:
            claim_id = claim_data.get("id", claim_data.get("claim_id", "UNKNOWN"))
            claim_text = claim_data.get("claim", "")
            claim_status = claim_data.get("status", "unverified")

            # Step 1: UPDATE_CLAIM — register claim through DispatchGate
            if self._dispatch_available and self._gate:
                try:
                    self._dispatch_update_claim(claim_id, claim_text, claim_status)
                except Exception as exc:
                    logger.warning("DispatchGate UPDATE_CLAIM failed for %s: %s", claim_id, exc)
                    await self.bus.publish(Event(
                        event_type=EVENT_RUNTIME_ERROR,
                        source="karma",
                        payload={"error": f"UPDATE_CLAIM dispatch failed: {exc}", "claim_id": claim_id},
                        correlation_id=event.correlation_id,
                    ))
                    # Still produce a result for this claim even if dispatch failed
                    result = FalsificationResult(
                        claim_id=claim_id,
                        result="unverified",
                        evidence=[f"DispatchGate error: {exc}"],
                        confidence=0.0,
                    )
                    results.append(result)
                    continue

            # Step 2: FALSIFY — evaluate claim
            result = await self._falsify_claim(claim_data)

            # Step 3: FALSIFY dispatch — persist result through DispatchGate
            if self._dispatch_available and self._gate:
                try:
                    self._dispatch_falsify(claim_id, result)
                except Exception as exc:
                    logger.warning("DispatchGate FALSIFY failed for %s: %s", claim_id, exc)

            results.append(result)
            self._falsification_count += 1

        # Publish falsification results (use actual results count, not input count)
        await self.bus.publish(Event(
            event_type=EVENT_KARMA_FALSIFIED,
            source="karma",
            payload={
                "results": [r.to_dict() for r in results],
                "claim_count": len(results),
                "falsified": sum(1 for r in results if r.result != "unverified"),
            },
            correlation_id=event.correlation_id,
        ))

        # Record experience
        experience = ExperienceRecord(
            experience_id=f"EXP-{self._falsification_count:06d}",
            action="falsify_claims",
            outcome="completed",
            reward=self._calculate_reward(results),
            context_snapshot={
                "claim_ids": [c.get("id", "?") for c in claims],
                "result_summary": {r.claim_id: r.result for r in results},
            },
        )
        self._experience_count += 1

        await self.bus.publish(Event(
            event_type=EVENT_KARMA_EXPERIENCE,
            source="karma",
            payload={"experience": experience.to_dict()},
            correlation_id=event.correlation_id,
        ))

        logger.info(
            "KARMA falsified %d claims: %s",
            len(results),
            {r.claim_id: r.result for r in results},
        )

    async def on_run_completed(self, event: Event) -> None:
        """Handle runtime.completed — finalize Experience Store."""
        logger.info(
            "KARMA run completed: %d claims processed, cid=%s",
            self._falsification_count,
            event.correlation_id,
        )

    # ── DispatchGate Integration ─────────────────────────────────────

    def _dispatch_update_claim(self, claim_id: str, claim_text: str, status: str) -> None:
        """Register a claim through DispatchGate as UPDATE_CLAIM action.

        This writes to /claims/{id}/ (allowed by MUTATION_MATRIX).
        """
        action = self._Action(
            type="UPDATE_CLAIM",
            payload={
                "claim_id": claim_id,
                "claim": claim_text,
                "status": status,
            },
        )
        self._gate.dispatch(action)  # sync — fast SQLite writes, fine for event loop
        logger.debug("UPDATE_CLAIM dispatched: %s → state_version=%d", claim_id, self._gate.version)

    def _dispatch_falsify(self, claim_id: str, result: FalsificationResult) -> None:
        """Persist falsification result through DispatchGate as FALSIFY action.

        This writes to /claims/{id}/status and /karma_executions/.
        """
        action = self._Action(
            type="FALSIFY",
            payload={
                "claim_id": claim_id,
                "result": result.result,
                "confidence": result.confidence,
                "evidence": result.evidence,
                "gate_version": result.gate_version,
            },
        )
        self._gate.dispatch(action)  # sync — fast SQLite writes, fine for event loop
        logger.debug("FALSIFY dispatched: %s → %s (state_version=%d)", claim_id, result.result, self._gate.version)

    # ── Falsification Logic ──────────────────────────────────────────

    async def _falsify_claim(self, claim_data: Dict[str, Any]) -> FalsificationResult:
        """Falsify a single claim through FalsificationGate (6 probes).

        Writes claim text to temp file, runs through FalsificationGate.run(),
        maps probe results to claim verdict. Falls back to heuristic
        if FalsificationGate is unavailable.

        Probe → Verdict mapping:
          - assumptions    → "are claims sourced?" → supported/refuted
          - contradictions → "contradicts known facts?" → refuted/conflicted
          - determinism    → "uses vague language?" → unverified
          - regressions    → "regression markers in claim?" → conflicted
          - idempotency    → "is claim repeatable?" → confirmed
          - test_coverage  → "is claim testable?" → unverified/supported
        """
        claim_id = claim_data.get("id", claim_data.get("claim_id", "UNKNOWN"))
        claim_text = claim_data.get("claim", "")
        status = claim_data.get("status", "unverified")

        # If claim was already refuted, skip gate (preserve existing verdict)
        if status == "refuted":
            self._heuristic_falsifications += 1
            return FalsificationResult(
                claim_id=claim_id,
                result="refuted",
                evidence=["Previously refuted in claim-log.jsonl — gate skipped"],
                confidence=0.9,
                gate_version="heuristic-v1",
            )

        # ── Cross-reference against preprocessor evidence FIRST ──
        cross_ref = self._cross_reference_claim(claim_text)
        has_preprocess_evidence = bool(
            self._preprocess_evidence_requirements or self._preprocess_evidence_tests
        )

        # If we have preprocessor evidence and a strong match, use it directly
        if has_preprocess_evidence:
            req_overlap = cross_ref.get("req_overlap", 0.0)
            test_overlap = cross_ref.get("test_overlap", 0.0)

            # Strong match: claim aligns with an LLM requirement AND an LLM test
            if req_overlap >= 0.3 and test_overlap >= 0.2:
                self._cross_reference_hits += 1
                evidence_lines = [
                    f"[preprocess] ✅ Matched requirement: {cross_ref.get('matched_requirement', '?')[:150]}",
                    f"[preprocess] ✅ Matched test: {cross_ref.get('matched_test', '?')[:150]}",
                    f"[preprocess] req_overlap={req_overlap} test_overlap={test_overlap} goal_overlap={cross_ref.get('goal_overlap', 0)}",
                    f"[preprocess] Source: LLMPreProcessor structured output (mode={self._preprocess_evidence.get('mode', '?')})",
                ]
                confidence = min(0.95, 0.5 + req_overlap * 0.5 + test_overlap * 0.4)
                return FalsificationResult(
                    claim_id=claim_id,
                    result="supported",
                    evidence=evidence_lines,
                    confidence=round(confidence, 2),
                    gate_version="preprocess-crossref-v1",
                )

            # Medium match: claim aligns with a requirement only
            if req_overlap >= 0.2:
                self._cross_reference_hits += 1
                evidence_lines = [
                    f"[preprocess] ✅ Matched requirement: {cross_ref.get('matched_requirement', '?')[:150]}",
                    f"[preprocess] req_overlap={req_overlap} (test_overlap={test_overlap})",
                    f"[preprocess] Source: LLMPreProcessor (mode={self._preprocess_evidence.get('mode', '?')})",
                ]
                return FalsificationResult(
                    claim_id=claim_id,
                    result="supported",
                    evidence=evidence_lines,
                    confidence=round(min(0.75, 0.4 + req_overlap * 0.8), 2),
                    gate_version="preprocess-crossref-v1",
                )

            # Weak match: claim has some overlap with tests
            if test_overlap >= 0.15:
                self._cross_reference_hits += 1
                evidence_lines = [
                    f"[preprocess] ⚠️ Partial test match: {cross_ref.get('matched_test', '?')[:150]}",
                    f"[preprocess] test_overlap={test_overlap} (req_overlap={req_overlap})",
                ]
                return FalsificationResult(
                    claim_id=claim_id,
                    result="unverified",
                    evidence=evidence_lines,
                    confidence=round(0.25 + test_overlap * 0.5, 2),
                    gate_version="preprocess-crossref-v1",
                )

            # No match: claim has NO overlap with requirements or tests
            # This is suspicious — the LLM didn't anticipate this claim
            if req_overlap < 0.1 and test_overlap < 0.1 and has_preprocess_evidence:
                evidence_lines = [
                    f"[preprocess] ⚠️ No match: claim not found in LLM's requirements or tests",
                    f"[preprocess] req_overlap={req_overlap} test_overlap={test_overlap}",
                    f"[preprocess] {len(self._preprocess_evidence_requirements)} requirements, {len(self._preprocess_evidence_tests)} tests checked",
                ]
                return FalsificationResult(
                    claim_id=claim_id,
                    result="unverified",
                    evidence=evidence_lines,
                    confidence=0.15,  # Lower than default — no evidence at all
                    gate_version="preprocess-crossref-v1",
                )

        # ── Path A: Real FalsificationGate ──
        if self._falsification_gate_available and self._falsification_gate:
            try:
                return await self._falsify_via_gate(claim_id, claim_text)
            except Exception as exc:
                logger.warning(
                    "FalsificationGate.run() failed for %s: %s — falling back to heuristic",
                    claim_id, exc,
                )
                # Fall through to heuristic

        # ── Path B: Heuristic fallback ──
        self._heuristic_falsifications += 1
        return self._falsify_heuristic(claim_id, claim_text, claim_data)

    async def _falsify_via_gate(self, claim_id: str, claim_text: str) -> FalsificationResult:
        """Evaluate claim through FalsificationGate's 6 probes with claim-log evidence.

        1. Load evidence from claim-log.jsonl (previously verified/falsified claims)
        2. Find related claims by keyword overlap
        3. Write enriched claim file with evidence context
        4. Run gate with evidence in cascade_state
        5. Cross-reference results against known evidence
        """
        # Load evidence context from claim-log.jsonl
        evidence_claims = self._load_claim_evidence(claim_text)
        related_verified = [c for c in evidence_claims if c.get("status") == "verified"]
        related_refuted = [c for c in evidence_claims if c.get("status") == "refuted"]

        # Build enriched claim file with evidence context
        evidence_section = ""
        if related_verified:
            evidence_section += "\n## Previously Verified Claims (evidence source: claim-log.jsonl)\n\n"
            for c in related_verified[:5]:
                evidence_section += f"- ✅ {c['id']}: {c.get('claim', '')[:150]}\n"
                evidence_section += f"  evidence_type={c.get('evidence_type', '?')}, confidence={c.get('confidence', '?')}\n"
        if related_refuted:
            evidence_section += "\n## Previously Refuted Claims (evidence source: claim-log.jsonl)\n\n"
            for c in related_refuted[:5]:
                evidence_section += f"- ❌ {c['id']}: {c.get('claim', '')[:150]}\n"
                evidence_section += f"  evidence_type={c.get('evidence_type', '?')}\n"

        if evidence_claims:
            self._evidence_hits += 1

        claim_file = self._tmp_dir / f"{claim_id}.md"
        claim_file.write_text(
            f"# Claim: {claim_id}\n\n"
            f"{claim_text}\n\n"
            f"---\n"
            f"assumptions:\n"
            f"  - source: promtguard-claims (claim-log.jsonl)\n"
            f"  - domain: software-verification\n"
            f"  - evidence_claims_found: {len(evidence_claims)}\n"
            f"  - verified: {len(related_verified)}\n"
            f"  - refuted: {len(related_refuted)}\n"
            f"{evidence_section}\n",
            encoding="utf-8",
        )

        gate = self._falsification_gate
        cascade_state = {
            "project": self._project,
            "claim_id": claim_id,
            "evidence": {
                "total_related": len(evidence_claims),
                "verified_count": len(related_verified),
                "refuted_count": len(related_refuted),
                "verified_ids": [c["id"] for c in related_verified[:5]],
                "refuted_ids": [c["id"] for c in related_refuted[:5]],
                "source": "claim-log.jsonl",
            },
        }

        try:
            passed, probe_results = gate.run(
                step_name="claim_falsify",
                skill_name="karma",
                output_file=str(claim_file),
                cascade_state=cascade_state,
            )
        finally:
            if not logger.isEnabledFor(logging.DEBUG):
                claim_file.unlink(missing_ok=True)

        self._gate_falsifications += 1

        # Map probe results to claim verdict
        return self._map_gate_results_to_verdict(
            claim_id, claim_text, passed, probe_results, cascade_state["evidence"]
        )

    # ── Claim Evidence Loading ───────────────────────────────────────

    def _load_claim_evidence(self, claim_text: str) -> List[Dict[str, Any]]:
        """Load related claims from claim-log.jsonl as evidence context.

        Finds claims with keyword overlap (same domain, similar patterns).
        Caches results for 30 seconds to avoid repeated file I/O.

        Args:
            claim_text: The claim being evaluated.

        Returns:
            List of related claim dicts from the log.
        """
        import time as _time

        # Cache check
        now = _time.monotonic()
        if self._claim_evidence_cache is not None and (now - self._claim_evidence_loaded_at) < 30:
            return self._find_related_claims(claim_text, self._claim_evidence_cache)

        # Load claim-log.jsonl
        all_claims: List[Dict[str, Any]] = []
        for log_path in self._claim_log_paths:
            if log_path.exists():
                try:
                    for line in log_path.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            import json as _json
                            all_claims.append(_json.loads(line))
                        except Exception:
                            continue
                    logger.debug("Loaded %d claims from %s", len(all_claims), log_path)
                    break  # Use first available log
                except Exception as exc:
                    logger.warning("Failed to read claim-log %s: %s", log_path, exc)

        self._claim_evidence_cache = all_claims
        self._claim_evidence_loaded_at = now
        return self._find_related_claims(claim_text, all_claims)

    def _find_related_claims(
        self, claim_text: str, all_claims: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find claims related to the given claim text by keyword overlap.

        Uses simple token intersection — claims sharing >=2 significant
        words with the target are considered related.
        """
        if not claim_text or not all_claims:
            return []

        # Extract significant words (>=4 chars, not stopwords)
        stopwords = {"this", "that", "with", "from", "have", "been", "were", "they",
                     "will", "would", "could", "should", "must", "shall", "also", "then"}
        target_words = set(
            w.lower().rstrip(".,;:!?)")
            for w in claim_text.split()
            if len(w) >= 4 and w.lower() not in stopwords
        )

        if len(target_words) < 2:
            return []

        related = []
        for c in all_claims:
            claim_words = set(
                w.lower().rstrip(".,;:!?)")
                for w in c.get("claim", "").split()
                if len(w) >= 4 and w.lower() not in stopwords
            )
            overlap = target_words & claim_words
            if len(overlap) >= 2:  # At least 2 significant words in common
                related.append(c)

        return related[:10]  # Max 10 related claims

    def _map_gate_results_to_verdict(
        self,
        claim_id: str,
        claim_text: str,
        all_passed: bool,
        probe_results: list,
        evidence_context: Optional[Dict[str, Any]] = None,
    ) -> FalsificationResult:
        """Map FalsificationGate probe results to a claim verdict.

        Probe → Claim interpretation:
          - assumptions PASS  → claim has documented source (+evidence)
          - assumptions FAIL  → claim has no source (= unverified)
          - contradictions PASS → no conflicts with known facts (+confidence)
          - contradictions FAIL → claim contradicts known state (= refuted)
          - determinism PASS  → claim uses precise language (+confidence)
          - determinism FAIL  → claim uses vague/ambiguous terms (= unverified)
          - regressions FAIL  → claim contains error markers (= conflicted)
          - idempotency PASS  → claim is repeatable/consistent (+confidence)
        """
        evidence = []
        confidence = 0.5
        verdict = "unverified"

        passed_count = 0
        failed_count = 0

        for r in probe_results:
            probe_name = getattr(r, "probe_name", "unknown")
            probe_passed = getattr(r, "passed", False)
            probe_evidence = getattr(r, "evidence_str", getattr(r, "evidence", ""))

            if probe_passed:
                passed_count += 1
                evidence.append(f"[{probe_name}] PASS: {probe_evidence[:150]}")
            else:
                failed_count += 1
                evidence.append(f"[{probe_name}] FAIL: {probe_evidence[:150]}")

        # Cross-claim evidence: if similar claims were previously verified,
        # that supports this claim. If similar claims were refuted, that weakens it.
        if evidence_context:
            verified_count = evidence_context.get("verified_count", 0)
            refuted_count = evidence_context.get("refuted_count", 0)
            if refuted_count > verified_count and refuted_count > 0:
                evidence.append(
                    f"[evidence] ⚠️ {refuted_count} related claims previously REFUTED — "
                    f"cross-claim contradiction detected (source: claim-log.jsonl)"
                )
                verdict = "refuted"
                confidence = 0.7
                return FalsificationResult(
                    claim_id=claim_id,
                    result=verdict,
                    evidence=evidence,
                    confidence=confidence,
                    gate_version="falsification-gate-v2+evidence",
                )
            elif verified_count > 0 and refuted_count == 0:
                evidence.append(
                    f"[evidence] ✅ {verified_count} related claims previously VERIFIED — "
                    f"cross-claim evidence supports this claim (source: claim-log.jsonl)"
                )
                # Boost confidence if supported by verified evidence
                confidence = min(0.9, confidence + 0.15)

        # Derive verdict from probe pattern (ordered by severity)
        # Highest priority: contradictions or regressions → refuted/conflicted
        if any("contradiction" in (getattr(r, "probe_name", "")).lower() and not getattr(r, "passed", True)
               for r in probe_results):
            verdict = "refuted"
            confidence = 0.75
        elif any("regression" in (getattr(r, "probe_name", "")).lower() and not getattr(r, "passed", True)
                 for r in probe_results):
            verdict = "conflicted"
            confidence = 0.6
        elif all_passed:
            verdict = "supported"
            confidence = 0.8
        elif failed_count == 1:
            verdict = "supported"
            confidence = 0.65
        elif not any("assumption" in (getattr(r, "probe_name", "")).lower() and getattr(r, "passed", False)
                      for r in probe_results):
            verdict = "unverified"
            confidence = 0.25
        else:
            confidence = 0.4

        return FalsificationResult(
            claim_id=claim_id,
            result=verdict,
            evidence=evidence,
            confidence=confidence,
            gate_version="falsification-gate-v2",
        )

    def _falsify_heuristic(
        self, claim_id: str, claim_text: str, claim_data: Dict[str, Any]
    ) -> FalsificationResult:
        """Fallback heuristic falsifier — regex-based, used when gate unavailable."""
        if claim_data.get("evidence", ""):
            result = "supported"
            evidence = [claim_data["evidence"]]
            confidence = 0.7
        elif re.search(r'\b(must|shall)\b', claim_text, re.I):
            result = "unverified"
            evidence = ["Imperative claim requires code verification (heuristic fallback)"]
            confidence = 0.3
        else:
            result = "unverified"
            evidence = ["No evidence provided — heuristic fallback"]
            confidence = 0.2

        return FalsificationResult(
            claim_id=claim_id,
            result=result,
            evidence=evidence,
            confidence=confidence,
            gate_version="heuristic-v1",
        )

    # ── Reward Calculation ──────────────────────────────────────────

    def _calculate_reward(self, results: List[FalsificationResult]) -> float:
        """Calculate reward based on falsification outcomes."""
        if not results:
            return 0.0
        falsified = sum(1 for r in results if r.result != "unverified")
        return falsified / len(results)

    # ── Stats ────────────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "falsifications": self._falsification_count,
            "experiences": self._experience_count,
            "dispatch_available": 1 if self._dispatch_available else 0,
            "falsification_gate_available": 1 if self._falsification_gate_available else 0,
            "gate_falsifications": self._gate_falsifications,
            "heuristic_falsifications": self._heuristic_falsifications,
            "evidence_hits": self._evidence_hits,
            "cross_reference_hits": self._cross_reference_hits,
            "preprocess_evidence_available": 1 if self._preprocess_evidence else 0,
        }
