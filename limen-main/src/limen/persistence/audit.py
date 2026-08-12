"""Audit event log backed by the SQLite events table."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import threading


class AuditLog:
    """Write, read, and prune audit events in the ``events`` table.

    Owns no connection — operates on the connection and lock provided
    by the owning ``Database`` instance.  All public methods swallow
    ``sqlite3.DatabaseError`` / ``OSError`` so the request path is
    never blocked by audit writes.
    """

    __slots__ = ("_connection", "_lock")

    def __init__(self, connection: sqlite3.Connection, lock: threading.RLock) -> None:
        self._connection = connection
        self._lock = lock

    # ── Write ───────────────────────────────────────────────────────

    def write_event(
        self,
        event_type: str,
        payload: dict[str, object],
        *,
        correlation_id: str = "",
    ) -> None:
        """Write a redacted audit event.  Fire-and-forget safe."""
        try:
            with self._lock:
                self._connection.execute(
                    "INSERT INTO events(event_type, payload_json, timestamp,"
                    " correlation_id) VALUES (?, ?, ?, ?)",
                    (
                        event_type,
                        json.dumps(payload, default=str),
                        datetime.now(UTC).isoformat(),
                        correlation_id,
                    ),
                )
                self._connection.commit()
        except (sqlite3.DatabaseError, OSError) as exc:
            import sys

            print(f"[limen] audit write failed: {exc}", file=sys.stderr)

    # ── Read ────────────────────────────────────────────────────────

    def read_events(self, *, since_id: int = 0, limit: int = 100) -> list[dict[str, object]]:
        """Return recent events for SSE replay / inspection."""
        rows = self._connection.execute(
            "SELECT id, event_type, payload_json, timestamp, correlation_id"
            " FROM events WHERE id > ? ORDER BY id ASC LIMIT ?",
            (since_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    # ── Prune ───────────────────────────────────────────────────────

    def prune_events(self, *, keep_count: int = 100_000) -> int:
        """Delete oldest rows beyond *keep_count* most recent events.

        Returns the number of deleted rows.
        """
        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                cutoff_row = self._connection.execute(
                    "SELECT id FROM events ORDER BY id DESC LIMIT 1 OFFSET ?",
                    (keep_count,),
                ).fetchone()
                if cutoff_row is None:
                    self._connection.commit()
                    return 0
                result = self._connection.execute(
                    "DELETE FROM events WHERE id <= ?",
                    (cutoff_row["id"],),
                )
                self._connection.commit()
                return result.rowcount
            except (sqlite3.DatabaseError, OSError):
                if self._connection.in_transaction:
                    self._connection.rollback()
                return 0
