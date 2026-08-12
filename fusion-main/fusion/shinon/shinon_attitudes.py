"""
Attitude Tracker — Dynamic per-user attitudes with SQLite persistence (ported from tracker.ts)
v2: + WAL mode, normalized history table, attitude drift, cross-session persistence

Scope: 0.3.0  |  Source: ShinonLLM-main/character/src/attitudes/tracker.ts
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional


AttitudeDimension = str  # "warmth" | "respect" | "patience" | "trust"


@dataclass
class AttitudeHistoryEntry:
    timestamp: str
    dimension: AttitudeDimension
    change: float
    reason: str


@dataclass
class AttitudeState:
    """Per-user attitude state (-10..+10 per dimension)."""
    user_id: str
    warmth: float = 0.0       # -10 (cold) to +10 (warm)
    respect: float = 0.0       # -10 (contempt) to +10 (appreciative)
    patience: float = 5.0      # -10 (annoyed) to +10 (indulgent) — starts neutral-positive
    trust: float = 0.0         # -10 (suspicious) to +10 (trusting)
    updated_at: str = ""
    history: List[AttitudeHistoryEntry] = field(default_factory=list)

    def __post_init__(self):
        if not self.updated_at:
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "warmth": self.warmth,
            "respect": self.respect,
            "patience": self.patience,
            "trust": self.trust,
            "updated_at": self.updated_at,
        }


@dataclass
class AttitudeUpdateRule:
    event: str
    dimension: AttitudeDimension
    change: float


# Standard update rules (ported from TypeScript)
ATTITUDE_UPDATE_RULES: List[AttitudeUpdateRule] = [
    AttitudeUpdateRule("inkonsistenz_gefunden", "patience", -2),
    AttitudeUpdateRule("inkonsistenz_gefunden", "respect", -1),
    AttitudeUpdateRule("inkonsistenz_gefunden", "trust", -3),
    AttitudeUpdateRule("versprechen_eingehalten", "trust", +3),
    AttitudeUpdateRule("versprechen_eingehalten", "respect", +2),
    AttitudeUpdateRule("versprechen_gebrochen", "trust", -5),
    AttitudeUpdateRule("versprechen_gebrochen", "respect", -3),
    AttitudeUpdateRule("positives_muster", "warmth", +1),
    AttitudeUpdateRule("negatives_muster", "warmth", -1),
    AttitudeUpdateRule("wiederholte_inkonsistenz", "patience", -3),
    AttitudeUpdateRule("wiederholte_inkonsistenz", "trust", -4),
]

# Drift config: how fast attitudes return toward neutral when idle
DRIFT_CONFIG = {
    "warmth":   0.1,   # per day toward 0
    "respect":  0.1,   # per day toward 0
    "patience": 0.3,   # per day toward 5 (neutral-positive)
    "trust":    0.1,   # per day toward 0
}
DEFAULT_NEUTRALS = {"warmth": 0.0, "respect": 0.0, "patience": 5.0, "trust": 0.0}


# ─── SQLite Adapter ───────────────────────────────────────────────────


class AttitudeAdapter:
    """SQLite adapter for attitude persistence with WAL mode + thread safety."""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
            
            # Dimension scores (one row per user+dimension)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS attitudes (
                    user_id TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    score REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, dimension)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_att_user ON attitudes(user_id)")
            
            # Normalized history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS attitude_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    change REAL NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_att_hist_user ON attitude_history(user_id, timestamp)")
            
            conn.commit()
    
    def _connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    
    def all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self._lock:
            with self._connection() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(sql, params).fetchall()
                return [dict(r) for r in rows]
    
    def run(self, sql: str, params: tuple = ()) -> None:
        with self._lock:
            with self._connection() as conn:
                conn.execute(sql, params)
                conn.commit()


# ─── Attitude Functions ───────────────────────────────────────────────


def load_attitude_state(adapter: AttitudeAdapter, user_id: str) -> AttitudeState:
    """Load full attitude state including history."""
    rows = adapter.all(
        "SELECT dimension, score, updated_at FROM attitudes WHERE user_id = ?",
        (user_id,)
    )

    state = AttitudeState(user_id=user_id)
    for row in rows:
        dim = row.get("dimension", "")
        score = float(row.get("score", 0))
        if dim in ("warmth", "respect", "patience", "trust"):
            setattr(state, dim, score)
        if row.get("updated_at"):
            state.updated_at = row["updated_at"]

    # Load history
    history_rows = adapter.all(
        "SELECT dimension, change, reason, timestamp FROM attitude_history "
        "WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50",
        (user_id,)
    )
    state.history = [
        AttitudeHistoryEntry(
            timestamp=r["timestamp"],
            dimension=r["dimension"],
            change=float(r["change"]),
            reason=r.get("reason", ""),
        )
        for r in reversed(history_rows)  # Reverse to chronological
    ]

    if not rows:
        save_attitude_state(adapter, state)
    return state


def save_attitude_state(adapter: AttitudeAdapter, state: AttitudeState) -> None:
    """Persist attitude state + new history entries."""
    now = datetime.now(timezone.utc).isoformat()
    dimensions = [
        ("warmth", state.warmth),
        ("respect", state.respect),
        ("patience", state.patience),
        ("trust", state.trust),
    ]
    for key, value in dimensions:
        adapter.run(
            "INSERT OR REPLACE INTO attitudes (user_id, dimension, score, updated_at) VALUES (?, ?, ?, ?)",
            (state.user_id, key, value, now)
        )
    # Persist only new history entries (those without a DB id)
    for entry in state.history[-20:]:  # Keep last 20 in memory, all in DB
        adapter.run(
            "INSERT INTO attitude_history (user_id, dimension, change, reason, timestamp, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (state.user_id, entry.dimension, entry.change, entry.reason, entry.timestamp, now)
        )


def create_attitude_state(user_id: str) -> AttitudeState:
    return AttitudeState(user_id=user_id)


def update_attitude_value(
    adapter: Optional[AttitudeAdapter],
    state: AttitudeState,
    dimension: AttitudeDimension,
    change: float,
    reason: str,
) -> AttitudeState:
    """Update a single attitude dimension."""
    current = getattr(state, dimension, 0)
    next_val = max(-10.0, min(10.0, current + change))

    new_state = AttitudeState(
        user_id=state.user_id,
        warmth=next_val if dimension == "warmth" else state.warmth,
        respect=next_val if dimension == "respect" else state.respect,
        patience=next_val if dimension == "patience" else state.patience,
        trust=next_val if dimension == "trust" else state.trust,
        updated_at=datetime.now(timezone.utc).isoformat(),
        history=state.history + [
            AttitudeHistoryEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                dimension=dimension, change=change, reason=reason,
            )
        ],
    )

    if adapter:
        save_attitude_state(adapter, new_state)
    return new_state


def apply_attitude_rules(
    adapter: Optional[AttitudeAdapter],
    state: AttitudeState,
    event: str,
) -> AttitudeState:
    """Apply all matching rules for an event."""
    rules = [r for r in ATTITUDE_UPDATE_RULES if r.event == event]
    new_state = state
    for rule in rules:
        new_state = update_attitude_value(adapter, new_state, rule.dimension, rule.change, event)
    return new_state


def apply_drift(
    adapter: Optional[AttitudeAdapter],
    state: AttitudeState,
) -> AttitudeState:
    """Apply attitude drift toward neutral based on time since last update.
    
    Each dimension drifts toward its neutral value at the configured rate.
    Patience drifts toward 5 (neutral-positive), others toward 0.
    """
    try:
        last_update = datetime.fromisoformat(state.updated_at.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return state
    
    now = datetime.now(timezone.utc)
    days_passed = (now - last_update).total_seconds() / (60 * 60 * 24)
    
    if days_passed < 0.05:  # Less than ~1 hour: no drift
        return state
    
    new_warmth = _drift_dimension(state.warmth, 0.0, DRIFT_CONFIG["warmth"], days_passed)
    new_respect = _drift_dimension(state.respect, 0.0, DRIFT_CONFIG["respect"], days_passed)
    new_patience = _drift_dimension(state.patience, 5.0, DRIFT_CONFIG["patience"], days_passed)
    new_trust = _drift_dimension(state.trust, 0.0, DRIFT_CONFIG["trust"], days_passed)
    
    # Only update if something changed
    if (new_warmth == state.warmth and new_respect == state.respect and 
        new_patience == state.patience and new_trust == state.trust):
        return state
    
    drifted = AttitudeState(
        user_id=state.user_id,
        warmth=new_warmth,
        respect=new_respect,
        patience=new_patience,
        trust=new_trust,
        updated_at=now.isoformat(),
        history=state.history + [
            AttitudeHistoryEntry(
                timestamp=now.isoformat(),
                dimension="patience",
                change=round(new_patience - state.patience, 2),
                reason=f"drift ({days_passed:.1f}d idle)",
            )
        ],
    )
    
    if adapter:
        save_attitude_state(adapter, drifted)
    return drifted


def _drift_dimension(current: float, neutral: float, rate: float, days: float) -> float:
    """Drift a single dimension toward its neutral value."""
    if abs(current - neutral) < 0.01:
        return current
    
    drift_amount = rate * days
    if current < neutral:
        return min(neutral, current + drift_amount)
    else:
        return max(neutral, current - drift_amount)


def should_confront(state: AttitudeState, pattern_confidence: float) -> bool:
    return state.patience < 5 and pattern_confidence > 0.8


def format_attitude_for_prompt(state: AttitudeState) -> str:
    def _bar(value: float, neutral: float, label: str) -> str:
        # Map -10..+10 to 0..10 segments (each segment = 2 pts)
        # Visual: 10-segment bar, filled from 0 toward value
        segments = 10
        offset = int((value + 10) / 2)  # 0..10
        offset = max(0, min(segments, offset))
        # Neutral marker
        neutral_offset = int((neutral + 10) / 2)
        
        bar = ""
        for i in range(segments):
            if i == neutral_offset and neutral != 0:
                bar += "┃" if offset == neutral_offset else "╎"
            elif i < offset:
                bar += "█"
            else:
                bar += "░"
        
        sign = "+" if value > 0 else ""
        return f"{label:8s} {bar} ({sign}{value:.0f})"

    return "\n".join([
        "Shinons aktuelle Haltung:",
        _bar(state.warmth,   0.0, "Wärme"),
        _bar(state.respect,  0.0, "Respekt"),
        _bar(state.patience, 5.0, "Geduld"),
        _bar(state.trust,    0.0, "Vertrauen"),
    ])


def get_tone_directive(state: AttitudeState) -> str:
    if state.patience < 3:
        return "Du bist genervt und direkt. Kurze, präzise Antworten ohne Umschweife."
    if state.patience < 5:
        return "Du bist sarkastisch und leicht gereizt."
    if state.trust > 5:
        return "Du bist warm und wertschätzend."
    if state.trust < -5:
        return "Du bist misstrauisch und distanziert."
    return "Du bist neutral und sachlich."


# Backward-compat alias
update_attitude = update_attitude_value
