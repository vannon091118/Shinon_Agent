"""
Event Runtime — Async Event-Driven Pipeline Orchestrator

The main entry point that wires Shinon, Promtguard, and KARMA
as async subscribers to the EventBus, replacing the linear
HOFF-0001 → HOFF-0002 → ... handoff sequence.

Flow (event-driven, non-linear):
    User Input
        ↓
    runtime.input event
        ↓
    Shinon (subscriber) → shinon.output event
        ↓
    Promtguard (subscriber) → promtguard.claims event
        ↓
    KARMA (subscriber) → karma.falsified event
        ↓
    runtime.completed event

Each component receives events and publishes results asynchronously.
The WIRING.md remains the logical spec — this is the runtime.

Usage:
    rt = ControlPlaneRuntime()
    await rt.start()                    # Wire all subscribers
    result = await rt.process("Build OAuth2 login")  # Full pipeline
    print(rt.summary())
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fusion.event_bus import (
    AsyncEventBus,
    Event,
    get_event_bus,
    EVENT_RUNTIME_INPUT,
    EVENT_SHINON_OUTPUT,
    EVENT_PROMTGUARD_CLAIMS,
    EVENT_PROMTGUARD_HANDOFF,
    EVENT_KARMA_FALSIFIED,
    EVENT_KARMA_EXPERIENCE,
    EVENT_RUNTIME_ERROR,
    EVENT_RUNTIME_COMPLETED,
    EVENT_RUNTIME_HEARTBEAT,
    EVENT_GOAL_CHAIN_TRIGGERED,
    EVENT_GOAL_CHAIN_SKILL_CHAIN,
)
from fusion.shinon import (
    ShinonEngine,
    ShinonInput,
    ShinonOutput,
)
# Legacy alias for backward compatibility
from fusion.shinon_passthrough import ShinonPassthrough
from fusion.promtguard_claims import (
    Claim,
    ContextToken,
    Handoff,
    PromtguardClaims,
)
from fusion.goal_chain_subscriber import (
    GoalChainSubscriber,
    SkillChainTrigger,
    EVENT_GOAL_CHAIN_TRIGGERED,
    EVENT_GOAL_CHAIN_SKILL_CHAIN,
)
from fusion.limen_subscriber import (
    LIMENSubscriber,
    RateLimitEvent,
    KeyStateEvent,
    BudgetWarning,
)
from fusion.karma_subscriber import (
    KARMASubscriber,
    FalsificationResult,
    ExperienceRecord,
)
from fusion.sanitize_schema import (
    sanitize,
    sanitize_by_schema_name,
    assert_patches_allowed,
)

logger = logging.getLogger(__name__)


# ─── Runtime Result ───────────────────────────────────────────────────


@dataclass
class RuntimeResult:
    """Complete result of one event-driven pipeline run."""

    correlation_id: str = ""
    input_text: str = ""
    shinon_output: Optional[ShinonOutput] = None
    claims: List[Claim] = field(default_factory=list)
    falsification_results: List[FalsificationResult] = field(default_factory=list)
    experience_records: List[ExperienceRecord] = field(default_factory=list)
    error: Optional[str] = None
    started_at: str = ""
    completed_at: str = ""

    def __post_init__(self):
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())[:8]
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()

    def summary(self) -> str:
        lines = [
            f"RuntimeResult(cid={self.correlation_id})",
            f"  input: {self.input_text[:80]}...",
            f"  shinon: {'OK' if self.shinon_output else 'FAIL'}",
            f"  claims: {len(self.claims)} extracted",
            f"  falsified: {sum(1 for r in self.falsification_results if r.result != 'unverified')}/{len(self.falsification_results)}",
        ]
        if self.error:
            lines.append(f"  ERROR: {self.error}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "input_text": self.input_text[:200],
            "shinon_output": self.shinon_output.to_dict() if self.shinon_output else None,
            "claims_count": len(self.claims),
            "falsification_results": [r.to_dict() for r in self.falsification_results],
            "experience_records": [r.to_dict() for r in self.experience_records],
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ─── Control Plane Runtime ────────────────────────────────────────────


class ControlPlaneRuntime:
    """Event-Driven Control Plane Runtime.

    Wires Shinon, Promtguard, and KARMA as async subscribers
    to the EventBus. Processes user input through the full
    pipeline using event-driven communication.

    Each component remains loosely coupled — they only know
    about events, not about each other.
    """

    def __init__(
        self,
        bus: Optional[AsyncEventBus] = None,
        state_dir: Optional[Path] = None,
        identity: Optional[Dict[str, str]] = None,
        dispatch_gate: Optional[Any] = None,
        persistence: Optional[Any] = None,
        timeout: float = 30.0,
    ):
        self.bus = bus or get_event_bus()
        self._state_dir = Path(state_dir) if state_dir else Path(".promtset/state")
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._timeout = timeout

        # Components
        # ── Shinon Engine (Pattern + Memory + Attitudes) ──
        try:
            self.shinon = ShinonEngine(
                identity=None,
                memory_db=Path("fusion-main/data/shinon_memory.db"),
                attitude_db=Path("fusion-main/data/shinon_attitudes.db"),
            )
        except Exception:
            self.shinon = ShinonPassthrough(identity=identity)

        self.promtguard = PromtguardClaims(state_dir=self._state_dir)

        # ── KARMA with real FalsificationGate + DispatchGate ──
        # Try to wire real gates from karma-main. Falls back to heuristic if unavailable.
        dispatch_gate_resolved = dispatch_gate
        falsification_gate_resolved = None
        persistence_resolved = persistence

        if dispatch_gate is None or persistence is None:
            try:
                from karma.core.persistence import create_persistence, create_project_persistence
                from karma.core.dispatch import DispatchGate as KARMA_DispatchGate
                from karma.core.falsification_gate import FalsificationGate

                if persistence is None:
                    persistence_resolved = create_project_persistence("PZ")
                if dispatch_gate is None:
                    dispatch_gate_resolved = KARMA_DispatchGate(persistence_resolved)
                if falsification_gate_resolved is None:
                    falsification_gate_resolved = FalsificationGate(persistence_resolved, "PZ")

                logger.info("KARMA gates wired: DispatchGate + FalsificationGate (6 probes)")
            except ImportError as exc:
                logger.info("karma-main not available — KARMA will use heuristic falsifier: %s", exc)
            except Exception as exc:
                logger.warning("KARMA gate init failed — heuristic fallback: %s", exc)

        self.karma = KARMASubscriber(
            self.bus,
            dispatch_gate=dispatch_gate_resolved,
            falsification_gate=falsification_gate_resolved,
            persistence=persistence_resolved,
            state_dir=Path("karma-main/state"),
        )
        self.goal_chain = GoalChainSubscriber(
            self.bus,
            project_root=Path.cwd(),
            dispatch_mode="seed",
        )
        self.limen = LIMENSubscriber(
            self.bus,
            mode="eventbus",
        )

        # Results accumulator (per-run)
        self._current_result: Optional[RuntimeResult] = None
        self._completion_event: Optional[asyncio.Event] = None
        self._session_counter: int = 0
        self._wired: bool = False

    # ── Wiring ───────────────────────────────────────────────────────

    def wire(self) -> None:
        """Wire all subscribers to the EventBus (idempotent).

        Subscriptions:
          - runtime.input          → _handle_input (Shinon → Promtguard → KARMA)
          - runtime.error          → _handle_error
          - runtime.completed      → _handle_completed
          - KARMA wired separately via KARMASubscriber.wire()
        """
        if self._wired:
            return

        # Core pipeline: input → shinon → promtguard → karma
        self.bus.subscribe(EVENT_RUNTIME_INPUT, self._handle_input)
        self.bus.subscribe(EVENT_SHINON_OUTPUT, self._handle_shinon_output)
        self.bus.subscribe(EVENT_PROMTGUARD_CLAIMS, self._handle_promtguard_claims)

        # Infrastructure
        self.bus.subscribe(EVENT_RUNTIME_ERROR, self._handle_error)
        self.bus.subscribe(EVENT_RUNTIME_COMPLETED, self._handle_completed)

        # KARMA subscriber
        self.karma.wire(self.bus)

        # Goal-Chain subscriber (listens to karma.falsified + limen.*)
        self.goal_chain.wire(self.bus)

        # LIMEN subscriber (publishes limen.* events)
        self.limen.wire(self.bus)

        self._wired = True
        logger.info("ControlPlaneRuntime wired (%d subscribers)", self.bus.stats["subscribers"])

    # ── Main Entry Point ─────────────────────────────────────────────

    async def process(
        self,
        user_text: str,
        session_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        conversation_id: Optional[str] = None,
    ) -> RuntimeResult:
        """Run the full event-driven pipeline for a single user input.

        Args:
            user_text: Raw user input text.
            session_id: Optional session identifier.
            history: Optional conversation history.
            conversation_id: Optional conversation thread ID.

        Returns:
            RuntimeResult with all outputs from the pipeline run.
        """
        if not self._wired:
            self.wire()

        if not session_id:
            self._session_counter += 1
            session_id = f"auto-sess-{self._session_counter:04d}"

        self._completion_event = asyncio.Event()

        # Create the result accumulator for this run
        result = RuntimeResult(input_text=user_text)
        self._current_result = result

        # Per-invocation result accumulator (avoids shared mutable state)
        captured_falsifications: List[FalsificationResult] = []
        captured_experiences: List[ExperienceRecord] = []
        captured_claims: List[Claim] = []
        captured_shinon_outputs: List[dict] = []

        # Subscribe to capture KARMA results during this run
        async def capture_falsified(event: Event) -> None:
            captured_falsifications.extend([
                FalsificationResult(**{k: v for k, v in r.items()
                    if k in ("claim_id", "result", "evidence", "confidence", "gate_version", "falsified_at")})
                for r in event.payload.get("results", [])
            ])

        async def capture_experience(event: Event) -> None:
            exp_data = event.payload.get("experience", {})
            if exp_data:
                captured_experiences.append(ExperienceRecord(**{k: v for k, v in exp_data.items()
                    if k in ("experience_id", "action", "outcome", "reward", "context_snapshot", "timestamp")}))

        async def capture_claims_data(event: Event) -> None:
            for c in event.payload.get("claims", []):
                captured_claims.append(Claim(
                    id=c.get("id", "?"), claim=c.get("claim", ""),
                    status=c.get("status", "unverified")
                ))

        async def capture_shinon_data(event: Event) -> None:
            captured_shinon_outputs.append(event.payload)

        # Temporary subscriptions for this run
        unsub_falsified = self.bus.subscribe(EVENT_KARMA_FALSIFIED, capture_falsified)
        unsub_experience = self.bus.subscribe(EVENT_KARMA_EXPERIENCE, capture_experience)
        unsub_claims = self.bus.subscribe(EVENT_PROMTGUARD_CLAIMS, capture_claims_data)
        unsub_shinon = self.bus.subscribe(EVENT_SHINON_OUTPUT, capture_shinon_data)

        try:
            # Publish the input event — this kicks off the entire chain
            await self.bus.publish(Event(
                event_type=EVENT_RUNTIME_INPUT,
                source="runtime",
                payload={
                    "user_text": user_text,
                    "session_id": session_id,
                    "conversation_id": conversation_id or "",
                    "history": history or [],
                },
                correlation_id=result.correlation_id,
            ))

            # Wait for the pipeline to complete
            # The runtime.completed event signals completion
            # (with a timeout for safety)
            try:
                await asyncio.wait_for(
                    self._completion_event.wait(),
                    timeout=self._timeout,
                )
            except asyncio.TimeoutError:
                result.error = f"Pipeline timed out after {self._timeout}s"
                logger.warning("Pipeline timed out (cid=%s)", result.correlation_id)

            # Populate result from captured data (per-invocation, not shared)
            result.claims = captured_claims or (self._current_result.claims if self._current_result else [])
            result.falsification_results = captured_falsifications
            result.experience_records = captured_experiences
            result.shinon_output = self._current_result.shinon_output if self._current_result else None
            result.completed_at = datetime.now(timezone.utc).isoformat()

        finally:
            # Clean up temporary subscriptions
            unsub_shinon()
            unsub_claims()
            unsub_falsified()
            unsub_experience()

        return result

    # ── Event Handlers (the pipeline chain) ──────────────────────────

    async def _handle_input(self, event: Event) -> None:
        """Step 1: Shinon processes user input → publishes shinon.output."""
        payload = event.payload

        try:
            shinon_input = ShinonInput(
                user_text=payload["user_text"],
                session_id=payload.get("session_id", ""),
                conversation_id=payload.get("conversation_id", ""),
                history=payload.get("history", []),
            )

            shinon_output = self.shinon.process(shinon_input)
        except Exception as exc:
            logger.exception("Shinon processing failed")
            await self.bus.publish(Event(
                event_type=EVENT_RUNTIME_ERROR,
                source="runtime",
                payload={"error": f"Shinon error: {exc}", "component": "shinon"},
                correlation_id=event.correlation_id,
            ))
            return

        if self._current_result:
            self._current_result.shinon_output = shinon_output

        await self.bus.publish(Event(
            event_type=EVENT_SHINON_OUTPUT,
            source="shinon",
            payload=shinon_output.to_dict(),
            correlation_id=event.correlation_id,
        ))

    async def _handle_shinon_output(self, event: Event) -> None:
        """Step 2: Promtguard extracts claims → publishes promtguard.claims."""
        payload = event.payload

        try:
            handoff = payload.get("handoff_to_promtguard", {})
            processed_input = handoff.get("processed_input", payload.get("reply", ""))

            claims = self.promtguard.extract_claims(processed_input, source="shinon_passthrough")
            self.promtguard.append_claims(claims)

            ctx_token = ContextToken(
                id=self.promtguard._next_ctx_id(),
                source="shinon_passthrough",
                summary=processed_input[:200],
                claims_extracted=len(claims),
            )
            self.promtguard.append_context_token(ctx_token)
        except Exception as exc:
            logger.exception("Promtguard processing failed")
            await self.bus.publish(Event(
                event_type=EVENT_RUNTIME_ERROR,
                source="runtime",
                payload={"error": f"Promtguard error: {exc}", "component": "promtguard"},
                correlation_id=event.correlation_id,
            ))
            return

        if self._current_result:
            self._current_result.claims = claims

        await self.bus.publish(Event(
            event_type=EVENT_PROMTGUARD_CLAIMS,
            source="promtguard",
            payload={
                "claims": [c.to_dict() for c in claims],
                "context_token_id": ctx_token.id,
                "claim_count": len(claims),
            },
            correlation_id=event.correlation_id,
        ))

        handoff_obj = Handoff(
            from_component="promtguard",
            to_component="karma",
            note=f"Claims extracted: {len(claims)}. Ready for falsification.",
        )
        self.promtguard.append_handoff(handoff_obj)

        await self.bus.publish(Event(
            event_type=EVENT_PROMTGUARD_HANDOFF,
            source="promtguard",
            payload=handoff_obj.to_dict(),
            correlation_id=event.correlation_id,
        ))

    async def _handle_promtguard_claims(self, event: Event) -> None:
        """Step 3: After KARMA processes claims (via its own subscriber),
        signal runtime completion."""
        # KARMA is wired independently and handles promtguard.claims
        # This handler runs AFTER KARMA finishes (sequential within asyncio)

        # Signal completion
        await self.bus.publish(Event(
            event_type=EVENT_RUNTIME_COMPLETED,
            source="runtime",
            payload={
                "status": "ok",
                "claim_count": event.payload.get("claim_count", 0),
            },
            correlation_id=event.correlation_id,
        ))

    async def _handle_completed(self, event: Event) -> None:
        """Handle runtime.completed — signal the waiting process() call."""
        logger.info("Runtime completed (cid=%s)", event.correlation_id)
        if self._completion_event:
            self._completion_event.set()

    async def _handle_error(self, event: Event) -> None:
        """Handle runtime.error — log and signal completion with error."""
        payload = event.payload
        error_msg = payload.get("error", "Unknown error")
        logger.error("Runtime error: %s (cid=%s)", error_msg, event.correlation_id)
        if self._current_result:
            self._current_result.error = error_msg
        if self._completion_event:
            self._completion_event.set()

    # ── Convenience ──────────────────────────────────────────────────

    def summary(self) -> str:
        """Return a summary of the runtime state."""
        return (
            f"ControlPlaneRuntime(wired={self._wired}, "
            f"sessions={self._session_counter}, "
            f"bus={self.bus.stats})"
        )


# ─── Quick Entry Point ────────────────────────────────────────────────


async def run_pipeline(
    user_text: str,
    identity: Optional[Dict[str, str]] = None,
) -> RuntimeResult:
    """Quick entry point: run one pipeline end-to-end."""
    rt = ControlPlaneRuntime(identity=identity)
    return await rt.process(user_text)
