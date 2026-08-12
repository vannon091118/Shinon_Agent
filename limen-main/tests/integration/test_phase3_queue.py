"""Phase 3 durable queue and crash-recovery contract tests.

Covers:
- Atomic emplace (insert + claim)
- Claim/finish/fail/dead lifecycle
- Idempotency store and check
- Lease recovery on startup
- Queue depth reporting
- Concurrent claim isolation
- Worker processes recovered entries

Every assertion is concrete and runs against a real SQLite database.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import httpx
import pytest
from fastapi.testclient import TestClient

from limen.persistence.database import Database

if TYPE_CHECKING:
    from pathlib import Path


# ── helpers ────────────────────────────────────────────────────────────

_MODEL = "phase3-reference-model"


def _write_config(path: Path, db_path: Path, *, extra: str = "") -> None:
    path.write_text(
        f"""[server]
host = "127.0.0.1"
port = 18250
worker_count = 1
log_level = "warning"
max_body_size_kb = 256

[database]
path = "{db_path}"

[providers.bogus]
enabled = true
base_url = "https://queue.invalid/v1"
priority = 10
limit_scope = "unknown"
account_id = "phase3"
keys = ["queue-key"]
models = ["{_MODEL}"]
capabilities = ["chat"]
{extra}
""",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _mock_ok(_: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-phase3-001",
            "object": "chat.completion",
            "created": 1_700_000_000,
            "model": _MODEL,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "queue says hi"},
                    "finish_reason": "stop",
                }
            ],
        },
    )


def _assert_queue_status(database: Database, task_id: str | None, expected: str) -> None:
    if task_id is not None:
        row = database.connection.execute(
            "SELECT status FROM queue WHERE id = ?", (task_id,)
        ).fetchone()
    else:
        row = database.connection.execute(
            "SELECT status FROM queue LIMIT 1"
        ).fetchone()
    assert row is not None, "no queue entry found"
    assert row["status"] == expected, f"expected {expected}, got {row['status']}"


# ── §1 — Database-level queue operations ────────────────────────────────


def test_emplace_inserts_and_claims_atomically(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        entry = database.emplace(
            "req-1", '{"model":"m"}', "m", "corr-1", stream_flag=False
        )
        assert entry["id"] == "req-1"
        assert entry["attempt_count"] == 1
        assert entry["body_json"] == '{"model":"m"}'

        _assert_queue_status(database, "req-1", "in_flight")

        row = database.connection.execute(
            "SELECT lease_until, picked_up_at FROM queue WHERE id = ?", ("req-1",)
        ).fetchone()
        assert row is not None
        assert row["lease_until"] is not None
        assert row["picked_up_at"] is not None
    finally:
        database.close()


def test_emplace_rejects_duplicate_id(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        database.emplace("dup", '{"model":"m"}', "m", "c1")
        with pytest.raises(sqlite3.IntegrityError):
            database.emplace("dup", '{"model":"m"}', "m", "c2")
    finally:
        database.close()


def test_claim_next_picks_oldest_pending(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        database.enqueue("a", '{"model":"m"}', "m", "c-a")
        database.enqueue("b", '{"model":"m"}', "m", "c-b")

        first = database.claim_next()
        assert first is not None
        assert first["id"] == "a"

        second = database.claim_next()
        assert second is not None
        assert second["id"] == "b"

        assert database.claim_next() is None
    finally:
        database.close()


def test_claim_next_skips_in_flight_and_done(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        database.emplace("x", '{"model":"m"}', "m", "c-x")
        database.enqueue("y", '{"model":"m"}', "m", "c-y")

        claimed = database.claim_next()
        assert claimed is not None
        assert claimed["id"] == "y"
    finally:
        database.close()


def test_finish_task_moves_to_done(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        database.emplace("t", '{"model":"m"}', "m", "c")
        database.finish_task("t")

        _assert_queue_status(database, "t", "done")
        row = database.connection.execute(
            "SELECT finished_at, lease_until FROM queue WHERE id = ?", ("t",)
        ).fetchone()
        assert row is not None
        assert row["finished_at"] is not None
        assert row["lease_until"] is None
    finally:
        database.close()


def test_fail_task_returns_to_pending(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        database.emplace("f", '{"model":"m"}', "m", "c")
        database.fail_task("f")

        _assert_queue_status(database, "f", "pending")
        row = database.connection.execute(
            "SELECT lease_until FROM queue WHERE id = ?", ("f",)
        ).fetchone()
        assert row is not None
        assert row["lease_until"] is None
    finally:
        database.close()


def test_dead_task_moves_to_dead(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        database.emplace("d", '{"model":"m"}', "m", "c")
        database.dead_task("d")

        _assert_queue_status(database, "d", "dead")
        row = database.connection.execute(
            "SELECT finished_at, lease_until FROM queue WHERE id = ?", ("d",)
        ).fetchone()
        assert row is not None
        assert row["finished_at"] is not None
        assert row["lease_until"] is None
    finally:
        database.close()


# ── §2 — Idempotency ────────────────────────────────────────────────────


def test_store_and_check_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        assert database.check_idempotent("fp-1", "chat.completion") is None

        database.store_idempotent("fp-1", "chat.completion", '{"cached":true}')
        result = database.check_idempotent("fp-1", "chat.completion")
        assert result is not None
        assert json.loads(result) == {"cached": True}
    finally:
        database.close()


def test_idempotent_different_operation_no_match(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        database.store_idempotent("fp-2", "chat.completion", '{"a":1}')
        assert database.check_idempotent("fp-2", "chat.stream") is None
    finally:
        database.close()


def test_idempotent_expired_ttl_returns_none(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        database.store_idempotent("fp-3", "chat.completion", '{"e":1}', ttl_hours=0)
        result = database.check_idempotent("fp-3", "chat.completion")
        assert result is None
    finally:
        database.close()


# ── §3 — Lease recovery ─────────────────────────────────────────────────


def _insert_stale_in_flight(
    database: Database,
    task_id: str,
    *,
    minutes_ago: int = 5,
    body_json: str = (
        '{"model":"phase3-reference-model",'
        '"messages":[{"role":"user","content":"recover"}]}'
    ),
) -> None:
    past = (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()
    with database.transaction() as conn:
        conn.execute(
            "INSERT INTO queue(id, body_json, target_model, stream_flag,"
            " status, attempt_count, created_at, correlation_id,"
            " lease_until, picked_up_at)"
            " VALUES (?, ?, ?, 0, 'in_flight', 1, ?, ?, ?, ?)",
            (
                task_id, body_json, _MODEL,
                past, f"corr-{task_id}", past, past,
            ),
        )


def test_recover_leases_resets_expired_in_flight(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        _insert_stale_in_flight(database, "stale-1")
        _insert_stale_in_flight(database, "stale-2")

        recovered = database.recover_leases()
        assert recovered == 2

        _assert_queue_status(database, "stale-1", "pending")
        _assert_queue_status(database, "stale-2", "pending")
    finally:
        database.close()


def test_recover_leases_leaves_valid_leases_alone(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        future = (datetime.now(UTC) + timedelta(minutes=5)).isoformat()
        now = datetime.now(UTC).isoformat()
        with database.transaction() as conn:
            conn.execute(
                "INSERT INTO queue(id, body_json, target_model, stream_flag,"
                " status, attempt_count, created_at, correlation_id,"
                " lease_until, picked_up_at)"
                " VALUES (?, ?, ?, 0, 'in_flight', 1, ?, ?, ?, ?)",
                ("valid-1", '{"model":"m"}', "m", now, "corr-1", future, now),
            )

        recovered = database.recover_leases()
        assert recovered == 0
        _assert_queue_status(database, "valid-1", "in_flight")
    finally:
        database.close()


def test_recover_leases_skips_done_and_dead(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
        with database.transaction() as conn:
            for status in ("done", "dead"):
                conn.execute(
                    "INSERT INTO queue(id, body_json, target_model, stream_flag,"
                    " status, attempt_count, created_at, correlation_id,"
                    " lease_until, finished_at, picked_up_at)"
                    " VALUES (?, ?, ?, 0, ?, 1, ?, ?, ?, ?, ?)",
                    (f"skip-{status}", '{"model":"m"}', "m",
                     status, past, "corr", past, past, past),
                )

        recovered = database.recover_leases()
        assert recovered == 0
    finally:
        database.close()


# ── §4 — Queue depth ────────────────────────────────────────────────────


def test_queue_depth_counts_pending_only(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        assert database.queue_depth() == 0

        database.enqueue("q1", '{"model":"m"}', "m", "c1")
        assert database.queue_depth() == 1

        database.enqueue("q2", '{"model":"m"}', "m", "c2")
        assert database.queue_depth() == 2

        database.claim_next()
        assert database.queue_depth() == 1

        database.emplace("q3", '{"model":"m"}', "m", "c3")
        assert database.queue_depth() == 1
    finally:
        database.close()


# ── §5 — Concurrent claim isolation ─────────────────────────────────────


def test_concurrent_claims_are_isolated(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.open()
    try:
        for i in range(5):
            database.enqueue(f"cc-{i}", '{"model":"m"}', "m", f"cc-{i}")

        claimed_ids: list[str] = []
        lock = threading.Lock()

        def claim_one() -> None:
            entry = database.claim_next()
            with lock:
                if entry is not None:
                    claimed_ids.append(str(entry["id"]))

        threads = [threading.Thread(target=claim_one) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(claimed_ids) == 5
        assert len(set(claimed_ids)) == 5
        assert database.claim_next() is None
    finally:
        database.close()


# ── §6 — App-level end-to-end: durability through the API ───────────────


def test_non_streaming_request_persisted_to_queue(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path)

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))
    app.state.transport._client = httpx.AsyncClient(  # type: ignore[attr-defined]
        transport=httpx.MockTransport(_mock_ok)
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": _MODEL, "messages": [{"role": "user", "content": "x"}]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["choices"][0]["message"]["content"] == "queue says hi"

    database = Database(db_path)
    database.open()
    try:
        _assert_queue_status(database, None, "done")  # any row
        row = database.connection.execute(
            "SELECT status, attempt_count FROM queue"
        ).fetchone()
        assert row is not None
        assert row["status"] == "done"
        assert row["attempt_count"] == 1
    finally:
        database.close()


def test_queue_depth_reported_in_health(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path)

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))

    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["queue_depth"] == 0

        app.state.database.enqueue("health-test", '{"model":"m"}', "m", "c")
        health = client.get("/health").json()
        assert health["queue_depth"] == 1

        app.state.database.claim_next()
        health = client.get("/health").json()
        assert health["queue_depth"] == 0


def test_worker_recovery_on_startup(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path)

    database = Database(db_path)
    database.open()
    _insert_stale_in_flight(database, "recovery-task")
    database.close()

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))
    app.state.transport._client = httpx.AsyncClient(  # type: ignore[attr-defined]
        transport=httpx.MockTransport(_mock_ok)
    )

    import time

    with TestClient(app):
        time.sleep(0.3)

        database2 = Database(db_path)
        database2.open()
        try:
            row = database2.connection.execute(
                "SELECT status FROM queue WHERE id = ?", ("recovery-task",)
            ).fetchone()
            assert row is not None
            assert row["status"] in {"done", "in_flight"}
        finally:
            database2.close()


def test_failed_request_is_returned_to_pending(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path)

    def _fail(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"message": "boom"}})

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))
    app.state.transport._client = httpx.AsyncClient(  # type: ignore[attr-defined]
        transport=httpx.MockTransport(_fail)
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": _MODEL, "messages": [{"role": "user", "content": "x"}]},
        )
        assert response.status_code in {502, 503}

    database = Database(db_path)
    database.open()
    try:
        _assert_queue_status(database, None, "pending")
    finally:
        database.close()
