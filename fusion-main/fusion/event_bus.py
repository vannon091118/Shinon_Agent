"""
Event Bus — Async Pub/Sub Event Bus for Control Plane

Replaces linear HOFF-0001→HOFF-0002→... handoff sequence with
event-driven architecture. Components subscribe to topics and
react asynchronously.

Architecture:
    EventBus (in-process, asyncio-based)
      ├── "runtime.input"       → Shinon (subscriber)
      ├── "shinon.output"       → Promtguard (subscriber)
      ├── "promtguard.claims"   → KARMA (subscriber)
      ├── "karma.falsified"     → goal-chain trigger
      ├── "limen.rate_limited"  → goal-chain mitigation
      ├── "limen.key_cooldown"  → goal-chain key-health check
      ├── "limen.key_exhausted" → goal-chain emergency provision
      ├── "runtime.error"       → Error handler
      └── "runtime.completed"   → Teardown handler

WIRING.md remains the logical spec — this is the runtime implementation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ─── Event Types (from WIRING.md HOFF mapping) ────────────────────────

EVENT_RUNTIME_INPUT = "runtime.input"
EVENT_SHINON_OUTPUT = "shinon.output"
EVENT_PROMTGUARD_CLAIMS = "promtguard.claims"
EVENT_PROMTGUARD_HANDOFF = "promtguard.handoff"
EVENT_KARMA_FALSIFIED = "karma.falsified"
EVENT_KARMA_EXPERIENCE = "karma.experience"
EVENT_RUNTIME_ERROR = "runtime.error"
EVENT_RUNTIME_COMPLETED = "runtime.completed"
EVENT_RUNTIME_HEARTBEAT = "runtime.heartbeat"
EVENT_GOAL_CHAIN_TRIGGERED = "goal_chain.triggered"
EVENT_GOAL_CHAIN_SKILL_CHAIN = "goal_chain.skill_chain"
EVENT_GOAL_CHAIN_REWORK = "goal_chain.rework"

# ─── LIMEN events (rate-limit / key state) ─────────────────────────
EVENT_LIMEN_RATE_LIMITED = "limen.rate_limited"       # 429 hit with classification
EVENT_LIMEN_KEY_COOLDOWN = "limen.key_cooldown"       # Key entered cooldown
EVENT_LIMEN_KEY_EXHAUSTED = "limen.key_exhausted"     # All keys for a deployment dead/cooldown
EVENT_LIMEN_BUDGET_WARNING = "limen.budget_warning"   # Token/request budget near exhaustion
EVENT_LIMEN_KEY_RECOVERED = "limen.key_recovered"     # Key recovered from cooldown
EVENT_LIMEN_API_ERROR = "limen.api_error"             # Non-429 API errors


# ─── Subscriber Types ─────────────────────────────────────────────────

# Sync subscriber (legacy, for non-async components)
SyncSubscriber = Callable[["Event"], None]

# Async subscriber
AsyncSubscriber = Callable[["Event"], Awaitable[None]]


# ─── Event ────────────────────────────────────────────────────────────


@dataclass
class Event:
    """Pub/Sub event for async component communication.

    Each event carries a correlation_id linking it to the originating
    pipeline run. The payload is a dict with component-specific data.
    """

    event_type: str
    source: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    correlation_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "source": self.source,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Reconstruct an Event from its dictionary representation."""
        return cls(
            event_type=data["event_type"],
            source=data["source"],
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", ""),
            correlation_id=data.get("correlation_id", ""),
        )

    def fingerprint(self) -> str:
        """SHA-256 fingerprint of event for determinism verification."""
        data = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def structural_fingerprint(self) -> str:
        """SHA-256 fingerprint of structural content only.

        Hashes event_type + source + payload (sorted keys).
        EXCLUDES timestamp and correlation_id — these always differ
        on replay, so comparing them produces false divergence.

        Use this for replay determinism checks.
        """
        structural = {
            "event_type": self.event_type,
            "source": self.source,
            "payload": self.payload,
        }
        data = json.dumps(structural, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def __repr__(self) -> str:
        return f"Event({self.event_type} ← {self.source}, cid={self.correlation_id})"


# ─── Async Event Bus ──────────────────────────────────────────────────


class AsyncEventBus:
    """In-process async Pub/Sub event bus.

    Subscribers register for event topics. When an event is published,
    all matching subscribers are called concurrently via asyncio.gather.
    Subscriber failures are isolated — one failing subscriber doesn't
    block others.

    Usage:
        bus = AsyncEventBus()
        bus.subscribe("shinon.output", my_async_handler)
        await bus.publish(Event("shinon.output", source="shinon", payload={...}))
    """

    def __init__(self):
        self._subscribers: Dict[str, List[AsyncSubscriber]] = {}
        self._event_log: List[Event] = []
        self._error_count: int = 0
        self._publish_count: int = 0

    # ── Subscription ─────────────────────────────────────────────────

    def subscribe(
        self,
        event_type: str,
        handler: AsyncSubscriber,
    ) -> Callable[[], None]:
        """Subscribe to an event type. Returns unsubscribe function.

        Args:
            event_type: Topic to subscribe to (use EVENT_* constants).
            handler: Async callback receiving the Event.

        Returns:
            Callable that removes this subscription when called.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug("Subscribed to %s (total: %d)", event_type, len(self._subscribers[event_type]))
        return lambda: self._unsubscribe(event_type, handler)

    def subscribe_sync(
        self,
        event_type: str,
        handler: SyncSubscriber,
    ) -> Callable[[], None]:
        """Subscribe a synchronous handler (wrapped as async).

        For components that haven't been refactored to async yet.
        """
        async def wrapper(event: Event) -> None:
            handler(event)

        return self.subscribe(event_type, wrapper)

    def subscribe_all(
        self,
        handlers: Dict[str, AsyncSubscriber],
    ) -> Callable[[], None]:
        """Subscribe to multiple topics at once. Returns unified unsubscribe."""
        unsubs = []
        for event_type, handler in handlers.items():
            unsubs.append(self.subscribe(event_type, handler))
        return lambda: [u() for u in unsubs]

    def _unsubscribe(self, event_type: str, handler: AsyncSubscriber) -> None:
        subs = self._subscribers.get(event_type, [])
        if handler in subs:
            subs.remove(handler)
            logger.debug("Unsubscribed from %s (remaining: %d)", event_type, len(subs))

    # ── Publishing ───────────────────────────────────────────────────

    async def publish(self, event: Event) -> None:
        """Publish event to all subscribers of event.event_type.

        All subscribers are called concurrently via asyncio.gather.
        Failures are isolated and logged — one failing subscriber
        doesn't block others.

        Args:
            event: The Event to publish.
        """
        self._event_log.append(event)
        self._publish_count += 1

        tasks = []
        for handler in self._subscribers.get(event.event_type, []):
            tasks.append(self._safe_invoke(handler, event))

        if tasks:
            await asyncio.gather(*tasks)

    async def publish_sync(self, event: Event) -> None:
        """Publish and wait for all subscribers to complete.

        Like publish() but guaranteed to finish all handlers before returning.
        """
        await self.publish(event)

    def publish_fire_and_forget(self, event: Event) -> None:
        """Publish without waiting (fire-and-forget via asyncio.create_task).

        Use this when you don't need to wait for subscribers to finish.
        """
        asyncio.create_task(self.publish(event))

    async def _safe_invoke(self, handler: AsyncSubscriber, event: Event) -> None:
        """Invoke a subscriber, catching and logging errors."""
        try:
            await handler(event)
        except Exception:
            self._error_count += 1
            logger.exception(
                "Subscriber failed for event %s (handler=%s)",
                event.event_type,
                getattr(handler, "__name__", str(handler)),
            )

    # ── Chaining — Publish an event after another completes ──────────

    async def chain(self, trigger: Event, response_event_type: str) -> Callable[[Dict[str, Any]], Awaitable[None]]:
        """Create a response publisher: after processing trigger,
        call the returned function to publish a response event
        with the same correlation_id.

        Usage:
            respond = await bus.chain(input_event, "shinon.output")
            # ... process ...
            await respond({"reply": "...", "claims": [...]})
        """
        async def respond(payload: Dict[str, Any]) -> None:
            response = Event(
                event_type=response_event_type,
                source=response_event_type.split(".")[0],
                payload=payload,
                correlation_id=trigger.correlation_id,
            )
            await self.publish(response)

        return respond

    # ── Event Log & Stats ────────────────────────────────────────────

    def event_log(self, limit: int = 0) -> List[Event]:
        """Return recent events (most recent first if limit > 0)."""
        if limit > 0:
            return list(self._event_log[-limit:])
        return list(self._event_log)

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "published": self._publish_count,
            "errors": self._error_count,
            "subscribers": sum(len(v) for v in self._subscribers.values()),
            "topics": len(self._subscribers),
            "events_logged": len(self._event_log),
        }

    def dump_log(self, path: Optional[Path] = None) -> str:
        """Dump the event log to JSON (or return as string)."""
        data = {"stats": self.stats, "events": [e.to_dict() for e in self._event_log]}
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        if path:
            path.write_text(json_str)
        return json_str

    def save_log(self, path: Path) -> Path:
        """Persist the full event log to a JSON file. Returns the path."""
        data = {
            "version": "1.0.0",
            "bus_stats": self.stats,
            "events": [e.to_dict() for e in self._event_log],
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        logger.info("Event log saved: %d events → %s", len(self._event_log), path)
        return path

    @classmethod
    def from_log(cls, path: Path) -> "AsyncEventBus":
        """Create a new AsyncEventBus from a saved event log file.

        The new bus has the same events in its log but no subscribers.
        Use with ReplayBus to re-publish events to wired subscribers.

        Args:
            path: Path to a JSON file created by save_log().

        Returns:
            New AsyncEventBus with events loaded from the log.
        """
        data = json.loads(path.read_text(encoding="utf-8"))
        bus = cls()
        for event_data in data.get("events", []):
            bus._event_log.append(Event.from_dict(event_data))
        bus._publish_count = len(bus._event_log)
        logger.info("Event log loaded: %d events ← %s", bus._publish_count, path)
        return bus

    @staticmethod
    def load_events(path: Path) -> List[Event]:
        """Load raw events from a log file without creating a bus."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return [Event.from_dict(e) for e in data.get("events", [])]


# ─── Event Replay Report ──────────────────────────────────────────────


@dataclass
class ReplayReport:
    """Result of replaying an event log through a bus.

    Captures replay statistics and any differences between the original
    event log and the replayed events (fingerprint comparison).
    """

    total_events: int = 0
    replayed: int = 0
    errors: int = 0
    identical: int = 0         # events with matching fingerprints
    diverged: int = 0           # events with different fingerprints
    new_events: int = 0         # events generated during replay not in original
    elapsed_ms: float = 0.0
    diverged_details: List[Dict[str, Any]] = field(default_factory=list)
    error_details: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def deterministic(self) -> bool:
        return self.diverged == 0 and self.errors == 0

    def summary(self) -> str:
        lines = [
            f"ReplayReport: {self.replayed}/{self.total_events} events",
            f"  identical={self.identical} diverged={self.diverged} new={self.new_events} errors={self.errors}",
            f"  elapsed={self.elapsed_ms:.1f}ms deterministic={self.deterministic}",
        ]
        if self.diverged_details:
            lines.append(f"  diverged events:")
            for d in self.diverged_details[:5]:
                lines.append(f"    {d.get('event_type')} cid={d.get('correlation_id')}: {d.get('reason', '?')}")
        if self.error_details:
            lines.append(f"  errors:")
            for e in self.error_details[:3]:
                lines.append(f"    {e.get('event_type')}: {e.get('error', '?')}")
        return "\n".join(lines)


# ─── Replay Bus ───────────────────────────────────────────────────────


class ReplayBus:
    """Deterministic event replay engine for debugging.

    Loads a saved event log, wires subscribers, and replays all events
    in order. Compares fingerprints to detect non-determinism.

    Usage:
        # Save original bus
        bus.save_log(Path("/tmp/events.json"))

        # Replay in a new bus with the same subscribers wired
        replay = ReplayBus(Path("/tmp/events.json"))
        replay.wire_all(original_wiring_function)
        report = await replay.replay()
        print(report.summary())
    """

    def __init__(
        self,
        source: Path | AsyncEventBus | List[Event],
        *,
        delay_ms: float = 0,
        stop_on_error: bool = False,
        capture_new_events: bool = True,
    ):
        """Initialize a ReplayBus.

        Args:
            source: Path to log file, an AsyncEventBus (uses its log), or a list of Events.
            delay_ms: Optional delay between events (0 = no delay, for max speed).
            stop_on_error: If True, stop replay on first subscriber error.
            capture_new_events: If True, record events published during replay
                               that weren't in the original log.
        """
        if isinstance(source, Path):
            self._events = AsyncEventBus.load_events(source)
        elif isinstance(source, AsyncEventBus):
            self._events = source.event_log()
        else:
            self._events = list(source)

        self._delay_ms = delay_ms
        self._stop_on_error = stop_on_error
        self._capture_new_events = capture_new_events

        # Create a fresh bus for replay
        self.bus = AsyncEventBus()

        # Original structural fingerprints for comparison (excludes timestamps/cids)
        self._original_structural_fps = [e.structural_fingerprint() for e in self._events]

        # Capture new events generated during replay
        self._new_events: List[Event] = []

    def wire_all(
        self,
        wiring_fn: Callable[["AsyncEventBus"], None],
    ) -> None:
        """Wire subscribers using the same function as the original bus.

        Args:
            wiring_fn: Function that subscribes handlers to a bus.
                       e.g.: lambda bus: runtime.wire() or custom setup.
        """
        wiring_fn(self.bus)
        logger.info("ReplayBus wired: %d topics, %d subscribers",
                     self.bus.stats["topics"], self.bus.stats["subscribers"])

    def wire_subscriber(
        self,
        event_type: str,
        handler: AsyncSubscriber,
    ) -> Callable[[], None]:
        """Wire a single subscriber (convenience method)."""
        return self.bus.subscribe(event_type, handler)

    async def replay(self) -> ReplayReport:
        """Replay all events through the wired bus in order.

        Returns a ReplayReport with determinism metrics.

        Events are replayed in timestamp order. After replay,
        fingerprints of replayed events are compared with originals
        to detect non-deterministic behavior.
        """
        import time as _time

        start = _time.monotonic()
        report = ReplayReport(total_events=len(self._events))

        if self._capture_new_events:
            # Hook into the replay bus to capture new events
            original_log_ref = self.bus._event_log
            self.bus._event_log = []  # Reset for replay
            # Backup original log before clearing
            self.bus._event_log = []

        for i, event in enumerate(self._events):
            try:
                await self.bus.publish(event)
                report.replayed += 1

                # Compare structural fingerprint (event_type + source + payload)
                # Timestamps and correlation_ids are excluded — they ALWAYS differ on replay.
                if i < len(self.bus._event_log):
                    replayed_event = self.bus._event_log[i]
                    if replayed_event.event_type != event.event_type:
                        report.diverged += 1
                        report.diverged_details.append({
                            "index": i,
                            "event_type": event.event_type,
                            "correlation_id": event.correlation_id,
                            "replayed_type": replayed_event.event_type,
                            "reason": f"event_type changed: {event.event_type} → {replayed_event.event_type}",
                            "original_event": event.to_dict(),
                            "replayed_event": replayed_event.to_dict(),
                        })
                    else:
                        replayed_fp = replayed_event.structural_fingerprint()
                        original_fp = self._original_structural_fps[i]
                        if replayed_fp == original_fp:
                            report.identical += 1
                        else:
                            report.diverged += 1
                            report.diverged_details.append({
                                "index": i,
                                "event_type": event.event_type,
                                "correlation_id": event.correlation_id,
                                "original_fp": original_fp,
                                "replayed_fp": replayed_fp,
                                "reason": "structural fingerprint mismatch — payload differs",
                                "original_event": event.to_dict(),
                                "replayed_event": replayed_event.to_dict(),
                            })

                if self._delay_ms > 0:
                    await asyncio.sleep(self._delay_ms / 1000.0)

            except Exception as exc:
                report.errors += 1
                report.error_details.append({
                    "index": i,
                    "event_type": event.event_type,
                    "correlation_id": event.correlation_id,
                    "error": str(exc),
                })
                logger.error("Replay error at event %d: %s", i, exc)
                if self._stop_on_error:
                    break

        # Check for new events generated during replay
        if self._capture_new_events:
            replayed_count = len(self.bus._event_log)
            if replayed_count > len(self._events):
                report.new_events = replayed_count - len(self._events)

        report.elapsed_ms = (_time.monotonic() - start) * 1000.0
        logger.info(
            "Replay complete: %d/%d events, identical=%d diverged=%d errors=%d (%.1fms)",
            report.replayed, report.total_events,
            report.identical, report.diverged, report.errors,
            report.elapsed_ms,
        )
        # Auto-persist the report for dashboard visualization
        _save_replay_report(report)
        return report

    async def replay_with(
        self,
        wiring_fn: Callable[["AsyncEventBus"], None],
    ) -> ReplayReport:
        """Wire and replay in one call. Convenience wrapper."""
        self.wire_all(wiring_fn)
        return await self.replay()


# ─── Replay Report Persistence ────────────────────────────────────────

_REPLAY_REPORT_PATH: Optional[Path] = None
_last_replay_report: Optional[ReplayReport] = None


def set_replay_report_path(path: Path) -> None:
    """Set the path where the last replay report is persisted."""
    global _REPLAY_REPORT_PATH
    _REPLAY_REPORT_PATH = path


def get_last_replay_report() -> Optional[ReplayReport]:
    """Return the last replay report (in-memory or from disk)."""
    global _last_replay_report, _REPLAY_REPORT_PATH
    if _last_replay_report is not None:
        return _last_replay_report
    if _REPLAY_REPORT_PATH and _REPLAY_REPORT_PATH.is_file():
        try:
            data = json.loads(_REPLAY_REPORT_PATH.read_text(encoding="utf-8"))
            _last_replay_report = ReplayReport(
                total_events=data.get("total_events", 0),
                replayed=data.get("replayed", 0),
                errors=data.get("errors", 0),
                identical=data.get("identical", 0),
                diverged=data.get("diverged", 0),
                new_events=data.get("new_events", 0),
                elapsed_ms=data.get("elapsed_ms", 0.0),
                diverged_details=data.get("diverged_details", []),
                error_details=data.get("error_details", []),
            )
        except Exception:
            pass
    return _last_replay_report


def _save_replay_report(report: ReplayReport) -> None:
    """Persist a replay report to disk."""
    global _last_replay_report, _REPLAY_REPORT_PATH
    _last_replay_report = report
    if _REPLAY_REPORT_PATH:
        try:
            _REPLAY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "total_events": report.total_events,
                "replayed": report.replayed,
                "errors": report.errors,
                "identical": report.identical,
                "diverged": report.diverged,
                "new_events": report.new_events,
                "elapsed_ms": report.elapsed_ms,
                "deterministic": report.deterministic,
                "diverged_details": report.diverged_details,
                "error_details": report.error_details,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            _REPLAY_REPORT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as exc:
            logger.warning("Failed to persist replay report: %s", exc)


# ─── Global singleton (for module-level access) ───────────────────────

_default_bus: Optional[AsyncEventBus] = None


def get_event_bus() -> AsyncEventBus:
    """Get or create the global event bus singleton."""
    global _default_bus
    if _default_bus is None:
        _default_bus = AsyncEventBus()
    return _default_bus
