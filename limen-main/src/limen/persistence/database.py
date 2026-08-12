"""SQLite state store for the LIMEN foundation."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from limen.persistence.audit import AuditLog

if TYPE_CHECKING:
    from collections.abc import Iterator

SCHEMA_VERSION = 2

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS providers (
        key_id TEXT PRIMARY KEY,
        provider TEXT NOT NULL,
        deployment TEXT NOT NULL,
        api_key_fingerprint TEXT NOT NULL,
        account_id TEXT,
        limit_scope TEXT NOT NULL CHECK (
            limit_scope IN ('key', 'account', 'provider', 'model', 'unknown')
        ),
        status TEXT NOT NULL CHECK (status IN ('active', 'cooldown', 'dead')),
        cooldown_until TEXT,
        last_used_at TEXT,
        priority INTEGER NOT NULL,
        observed_rpm INTEGER,
        observed_itpm INTEGER,
        observed_otpm INTEGER,
        error_count INTEGER NOT NULL DEFAULT 0,
        success_count INTEGER NOT NULL DEFAULT 0,
        meta_json TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS queue (
        id TEXT PRIMARY KEY,
        body_json TEXT NOT NULL,
        target_model TEXT NOT NULL,
        tool_label TEXT,
        stream_flag INTEGER NOT NULL CHECK (stream_flag IN (0, 1)),
        status TEXT NOT NULL CHECK (status IN ('pending', 'in_flight', 'done', 'dead')),
        attempt_count INTEGER NOT NULL DEFAULT 0,
        lease_until TEXT,
        created_at TEXT NOT NULL,
        picked_up_at TEXT,
        finished_at TEXT,
        correlation_id TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS idempotency_keys (
        key TEXT PRIMARY KEY,
        request_fingerprint TEXT NOT NULL,
        operation TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        result_json TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        correlation_id TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS worker_heartbeats (
        worker_id TEXT PRIMARY KEY,
        last_beat_at TEXT NOT NULL,
        state TEXT NOT NULL CHECK (state IN ('idle', 'busy', 'dead')),
        current_task_id TEXT,
        beat_count INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
)

_REQUIRED_TABLES = {
    "providers",
    "queue",
    "idempotency_keys",
    "events",
    "worker_heartbeats",
    "schema_meta",
}


class Database:
    """Own one SQLite connection and its schema lifecycle."""

    def __init__(
        self,
        path: Path,
        *,
        busy_timeout_ms: int = 30_000,
        sync_mode: str = "normal",
    ) -> None:
        self.path = path.expanduser()
        self.busy_timeout_ms = busy_timeout_ms
        self.sync_mode = sync_mode
        self._connection: sqlite3.Connection | None = None
        self._lock = threading.RLock()

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the open connection or fail explicitly."""
        if self._connection is None:
            raise RuntimeError("Database is not open")
        return self._connection

    def open(self) -> None:
        """Create parent directories, open SQLite, apply safety pragmas, and initialize schema."""
        if self._connection is not None:
            return
        self._ensure_parent_directory()
        if self.path.exists():
            self.path.chmod(0o600)
        else:
            self.path.touch(mode=0o600)
        for sidecar in self._sidecar_paths():
            if sidecar.exists():
                sidecar.chmod(0o600)
        self._connection = sqlite3.connect(
            self.path,
            timeout=self.busy_timeout_ms / 1000,
            check_same_thread=False,
        )
        self.audit = AuditLog(self._connection, self._lock)
        try:
            connection = self.connection
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
            journal_mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            if journal_mode.lower() != "wal":
                raise sqlite3.DatabaseError(f"SQLite WAL could not be enabled: {journal_mode}")
            connection.execute(f"PRAGMA synchronous = {self.sync_mode.upper()}")
            applied_sync_mode = connection.execute("PRAGMA synchronous").fetchone()
            if applied_sync_mode is None:
                raise sqlite3.DatabaseError("SQLite synchronous pragma returned no value")
            self.initialize_schema()
            for sidecar in self._sidecar_paths():
                if sidecar.exists():
                    sidecar.chmod(0o600)
        except (sqlite3.DatabaseError, OSError):
            for sidecar in self._sidecar_paths():
                if sidecar.exists():
                    sidecar.chmod(0o600)
            self.close()
            raise

    def _ensure_parent_directory(self) -> None:
        """Create missing database directories with owner-only permissions."""
        missing: list[Path] = []
        current = self.path.parent
        while not current.exists():
            missing.append(current)
            current = current.parent
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for directory in missing:
            directory.chmod(0o700)

    def _sidecar_paths(self) -> tuple[Path, Path]:
        return Path(f"{self.path}-wal"), Path(f"{self.path}-shm")

    def close(self) -> None:
        """Close the connection and release the local handle."""
        if self._connection is not None:
            with self._lock:
                self._connection.close()
                self._connection = None

    def _migrate_v1_to_v2(self, connection: sqlite3.Connection) -> None:
        """Add error_count and success_count columns for health tracking.

        Uses ALTER TABLE ADD COLUMN with IF NOT EXISTS semantics —
        catches the 'duplicate column name' error silently since SQLite
        doesn't support IF NOT EXISTS for ALTER TABLE.
        """
        for col, col_type in [
            ("error_count", "INTEGER NOT NULL DEFAULT 0"),
            ("success_count", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            try:
                connection.execute(
                    f"ALTER TABLE providers ADD COLUMN {col} {col_type}"
                )
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise

    def initialize_schema(self) -> None:
        """Apply the current schema or reject a corrupt/incompatible database."""
        connection = self.connection
        current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if current_version > SCHEMA_VERSION:
            raise sqlite3.DatabaseError(
                f"Database schema {current_version} is newer than supported {SCHEMA_VERSION}"
            )
        existing_tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        if current_version == 0 and existing_tables:
            existing = ", ".join(sorted(existing_tables))
            raise sqlite3.DatabaseError(
                f"Unversioned database contains existing tables: {existing}"
            )
        if current_version == SCHEMA_VERSION:
            missing_tables = _REQUIRED_TABLES - existing_tables
            if missing_tables:
                missing = ", ".join(sorted(missing_tables))
                raise sqlite3.DatabaseError(
                    f"Database schema {SCHEMA_VERSION} is incomplete; missing tables: {missing}"
                )
            return

        # ── Migrations ──
        with self.transaction():
            # Fresh DB: create all tables
            if current_version == 0:
                for statement in _SCHEMA_STATEMENTS:
                    connection.execute(statement)
            else:
                # v1 → v2: add health tracking columns
                if current_version <= 1:
                    self._migrate_v1_to_v2(connection)

            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.execute(
                "INSERT OR REPLACE INTO schema_meta(key, value) VALUES (?, ?)",
                ("schema_version", str(SCHEMA_VERSION)),
            )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run a state mutation with rollback for database and application failures."""
        connection = self.connection
        with self._lock:
            try:
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.commit()
            except BaseException:
                if connection.in_transaction:
                    connection.rollback()
                raise

    def health_check(self) -> bool:
        """Verify that SQLite is open and accepts a read/write transaction."""
        connection = self.connection
        with self._lock:
            try:
                connection.execute("SELECT 1").fetchone()
                with self.transaction() as transaction:
                    transaction.execute(
                        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES (?, ?)",
                        ("last_health_check", datetime.now(UTC).isoformat()),
                    )
                return True
            except sqlite3.DatabaseError:
                if connection.in_transaction:
                    connection.rollback()
                return False

    # ── Queue operations (Phase 3) ──────────────────────────────────

    def enqueue(
        self,
        request_id: str,
        body_json: str,
        target_model: str,
        correlation_id: str,
        *,
        stream_flag: bool = False,
    ) -> None:
        """Insert a request into the durable queue with status ``pending``."""
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO queue(id, body_json, target_model, stream_flag,"
                " status, attempt_count, created_at, correlation_id)"
                " VALUES (?, ?, ?, ?, 'pending', 0, ?, ?)",
                (
                    request_id,
                    body_json,
                    target_model,
                    1 if stream_flag else 0,
                    datetime.now(UTC).isoformat(),
                    correlation_id,
                ),
            )

    def emplace(
        self,
        request_id: str,
        body_json: str,
        target_model: str,
        correlation_id: str,
        *,
        stream_flag: bool = False,
        lease_seconds: int = 60,
    ) -> dict[str, object]:
        """Atomically insert a queue entry and claim it.

        Returns the entry as a dict. This is the primary path for the API
        handler — no race with the background worker.
        """
        now = datetime.now(UTC).isoformat()
        lease_ts = datetime.now(UTC).timestamp() + lease_seconds
        lease_iso = datetime.fromtimestamp(lease_ts, UTC).isoformat()
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO queue(id, body_json, target_model, stream_flag,"
                " status, attempt_count, created_at, correlation_id,"
                " picked_up_at, lease_until)"
                " VALUES (?, ?, ?, ?, 'in_flight', 1, ?, ?, ?, ?)",
                (
                    request_id,
                    body_json,
                    target_model,
                    1 if stream_flag else 0,
                    now,
                    correlation_id,
                    now,
                    lease_iso,
                ),
            )
            row = conn.execute(
                "SELECT id, body_json, target_model, stream_flag, attempt_count,"
                " correlation_id FROM queue WHERE id = ?",
                (request_id,),
            ).fetchone()
        return dict(row)

    def claim_next(self, *, lease_seconds: int = 60) -> dict[str, object] | None:
        """Atomically claim the oldest pending queue entry.

        Returns the row as a dict, or ``None`` if the queue is empty.
        Sets ``status='in_flight'`` and ``lease_until`` in the same
        transaction.
        """
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT id, body_json, target_model, stream_flag, attempt_count,"
                " correlation_id FROM queue"
                " WHERE status = 'pending'"
                " ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            now = datetime.now(UTC).isoformat()
            lease_until = datetime.now(UTC).timestamp() + lease_seconds
            lease_iso = datetime.fromtimestamp(lease_until, UTC).isoformat()
            conn.execute(
                "UPDATE queue SET status = 'in_flight',"
                " lease_until = ?, picked_up_at = ?, attempt_count = attempt_count + 1"
                " WHERE id = ?",
                (lease_iso, now, row["id"]),
            )
        return dict(row)

    def finish_task(self, task_id: str) -> None:
        """Mark a claimed queue entry as ``done``."""
        with self.transaction() as conn:
            conn.execute(
                "UPDATE queue SET status = 'done', finished_at = ?, lease_until = NULL"
                " WHERE id = ?",
                (datetime.now(UTC).isoformat(), task_id),
            )

    def fail_task(self, task_id: str) -> None:
        """Return a claimed queue entry back to ``pending``."""
        with self.transaction() as conn:
            conn.execute(
                "UPDATE queue SET status = 'pending', lease_until = NULL WHERE id = ?",
                (task_id,),
            )

    def dead_task(self, task_id: str) -> None:
        """Mark a queue entry as ``dead`` — too many failures."""
        with self.transaction() as conn:
            conn.execute(
                "UPDATE queue SET status = 'dead', finished_at = ?, lease_until = NULL"
                " WHERE id = ?",
                (datetime.now(UTC).isoformat(), task_id),
            )

    def recover_leases(self) -> int:
        """Reset expired in_flight leases back to pending. Called on startup.

        Returns the number of recovered entries.
        """
        now_ts = datetime.now(UTC).timestamp()
        count = 0
        with self.transaction() as conn:
            rows = conn.execute(
                "SELECT id, lease_until FROM queue WHERE status = 'in_flight'"
            ).fetchall()
            for row in rows:
                try:
                    if row["lease_until"] is None:
                        lease_ts = 0.0
                    else:
                        lease_ts = datetime.fromisoformat(str(row["lease_until"])).timestamp()
                except (ValueError, OSError, TypeError):
                    lease_ts = 0.0
                if lease_ts < now_ts:
                    conn.execute(
                        "UPDATE queue SET status = 'pending', lease_until = NULL WHERE id = ?",
                        (row["id"],),
                    )
                    count += 1
        return count

    def queue_depth(self) -> int:
        """Return the number of ``pending`` entries in the queue."""
        row = self.connection.execute(
            "SELECT COUNT(*) as cnt FROM queue WHERE status = 'pending'"
        ).fetchone()
        return int(row["cnt"]) if row else 0

    # ── Idempotency (Phase 3) ───────────────────────────────────────

    def check_idempotent(self, fingerprint: str, operation: str, ttl_hours: int = 24) -> str | None:
        """Return ``result_json`` if a matching idempotent request exists,
        or ``None`` if this is a new request."""
        row = self.connection.execute(
            "SELECT result_json FROM idempotency_keys"
            " WHERE key = ? AND operation = ? AND expires_at > ?",
            (
                fingerprint,
                operation,
                datetime.now(UTC).isoformat(),
            ),
        ).fetchone()
        return str(row["result_json"]) if row and row["result_json"] else None

    def store_idempotent(
        self, fingerprint: str, operation: str, result_json: str, ttl_hours: int = 24
    ) -> None:
        """Record a completed request so future identical calls can deduplicate."""
        from datetime import timedelta

        expires = (datetime.now(UTC) + timedelta(hours=ttl_hours)).isoformat()
        with self.transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO idempotency_keys"
                " (key, request_fingerprint, operation, expires_at, result_json)"
                " VALUES (?, ?, ?, ?, ?)",
                (fingerprint, fingerprint, operation, expires, result_json),
            )

    # ── Heartbeat / Reaper (Phase 4) ────────────────────────────────

    def heartbeat(self, worker_id: str, *, state: str = "idle", task_id: str = "") -> None:
        """Write or update the worker heartbeat row."""
        now = datetime.now(UTC).isoformat()
        with self._lock:
            self.connection.execute(
                "INSERT INTO worker_heartbeats(worker_id, last_beat_at, state,"
                " current_task_id, beat_count)"
                " VALUES (?, ?, ?, ?, 1)"
                " ON CONFLICT(worker_id) DO UPDATE SET"
                " last_beat_at = excluded.last_beat_at,"
                " state = excluded.state,"
                " current_task_id = excluded.current_task_id,"
                " beat_count = worker_heartbeats.beat_count + 1",
                (worker_id, now, state, task_id if task_id else None),
            )
            self.connection.commit()

    def reap_dead_workers(self, *, stale_seconds: int = 30) -> list[str]:
        """Mark workers as dead if they haven't heartbeated recently.

        Returns the list of worker IDs that were marked dead.
        """
        cutoff = datetime.now(UTC).timestamp() - stale_seconds
        cutoff_iso = datetime.fromtimestamp(cutoff, UTC).isoformat()
        dead_ids: list[str] = []
        with self.transaction() as conn:
            rows = conn.execute(
                "SELECT worker_id, current_task_id FROM worker_heartbeats"
                " WHERE state != 'dead' AND last_beat_at < ?",
                (cutoff_iso,),
            ).fetchall()
            for row in rows:
                conn.execute(
                    "UPDATE worker_heartbeats SET state = 'dead' WHERE worker_id = ?",
                    (row["worker_id"],),
                )
                dead_ids.append(row["worker_id"])
                if row["current_task_id"]:
                    conn.execute(
                        "UPDATE queue SET status = 'pending', lease_until = NULL"
                        " WHERE id = ? AND status = 'in_flight'",
                        (row["current_task_id"],),
                    )
        return dead_ids

    # ── Key state persistence ──────────────────────────────────────

    def persist_key_state(
        self,
        deployment: str,
        key_value: str,
        status: str,
        *,
        cooldown_until: str | None = None,
        provider: str = "",
        limit_scope: str = "key",
        account_id: str = "",
        priority: int = 1,
    ) -> None:
        """Upsert a key's runtime state into the providers table.

        Called after every claim/release so state survives restart.
        The key fingerprint is a truncated SHA-256 of the value.
        """
        import hashlib as _hl

        fingerprint = _hl.sha256(key_value.encode()).hexdigest()[:16]
        key_id = f"{deployment}:{fingerprint}"
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO providers"
                " (key_id, provider, deployment, api_key_fingerprint,"
                "  account_id, limit_scope, status, cooldown_until,"
                "  priority, meta_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '{}')"
                " ON CONFLICT(key_id) DO UPDATE SET"
                " status = excluded.status,"
                " cooldown_until = excluded.cooldown_until",
                (
                    key_id,
                    provider,
                    deployment,
                    fingerprint,
                    account_id,
                    limit_scope,
                    status,
                    cooldown_until,
                    priority,
                ),
            )

    def recover_key_states(
        self,
    ) -> dict[str, dict[str, object]]:
        """Return all persisted key states keyed by deployment name.

        Returns ``{deployment: {key_id: {status, cooldown_until, …}, …}, …}``.
        Called once on startup to seed in-memory KeyPool state.
        """
        rows = self.connection.execute(
            "SELECT key_id, provider, deployment, status, cooldown_until FROM providers"
        ).fetchall()
        result: dict[str, dict[str, object]] = {}
        for row in rows:
            dep = str(row["deployment"])
            if dep not in result:
                result[dep] = {}
            result[dep][str(row["key_id"])] = {
                "status": str(row["status"]),
                "cooldown_until": (str(row["cooldown_until"]) if row["cooldown_until"] else None),
            }
        return result

    # ── Health snapshot sync (KeyPool → DB, every 30s) ────────────

    def sync_health_snapshot(
        self,
        deployment: str,
        health_data: dict[str, dict[str, object]],
        *,
        provider: str = "",
    ) -> int:
        """Write per-key health data from in-memory KeyPool to providers table.

        Updates error_count, success_count, and status for each key.
        Returns number of rows updated.
        """
        updated = 0
        with self.transaction() as conn:
            for key_id, data in health_data.items():
                conn.execute(
                    "UPDATE providers SET"
                    " error_count = ?, success_count = ?, status = ?,"
                    " cooldown_until = ?"
                    " WHERE key_id = ?",
                    (
                        int(data.get("error_count", 0)),
                        int(data.get("success_count", 0)),
                        str(data.get("status", "active")),
                        data.get("cooldown_until"),
                        key_id,
                    ),
                )
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    updated += 1
        return updated

    # ── Budget persistence (rate limit tracking) ──────────────────

    def persist_budget_state(
        self,
        deployment: str,
        key_value: str,
        *,
        provider: str = "",
        tokens_used: int = 0,
        tokens_max: int = 1_000_000,
        requests_used: int = 0,
        requests_max: int = 500,
        last_updated: str = "",
    ) -> None:
        """Persist current rate limit budget state to the providers table.

        Writes observed_itpm (input tokens used), observed_otpm (output tokens -
        stored as zero for now since we track total), observed_rpm (requests used),
        and budget metadata into meta_json for recovery.

        Called periodically (not on every release — batched or significant changes).
        """
        import hashlib as _hl
        import json

        if not last_updated:
            last_updated = datetime.now(UTC).isoformat()

        fingerprint = _hl.sha256(key_value.encode()).hexdigest()[:16]
        key_id = f"{deployment}:{fingerprint}"

        budget_meta = json.dumps({
            "tokens_used": tokens_used,
            "tokens_max": tokens_max,
            "requests_used": requests_used,
            "requests_max": requests_max,
            "last_updated": last_updated,
        })

        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO providers"
                " (key_id, provider, deployment, api_key_fingerprint,"
                "  account_id, limit_scope, status, priority,"
                "  observed_itpm, observed_rpm, meta_json, last_used_at)"
                " VALUES (?, ?, ?, ?, '', 'key', 'active', 1, ?, ?, ?, ?)"
                " ON CONFLICT(key_id) DO UPDATE SET"
                " observed_itpm = excluded.observed_itpm,"
                " observed_rpm = excluded.observed_rpm,"
                " meta_json = excluded.meta_json,"
                " last_used_at = excluded.last_used_at",
                (
                    key_id,
                    provider if provider else deployment,
                    deployment,
                    fingerprint,
                    tokens_used,
                    requests_used,
                    budget_meta,
                    last_updated,
                ),
            )

    def recover_budget_state(
        self,
    ) -> dict[str, dict[str, object]]:
        """Recover persisted budget state for all keys.

        Returns {key_id: {tokens_used, tokens_max, requests_used, requests_max, last_updated}}
        for all keys that have persisted budget data within the rate limit window.

        Called once on startup to seed in-memory RateLimitTracker.
        """
        import json

        rows = self.connection.execute(
            "SELECT key_id, deployment, provider, observed_itpm, observed_rpm, meta_json, last_used_at"
            " FROM providers WHERE observed_itpm IS NOT NULL OR observed_rpm IS NOT NULL"
        ).fetchall()

        result: dict[str, dict[str, object]] = {}
        now = datetime.now(UTC)

        for row in rows:
            key_id = str(row["key_id"])
            budget: dict[str, object] = {
                "tokens_used": int(row["observed_itpm"] or 0),
                "tokens_max": 1_000_000,
                "requests_used": int(row["observed_rpm"] or 0),
                "requests_max": 500,
                "last_updated": str(row["last_used_at"] or ""),
            }

            # Try to parse richer data from meta_json
            try:
                meta = json.loads(str(row["meta_json"] or "{}"))
                if isinstance(meta, dict):
                    if "tokens_max" in meta:
                        budget["tokens_max"] = int(meta["tokens_max"])
                    if "requests_max" in meta:
                        budget["requests_max"] = int(meta["requests_max"])
                    if "last_updated" in meta:
                        budget["last_updated"] = str(meta["last_updated"])
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            # Budget data is ephemeral (sliding window = 60s).
            # Only restore if less than 60s old — otherwise reset.
            last_str = str(budget.get("last_updated", ""))
            if last_str:
                try:
                    last_dt = datetime.fromisoformat(last_str)
                    if (now - last_dt).total_seconds() > 60:
                        budget["tokens_used"] = 0
                        budget["requests_used"] = 0
                except (ValueError, OSError):
                    pass
            else:
                # No timestamp = assume stale
                budget["tokens_used"] = 0
                budget["requests_used"] = 0

            result[key_id] = budget

        return result

    # ── Audit events (delegated to persistence.AuditLog) ────────────

    def write_event(
        self, event_type: str, payload: dict[str, object], *, correlation_id: str = ""
    ) -> None:
        """Write a redacted audit event.  Delegates to ``self.audit``."""
        self.audit.write_event(event_type, payload, correlation_id=correlation_id)

    def read_events(self, *, since_id: int = 0, limit: int = 100) -> list[dict[str, object]]:
        """Return recent audit events.  Delegates to ``self.audit``."""
        return self.audit.read_events(since_id=since_id, limit=limit)

    def prune_events(self, *, keep_count: int = 100_000) -> int:
        """Delete oldest events.  Delegates to ``self.audit``."""
        return self.audit.prune_events(keep_count=keep_count)
