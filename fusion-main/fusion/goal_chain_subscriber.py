"""
Goal-Chain Subscriber — EventBus-driven skill-chain trigger

Subscribes to ``karma.falsified`` AND ``limen.*`` events and maps
results to goal-chain skill-chain triggers. When KARMA refutes
or LIMEN hits rate limits, goal-chain spawns targeted TIDs.

Architecture:
    karma.falsified / limen.rate_limited / limen.key_exhausted events
        ↓
    GoalChainSubscriber.on_falsification() / on_limen_*()
        ↓
    1. Analyze: which claims refuted? Which keys in cooldown?
    2. Map: claim domain / rate-limit type → relevant skill-chain
    3. Trigger: seed TIDs in goal-chain DB via dispatch
    4. Publish: goal_chain.triggered event

Position: 4 (orchestration layer)
Subscribes to: "karma.falsified", "limen.rate_limited", "limen.key_cooldown",
               "limen.key_exhausted", "limen.budget_warning"
Publishes: "goal_chain.triggered", "goal_chain.skill_chain"

WIRING.md: Goal-Chain sits between KARMA (cognition) and LIMEN (execution).
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fusion.event_bus import (
    AsyncEventBus,
    Event,
    EVENT_KARMA_FALSIFIED,
    EVENT_LIMEN_RATE_LIMITED,
    EVENT_LIMEN_KEY_COOLDOWN,
    EVENT_LIMEN_KEY_EXHAUSTED,
    EVENT_LIMEN_BUDGET_WARNING,
    EVENT_LIMEN_KEY_RECOVERED,
)

logger = logging.getLogger(__name__)

# ─── Event types ──────────────────────────────────────────────────────

EVENT_GOAL_CHAIN_TRIGGERED = "goal_chain.triggered"
EVENT_GOAL_CHAIN_SKILL_CHAIN = "goal_chain.skill_chain"
EVENT_GOAL_CHAIN_REWORK = "goal_chain.rework"


# ─── Claim → Skill-Chain Mapping ──────────────────────────────────────

# Hardcoded fallback — when the external JSON file is missing or unreadable.
# Maps claim keywords/patterns to goal-chain skill sections.
# When KARMA refutes a claim matching a pattern, the corresponding
# skill-chain TIDs are triggered for gap-filling.



# Hardcoded fallback — when the external JSON file is missing or unreadable.
# Maps claim keywords/patterns to goal-chain skill sections.
# When KARMA refutes a claim matching a pattern, the corresponding
# skill-chain TIDs are triggered for gap-filling.
_DEFAULT_CLAIM_TO_SKILL_MAP: Dict[str, List[str]] = {}


def _build_reverse_map(mapping: Dict[str, List[str]]) -> Dict[str, Set[str]]:
    """Build reverse map: skill → set of domains that trigger it."""
    reverse: Dict[str, Set[str]] = {}
    for domain, skills in mapping.items():
        for skill in skills:
            if skill not in reverse:
                reverse[skill] = set()
            reverse[skill].add(domain)
    return reverse


def _load_claim_skill_map(project_root: Optional[Path] = None) -> Dict[str, List[str]]:
    """Load CLAIM_TO_SKILL_MAP from external JSON file.

    Tries in order:
      1. fusion-main/fusion/claim-to-skill-map.json (relative to project_root)
      2. Hardcoded _DEFAULT_CLAIM_TO_SKILL_MAP fallback

    The JSON format:
      { "version": "1.0.0", "mappings": { "keyword": ["skill-1", "skill-2"], ... } }

    Returns a dict suitable for _map_claim_to_skills().
    """
    root = Path(project_root) if project_root else Path.cwd()
    json_paths = [
        root / "fusion-main" / "fusion" / "claim-to-skill-map.json",
        root / "claim-to-skill-map.json",
    ]

    for path in json_paths:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            mappings = data.get("mappings", {})
            if mappings and isinstance(mappings, dict):
                # Validate: all values must be non-empty lists of strings
                validated: Dict[str, List[str]] = {}
                for kw, skills in mappings.items():
                    if isinstance(skills, list) and skills and all(isinstance(s, str) for s in skills):
                        validated[kw] = skills
                if validated:
                    logger.info(
                        "GoalChain: loaded %d claim→skill mappings from %s (version %s)",
                        len(validated), path, data.get("version", "?"),
                    )
                    return validated
                else:
                    logger.warning("GoalChain: claim-to-skill-map.json has no valid mappings — using fallback")
        except (json.JSONDecodeError, OSError, KeyError, TypeError) as exc:
            logger.warning("GoalChain: failed to load %s: %s — using fallback", path, exc)

    logger.debug("GoalChain: using hardcoded CLAIM_TO_SKILL_MAP (%d keywords)", len(_DEFAULT_CLAIM_TO_SKILL_MAP))
    return dict(_DEFAULT_CLAIM_TO_SKILL_MAP)


# Module-level reverse map for external consumers.
# NOTE: Built from the hardcoded default — does NOT reflect JSON file overrides.
# The GoalChainSubscriber instance uses self._claim_skill_map for internal lookups.
# Load at module level from JSON file
CLAIM_TO_SKILL_MAP = _load_claim_skill_map()

# Module-level reverse map for external consumers
SKILL_TO_CLAIM_DOMAINS = _build_reverse_map(CLAIM_TO_SKILL_MAP)


# ─── Data Classes ─────────────────────────────────────────────────────


@dataclass
class SkillChainTrigger:
    """A skill-chain triggered by a falsification result."""

    claim_id: str
    trigger_id: str = ""
    claim_text: str = ""
    falsification_result: str = ""  # refuted | unverified | supported
    confidence: float = 0.0
    skills_triggered: List[str] = field(default_factory=list)
    rationale: str = ""
    correlation_id: str = ""
    triggered_at: str = ""
    priority: str = "normal"  # rework | normal

    def __post_init__(self):
        if not self.trigger_id:
            self.trigger_id = f"TRIG-{str(uuid.uuid4())[:8]}"
        if not self.triggered_at:
            self.triggered_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "claim_id": self.claim_id,
            "claim_text": self.claim_text[:200],
            "falsification_result": self.falsification_result,
            "confidence": self.confidence,
            "skills_triggered": self.skills_triggered,
            "rationale": self.rationale,
            "correlation_id": self.correlation_id,
            "triggered_at": self.triggered_at,
            "priority": self.priority,
        }


@dataclass
class ReworkTrigger:
    """A rework TID trigger for refuted claims — highest priority."""

    claim_id: str
    rework_id: str = ""
    claim_text: str = ""
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    skills_triggered: List[str] = field(default_factory=list)
    rework_goal: str = ""
    correlation_id: str = ""
    triggered_at: str = ""

    def __post_init__(self):
        if not self.rework_id:
            self.rework_id = f"RW-{str(uuid.uuid4())[:8]}"
        if not self.triggered_at:
            self.triggered_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rework_id": self.rework_id,
            "claim_id": self.claim_id,
            "claim_text": self.claim_text[:200],
            "evidence": self.evidence[:5],
            "confidence": self.confidence,
            "skills_triggered": self.skills_triggered,
            "rework_goal": self.rework_goal,
            "correlation_id": self.correlation_id,
            "triggered_at": self.triggered_at,
        }


# ─── Goal-Chain Subscriber ────────────────────────────────────────────


class GoalChainSubscriber:
    """Goal-Chain EventBus subscriber — triggers skill-chains from falsification.

    Listens to ``karma.falsified`` events, analyzes which claims were
    refuted or unverified, maps them to relevant skill domains, and
    triggers corresponding goal-chain TID chains.

    Integration modes:
      - ``dispatch_mode="seed"``: Directly seed TIDs via seed_tids.py (default)
      - ``dispatch_mode="event"``: Publish ``goal_chain.triggered`` events only
        (for testing/observation without side effects)

    Usage:
        gc = GoalChainSubscriber(bus, project_root=Path("."))
        gc.wire(bus)
        # Now listens to karma.falsified automatically
    """

    # Only trigger on results that indicate action is needed
    ACTIONABLE_RESULTS = {"refuted", "unverified", "conflicted"}

    def __init__(
        self,
        bus: AsyncEventBus,
        project_root: Optional[Path] = None,
        *,
        dispatch_mode: str = "seed",
        max_investigation_confidence: float = 0.7,
        max_skills_per_trigger: int = 5,
    ):
        self.bus = bus
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._dispatch_mode = dispatch_mode
        # INVERTED threshold: we investigate claims with confidence BELOW this value.
        # Low confidence = KARMA is uncertain → needs MORE investigation.
        # High confidence (>0.7) = KARMA is certain → no investigation needed.
        # Refuted claims are ALWAYS actionable regardless of confidence.
        self._max_investigation_confidence = max_investigation_confidence
        self._max_skills_per_trigger = max_skills_per_trigger

        # Stats
        self._trigger_count = 0
        self._skills_triggered_total = 0
        self._rework_count = 0
        self._rework_skills_total = 0

        # Load claim→skill mapping (JSON file with hardcoded fallback)
        self._claim_skill_map = _load_claim_skill_map(self._project_root)

        # Paths
        self._goal_chain_dir = self._project_root / ".agents" / "skills" / "goal-chain"
        self._seed_script = self._goal_chain_dir / "scripts" / "seed_tids.py"
        self._dispatch_script = self._goal_chain_dir / "scripts" / "dispatch.sh"

    def wire(self, bus: Optional[AsyncEventBus] = None) -> None:
        """Wire goal-chain subscriptions to the EventBus."""
        b = bus or self.bus
        b.subscribe(EVENT_KARMA_FALSIFIED, self.on_falsification)

        # ── LIMEN events → goal-chain mitigation ──
        b.subscribe(EVENT_LIMEN_RATE_LIMITED, self.on_limen_rate_limited)
        b.subscribe(EVENT_LIMEN_KEY_COOLDOWN, self.on_limen_key_cooldown)
        b.subscribe(EVENT_LIMEN_KEY_EXHAUSTED, self.on_limen_key_exhausted)
        b.subscribe(EVENT_LIMEN_BUDGET_WARNING, self.on_limen_budget_warning)
        b.subscribe(EVENT_LIMEN_KEY_RECOVERED, self.on_limen_key_recovered)

        logger.info(
            "GoalChain wired to EventBus (karma.falsified + limen.*) dispatch=%s",
            self._dispatch_mode,
        )

    # ── Event Handler ─────────────────────────────────────────────────

    async def on_falsification(self, event: Event) -> None:
        """Handle ``karma.falsified`` — analyze results and trigger skill-chains.

        For each refuted/unverified claim above confidence threshold:
        1. Match claim text against CLAIM_TO_SKILL_MAP
        2. Deduplicate skills across claims
        3. Trigger skill-chains (seed TIDs or publish events)
        """
        payload = event.payload
        results = payload.get("results", [])
        cid = event.correlation_id

        # Separate claims by type:
        # - refuted: ALWAYS actionable (KARMA found hard evidence against it)
        # - unverified/conflicted: actionable only when confidence is LOW
        #   (low confidence = KARMA uncertain → needs investigation)
        # - high-confidence unverified: KARMA is sure it's fine → skip
        refuted = [
            r for r in results
            if r.get("result") == "refuted"
        ]
        uncertain = [
            r for r in results
            if r.get("result") in ("unverified", "conflicted")
            and r.get("confidence", 0.5) < self._max_investigation_confidence
        ]
        actionable = refuted + uncertain

        if not actionable:
            logger.debug("GoalChain: no actionable claims in run %s", cid)
            return

        logger.info(
            "GoalChain: %d/%d claims actionable (cid=%s)",
            len(actionable), len(results), cid,
        )

        # Separate refuted (→ rework) from unverified (→ investigate)
        refuted_claims = [r for r in actionable if r.get("result") == "refuted"]
        unverified_claims = [r for r in actionable if r.get("result") != "refuted"]

        # Map claims to skills (deduplicated)
        triggered_skills: Set[str] = set()
        triggers: List[SkillChainTrigger] = []
        rework_triggers: List[ReworkTrigger] = []

        # Collect rework skills for dedup (prevent double-seeding)
        rework_skills_set: Set[str] = set()

        # ── Path A: REFUTED → REWORK (high priority) ──
        for r in refuted_claims:
            claim_id = r.get("claim_id", "UNKNOWN")
            evidence_list = r.get("evidence", []) if isinstance(r.get("evidence"), list) else [str(r.get("evidence", ""))]
            evidence_text = " ".join(evidence_list)
            claim_text = r.get("claim_text", r.get("claim", f"{claim_id} {evidence_text}"))
            confidence = r.get("confidence", 0.0)

            skills = self._map_claim_to_skills(claim_text, claim_id)
            if not skills:
                continue

            rework_goal = (
                f"REWORK: Fix refuted claim {claim_id} — {claim_text[:100]}"
            )
            rationale = (
                f"KARMA REFUTED '{claim_text[:80]}...' "
                f"(confidence={confidence:.1f}) → REWORK: triggering {skills[:3]}"
            )

            # Rework trigger — highest priority
            rework = ReworkTrigger(
                claim_id=claim_id,
                claim_text=claim_text,
                evidence=evidence_list,
                confidence=confidence,
                skills_triggered=list(skills[:self._max_skills_per_trigger]),
                rework_goal=rework_goal,
                correlation_id=cid,
            )
            rework_triggers.append(rework)
            rework_skills_set.update(skills[:self._max_skills_per_trigger])
            self._rework_count += 1
            self._rework_skills_total += len(skills[:self._max_skills_per_trigger])

            # Also register as a regular trigger for the skill-chain event
            trigger = SkillChainTrigger(
                claim_id=claim_id,
                claim_text=claim_text,
                falsification_result="refuted",
                confidence=confidence,
                skills_triggered=list(skills[:self._max_skills_per_trigger]),
                rationale=rationale,
                correlation_id=cid,
                priority="rework",
            )
            triggers.append(trigger)
            self._trigger_count += 1
            self._skills_triggered_total += len(skills[:self._max_skills_per_trigger])

        # ── Path B: UNVERIFIED → INVESTIGATE (normal priority) ──
        for r in unverified_claims:
            claim_id = r.get("claim_id", "UNKNOWN")
            evidence_text = " ".join(r.get("evidence", [])) if isinstance(r.get("evidence"), list) else str(r.get("evidence", ""))
            claim_text = r.get("claim_text", r.get("claim", f"{claim_id} {evidence_text}"))
            result_type = r.get("result", "unverified")
            confidence = r.get("confidence", 0.0)

            skills = self._map_claim_to_skills(claim_text, claim_id)
            if not skills:
                continue

            # Deduplicate: skip skills already handled by rework path
            new_skills = [s for s in skills if s not in triggered_skills and s not in rework_skills_set]
            new_skills = new_skills[:self._max_skills_per_trigger]

            if not new_skills:
                continue

            triggered_skills.update(new_skills)

            rationale = (
                f"KARMA {result_type} '{claim_text[:80]}...' "
                f"(confidence={confidence:.1f}) → triggering {new_skills}"
            )

            trigger = SkillChainTrigger(
                claim_id=claim_id,
                claim_text=claim_text,
                falsification_result=result_type,
                confidence=confidence,
                skills_triggered=list(new_skills),
                rationale=rationale,
                correlation_id=cid,
                priority="normal",
            )
            triggers.append(trigger)
            self._trigger_count += 1
            self._skills_triggered_total += len(new_skills)

        # Publish triggered event (all triggers)
        await self.bus.publish(Event(
            event_type=EVENT_GOAL_CHAIN_TRIGGERED,
            source="goal_chain",
            payload={
                "triggers": [t.to_dict() for t in triggers],
                "trigger_count": len(triggers),
                "rework_count": len(rework_triggers),
                "skills_triggered": sorted(triggered_skills),
                "total_skills": len(triggered_skills),
            },
            correlation_id=cid,
        ))

        # Publish rework event (refuted claims only — highest priority)
        if rework_triggers:
            await self.bus.publish(Event(
                event_type=EVENT_GOAL_CHAIN_REWORK,
                source="goal_chain",
                payload={
                    "reworks": [r.to_dict() for r in rework_triggers],
                    "rework_count": len(rework_triggers),
                    "claim_ids": [r.claim_id for r in rework_triggers],
                    "rework_goals": [r.rework_goal for r in rework_triggers],
                },
                correlation_id=cid,
            ))

        # Dispatch: seed TIDs if in seed mode
        # Rework dispatch first (higher priority), then skill-chain dispatch
        if self._dispatch_mode == "seed":
            if rework_triggers:
                self._dispatch_rework_tids(rework_triggers, cid)
            if triggered_skills:
                self._dispatch_skill_chains(sorted(triggered_skills), cid)

        logger.info(
            "GoalChain: triggered %d skill-chains (%s) for run %s",
            len(triggered_skills), ", ".join(sorted(triggered_skills)[:5]), cid,
        )

    # ── Claim → Skill Mapping ────────────────────────────────────────

    def _map_claim_to_skills(self, claim_text: str, claim_id: str = "") -> List[str]:
        """Map a claim to relevant skill-chain sections.

        Uses CLAIM_TO_SKILL_MAP to match keywords in the claim text
        to skill sections. Falls back to ``track-findings`` for
        unmatched claims.

        Args:
            claim_text: The claim text to analyze.
            claim_id: Optional claim ID for logging.

        Returns:
            List of skill section names (ordered by relevance).
        """
        if not claim_text:
            return ["track-findings"]

        text_lower = claim_text.lower()
        matched_skills: Dict[str, int] = {}  # skill → match score

        for keyword, skills in self._claim_skill_map.items():
            if keyword in text_lower:
                for skill in skills:
                    matched_skills[skill] = matched_skills.get(skill, 0) + 1

        if not matched_skills:
            # Fallback: track-findings for any unverifiable claim
            return ["track-findings"]

        # Sort by match score (descending), then alphabetically
        sorted_skills = sorted(
            matched_skills.items(),
            key=lambda x: (-x[1], x[0]),
        )
        return [s for s, _ in sorted_skills]

    # ── TID Dispatch ──────────────────────────────────────────────────

    def _dispatch_rework_tids(
        self, rework_triggers: List[ReworkTrigger], correlation_id: str
    ) -> None:
        """Seed REWORK TIDs for refuted claims — highest priority.

        Each refuted claim gets a dedicated REWORK goal that includes
        the claim ID, evidence, and targeted skills. The goal-chain
        runtime will execute these TIDs before normal skill-chain TIDs.

        Args:
            rework_triggers: List of ReworkTrigger objects.
            correlation_id: Event correlation ID for tracing.
        """
        if not self._seed_script.exists():
            logger.warning("GoalChain: seed_tids.py not found — cannot dispatch rework")
            return

        for rework in rework_triggers:
            try:
                goal = rework.rework_goal
                skills = rework.skills_triggered[:3]

                result = subprocess.run(
                    [
                        "python3",
                        str(self._seed_script),
                        "PZ",
                        goal,
                        "--skills-only",
                        "--skills", ",".join(skills),
                    ],
                    cwd=str(self._project_root),
                    capture_output=True,
                    text=True,
                    timeout=15,
                )

                if result.returncode == 0:
                    logger.info(
                        "GoalChain REWORK: seeded TIDs for %s → %s",
                        rework.claim_id, skills,
                    )
                else:
                    logger.error(
                        "GoalChain REWORK: seed_tids.py failed for %s: %s",
                        rework.claim_id,
                        result.stderr[:200] if result.stderr else "unknown",
                    )
            except subprocess.TimeoutExpired:
                logger.error("GoalChain REWORK: seed_tids.py timed out for %s", rework.claim_id)
            except Exception as exc:
                logger.exception("GoalChain REWORK: dispatch failed for %s: %s", rework.claim_id, exc)

    def _dispatch_skill_chains(self, skills: List[str], correlation_id: str) -> None:
        """Seed goal-chain TIDs for triggered skills.

        Calls ``seed_tids.py`` to insert STACK TIDs for the triggered
        skills into the active run. This is a fire-and-forget operation
        — the goal-chain runtime handles execution.

        Args:
            skills: List of skill section names to trigger.
            correlation_id: Event correlation ID for tracing.
        """
        if not self._seed_script.exists():
            logger.warning(
                "GoalChain: seed_tids.py not found at %s — cannot dispatch",
                self._seed_script,
            )
            return

        try:
            # Build a mini-goal for the triggered skills
            goal = f"KARMA-Falsifikation (cid={correlation_id}): " + ", ".join(skills[:3])
            if len(skills) > 3:
                goal += f" +{len(skills) - 3} more"

            result = subprocess.run(
                [
                    "python3",
                    str(self._seed_script),
                    "PZ",
                    goal,
                    "--skills-only",
                    "--skills", ",".join(skills),
                ],
                cwd=str(self._project_root),
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                logger.info(
                    "GoalChain: seeded %d skill TIDs (run goal: %s)",
                    len(skills), goal[:80],
                )
                # Publish skill_chain event (fire-and-forget with error handling)
                def _safe_publish():
                    try:
                        asyncio.create_task(self._publish_skill_chain(skills, correlation_id, goal))
                    except RuntimeError as exc:
                        logger.warning("GoalChain: cannot create publish task (no event loop): %s", exc)
                _safe_publish()
            else:
                logger.error(
                    "GoalChain: seed_tids.py failed: %s",
                    result.stderr[:200] if result.stderr else "unknown error",
                )

        except subprocess.TimeoutExpired:
            logger.error("GoalChain: seed_tids.py timed out")
        except Exception as exc:
            logger.exception("GoalChain: dispatch failed: %s", exc)

    # ── LIMEN Rate-Limit → TID FAIL ──────────────────────────────────

    def _fail_active_tids_for_provider(
        self,
        *,
        provider: str,
        deployment: str,
        reason: str,
        limit_type: str = "unknown",
        cooldown_seconds: float = 0.0,
        correlation_id: str = "",
    ) -> int:
        """Set all IN_PROGRESS TIDs to FAILED when LIMEN reports rate limit / key exhaustion.

        Writes a dispatcher_decision entry with rate-limit details so the
        dashboard can show WHY the TID failed. This enforces REGEL 1:
        TIDs whose execution was interrupted by infrastructure failure
        are explicitly marked, not left dangling.

        Returns the number of TIDs that were set to FAILED.
        """
        import sqlite3 as _sqlite
        from datetime import datetime as _dt, timezone as _tz

        goal_db = self._goal_chain_dir / "db" / "tid-state.db"
        if not goal_db.exists():
            logger.warning("GoalChain: tid-state.db not found — cannot fail TIDs")
            return 0

        try:
            conn = _sqlite.connect(str(goal_db))
            conn.row_factory = _sqlite.Row
            now = _dt.now(_tz.utc).isoformat()

            # Find all IN_PROGRESS TIDs across all runs
            inprog = conn.execute(
                "SELECT tid, run_id, phase, phase_section, skill_name FROM tasks WHERE status='IN_PROGRESS'"
            ).fetchall()

            if not inprog:
                logger.info("GoalChain: no IN_PROGRESS TIDs to fail for %s/%s", provider, deployment)
                conn.close()
                return 0

            failed_count = 0
            for row in inprog:
                tid = row["tid"]
                run_id = row["run_id"]

                # Set TID to FAILED
                conn.execute(
                    "UPDATE tasks SET status='FAILED', updated_at=?, completed_at=? WHERE tid=?",
                    (now, now, tid),
                )

                # Write dispatcher_decision with rate-limit context
                decision_value = (
                    f"LIMEN_{limit_type.upper()}: {provider}/{deployment} "
                    f"cooldown={cooldown_seconds:.0f}s reason={reason[:200]}"
                )
                conn.execute(
                    """INSERT INTO dispatcher_decisions
                       (tid, decision_type, decision_value, rationale, timestamp)
                       VALUES (?, 'LIMEN_RATE_LIMITED', ?, ?, ?)""",
                    (tid, decision_value, reason[:500], now),
                )

                failed_count += 1
                logger.warning(
                    "GoalChain: FAILED TID %s due to LIMEN %s: %s/%s",
                    tid, limit_type.upper(), provider, deployment,
                )

            conn.commit()
            conn.close()

            if failed_count > 0:
                logger.warning(
                    "GoalChain: FAILED %d IN_PROGRESS TIDs due to LIMEN %s on %s/%s",
                    failed_count, limit_type.upper(), provider, deployment,
                )

            return failed_count

        except Exception as exc:
            logger.exception("GoalChain: failed to set TIDs to FAILED: %s", exc)
            return 0

    def _recover_failed_tids_for_provider(
        self,
        *,
        provider: str,
        deployment: str,
        correlation_id: str = "",
    ) -> int:
        """Reset FAILED TIDs to PENDING when a LIMEN key recovers from cooldown.

        Finds TIDs that were marked FAILED due to LIMEN rate limits / key
        exhaustion for the given provider/deployment, and resets them to
        PENDING so the goal-chain worker can retry them automatically.

        Only resets TIDs that have a dispatcher_decision with LIMEN_RATE_LIMITED
        or LIMEN_KEY_EXHAUSTED — not TIDs that failed for other reasons.

        Returns the number of TIDs recovered.
        """
        import sqlite3 as _sqlite

        goal_db = self._goal_chain_dir / "db" / "tid-state.db"
        if not goal_db.exists():
            logger.warning("GoalChain: tid-state.db not found — cannot recover TIDs")
            return 0

        try:
            conn = _sqlite.connect(str(goal_db))
            conn.row_factory = _sqlite.Row
            now = datetime.now(timezone.utc).isoformat()

            # Find FAILED TIDs with LIMEN-related dispatcher_decisions
            # matching this provider/deployment
            failed_tids = conn.execute(
                """SELECT DISTINCT t.tid, t.run_id,
                          d.decision_value, d.decision_type
                   FROM tasks t
                   JOIN dispatcher_decisions d ON d.tid = t.tid
                   WHERE t.status = 'FAILED'
                     AND d.decision_type IN ('LIMEN_RATE_LIMITED', 'LIMEN_KEY_EXHAUSTED')
                     AND (d.decision_value LIKE ? OR d.decision_value LIKE ?)
                """,
                (f"%{provider}/{deployment}%", f"%{provider}%{deployment}%"),
            ).fetchall()

            if not failed_tids:
                logger.info(
                    "GoalChain: no FAILED TIDs to recover for %s/%s",
                    provider, deployment,
                )
                conn.close()
                return 0

            recovered_count = 0
            for row in failed_tids:
                tid = row["tid"]
                old_reason = row["decision_value"]

                # Reset TID to PENDING
                conn.execute(
                    "UPDATE tasks SET status='PENDING', completed_at=NULL, updated_at=? WHERE tid=?",
                    (now, tid),
                )

                # Record recovery decision
                recovery_value = (
                    f"RECOVERED: Key {provider}/{deployment} returned from cooldown. "
                    f"Previous failure: {old_reason[:200]}"
                )
                conn.execute(
                    """INSERT INTO dispatcher_decisions
                       (tid, decision_type, decision_value, rationale, timestamp)
                       VALUES (?, 'LIMEN_KEY_RECOVERED', ?, ?, ?)""",
                    (
                        tid,
                        recovery_value,
                        f"Automatic recovery after {provider}/{deployment} key cooldown ended. "
                        f"TID reset from FAILED → PENDING for retry.",
                        now,
                    ),
                )

                recovered_count += 1
                logger.info(
                    "GoalChain: RECOVERED TID %s → PENDING (was FAILED for %s/%s)",
                    tid, provider, deployment,
                )

            conn.commit()
            conn.close()

            if recovered_count > 0:
                logger.warning(
                    "GoalChain: RECOVERED %d FAILED TIDs → PENDING for %s/%s",
                    recovered_count, provider, deployment,
                )

            return recovered_count

        except Exception as exc:
            logger.exception("GoalChain: failed to recover TIDs: %s", exc)
            return 0

    async def _publish_skill_chain(
        self, skills: List[str], correlation_id: str, goal: str
    ) -> None:
        """Publish ``goal_chain.skill_chain`` event after seeding TIDs."""
        await self.bus.publish(Event(
            event_type=EVENT_GOAL_CHAIN_SKILL_CHAIN,
            source="goal_chain",
            payload={
                "skills": skills,
                "goal": goal,
                "correlation_id": correlation_id,
            },
            correlation_id=correlation_id,
        ))

    # ── LIMEN Event Handlers ──────────────────────────────────────────

    # Maps rate limit types to skill-chains for mitigation
    RATELIMIT_TO_SKILL_MAP: Dict[str, List[str]] = {
        "tpm": ["track-findings", "validation"],
        "rpd": ["track-findings", "delivery-tracking"],
        "rpm": ["track-findings", "validation"],
        "monthly": ["autorun", "delivery-tracking"],   # Monthly = critical
        "concurrent": ["track-findings"],
        "unknown": ["track-findings", "validation"],
    }

    async def on_limen_rate_limited(self, event: Event) -> None:
        """Handle ``limen.rate_limited`` — FAIL active TIDs + trigger mitigation.

        When LIMEN hits a 429, goal-chain:
        1. FAILs all IN_PROGRESS TIDs for the affected provider/deployment
        2. Writes dispatcher_decisions with rate-limit details
        3. Classifies the rate limit type (TPM/RPD/RPM/MONTHLY/CONCURRENT)
        4. Maps to relevant skill-chains for investigation
        5. Seeds targeted TIDs for rate-limit analysis
        """
        payload = event.payload
        limit_type = payload.get("limit_type", "unknown")
        deployment = payload.get("deployment", "unknown")
        provider = payload.get("provider", "unknown")
        cooldown = payload.get("cooldown_seconds", 60)
        strategy = payload.get("strategy", "")

        # ── FAIL active TIDs that were using this provider ──
        self._fail_active_tids_for_provider(
            provider=provider,
            deployment=deployment,
            reason=f"LIMEN 429 {limit_type.upper()}: {provider}/{deployment} cooldown={cooldown:.0f}s",
            limit_type=limit_type,
            cooldown_seconds=cooldown,
            correlation_id=event.correlation_id,
        )

        logger.info(
            "GoalChain: LIMEN rate_limited — type=%s deployment=%s/%s cooldown=%.1fs",
            limit_type, deployment, provider, cooldown,
        )

        # Map to skills
        skills = self.RATELIMIT_TO_SKILL_MAP.get(
            limit_type, self.RATELIMIT_TO_SKILL_MAP["unknown"]
        )

        # Build goal
        goal = (
            f"LIMEN-RateLimit [{limit_type.upper()}] on {provider}/{deployment}: "
            f"{cooldown:.0f}s cooldown — investigate and mitigate"
        )
        rationale = (
            f"LIMEN detected {limit_type.upper()} rate limit on {provider}/{deployment}. "
            f"Cooldown: {cooldown:.0f}s. Strategy: {strategy}. "
            f"Triggering: {skills}"
        )

        trigger = SkillChainTrigger(
            claim_id=f"RL-{deployment}-{limit_type}",
            claim_text=goal,
            falsification_result="rate_limited",
            confidence=1.0,
            skills_triggered=skills,
            rationale=rationale,
            correlation_id=event.correlation_id,
            priority="normal",
        )
        self._trigger_count += 1
        self._skills_triggered_total += len(skills)

        await self.bus.publish(Event(
            event_type=EVENT_GOAL_CHAIN_TRIGGERED,
            source="goal_chain",
            payload={
                "triggers": [trigger.to_dict()],
                "trigger_count": 1,
                "rework_count": 0,
                "skills_triggered": skills,
                "total_skills": len(skills),
                "source_event": "limen.rate_limited",
            },
            correlation_id=event.correlation_id,
        ))

        if self._dispatch_mode == "seed":
            self._dispatch_skill_chains(skills, event.correlation_id)

    async def on_limen_key_cooldown(self, event: Event) -> None:
        """Handle ``limen.key_cooldown`` — monitor key-health (NO TID dispatch).

        Key cooldown is informational. TID seeding is handled by
        ``on_limen_rate_limited`` (same pipeline event). This handler
        only publishes a ``goal_chain.triggered`` event for observability
        — it does NOT dispatch duplicate TIDs.
        """
        payload = event.payload
        deployment = payload.get("deployment", "unknown")
        provider = payload.get("provider", "unknown")
        failure_type = payload.get("failure_type", "")
        cooldown_until = payload.get("cooldown_until", "")

        logger.info(
            "GoalChain: LIMEN key_cooldown — %s/%s reason=%s until=%s (monitoring only)",
            provider, deployment, failure_type, cooldown_until,
        )

        # Publish observability event (no TID dispatch — rate_limited handler covers that)
        await self.bus.publish(Event(
            event_type=EVENT_GOAL_CHAIN_TRIGGERED,
            source="goal_chain",
            payload={
                "triggers": [],
                "trigger_count": 0,
                "skills_triggered": [],
                "total_skills": 0,
                "source_event": "limen.key_cooldown",
                "note": "Monitoring only — rate_limited handler dispatches TIDs",
                "deployment": deployment,
                "provider": provider,
                "failure_type": failure_type,
            },
            correlation_id=event.correlation_id,
        ))

    async def on_limen_key_exhausted(self, event: Event) -> None:
        """Handle ``limen.key_exhausted`` — CRITICAL: FAIL ALL + emergency provision.

        When all keys for a deployment are exhausted (dead/cooldown),
        goal-chain FAILs ALL active TIDs for that provider and triggers
        EMERGENCY TIDs for key rotation/provisioning.
        This is the highest-priority LIMEN event.
        """
        payload = event.payload
        deployment = payload.get("deployment", "unknown")
        provider = payload.get("provider", "unknown")
        severity = payload.get("severity", "critical")
        message = payload.get("message", "")
        active = payload.get("active_count", 0)
        cooldown = payload.get("cooldown_count", 0)
        dead = payload.get("dead_count", 0)

        logger.critical(
            "GoalChain: LIMEN key_exhausted — %s/%s active=%d cooldown=%d dead=%d: %s",
            provider, deployment, active, cooldown, dead, message,
        )

        # ── FAIL ALL active TIDs — no keys available to execute them ──
        self._fail_active_tids_for_provider(
            provider=provider,
            deployment=deployment,
            reason=f"LIMEN KEY_EXHAUSTED: {provider}/{deployment} active={active} cooldown={cooldown} dead={dead}",
            limit_type="exhausted",
            cooldown_seconds=0,
            correlation_id=event.correlation_id,
        )

        # Emergency skills: autorun (quick assessment) + delivery-tracking (key rot)
        skills = ["autorun", "delivery-tracking", "security-scan"]
        goal = (
            f"EMERGENCY: All keys exhausted for {provider}/{deployment}! "
            f"active={active} cooldown={cooldown} dead={dead}. "
            f"IMMEDIATE key rotation required."
        )

        # REWORK-level priority for key exhaustion
        rework = ReworkTrigger(
            claim_id=f"KEY-EXHAUST-{deployment}",
            claim_text=goal,
            evidence=[message],
            confidence=1.0,
            skills_triggered=skills,
            rework_goal=goal,
            correlation_id=event.correlation_id,
        )
        self._rework_count += 1
        self._rework_skills_total += len(skills)

        # Publish rework event for emergency key rotation
        await self.bus.publish(Event(
            event_type=EVENT_GOAL_CHAIN_REWORK,
            source="goal_chain",
            payload={
                "reworks": [rework.to_dict()],
                "rework_count": 1,
                "claim_ids": [rework.claim_id],
                "rework_goals": [goal],
                "severity": "CRITICAL",
            },
            correlation_id=event.correlation_id,
        ))

        if self._dispatch_mode == "seed":
            self._dispatch_rework_tids([rework], event.correlation_id)

    async def on_limen_budget_warning(self, event: Event) -> None:
        """Handle ``limen.budget_warning`` — proactive budget monitoring.

        When token or request budgets near exhaustion, goal-chain
        publishes a ``goal_chain.triggered`` event for observability
        and triggers monitoring TIDs for proactive rate-limit avoidance.
        """
        payload = event.payload
        deployment = payload.get("deployment", "unknown")
        provider = payload.get("provider", "unknown")
        budget_type = payload.get("budget_type", "")
        used = payload.get("used", 0)
        max_budget = payload.get("max_budget", 0)
        ratio = payload.get("ratio", 0.0)
        severity = payload.get("severity", "warning")

        logger.warning(
            "GoalChain: LIMEN budget_warning — %s/%s %s budget %.1f%% (%d/%d) severity=%s",
            provider, deployment, budget_type, ratio * 100, used, max_budget, severity,
        )

        skills = ["track-findings"]
        if severity == "critical":
            skills.append("delivery-tracking")

        # Publish observability event
        await self.bus.publish(Event(
            event_type=EVENT_GOAL_CHAIN_TRIGGERED,
            source="goal_chain",
            payload={
                "triggers": [],
                "trigger_count": 1,
                "skills_triggered": skills,
                "total_skills": len(skills),
                "source_event": "limen.budget_warning",
                "deployment": deployment,
                "provider": provider,
                "budget_type": budget_type,
                "ratio": ratio,
                "severity": severity,
            },
            correlation_id=event.correlation_id,
        ))

        self._dispatch_skill_chains(skills, event.correlation_id)

    async def on_limen_key_recovered(self, event: Event) -> None:
        """Handle ``limen.key_recovered`` — reset FAILED TIDs → PENDING.

        When a LIMEN key returns from cooldown (status: cooldown → active),
        goal-chain finds all TIDs that were FAILED due to that provider's
        rate limit / key exhaustion, and resets them to PENDING for
        automatic retry by the worker.

        This implements the RECOVERY action — the counterpart to the
        FAIL action in on_limen_rate_limited / on_limen_key_exhausted.
        """
        payload = event.payload
        deployment = payload.get("deployment", "unknown")
        provider = payload.get("provider", "unknown")

        logger.info(
            "GoalChain: LIMEN key_recovered — %s/%s, recovering FAILED TIDs",
            provider, deployment,
        )

        # Reset FAILED TIDs → PENDING
        recovered = self._recover_failed_tids_for_provider(
            provider=provider,
            deployment=deployment,
            correlation_id=event.correlation_id,
        )

        # Publish recovery event
        await self.bus.publish(Event(
            event_type=EVENT_GOAL_CHAIN_TRIGGERED,
            source="goal_chain",
            payload={
                "triggers": [],
                "trigger_count": 0,
                "skills_triggered": [],
                "total_skills": 0,
                "source_event": "limen.key_recovered",
                "deployment": deployment,
                "provider": provider,
                "tids_recovered": recovered,
                "note": f"Reset {recovered} FAILED TIDs → PENDING for automatic retry",
            },
            correlation_id=event.correlation_id,
        ))

    # ── Stats ─────────────────────────────────────────────────────────

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "triggers": self._trigger_count,
            "skills_triggered": self._skills_triggered_total,
            "reworks": self._rework_count,
            "rework_skills": self._rework_skills_total,
            "dispatch_mode": 1 if self._dispatch_mode == "seed" else 0,
        }
