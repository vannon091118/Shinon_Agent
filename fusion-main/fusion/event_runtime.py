"""
Event Runtime — Truly Decoupled Event-Driven Pipeline Orchestrator

v2.0: ComponentRegistry replaces hard-wired instantiation.
      ResultAggregator replaces linear completion-event chain.

Fix for Evil Twin Widerspruch #1:
  "Der EventBus simuliert Entkopplung, während die Runtime alles hart verdrahtet."

Before:
  ControlPlaneRuntime.__init__()
    → shinon = ShinonEngine(...)        # hard-wired
    → promtguard = PromtguardClaims(...) # hard-wired
    → karma = KARMASubscriber(...)      # hard-wired
  process() → publish → await completion_event  # linear chain

After:
  Registry.register("shinon", factory, subscriptions)
  Registry.register("karma", factory, subscriptions, deps=["shinon"])
  Runtime.wire() → Registry.wire_all(bus)  # creates + subscribes
  process() → publish → ResultAggregator tracks per-correlation_id

Components can be swapped by replacing registry entries.
New pipeline stages can be added without touching Runtime code.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

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
)
from fusion.component_registry import (
    ComponentRegistry,
    ResultAggregator,
    PipelineStage,
    default_pipeline_stages,
)

logger = logging.getLogger(__name__)


# ─── Runtime Result ───────────────────────────────────────────────────


@dataclass
class RuntimeResult:
    """Complete result of one event-driven pipeline run."""

    correlation_id: str = ""
    input_text: str = ""
    original_input: str = ""  # Before preprocessing (if any)
    shinon_output: Optional[Any] = None
    claims: List[Any] = field(default_factory=list)
    falsification_results: List[Any] = field(default_factory=list)
    experience_records: List[Any] = field(default_factory=list)
    aggregator_summary: Optional[Dict[str, Any]] = None
    preprocess_info: Optional[Dict[str, Any]] = None
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
            f"  input: {self.input_text[:80]}{'...' if len(self.input_text) > 80 else ''}",
            f"  shinon: {'OK' if self.shinon_output else 'N/A'}",
            f"  claims: {len(self.claims)} extracted",
        ]
        if self.falsification_results:
            falsified = sum(
                1 for r in self.falsification_results
                if getattr(r, 'result', None) not in (None, 'unverified')
            )
            lines.append(f"  falsified: {falsified}/{len(self.falsification_results)}")
        if self.error:
            lines.append(f"  ERROR: {self.error}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "correlation_id": self.correlation_id,
            "input_text": self.input_text[:200],
            "claims_count": len(self.claims),
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
        if self.shinon_output:
            if hasattr(self.shinon_output, 'to_dict'):
                d["shinon_output"] = self.shinon_output.to_dict()
            elif isinstance(self.shinon_output, dict):
                d["shinon_output"] = self.shinon_output
        if self.falsification_results:
            d["falsification_results"] = [
                r.to_dict() if hasattr(r, 'to_dict') else r
                for r in self.falsification_results
            ]
        if self.experience_records:
            d["experience_records"] = [
                r.to_dict() if hasattr(r, 'to_dict') else r
                for r in self.experience_records
            ]
        if self.aggregator_summary:
            d["aggregator"] = self.aggregator_summary
        return d


# ─── Standalone Pipeline Handlers (not class methods!) ───────────────
# These are the truly decoupled pipeline stages. Each handler:
#   - Receives an Event
#   - Processes it (calls a component)
#   - Publishes the result event
#   - Tracks completion in the ResultAggregator
#
# No handler knows about other handlers. The EventBus routes everything.


async def _handle_input(
    event: Event,
    shinon: Any,
    bus: AsyncEventBus,
    aggregator: Optional[ResultAggregator] = None,
) -> None:
    """Step 1: Shinon processes user input → publishes shinon.output."""
    payload = event.payload

    try:
        from fusion.shinon import ShinonInput
        shinon_input = ShinonInput(
            user_text=payload["user_text"],
            session_id=payload.get("session_id", ""),
            conversation_id=payload.get("conversation_id", ""),
            history=payload.get("history", []),
        )
        output = shinon.process(shinon_input)
    except Exception as exc:
        logger.exception("Shinon processing failed")
        if aggregator:
            aggregator.mark_error("shinon", str(exc))
        await bus.publish(Event(
            event_type=EVENT_RUNTIME_ERROR,
            source="runtime",
            payload={"error": f"Shinon: {exc}", "component": "shinon"},
            correlation_id=event.correlation_id,
        ))
        return

    if aggregator:
        aggregator.track(EVENT_SHINON_OUTPUT,
                         Event(event_type=EVENT_SHINON_OUTPUT, source="shinon",
                               payload=output.to_dict() if hasattr(output, 'to_dict') else output,
                               correlation_id=event.correlation_id))

    await bus.publish(Event(
        event_type=EVENT_SHINON_OUTPUT,
        source="shinon",
        payload=output.to_dict() if hasattr(output, 'to_dict') else output,
        correlation_id=event.correlation_id,
    ))


async def _handle_shinon_output(
    event: Event,
    promtguard: Any,
    bus: AsyncEventBus,
    aggregator: Optional[ResultAggregator] = None,
) -> None:
    """Step 2: Promtguard extracts claims → publishes promtguard.claims."""
    payload = event.payload

    try:
        handoff = payload.get("handoff_to_promtguard", {})
        processed_input = handoff.get("processed_input", payload.get("reply", ""))
        claims = promtguard.extract_claims(processed_input, source="shinon")
        promtguard.append_claims(claims)

        from fusion.promtguard_claims import ContextToken
        ctx_token = ContextToken(
            id=promtguard._next_ctx_id(),
            source="shinon",
            summary=processed_input[:200],
            claims_extracted=len(claims),
        )
        promtguard.append_context_token(ctx_token)
    except Exception as exc:
        logger.exception("Promtguard processing failed")
        if aggregator:
            aggregator.mark_error("promtguard", str(exc))
        await bus.publish(Event(
            event_type=EVENT_RUNTIME_ERROR,
            source="runtime",
            payload={"error": f"Promtguard: {exc}", "component": "promtguard"},
            correlation_id=event.correlation_id,
        ))
        return

    claims_dicts = [c.to_dict() if hasattr(c, 'to_dict') else c for c in claims]

    if aggregator:
        aggregator.track(EVENT_PROMTGUARD_CLAIMS,
                         Event(event_type=EVENT_PROMTGUARD_CLAIMS, source="promtguard",
                               payload={"claims": claims_dicts, "claim_count": len(claims)},
                               correlation_id=event.correlation_id))

    await bus.publish(Event(
        event_type=EVENT_PROMTGUARD_CLAIMS,
        source="promtguard",
        payload={
            "claims": claims_dicts,
            "context_token_id": ctx_token.id,
            "claim_count": len(claims),
        },
        correlation_id=event.correlation_id,
    ))

    from fusion.promtguard_claims import Handoff
    handoff_obj = Handoff(
        from_component="promtguard",
        to_component="karma",
        note=f"Claims: {len(claims)}. Ready for falsification.",
    )
    promtguard.append_handoff(handoff_obj)

    await bus.publish(Event(
        event_type=EVENT_PROMTGUARD_HANDOFF,
        source="promtguard",
        payload=handoff_obj.to_dict(),
        correlation_id=event.correlation_id,
    ))


async def _handle_promtguard_claims(
    event: Event,
    bus: AsyncEventBus,
    aggregator: Optional[ResultAggregator] = None,
) -> None:
    """Step 3: After KARMA processes claims, signal completion."""
    if aggregator:
        aggregator.track(EVENT_RUNTIME_COMPLETED,
                         Event(event_type=EVENT_RUNTIME_COMPLETED, source="runtime",
                               payload={"status": "ok"},
                               correlation_id=event.correlation_id))

    await bus.publish(Event(
        event_type=EVENT_RUNTIME_COMPLETED,
        source="runtime",
        payload={
            "status": "ok",
            "claim_count": event.payload.get("claim_count", 0),
        },
        correlation_id=event.correlation_id,
    ))


# ─── Control Plane Runtime (v2 — truly decoupled) ────────────────────


class ControlPlaneRuntime:
    """Truly decoupled Control Plane Runtime.

    Components are registered in a ComponentRegistry — not hard-wired
    in the constructor. The registry creates and subscribes them during
    wire(). New pipeline stages can be added by registering additional
    components without touching the Runtime class.

    Usage:
        # Default pipeline (shinon + promtguard + karma + goal-chain + limen)
        rt = ControlPlaneRuntime()
        result = await rt.process("Build OAuth2 login")

        # Custom pipeline
        registry = ComponentRegistry()
        registry.register("shinon", lambda: MyCustomShinon(), ...)
        rt = ControlPlaneRuntime(registry=registry)
    """

    def __init__(
        self,
        bus: Optional[AsyncEventBus] = None,
        registry: Optional[ComponentRegistry] = None,
        state_dir: Optional[Path] = None,
        timeout: float = 30.0,
        *,
        goal_chain_dispatch_mode: str = "seed",
        # Backward compat: accept individual components for testing
        shinon: Optional[Any] = None,
        promtguard: Optional[Any] = None,
        karma: Optional[Any] = None,
        goal_chain: Optional[Any] = None,
        limen: Optional[Any] = None,
        # Pre-processor: auto-structure imprecise prompts
        preprocessor: Optional[Any] = None,
        preprocess_mode: str = "auto",  # "auto" | "force" | "synthetic" | "off"
    ):
        self.bus = bus or get_event_bus()
        self._state_dir = Path(state_dir) if state_dir else Path(".promtset/state")
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._timeout = timeout
        self._goal_chain_dispatch_mode = goal_chain_dispatch_mode
        self._preprocess_mode = preprocess_mode
        self._preprocessor = preprocessor

        # If a registry is provided, use it. Otherwise build a default one.
        if registry is not None:
            self.registry = registry
        else:
            self.registry = self._build_default_registry(
                shinon=shinon, promtguard=promtguard, karma=karma,
                goal_chain=goal_chain, limen=limen,
            )

        self._wired = False
        self._session_counter = 0

        # Per-run state (set during process())
        self._current_aggregator: Optional[ResultAggregator] = None

    def set_goal_chain_dispatch_mode(self, mode: str) -> None:
        """Set goal-chain dispatch mode before wire().

        Must be called BEFORE wire() or process() to take effect.
        This is the fix for the "_dispatch_mode race" bug: the registry
        factory creates a fresh GoalChainSubscriber, so setting
        _dispatch_mode on a pre-wired instance has no effect.

        Args:
            mode: "seed" (default, spawns subprocess) or "event" (test mode)
        """
        if self._wired:
            logger.warning(
                "set_goal_chain_dispatch_mode(%s) called after wire() — "
                "too late, factory already created the instance", mode
            )
        self._goal_chain_dispatch_mode = mode

    def _build_default_registry(
        self,
        shinon: Optional[Any] = None,
        promtguard: Optional[Any] = None,
        karma: Optional[Any] = None,
        goal_chain: Optional[Any] = None,
        limen: Optional[Any] = None,
    ) -> ComponentRegistry:
        """Build the default component registry.

        Components are registered with factories and subscriptions.
        The registry doesn't know about component types — just factories
        and event wiring.
        """
        registry = ComponentRegistry()

        # ── Shinon: Character Layer ──
        def _create_shinon():
            if shinon is not None:
                return shinon
            try:
                from fusion.shinon import ShinonEngine
                return ShinonEngine(
                    memory_db=Path("fusion-main/data/shinon_memory.db"),
                    attitude_db=Path("fusion-main/data/shinon_attitudes.db"),
                )
            except Exception:
                from fusion.shinon_passthrough import ShinonPassthrough
                return ShinonPassthrough()

        registry.register(
            "shinon",
            factory=_create_shinon,
            subscriptions={},  # Handled via closure in _handle_input
        )

        # ── Promtguard: Claim Extraction ──
        def _create_promtguard():
            if promtguard is not None:
                return promtguard
            from fusion.promtguard_claims import PromtguardClaims
            return PromtguardClaims(state_dir=self._state_dir)

        registry.register(
            "promtguard",
            factory=_create_promtguard,
            subscriptions={},
        )

        # ── KARMA: Falsification + Dispatch ──
        def _create_karma():
            if karma is not None:
                return karma
            dispatch_gate = None
            falsification_gate = None
            persistence = None

            try:
                from karma.core.persistence import create_project_persistence
                from karma.core.dispatch import DispatchGate
                from karma.core.falsification_gate import FalsificationGate

                persistence = create_project_persistence("PZ")
                dispatch_gate = DispatchGate(persistence)
                falsification_gate = FalsificationGate(persistence, "PZ")
                logger.info("KARMA gates wired: DispatchGate + FalsificationGate (6 probes)")
            except ImportError:
                logger.info("karma-main not available — KARMA heuristic fallback")
            except Exception as exc:
                logger.warning("KARMA gate init failed — heuristic fallback: %s", exc)

            from fusion.karma_subscriber import KARMASubscriber
            return KARMASubscriber(
                self.bus,
                dispatch_gate=dispatch_gate,
                falsification_gate=falsification_gate,
                persistence=persistence,
                state_dir=Path("karma-main/state"),
            )

        # NOTE: No subscriptions dict — KARMASubscriber.wire() handles
        # its own EventBus subscriptions. Adding them here would cause
        # wire_all() to subscribe them TWICE (once via this dict, once
        # via component.wire()), producing duplicate event handlers.
        registry.register(
            "karma",
            factory=_create_karma,
            subscriptions={},
            dependencies=["promtguard"],
        )

        # ── Goal-Chain: Skill Trigger ──
        def _create_goal_chain():
            if goal_chain is not None:
                return goal_chain
            from fusion.goal_chain_subscriber import GoalChainSubscriber
            return GoalChainSubscriber(
                self.bus,
                project_root=Path.cwd(),
                dispatch_mode=self._goal_chain_dispatch_mode,
            )

        # NOTE: No subscriptions dict — GoalChainSubscriber.wire() handles
        # its own EventBus subscriptions. Same reason as KARMA above.
        registry.register(
            "goal_chain",
            factory=_create_goal_chain,
            subscriptions={},
            dependencies=["karma"],
        )

        # ── LIMEN: Key Pool + Rate Limiting ──
        def _create_limen():
            if limen is not None:
                return limen
            from fusion.limen_subscriber import LIMENSubscriber
            return LIMENSubscriber(self.bus, mode="eventbus")

        registry.register(
            "limen",
            factory=_create_limen,
            subscriptions={},
            dependencies=["karma"],
        )

        return registry

    def _attach_live_logger(self) -> None:
        """Attach EventBusLiveLogger to self.bus if not already attached.

        Ensures EVERY process() call automatically writes events to
        /tmp/eventbus-live-log.jsonl without manual bridge startup.

        Uses per-bus tracking (EventBusLiveLogger.is_bus_attached()) so
        custom bus instances also get logging, not just the global singleton.
        """
        try:
            from fusion.event_bus import EventBusLiveLogger

            # Check if THIS specific bus already has a logger (not just the global one)
            if EventBusLiveLogger.is_bus_attached(self.bus):
                logger.debug("LiveLogger already attached to bus %s", id(self.bus))
                return

            # Create and attach to THIS bus
            live_logger = EventBusLiveLogger()
            live_logger.attach(self.bus)
            logger.info("LiveLogger attached to bus %s → %s", id(self.bus), live_logger.log_path)
        except Exception as exc:
            logger.warning("Failed to attach LiveLogger: %s", exc)

    # ── Wiring ───────────────────────────────────────────────────────

    def wire(self) -> None:
        """Wire all components via the ComponentRegistry.

        Delegates to registry.wire_all(bus) which:
          1. Creates components in dependency order
          2. Subscribes declared handlers to the EventBus
          3. Calls each component's wire() method if present

        Also wires the core pipeline chain:
          runtime.input → shinon → promtguard → karma

        Also attaches the EventBusLiveLogger (if not already attached):
          ALL events → /tmp/eventbus-live-log.jsonl
        """
        if self._wired:
            return

        # ── Attach live logger (auto, no manual bridge needed) ──
        self._attach_live_logger()

        # Create and wire all registered components
        self.registry.wire_all(self.bus)

        # Wire the core pipeline chain using standalone handlers.
        # These handlers use closure to access component instances
        # from the registry — not hard-wired references.
        shinon = self.registry.get("shinon")
        promtguard = self.registry.get("promtguard")

        if shinon:
            async def handle_input(event: Event) -> None:
                await _handle_input(
                    event, shinon, self.bus, self._current_aggregator
                )
            self.bus.subscribe(EVENT_RUNTIME_INPUT, handle_input)

        if promtguard:
            async def handle_shinon(event: Event) -> None:
                await _handle_shinon_output(
                    event, promtguard, self.bus, self._current_aggregator
                )
            self.bus.subscribe(EVENT_SHINON_OUTPUT, handle_shinon)

        async def handle_claims_complete(event: Event) -> None:
            await _handle_promtguard_claims(
                event, self.bus, self._current_aggregator
            )
        self.bus.subscribe(EVENT_PROMTGUARD_CLAIMS, handle_claims_complete)

        # Track karma.falsified in the aggregator (KARMA subscriber fires this)
        async def handle_karma_falsified(event: Event) -> None:
            if self._current_aggregator:
                self._current_aggregator.track(EVENT_KARMA_FALSIFIED, event)
        self.bus.subscribe(EVENT_KARMA_FALSIFIED, handle_karma_falsified)

        # Track karma.experience too
        async def handle_karma_experience(event: Event) -> None:
            if self._current_aggregator:
                self._current_aggregator.track(EVENT_KARMA_EXPERIENCE, event)
        self.bus.subscribe(EVENT_KARMA_EXPERIENCE, handle_karma_experience)

        self._wired = True
        logger.info("ControlPlaneRuntime v2 wired: %d components on bus",
                    len(self.registry.list()))

    # ── Main Entry Point ─────────────────────────────────────────────

    async def process(
        self,
        user_text: str,
        session_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        conversation_id: Optional[str] = None,
    ) -> RuntimeResult:
        """Run the full event-driven pipeline for a single user input.

        Uses ResultAggregator instead of linear completion-event chain:
          - Each pipeline stage completes independently
          - Aggregator tracks stage completions by correlation_id
          - Returns when all mandatory stages complete (or timeout)

        When preprocessor is configured (preprocess_mode != "off"),
        imprecise/long-winded prompts are first structured via LLM or
        synthetic heuristics before entering the pipeline.
        """
        if not self._wired:
            self.wire()

        if not session_id:
            self._session_counter += 1
            session_id = f"auto-sess-{self._session_counter:04d}"

        # ── Pre-process: structure imprecise/vague prompts ──
        original_text = user_text
        preprocess_info: Optional[Dict[str, Any]] = None
        _structured_input = None  # Keep reference for evidence injection

        if self._preprocess_mode != "off":
            preprocessor = self._get_or_create_preprocessor()
            if preprocessor is not None:
                try:
                    structured = await preprocessor.structure(user_text)
                    _structured_input = structured
                    if structured.preprocessed:
                        user_text = structured.to_text()
                        preprocess_info = {
                            "original": original_text[:200],
                            "structured": True,
                            "mode": structured.mode,
                            "goal": structured.goal,
                            "requirements_count": len(structured.requirements),
                            "tests_count": len(structured.tests),
                        }
                        logger.info(
                            "PreProcessor: %s mode → %d requirements, %d tests",
                            structured.mode,
                            len(structured.requirements),
                            len(structured.tests),
                        )
                except Exception as exc:
                    logger.warning("PreProcessor failed — using original input: %s", exc)
                    user_text = original_text  # Fallback to original

        # ── Inject preprocess evidence into KARMA ──
        if _structured_input is not None:
            karma = self.registry.get("karma")
            if karma is not None and hasattr(karma, 'set_preprocess_evidence'):
                karma.set_preprocess_evidence(_structured_input)

        # Create result + aggregator for this run
        result = RuntimeResult(
            input_text=user_text,
            original_input=original_text,
            preprocess_info=preprocess_info,
        )
        stages = default_pipeline_stages()
        self._current_aggregator = ResultAggregator(
            correlation_id=result.correlation_id,
            stages=stages,
            timeout=self._timeout,
        )

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

        # Wait for all mandatory stages to complete
        await self._current_aggregator.wait()

        # Populate result from aggregator
        result.completed_at = datetime.now(timezone.utc).isoformat()
        result.aggregator_summary = self._current_aggregator.to_dict()

        if self._current_aggregator.has_errors():
            for name, stage in self._current_aggregator.to_dict()["stages"].items():
                if stage.get("status") == "error":
                    result.error = stage.get("error", f"Stage '{name}' failed")
                    break

        # Extract collected data from aggregator events
        for evt in self._current_aggregator.collected_events:
            etype = getattr(evt, 'event_type', '')
            if etype == EVENT_SHINON_OUTPUT:
                payload = getattr(evt, 'payload', {})
                result.shinon_output = payload
            elif etype == EVENT_PROMTGUARD_CLAIMS:
                payload = getattr(evt, 'payload', {})
                from fusion.promtguard_claims import Claim
                result.claims = [
                    Claim(
                        id=c.get("id", "?"),
                        claim=c.get("claim", ""),
                        status=c.get("status", "unverified"),
                    )
                    for c in payload.get("claims", [])
                ]
            elif etype == EVENT_KARMA_FALSIFIED:
                payload = getattr(evt, 'payload', {})
                from fusion.karma_subscriber import FalsificationResult
                result.falsification_results = [
                    FalsificationResult(**{k: v for k, v in r.items()
                        if k in ("claim_id", "result", "evidence", "confidence",
                                 "gate_version", "falsified_at")})
                    for r in payload.get("results", [])
                ]
            elif etype == EVENT_KARMA_EXPERIENCE:
                payload = getattr(evt, 'payload', {})
                exp_data = payload.get("experience", {})
                if exp_data:
                    from fusion.karma_subscriber import ExperienceRecord
                    result.experience_records.append(
                        ExperienceRecord(**{k: v for k, v in exp_data.items()
                            if k in ("experience_id", "action", "outcome", "reward",
                                     "context_snapshot", "timestamp")})
                    )

        return result

    # ── Convenience ──────────────────────────────────────────────────

    def _get_or_create_preprocessor(self):
        """Get or lazily create the LLMPreProcessor.

        Creates from LIMEN DB if no preprocessor was explicitly passed.
        In synthetic mode, creates without KeyPool (keyword-based only).
        """
        if self._preprocessor is not None:
            return self._preprocessor

        if self._preprocess_mode == "synthetic":
            from fusion.llm_preprocessor import LLMPreProcessor
            self._preprocessor = LLMPreProcessor(mode="synthetic")
            return self._preprocessor

        # Try creating from LIMEN DB
        try:
            from fusion.llm_preprocessor import create_preprocessor_from_limen
            self._preprocessor = create_preprocessor_from_limen(
                mode=self._preprocess_mode
            )
        except Exception as exc:
            logger.warning("Could not create LLMPreProcessor from LIMEN: %s", exc)
            # Fallback to synthetic
            from fusion.llm_preprocessor import LLMPreProcessor
            self._preprocessor = LLMPreProcessor(mode="synthetic")

        return self._preprocessor

    def get_preprocessor_stats(self) -> Optional[Dict[str, Any]]:
        """Return preprocessor stats if configured."""
        if self._preprocessor is not None:
            return self._preprocessor.stats
        return None

    def summary(self) -> str:
        return (
            f"ControlPlaneRuntime v2(wired={self._wired}, "
            f"sessions={self._session_counter}, "
            f"components={self.registry.list()}, "
            f"bus={self.bus.stats})"
        )


# ─── Quick Entry Point ────────────────────────────────────────────────


async def run_pipeline(user_text: str) -> RuntimeResult:
    """Quick entry point: run one pipeline end-to-end."""
    rt = ControlPlaneRuntime()
    return await rt.process(user_text)
