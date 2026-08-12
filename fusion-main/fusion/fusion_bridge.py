"""
Fusion Bridge — HOFF-0002 Orchestrator

Connects Shinon Passthrough → Promtguard Claims via HOFF-0002 handoff.
Event publishing for async subscribers (KARMA, goal-chain).
Implements the Evil Twin's recommendation: Event-Driven over linear pipeline.

Flow:
    User → Shinon.process() → HOFF-0002 → Promtguard.extract_claims()
         → claims persisted → HOFF-0003 handoff → KARMA (future)

Position: Bridge between Position 0 (Shinon) and Position 1 (Promtguard)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from fusion.shinon_passthrough import (
    ShinonInput,
    ShinonOutput,
    ShinonPassthrough,
)
from fusion.promtguard_claims import (
    Claim,
    ContextToken,
    Handoff,
    PromtguardClaims,
)

logger = logging.getLogger(__name__)


# ─── Event Types ─────────────────────────────────────────────────────


@dataclass
class Event:
    """Pub/Sub event for async component communication."""

    event_type: str
    source: str
    payload: Dict[str, Any]
    timestamp: str = ""
    correlation_id: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.correlation_id:
            import uuid
            self.correlation_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "source": self.source,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }


# ─── Subscriber Type ─────────────────────────────────────────────────

Subscriber = Callable[[Event], None]


# ─── Event Bus ───────────────────────────────────────────────────────


class EventBus:
    """Simple in-process Pub/Sub event bus.

    Evil Twin Synthesis: Instead of linear HOFF-0001→HOFF-0002→...
    handoffs, components SUBSCRIBE to events and react asynchronously.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Subscriber]] = {}
        self._event_log: List[Event] = []

    def subscribe(self, event_type: str, handler: Subscriber) -> Callable[[], None]:
        """Subscribe to an event type. Returns unsubscribe function."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        return lambda: self._unsubscribe(event_type, handler)

    def _unsubscribe(self, event_type: str, handler: Subscriber) -> None:
        subs = self._subscribers.get(event_type, [])
        if handler in subs:
            subs.remove(handler)

    def publish(self, event: Event) -> None:
        """Publish event to all subscribers."""
        self._event_log.append(event)
        subs = self._subscribers.get(event.event_type, [])
        for handler in subs:
            try:
                handler(event)
            except Exception:
                logger.exception("Subscriber failed for event %s", event.event_type)

    def event_log(self) -> List[Event]:
        return list(self._event_log)


# ─── Fusion Result ───────────────────────────────────────────────────


@dataclass
class FusionResult:
    """Complete result of one Shinon→Promtguard→KARMA cycle."""

    input: ShinonInput
    shinon_output: ShinonOutput
    claims: List[Claim] = field(default_factory=list)
    context_token: Optional[ContextToken] = None
    handoff: Optional[Handoff] = None
    events: List[Event] = field(default_factory=list)
    correlation_id: str = ""

    def __post_init__(self):
        if not self.correlation_id:
            import uuid
            self.correlation_id = str(uuid.uuid4())[:8]

    def summary(self) -> str:
        return (
            f"FusionResult(cid={self.correlation_id}, "
            f"claims={len(self.claims)}, "
            f"handoff={self.handoff.to_component if self.handoff else 'none'})"
        )


# ─── Fusion Bridge ───────────────────────────────────────────────────


class FusionBridge:
    """Orchestrates HOFF-0002 Shinon → Promtguard handoff.

    Usage:
        bridge = FusionBridge(state_dir=Path(".promtset/state"))
        result = bridge.process(user_text="Implement OAuth2 login",
                                session_id="sess-001")
        print(f"Extracted {len(result.claims)} claims")
    """

    def __init__(
        self,
        state_dir: Optional[Path] = None,
        identity: Optional[Dict[str, str]] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.shinon = ShinonPassthrough(identity=identity)
        self.promtguard = PromtguardClaims(
            state_dir=Path(state_dir) if isinstance(state_dir, str) else state_dir
        )
        self.event_bus = event_bus or EventBus()
        self._session_counter = 0

    def process(
        self,
        user_text: str,
        session_id: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        conversation_id: str = "",
    ) -> FusionResult:
        """Run the full HOFF-0002 handoff cycle.

        Args:
            user_text: Raw user input.
            session_id: Session identifier.
            history: Optional conversation history.
            conversation_id: Optional conversation thread ID.

        Returns:
            FusionResult with all claims, context tokens, and handoffs.
        """
        if not session_id:
            self._session_counter += 1
            session_id = f"auto-sess-{self._session_counter:04d}"

        # Track events for this call only (avoid picking up prior events)
        event_start_idx = len(self.event_bus._event_log)

        # ── Step 1: Shinon processes user input ──
        shinon_input = ShinonInput(
            user_text=user_text,
            session_id=session_id,
            conversation_id=conversation_id,
            history=history or [],
        )
        shinon_output = self.shinon.process(shinon_input)

        # Publish: shinon.output
        self.event_bus.publish(Event(
            event_type="shinon.output",
            source="shinon",
            payload=shinon_output.to_dict(),
        ))

        # ── Step 2: HOFF-0002 → Promtguard extracts claims ──
        claims = self.promtguard.extract_claims(
            shinon_output.handoff_to_promtguard["processed_input"],
            source="shinon_passthrough",
        )

        # Persist claims
        self.promtguard.append_claims(claims)

        # Context token
        ctx_token = ContextToken(
            id=self.promtguard._next_ctx_id(),
            source="shinon_passthrough",
            summary=user_text[:200],
            claims_extracted=len(claims),
        )
        self.promtguard.append_context_token(ctx_token)

        # Publish: promtguard.claims_extracted
        self.event_bus.publish(Event(
            event_type="promtguard.claims_extracted",
            source="promtguard",
            payload={
                "claim_count": len(claims),
                "context_token_id": ctx_token.id,
                "claim_ids": [c.id for c in claims],
            },
        ))

        # ── Step 3: HOFF-0003 handoff to KARMA ──
        handoff = Handoff(
            from_component="promtguard",
            to_component="karma",
            note=f"Claims extracted: {len(claims)}. Ready for falsification.",
        )
        self.promtguard.append_handoff(handoff)

        # Publish: promtguard.handoff
        self.event_bus.publish(Event(
            event_type="promtguard.handoff",
            source="promtguard",
            payload=handoff.to_dict(),
        ))

        return FusionResult(
            input=shinon_input,
            shinon_output=shinon_output,
            claims=claims,
            context_token=ctx_token,
            handoff=handoff,
            events=list(self.event_bus.event_log()[event_start_idx:]),
        )

    def subscribe_karma(self, handler: Subscriber) -> Callable[[], None]:
        """KARMA subscribes to promtguard.claims_extracted events."""
        return self.event_bus.subscribe("promtguard.claims_extracted", handler)

    @property
    def claim_stats(self) -> Dict[str, int]:
        return self.promtguard.stats()
