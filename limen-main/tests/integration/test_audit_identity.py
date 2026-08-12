"""Audit-identity contract: one ID per call, end-to-end.

One request must produce one ID that ties together:

- The response header ``X-Request-Id``.
- Every audit event for the call (``events.correlation_id``).
- The durable queue row's correlation column.

Before this fix, the response header was generated independently of the
audit correlation_id, and the non-streaming path did not propagate
``key.claimed``/``key.released`` from the pipeline into the audit log.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import httpx
from fastapi.testclient import TestClient

from tests.fixtures.mock_provider import make_success_response

if TYPE_CHECKING:
    from pathlib import Path

_MODEL = "audit-identity-model"


def _config_text(tmp_path: Path) -> str:
    return (
        '[server]\nhost = "127.0.0.1"\nport = 18320\nlog_level = "warning"\n\n'
        '[database]\npath = "'
        + str(tmp_path / "state.db")
        + '"\n\n'
        '[providers.audit]\nenabled = true\n'
        'base_url = "https://audit.invalid/v1"\npriority = 1\n'
        'limit_scope = "unknown"\naccount_id = "audit-acct"\n'
        f'keys = ["audit-key-1"]\nmodels = ["{_MODEL}"]\ncapabilities = ["chat"]\n'
    )


def _build_test_client(
    tmp_path: Path,
    transport: httpx.MockTransport,
) -> TestClient:
    config_path = tmp_path / "config.toml"
    config_path.write_text(_config_text(tmp_path), encoding="utf-8")
    config_path.chmod(0o600)
    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))
    app.state.database.open()
    app.state.transport._client = httpx.AsyncClient(transport=transport)  # type: ignore[attr-defined]
    return TestClient(app)


def _audit_rows(client: TestClient) -> tuple[tuple[str, str, str], ...]:
    db_path = client.app.state.database.path  # type: ignore[attr-defined]
    with sqlite3.connect(db_path) as conn:
        rows = list(
            conn.execute(
                "SELECT event_type, correlation_id, payload_json "
                "FROM events ORDER BY id ASC"
            )
        )
    return tuple((str(a), str(b), str(c)) for a, b, c in rows)


def _queued_correlation_ids(client: TestClient) -> set[str]:
    db_path = client.app.state.database.path  # type: ignore[attr-defined]
    with sqlite3.connect(db_path) as conn:
        rows = list(
            conn.execute(
                "SELECT DISTINCT correlation_id FROM queue "
                "WHERE correlation_id IS NOT NULL"
            )
        )
    return {str(row[0]) for row in rows}


# ─────────────────────────────────────────────────────────────────────
# §1 — One ID, two paths:
#   response header == audit correlation_id == durable queue row
# ─────────────────────────────────────────────────────────────────────


def test_non_streaming_response_header_pins_one_correlation_id(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda _: make_success_response(model=_MODEL, content="ok")
    )
    client = _build_test_client(tmp_path, transport)
    response = client.post(
        "/v1/chat/completions",
        json={"model": _MODEL, "messages": [{"role": "user", "content": "x"}]},
    )
    assert response.status_code == 200
    header_id = response.headers["x-request-id"]

    audit_corr_ids = {cid for _, cid, _ in _audit_rows(client)}
    assert audit_corr_ids == {header_id}, (
        f"every audit row must cite header id {header_id!r}; got {audit_corr_ids!r}"
    )
    assert header_id in _queued_correlation_ids(client), (
        f"durable queue row must carry the same id {header_id!r}"
    )


def test_streaming_response_header_pins_one_correlation_id(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=(
                b'data: {"id":"chatcmpl-x","object":"chat.completion.chunk",'
                b'"created":1,"model":"' + _MODEL.encode() + b'",'
                b'"choices":[{"index":0,"delta":{"role":"assistant"},'
                b'"finish_reason":"stop"}]}\n\n'
                b"data: [DONE]\n\n"
            ),
        )
    )
    client = _build_test_client(tmp_path, transport)
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": _MODEL,
            "messages": [{"role": "user", "content": "x"}],
            "stream": True,
        },
    ) as response:
        header_id = response.headers.get("x-request-id")
        assert response.status_code == 200
        for _ in response.iter_bytes():
            pass

    assert header_id, "X-Request-Id must be on streaming responses"
    audit_corr_ids = {cid for _, cid, _ in _audit_rows(client)}
    assert audit_corr_ids == {header_id}, (
        f"every audit row must cite header id {header_id!r} on streaming; "
        f"got {audit_corr_ids!r}"
    )


# ─────────────────────────────────────────────────────────────────────
# §2 — Pipeline key events reach the audit log on every successful call
# ─────────────────────────────────────────────────────────────────────


def test_pipeline_emits_key_claimed_and_released_under_request_correlation_id(
    tmp_path: Path,
) -> None:
    transport = httpx.MockTransport(
        lambda _: make_success_response(model=_MODEL, content="ok")
    )
    client = _build_test_client(tmp_path, transport)
    response = client.post(
        "/v1/chat/completions",
        json={"model": _MODEL, "messages": [{"role": "user", "content": "x"}]},
    )
    assert response.status_code == 200
    header_id = response.headers["x-request-id"]

    by_type: dict[str, list[dict[str, object]]] = {}
    for event_type, cid, payload in _audit_rows(client):
        if cid == header_id and event_type in {"key.claimed", "key.released"}:
            by_type.setdefault(event_type, []).append(json.loads(payload))

    assert "key.claimed" in by_type, (
        f"missing key.claimed under corr_id={header_id!r}; got {list(by_type)!r}"
    )
    assert "key.released" in by_type, (
        f"missing key.released under corr_id={header_id!r}; got {list(by_type)!r}"
    )
    success_releases = [
        p for p in by_type["key.released"] if p.get("failure_type") == "success"
    ]
    assert success_releases, (
        f"key.released must report failure_type='success' after a 200 response; "
        f"got: {by_type['key.released']!r}"
    )
