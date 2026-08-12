"""Phase 4 audit, heartbeat, and SSE contract tests.

Covers:
- Audit auth: 401 without token, 200 with valid token
- Internal status: worker heartbeat table, activity state
- SSE events: stream delivers events with correlation_id
- Heartbeat: worker writes heartbeat rows
- Reaper: detects dead workers, recovers tasks
- Typed events: task.started/completed/failed contain correlation_id
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import httpx
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from pathlib import Path


_MODEL = "phase4-ref"
_TOKEN = "audit-secret-phase4-test"  # noqa: S105


def _write_config(path: Path, db_path: Path, *, audit_token: str = "") -> None:
    token_block = f'audit_token_secret = "{audit_token}"' if audit_token else ""
    path.write_text(
        f"""[server]
host = "127.0.0.1"
port = 18260
worker_count = 1
log_level = "warning"
max_body_size_kb = 256

[database]
path = "{db_path}"

[audit]
{token_block}

[providers.bogus]
enabled = true
base_url = "https://audit.invalid/v1"
priority = 10
limit_scope = "unknown"
account_id = "phase4"
keys = ["audit-key"]
models = ["{_MODEL}"]
capabilities = ["chat"]
""",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _mock_ok(_: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-phase4-001",
            "object": "chat.completion",
            "created": 1_700_000_000,
            "model": _MODEL,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "phase 4"},
                    "finish_reason": "stop",
                }
            ],
        },
    )


def _auth_headers() -> dict[str, str]:
    return {"X-Proxy-Audit-Key": _TOKEN}


# ── §1 — Audit auth ────────────────────────────────────────────────────


def test_internal_status_rejects_without_token(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path, audit_token=_TOKEN)

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))

    with TestClient(app) as client:
        resp = client.get("/v1/_internal/status")
        assert resp.status_code == 401

        resp = client.get("/v1/_internal/status", headers={"X-Proxy-Audit-Key": "wrong"})
        assert resp.status_code == 401


def test_internal_status_accepts_valid_token(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path, audit_token=_TOKEN)

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))

    with TestClient(app) as client:
        resp = client.get("/v1/_internal/status", headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert "activity" in body
        assert "workers" in body
        assert body["activity"]["state"] in {"active", "degraded"}


def test_internal_status_401_when_audit_not_configured(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path, audit_token="")

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))

    with TestClient(app) as client:
        resp = client.get("/v1/_internal/status", headers=_auth_headers())
        assert resp.status_code == 401


# ── §2 — Internal status content ──────────────────────────────────────


def test_internal_status_includes_worker_heartbeat(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path, audit_token=_TOKEN)

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))

    with TestClient(app) as client:
        # Wait for worker to heartbeat
        time.sleep(0.2)
        resp = client.get("/v1/_internal/status", headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["workers"]) >= 1
        worker = body["workers"][0]
        assert "worker_id" in worker
        assert "last_beat_at" in worker
        assert worker["state"] in {"idle", "busy"}


# ── §3 — Typed events via API ─────────────────────────────────────────


def test_task_events_emitted_on_successful_request(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path, audit_token=_TOKEN)

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))
    app.state.transport._client = httpx.AsyncClient(  # type: ignore[attr-defined]
        transport=httpx.MockTransport(_mock_ok)
    )

    with TestClient(app) as client:
        # Do a successful request
        resp = client.post(
            "/v1/chat/completions",
            json={"model": _MODEL, "messages": [{"role": "user", "content": "hi"}]},
        )
        assert resp.status_code == 200

        # Check events in the DB
        rows = app.state.database.connection.execute(
            "SELECT event_type, payload_json, correlation_id FROM events"
            " WHERE event_type IN ('task.started', 'task.completed')"
            " ORDER BY id"
        ).fetchall()
        event_types = [row["event_type"] for row in rows]
        assert "task.started" in event_types
        assert "task.completed" in event_types

        # Verify correlation_id is present
        for row in rows:
            assert row["correlation_id"], f"missing correlation_id in {row['event_type']}"

        # Verify task.completed payload shape
        completed = [r for r in rows if r["event_type"] == "task.completed"]
        assert completed
        payload = json.loads(completed[0]["payload_json"])
        assert "provider_deployment" in payload
        assert "duration_seconds" in payload


def test_task_failed_event_emitted_on_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path, audit_token=_TOKEN)

    def _fail(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": {"message": "down"}})

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))
    app.state.transport._client = httpx.AsyncClient(  # type: ignore[attr-defined]
        transport=httpx.MockTransport(_fail)
    )

    with TestClient(app) as client:
        resp = client.post(
            "/v1/chat/completions",
            json={"model": _MODEL, "messages": [{"role": "user", "content": "x"}]},
        )
        assert resp.status_code in {502, 503}

        rows = app.state.database.connection.execute(
            "SELECT event_type, payload_json, correlation_id FROM events"
            " WHERE event_type IN ('task.started', 'task.failed')"
            " ORDER BY id"
        ).fetchall()
        event_types = [row["event_type"] for row in rows]
        assert "task.started" in event_types
        assert "task.failed" in event_types

        failed = [r for r in rows if r["event_type"] == "task.failed"]
        assert failed
        payload = json.loads(failed[0]["payload_json"])
        assert "failure_type" in payload
        assert "correlation_id" in payload


# ── §4 — SSE events endpoint ──────────────────────────────────────────


def test_sse_events_endpoint_requires_auth(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path, audit_token=_TOKEN)

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))

    with TestClient(app) as client:
        resp = client.get("/v1/_internal/events")
        assert resp.status_code == 401

        resp = client.get("/v1/_internal/events", headers=_auth_headers())
        assert resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        assert "text/event-stream" in ct
        assert "no-cache" in resp.headers.get("cache-control", "")


def test_events_table_stores_typed_events(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path, audit_token=_TOKEN)

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))

    with TestClient(app):
        app.state.database.write_event(
            "test.event",
            {"key": "value"},
            correlation_id="corr-test",
        )

        row = app.state.database.connection.execute(
            "SELECT event_type, payload_json, correlation_id FROM events"
            " WHERE event_type = 'test.event'"
        ).fetchone()
        assert row is not None
        assert row["correlation_id"] == "corr-test"
        payload = json.loads(row["payload_json"])
        assert payload["key"] == "value"


def test_read_events_returns_sse_fields(tmp_path: Path) -> None:
    """read_events() returns id, event_type, payload_json, timestamp, correlation_id."""
    from limen.persistence.database import Database

    db = Database(tmp_path / "state.db")
    db.open()
    db.write_event("task.started", {"id": "t1"}, correlation_id="corr-1")
    db.write_event("task.completed", {"id": "t2"}, correlation_id="corr-2")

    rows = db.read_events(since_id=0, limit=10)
    assert len(rows) == 2
    assert rows[0]["event_type"] == "task.started"
    assert rows[0]["correlation_id"] == "corr-1"
    assert rows[1]["event_type"] == "task.completed"
    assert rows[1]["correlation_id"] == "corr-2"
    for row in rows:
        assert "timestamp" in row
        assert "payload_json" in row
    db.close()


def test_redact_key_empty_produces_star_placeholder() -> None:
    """_redact_key('') returns '***' without crashing."""
    from limen.routing.pipeline import _redact_key

    assert _redact_key("") == "***"



# ── §5 — Heartbeat ────────────────────────────────────────────────────


def test_worker_heartbeat_writes_to_db(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path, audit_token=_TOKEN)

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))

    with TestClient(app):
        # Wait for heartbeat to fire (interval=5s in prod, but worker
        # writes initial beat on start)
        time.sleep(0.3)
        rows = app.state.database.connection.execute(
            "SELECT worker_id, state, beat_count FROM worker_heartbeats"
        ).fetchall()
        assert len(rows) >= 1
        worker = rows[0]
        assert worker["state"] in {"idle", "busy", "dead"}
        assert worker["beat_count"] >= 1


# ── §6 — Reaper ────────────────────────────────────────────────────────


def test_reaper_marks_stale_workers_as_dead(tmp_path: Path) -> None:
    """reap_dead_workers() at DB level marks stale workers dead."""
    from limen.persistence.database import Database

    db = Database(tmp_path / "state.db")
    db.open()
    past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    db.connection.execute(
        "INSERT INTO worker_heartbeats(worker_id, last_beat_at, state, beat_count)"
        " VALUES (?, ?, 'busy', 10)",
        ("stale-w", past),
    )
    db.connection.commit()

    dead = db.reap_dead_workers(stale_seconds=10)
    assert "stale-w" in dead

    row = db.connection.execute(
        "SELECT state FROM worker_heartbeats WHERE worker_id = ?", ("stale-w",)
    ).fetchone()
    assert row is not None
    assert row["state"] == "dead"
    db.close()


def test_reaper_recovers_task_to_pending(tmp_path: Path) -> None:
    """reap_dead_workers() resets in_flight task to pending for dead worker."""
    from limen.persistence.database import Database

    db = Database(tmp_path / "state.db")
    db.open()
    past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO queue(id, body_json, target_model, stream_flag,"
            " status, attempt_count, created_at, correlation_id, lease_until)"
            " VALUES (?, ?, ?, 0, 'in_flight', 1, ?, ?, ?)",
            ("reap-task", '{"model":"m"}', "m", past, "corr-reap", past),
        )
        conn.execute(
            "INSERT INTO worker_heartbeats(worker_id, last_beat_at, state,"
            " beat_count, current_task_id)"
            " VALUES (?, ?, 'busy', 10, ?)",
            ("stale-w", past, "reap-task"),
        )

    dead = db.reap_dead_workers(stale_seconds=10)
    assert "stale-w" in dead

    row = db.connection.execute(
        "SELECT status, lease_until FROM queue WHERE id = ?", ("reap-task",)
    ).fetchone()
    assert row is not None
    assert row["status"] == "pending"
    assert row["lease_until"] is None
    db.close()


# ── §7 — Public API stays audit-free ──────────────────────────────────


def test_public_endpoint_has_no_audit_headers(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    _write_config(config_path, db_path, audit_token=_TOKEN)

    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))

    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "X-Proxy-Audit-Key" not in resp.headers
        assert "x-proxy-audit-key" not in dict(resp.headers)
