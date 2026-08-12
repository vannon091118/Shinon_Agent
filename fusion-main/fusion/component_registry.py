"""
Component Registry — True decoupling for the Control Plane EventBus.

Replaces hard-wired component instantiation in ControlPlaneRuntime.__init__()
with a declarative registry. Components declare their factory, subscriptions,
and dependencies. The runtime creates and wires them without knowing their types.

This is the fix for Evil Twin Widerspruch #1:
  "Der EventBus simuliert Entkopplung, während die Runtime alles hart verdrahtet."

Architecture:
    ComponentRegistry
      ├── register(name, factory, subscriptions, dependencies)
      ├── wire_all(bus) → creates + subscribes all components
      ├── get(name) → returns created component
      └── list() → returns registered component names

    ResultAggregator (per-correlation_id)
      ├── track(stage_name, event)
      ├── is_complete() → True when all mandatory stages done
      └── build_result() → RuntimeResult

Usage:
    registry = ComponentRegistry()
    registry.register("shinon", lambda: ShinonEngine(...),
        subscriptions={"runtime.input": handle_input},
        publishes="shinon.output")
    
    rt = ControlPlaneRuntime(registry=registry)
    await rt.process("Build OAuth2 login")
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ─── Pipeline Stage ───────────────────────────────────────────────────


@dataclass
class PipelineStage:
    """Declarative pipeline stage definition.

    Each stage declares:
      - name: unique identifier (e.g. "shinon", "promtguard", "karma")
      - subscribes_to: event type this stage listens to
      - publishes: event type this stage emits on completion
      - mandatory: if True, pipeline fails when this stage errors
      - handler: async function (Event) → None
    """

    name: str
    subscribes_to: str
    publishes: str
    mandatory: bool = True
    handler: Optional[Callable] = None  # async (Event) → None

    def __hash__(self) -> int:
        return hash(self.name)


# ─── Component Registration ───────────────────────────────────────────


@dataclass
class ComponentRegistration:
    """A registered component in the registry.

    Components are created lazily — the factory is only called
    when wire_all() is invoked. Until then, only metadata exists.
    """

    name: str
    factory: Callable[[], Any]  # () → component instance
    subscriptions: Dict[str, str] = field(default_factory=dict)
    # subscriptions: {event_type: handler_method_name}
    dependencies: List[str] = field(default_factory=list)
    # components that must be wired before this one
    instance: Any = None  # Set by wire_all()


# ─── Component Registry ───────────────────────────────────────────────


class ComponentRegistry:
    """Registry of loosely-coupled components.

    Components declare WHAT they need (subscriptions, dependencies),
    not HOW they're created. The runtime creates them on wire_all()
    without knowing their types.

    This enables:
      - Swapping components without touching runtime code
      - Testing components in isolation
      - Adding new pipeline stages without modifying the orchestrator
    """

    def __init__(self):
        self._components: Dict[str, ComponentRegistration] = {}
        self._wired: bool = False

    def register(
        self,
        name: str,
        factory: Callable[[], Any],
        subscriptions: Optional[Dict[str, str]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> ComponentRegistry:
        """Register a component.

        Args:
            name: Unique component name (e.g. "shinon", "karma")
            factory: Zero-arg callable that creates the component instance
            subscriptions: {event_type: handler_method_name} mapping
            dependencies: Component names that must be wired before this one

        Returns:
            self (for chaining)

        Raises:
            ValueError: If name already registered
        """
        if name in self._components:
            raise ValueError(f"Component '{name}' already registered")

        self._components[name] = ComponentRegistration(
            name=name,
            factory=factory,
            subscriptions=subscriptions or {},
            dependencies=dependencies or [],
        )
        logger.debug("Registered component: %s (subs=%d, deps=%d)",
                     name, len(subscriptions or {}), len(dependencies or []))
        return self

    def wire_all(self, bus: Any) -> Dict[str, Any]:
        """Create all registered components and subscribe them to the EventBus.

        Components are created in dependency order. Each component's
        subscriptions are wired to the EventBus using getattr() to
        resolve handler method names.

        Args:
            bus: AsyncEventBus instance

        Returns:
            {name: component_instance} mapping

        Raises:
            ValueError: If circular dependency detected
        """
        if self._wired:
            return {name: reg.instance for name, reg in self._components.items()
                    if reg.instance is not None}

        # Topological sort by dependencies
        order = self._topological_sort()

        created: Dict[str, Any] = {}
        for name in order:
            reg = self._components[name]

            # Create the component
            instance = reg.factory()
            reg.instance = instance
            created[name] = instance

            # Wire subscriptions: {event_type: handler_method_name}
            for event_type, method_name in reg.subscriptions.items():
                handler = getattr(instance, method_name, None)
                if handler is None:
                    logger.warning(
                        "Component '%s': handler '%s' not found for event '%s'",
                        name, method_name, event_type,
                    )
                    continue

                # Subscribe to the EventBus
                bus.subscribe(event_type, handler)
                logger.debug("  %s subscribes to %s via %s()",
                            name, event_type, method_name)

            # Call wire() if the component has one
            wire_method = getattr(instance, "wire", None)
            if callable(wire_method):
                try:
                    wire_method(bus)
                except Exception as exc:
                    logger.warning("Component '%s'.wire() failed: %s", name, exc)

        self._wired = True
        logger.info("ComponentRegistry wired: %d components on bus (%d subscribers)",
                    len(created), bus.stats.get("subscribers", 0))
        return created

    def _topological_sort(self) -> List[str]:
        """Sort components by dependency order (Kahn's algorithm).

        Returns:
            List of component names in dependency order.

        Raises:
            ValueError: If circular dependency detected
        """
        # Build adjacency and in-degree
        in_degree: Dict[str, int] = {name: 0 for name in self._components}
        adj: Dict[str, List[str]] = {name: [] for name in self._components}

        for name, reg in self._components.items():
            for dep in reg.dependencies:
                if dep not in self._components:
                    raise ValueError(
                        f"Component '{name}' depends on unknown '{dep}'"
                    )
                adj[dep].append(name)
                in_degree[name] += 1

        # Kahn's algorithm
        queue = [name for name, deg in in_degree.items() if deg == 0]
        order: List[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(self._components):
            remaining = set(self._components) - set(order)
            raise ValueError(f"Circular dependency detected: {remaining}")

        return order

    def get(self, name: str) -> Optional[Any]:
        """Get a wired component instance by name."""
        reg = self._components.get(name)
        return reg.instance if reg else None

    def list(self) -> List[str]:
        """List all registered component names."""
        return list(self._components.keys())

    @property
    def wired(self) -> bool:
        return self._wired


# ─── Result Aggregator ────────────────────────────────────────────────


@dataclass
class StageResult:
    """Result from one pipeline stage."""
    stage: str
    status: str = "pending"  # pending | running | ok | error
    event: Optional[Any] = None  # The event that completed this stage
    error: Optional[str] = None
    started_at: str = ""
    completed_at: str = ""

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc).isoformat()


class ResultAggregator:
    """Collects pipeline stage results by correlation_id.

    Each stage (shinon, promtguard, karma) is tracked independently.
    When all mandatory stages complete (or any mandatory stage fails),
    the aggregator signals completion.

    This replaces the linear _handle_input → _handle_shinon_output →
    _handle_promtguard_claims chain with independent stage tracking.
    """

    def __init__(
        self,
        correlation_id: str,
        stages: List[PipelineStage],
        timeout: float = 30.0,
    ):
        self.correlation_id = correlation_id
        self._stages: Dict[str, StageResult] = {
            s.name: StageResult(stage=s.name)
            for s in stages
        }
        self._mandatory_stages = {s.name for s in stages if s.mandatory}
        self._completion = asyncio.Event()
        self._timeout = timeout
        self._collected_events: List[Any] = []

    def track(self, event_type: str, event: Any) -> None:
        """Track a pipeline event.

        Maps event types to stage names:
          - shinon.output → stage "shinon" complete
          - promtguard.claims → stage "promtguard" complete
          - karma.falsified → stage "karma" complete
          - runtime.error → marks the relevant stage as error
        """
        self._collected_events.append(event)

        stage_name = self._event_to_stage(event_type)
        if stage_name and stage_name in self._stages:
            stage = self._stages[stage_name]

            if event_type.startswith("runtime.error"):
                stage.status = "error"
                stage.error = event.payload.get("error", "Unknown error")
                stage.completed_at = datetime.now(timezone.utc).isoformat()
            else:
                stage.status = "ok"
                stage.event = event
                stage.completed_at = datetime.now(timezone.utc).isoformat()

        # Check if all mandatory stages are complete
        if self.is_complete():
            self._completion.set()

    def _event_to_stage(self, event_type: str) -> Optional[str]:
        """Map event type to stage name."""
        mapping = {
            "shinon.output": "shinon",
            "promtguard.claims": "promtguard",
            "promtguard.handoff": "promtguard",
            "karma.falsified": "karma",
            "karma.experience": "karma",
            "runtime.completed": "runtime",
        }
        # Error events carry the component name in payload
        if event_type == "runtime.error":
            return None  # handled separately
        return mapping.get(event_type)

    def mark_error(self, component: str, error: str) -> None:
        """Mark a stage as errored."""
        if component in self._stages:
            stage = self._stages[component]
            stage.status = "error"
            stage.error = error
            stage.completed_at = datetime.now(timezone.utc).isoformat()
            if self.is_complete():
                self._completion.set()

    def is_complete(self) -> bool:
        """Check if all mandatory stages are done (ok or error)."""
        for name in self._mandatory_stages:
            stage = self._stages.get(name)
            if not stage or stage.status == "pending":
                return False
        return True

    def has_errors(self) -> bool:
        """Check if any mandatory stage has errored."""
        for name in self._mandatory_stages:
            stage = self._stages.get(name)
            if stage and stage.status == "error":
                return True
        return False

    async def wait(self) -> None:
        """Wait for all mandatory stages to complete (or timeout)."""
        try:
            await asyncio.wait_for(
                self._completion.wait(),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("ResultAggregator timed out after %.1fs (cid=%s)",
                          self._timeout, self.correlation_id)

    def summary(self) -> str:
        """Return a human-readable summary of stage results."""
        lines = [f"ResultAggregator(cid={self.correlation_id})"]
        for name, stage in self._stages.items():
            mandatory = "●" if name in self._mandatory_stages else "○"
            status_icon = {"ok": "✅", "error": "❌", "pending": "⏳", "running": "🔄"}
            icon = status_icon.get(stage.status, "?")
            lines.append(f"  {mandatory} {icon} {name}: {stage.status}")
            if stage.error:
                lines.append(f"       error: {stage.error}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Return stage results as a dict."""
        return {
            "correlation_id": self.correlation_id,
            "stages": {
                name: {
                    "status": stage.status,
                    "error": stage.error,
                    "completed_at": stage.completed_at,
                }
                for name, stage in self._stages.items()
            },
            "complete": self.is_complete(),
            "has_errors": self.has_errors(),
            "events_collected": len(self._collected_events),
        }

    @property
    def collected_events(self) -> List[Any]:
        return self._collected_events


# ─── Default Pipeline ─────────────────────────────────────────────────


def default_pipeline_stages() -> List[PipelineStage]:
    """Return the default Control Plane pipeline stages.

    Order is declarative — the EventBus handles actual routing.
    """
    return [
        PipelineStage(
            name="shinon",
            subscribes_to="runtime.input",
            publishes="shinon.output",
            mandatory=True,
        ),
        PipelineStage(
            name="promtguard",
            subscribes_to="shinon.output",
            publishes="promtguard.claims",
            mandatory=True,
        ),
        PipelineStage(
            name="karma",
            subscribes_to="promtguard.claims",
            publishes="karma.falsified",
            mandatory=True,
        ),
        PipelineStage(
            name="runtime",
            subscribes_to="karma.falsified",
            publishes="runtime.completed",
            mandatory=False,
        ),
    ]
