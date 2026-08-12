"""Integration tests for the SSE Live-Visualizer endpoint."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from limen.api.routes.public import live_visualizer

if TYPE_CHECKING:
    from pathlib import Path


def _build_app(tmp_path: Path, *, model: str = "lv-test-model"):
    """Create a minimal LIMEN app with a mock provider for visualizer tests."""
    config_text = f"""
[server]
host = "127.0.0.1"
port = 18300
worker_count = 1
log_level = "warning"
max_body_size_kb = 256

[database]
path = "{tmp_path / "state.db"}"

[providers.bogus]
enabled = true
base_url = "https://provider.invalid/v1"
priority = 10
limit_scope = "unknown"
account_id = "lv-smoke"
keys = ["smoke-test-key"]
models = ["{model}"]
capabilities = ["chat"]
"""
    config_path = tmp_path / "config.toml"
    config_path.write_text(config_text, encoding="utf-8")
    config_path.chmod(0o600)

    from limen.api.app import create_app
    from limen.config import load_config

    config = load_config(config_path)
    app = create_app(config)
    app.state.database.open()
    return app


def _parse_sse_data(raw: str | bytes) -> list[dict[str, object]]:
    """Parse SSE data lines from raw bytes or the direct generator strings."""
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    events: list[dict[str, object]] = []
    for record in text.split("\n\n"):
        record = record.strip()
        if not record:
            continue
        for line in record.splitlines():
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                data = line[5:].strip()
                if data:
                    events.append(json.loads(data))
    return events




# ── §1 Connection and keepalive ──


def test_visualizer_stream_opens_and_receives_keepalive(tmp_path: Path) -> None:
    """SSE connection opens and emits an initial ``:ok`` keepalive comment."""
    app = _build_app(tmp_path)
    with TestClient(app) as client:
        with client.stream("GET", "/v1/_internal/live-visualizer") as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            first = next(resp.iter_bytes())
            assert b":ok" in first


# ── §2 Event delivery ──


@pytest.mark.asyncio
async def test_visualizer_delivers_pushed_events(tmp_path: Path) -> None:
    """Events pushed into ``ui_clients`` appear as SSE data lines."""
    app = _build_app(tmp_path)
    request = Request({"type": "http", "app": app})
    response = await live_visualizer(request)
    stream = response.body_iterator
    assert ":ok" in await anext(stream)

    event_a = {"type": "request.enqueued", "request_id": "abc", "ts": 1.0}
    event_b = {"type": "worker.claimed", "request_id": "abc", "task_id": "42", "ts": 1.1}
    queue = next(iter(app.state.ui_clients))
    queue.put_nowait(event_a)
    queue.put_nowait(event_b)
    events_received = _parse_sse_data(await anext(stream)) + _parse_sse_data(await anext(stream))
    await stream.aclose()

    types = [e["type"] for e in events_received]
    assert "request.enqueued" in types, f"events received: {events_received}"
    assert "worker.claimed" in types


# ── §3 Multiple clients ──


@pytest.mark.asyncio
async def test_visualizer_multiple_clients_receive_same_events(tmp_path: Path) -> None:
    """Two simultaneous SSE connections both receive pushed events."""
    app = _build_app(tmp_path)
    request_a = Request({"type": "http", "app": app})
    request_b = Request({"type": "http", "app": app})
    response_a = await live_visualizer(request_a)
    response_b = await live_visualizer(request_b)
    stream_a = response_a.body_iterator
    stream_b = response_b.body_iterator
    assert ":ok" in await anext(stream_a)
    assert ":ok" in await anext(stream_b)

    event = {"type": "request.enqueued", "request_id": "multi", "ts": 2.0}
    for queue in app.state.ui_clients:
        queue.put_nowait(event)
    events_a = _parse_sse_data(await anext(stream_a))
    events_b = _parse_sse_data(await anext(stream_b))
    await stream_a.aclose()
    await stream_b.aclose()

    assert len(events_a) == 1, "client A received no events"
    assert len(events_b) == 1, "client B received no events"
    assert events_a[0]["request_id"] == "multi"
    assert events_b[0]["request_id"] == "multi"


# ── §4 Disconnect cleanup ──


def test_visualizer_removes_client_on_disconnect(tmp_path: Path) -> None:
    """Disconnected clients are removed from ``ui_clients``."""
    app = _build_app(tmp_path)

    with TestClient(app) as client:
        with client.stream("GET", "/v1/_internal/live-visualizer") as resp:
            next(resp.iter_bytes())

    assert len(app.state.ui_clients) == 0


# ── §5 Event data integrity ──


@pytest.mark.asyncio
async def test_visualizer_events_preserve_all_fields(tmp_path: Path) -> None:
    """SSE events pass through all fields including nested extras."""
    app = _build_app(tmp_path)
    request = Request({"type": "http", "app": app})
    response = await live_visualizer(request)
    stream = response.body_iterator
    assert ":ok" in await anext(stream)

    event = {
        "type": "provider.dispatched",
        "request_id": "r1",
        "provider": "groq",
        "deployment": "groq#0",
        "key_index": 1,
        "ts": 3.0,
    }
    next(iter(app.state.ui_clients)).put_nowait(event)
    events_received = _parse_sse_data(await anext(stream))
    await stream.aclose()

    assert len(events_received) == 1, (
        f"expected 1 event, got {len(events_received)}: {events_received}"
    )
    e = events_received[0]
    assert e["type"] == "provider.dispatched"
    assert e["provider"] == "groq"
    assert e["deployment"] == "groq#0"
    assert e["key_index"] == 1
