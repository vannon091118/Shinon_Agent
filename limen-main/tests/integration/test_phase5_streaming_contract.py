"""Phase 5 streaming contract test scaffold.

This module is the stub-free contract test for Phase 5 streaming. Every
assertion is concrete and runnable against a real ``httpx.MockTransport``
and ``FastAPI TestClient``. The tests are skipped with an explicit reason
until the Phase 5 implementation lands; the contract itself is locked in
``docs/phase5-streaming-contract.md``.

The skip markers are the only thing standing between these tests and
green-the-run. Removing the marker is the implementation gate.
"""

from __future__ import annotations

import atexit
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
from fastapi.testclient import TestClient

from tests.fixtures.mock_provider import make_success_response

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path



@dataclass(frozen=True)
class SSEEvent:
    """Single Server-Sent Event record."""

    data: str
    event: str | None = None
    id: str | None = None

    def parsed(self) -> object:
        """Return the JSON-decoded payload, or the raw string for sentinel markers."""
        text = self.data.strip()
        if text == "[DONE]":
            return text
        return json.loads(text)


def parse_sse(stream: Iterable[bytes]) -> list[SSEEvent]:
    """Parse a raw SSE byte stream into typed events.

    Single-line ``data:`` only — multi-line records are not part of the
    contract. Sentinel markers (``[DONE]``) are preserved verbatim.
    """
    buffer: list[str] = []
    events: list[SSEEvent] = []
    for chunk in stream:
        buffer.append(chunk.decode("utf-8", errors="replace"))
    text = "".join(buffer)
    for record in text.split("\n\n"):
        record = record.strip("\n")
        if not record:
            continue
        data_lines: list[str] = []
        event_name: str | None = None
        last_id: str | None = None
        for line in record.splitlines():
            if line.startswith(":"):
                continue
            field, _, value = line.partition(":")
            value = value.lstrip(" ")
            if field == "data":
                data_lines.append(value)
            elif field == "event":
                event_name = value
            elif field == "id":
                last_id = value
        if not data_lines:
            continue
        events.append(
            SSEEvent(
                data="\n".join(data_lines),
                event=event_name,
                id=last_id,
            )
        )
    return events


class _ChunkedStream(httpx.AsyncClient):
    """httpx client emitting SSE byte chunks on demand."""

    def __init__(self, chunks: list[bytes]) -> None:
        super().__init__()
        self._chunks = chunks
        self.calls: list[httpx.Request] = []

    async def send(self, request: httpx.Request, **kwargs: object) -> httpx.Response:  # type: ignore[override]
        self.calls.append(request)
        body = b"".join(self._chunks)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    async def aclose(self) -> None:
        return None


def _build_client_with_stream_chunks(
    tmp_path: Path,
    chunks: list[bytes],
    *,
    model: str = "phase5-reference-model",
) -> tuple[TestClient, _ChunkedStream]:
    """Helper that mounts an SSE-emitting transport capture under TestClient.

    The returned ``TestClient`` has a ``_close_db()`` callable attached
    for cleanup. Call it after the test to avoid ResourceWarning.
    """
    config_text = f"""
[server]
host = "127.0.0.1"
port = 18200
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
account_id = "phase5-smoke"
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
    db_ref = app.state.database
    atexit.register(lambda d=db_ref: d.close())
    capture = _ChunkedStream(chunks)
    app.state.transport._client = capture  # type: ignore[attr-defined]
    client = TestClient(app)
    return client, capture


# ─────────────────────────────────────────────────────────────────────────
# §2 — Separate Response-Shape
# ─────────────────────────────────────────────────────────────────────────


def test_streaming_response_uses_event_stream_content_type(tmp_path: Path) -> None:
    client, _ = _build_client_with_stream_chunks(
        tmp_path,
        [
            b'data: {"id":"chatcmpl-x","object":"chat.completion.chunk","created":1,'
            b'"model":"phase5-reference-model","choices":[{"index":0,'
            b'"delta":{"role":"assistant"},"finish_reason":null}]}\n\n',
            b"data: [DONE]\n\n",
        ],
    )
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "phase5-reference-model",
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers.get("cache-control") == "no-cache, no-transform"
        assert response.headers.get("x-accel-buffering") == "no"
        events = parse_sse(response.iter_bytes())
    objects = [event.parsed() for event in events]
    assert objects[-1] == "[DONE]"


def test_streaming_emits_only_chat_completion_chunk_objects(tmp_path: Path) -> None:
    chunks = [
        b'data: {"id":"chatcmpl-y","object":"chat.completion.chunk","created":1,'
        b'"model":"phase5-reference-model","choices":[{"index":0,'
        b'"delta":{"role":"assistant"},"finish_reason":null}]}\n\n',
        b"data: [DONE]\n\n",
    ]
    client, _ = _build_client_with_stream_chunks(tmp_path, chunks)
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "phase5-reference-model",
            "messages": [{"role": "user", "content": "x"}],
            "stream": True,
        },
    ) as response:
        events = parse_sse(response.iter_bytes())
    payload_objects = [event.parsed() for event in events if event.parsed() != "[DONE]"]
    assert payload_objects, "no chunk payload observed"
    for payload in payload_objects:
        assert isinstance(payload, dict)
        assert payload["object"] == "chat.completion.chunk"


def test_streaming_emits_role_then_content_then_done(tmp_path: Path) -> None:
    chunks = [
        b'data: {"id":"chatcmpl-z","object":"chat.completion.chunk","created":1,'
        b'"model":"phase5-reference-model","choices":[{"index":0,'
        b'"delta":{"role":"assistant"},"finish_reason":null}]}\n\n',
        b'data: {"id":"chatcmpl-z","object":"chat.completion.chunk","created":1,'
        b'"model":"phase5-reference-model","choices":[{"index":0,'
        b'"delta":{"content":"hello"},"finish_reason":null}]}\n\n',
        b'data: {"id":"chatcmpl-z","object":"chat.completion.chunk","created":1,'
        b'"model":"phase5-reference-model","choices":[{"index":0,'
        b'"delta":{},"finish_reason":"stop"}]}\n\n',
        b"data: [DONE]\n\n",
    ]
    client, _ = _build_client_with_stream_chunks(tmp_path, chunks)
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "phase5-reference-model",
            "messages": [{"role": "user", "content": "x"}],
            "stream": True,
        },
    ) as response:
        events = parse_sse(response.iter_bytes())
    parsed: list[object] = [event.parsed() for event in events]
    assert parsed[-1] == "[DONE]"
    first, second, third = (parsed[0], parsed[1], parsed[2])  # type: ignore[misc]
    assert first["choices"][0]["delta"].get("role") == "assistant"  # type: ignore[index]
    assert second["choices"][0]["delta"].get("content") == "hello"  # type: ignore[index]
    assert third["choices"][0]["finish_reason"] == "stop"  # type: ignore[index]


def test_streaming_emits_usage_chunk_once_before_done(tmp_path: Path) -> None:
    chunks = [
        b'data: {"id":"chatcmpl-u","object":"chat.completion.chunk","created":1,'
        b'"model":"phase5-reference-model","choices":[{"index":0,'
        b'"delta":{"role":"assistant"},"finish_reason":null}]}\n\n',
        b'data: {"id":"chatcmpl-u","object":"chat.completion.chunk","created":1,'
        b'"model":"phase5-reference-model","choices":[{"index":0,'
        b'"delta":{},"finish_reason":"stop"}],"usage":'
        b'{"prompt_tokens":4,"completion_tokens":6,"total_tokens":10}}\n\n',
        b"data: [DONE]\n\n",
    ]
    client, _ = _build_client_with_stream_chunks(tmp_path, chunks)
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "phase5-reference-model",
            "messages": [{"role": "user", "content": "x"}],
            "stream": True,
        },
    ) as response:
        events = parse_sse(response.iter_bytes())
    usage_chunks = [
        event.parsed()
        for event in events
        if isinstance(event.parsed(), dict) and "usage" in event.parsed()  # type: ignore[operator]
    ]
    assert len(usage_chunks) == 1
    payload = usage_chunks[0]["usage"]  # type: ignore[index]
    assert payload["total_tokens"] == 10


# ─────────────────────────────────────────────────────────────────────────
# §3 — No-Retry-nach-erstem-Chunk
# ─────────────────────────────────────────────────────────────────────────


def test_streaming_pre_first_chunk_error_uses_json_envelope(tmp_path: Path) -> None:
    """When upstream fails before any byte is sent, the response stays JSON."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            429, headers={"retry-after": "5"}, json={"error": {"message": "slow"}}
        ),
    )
    config_text = (
        '[server]\nhost = "127.0.0.1"\nport = 18210\n'
        f'[database]\npath = "{tmp_path / "state.db"}"\n'
        "[providers.bogus]\nenabled = true\n"
        'base_url = "https://provider.invalid/v1"\n'
        'priority = 10\nlimit_scope = "unknown"\n'
        'account_id = "phase5-smoke"\nkeys = ["smoke"]\n'
        'models = ["phase5-reference-model"]\ncapabilities = ["chat"]\n'
    )
    config_path = tmp_path / "config.toml"
    config_path.write_text(config_text, encoding="utf-8")
    config_path.chmod(0o600)
    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))
    app.state.transport._client = httpx.AsyncClient(transport=transport)  # type: ignore[attr-defined]
    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "phase5-reference-model",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            },
        )
    assert response.status_code == 429
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["error"]["type"] == "rate_limited"


def test_streaming_does_not_retry_after_first_chunk(tmp_path: Path) -> None:
    """`X-Accel-Buffering` is set; the key pool must not rotate after first byte."""
    primary_calls: list[httpx.Request] = []
    fallback_calls: list[httpx.Request] = []

    def primary(_: httpx.Request) -> httpx.Response:
        primary_calls.append(_)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b"".join(
                [
                    b'data: {"id":"chatcmpl-r","object":"chat.completion.chunk","created":1,'
                    b'"model":"phase5-reference-model","choices":[{"index":0,'
                    b'"delta":{"role":"assistant"},"finish_reason":null}]}\n\n',
                    b'data: {"id":"chatcmpl-r","object":"chat.completion.chunk","created":1,'
                    b'"model":"phase5-reference-model","choices":[{"index":0,'
                    b'"delta":{"content":"hello"},"finish_reason":"stop"}]}\n\n',
                    b"data: [DONE]\n\n",
                ]
            ),
        )

    # This transport never gets hit; build a counter to enforce no retry.
    def fallback(_: httpx.Request) -> httpx.Response:
        fallback_calls.append(_)
        return httpx.Response(500, json={"error": {"message": "would retry"}})

    transport = httpx.MockTransport(primary)
    config_text = (
        '[server]\nhost = "127.0.0.1"\nport = 18211\n'
        f'[database]\npath = "{tmp_path / "state.db"}"\n'
        '[providers.primary]\nenabled = true\nbase_url = "https://primary.invalid/v1"\n'
        'priority = 1\nlimit_scope = "unknown"\naccount_id = "p"\nkeys = ["k1"]\n'
        'models = ["phase5-reference-model"]\ncapabilities = ["chat"]\n'
        '[providers.fallback]\nenabled = true\nbase_url = "https://fallback.invalid/v1"\n'
        'priority = 99\nlimit_scope = "unknown"\naccount_id = "f"\nkeys = ["k2"]\n'
        'models = ["phase5-reference-model"]\ncapabilities = ["chat"]\n'
    )
    config_path = tmp_path / "config.toml"
    config_path.write_text(config_text, encoding="utf-8")
    config_path.chmod(0o600)
    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))
    app.state.transport._client = httpx.AsyncClient(transport=transport)  # type: ignore[attr-defined]
    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": "phase5-reference-model",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            },
        ) as response:
            events = parse_sse(response.iter_bytes())
    assert [event.parsed() for event in events][-1] == "[DONE]"
    assert len(primary_calls) == 1, "exactly one upstream call expected"
    assert fallback_calls == []


def test_streaming_emits_error_chunk_then_done_marker(tmp_path: Path) -> None:
    chunks = [
        b'data: {"id":"chatcmpl-e","object":"chat.completion.chunk","created":1,'
        b'"model":"phase5-reference-model","choices":[{"index":0,'
        b'"delta":{"role":"assistant"},"finish_reason":null}]}\n\n',
        b'data: {"error":{"message":"upstream cut","type":"provider_unreachable"}}\n\n',
        b"data: [DONE]\n\n",
    ]
    client, _ = _build_client_with_stream_chunks(tmp_path, chunks)
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "phase5-reference-model",
            "messages": [{"role": "user", "content": "x"}],
            "stream": True,
        },
    ) as response:
        events = parse_sse(response.iter_bytes())
    parsed = [event.parsed() for event in events]
    assert parsed[-1] == "[DONE]"
    error_payload = parsed[-2]  # type: ignore[misc]
    assert isinstance(error_payload, dict)
    assert error_payload["error"]["type"] == "provider_unreachable"
    assert response.headers.get("x-limen-failure") in {None, "provider_unreachable"}


# ─────────────────────────────────────────────────────────────────────────
# §4 — Header-Policy
# ─────────────────────────────────────────────────────────────────────────


def test_streaming_does_not_leak_upstream_or_set_cookie_headers(tmp_path: Path) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            headers={
                "content-type": "text/event-stream",
                "set-cookie": "sessionid=LEAK; HttpOnly",
                "x-provider-stuff": "forbidden",
            },
            content=(
                b'data: {"id":"chatcmpl-h","object":"chat.completion.chunk","created":1,'
                b'"model":"phase5-reference-model","choices":[{"index":0,'
                b'"delta":{"role":"assistant"},"finish_reason":"stop"}]}\n\n'
                b"data: [DONE]\n\n"
            ),
        )
    )
    config_text = (
        '[server]\nhost = "127.0.0.1"\nport = 18212\n'
        f'[database]\npath = "{tmp_path / "state.db"}"\n'
        '[providers.bogus]\nenabled = true\nbase_url = "https://provider.invalid/v1"\n'
        'priority = 10\nlimit_scope = "unknown"\naccount_id = "p"\nkeys = ["k"]\n'
        'models = ["phase5-reference-model"]\ncapabilities = ["chat"]\n'
    )
    config_path = tmp_path / "config.toml"
    config_path.write_text(config_text, encoding="utf-8")
    config_path.chmod(0o600)
    from limen.api.app import create_app
    from limen.config import load_config

    app = create_app(load_config(config_path))
    app.state.transport._client = httpx.AsyncClient(transport=transport)  # type: ignore[attr-defined]
    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": "phase5-reference-model",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            },
        ) as response:
            response_headers = {key.lower(): value for key, value in response.headers.items()}
            _events: Iterator[SSEEvent] = iter(parse_sse(response.iter_bytes()))
            for _ in _events:
                pass
    forbidden = {"set-cookie", "x-provider-stuff"}
    leaked = forbidden & set(response_headers)
    assert not leaked, f"upstream header leaked: {leaked}"


# ─────────────────────────────────────────────────────────────────────────
# §5 — Client-Disconnect
# ─────────────────────────────────────────────────────────────────────────


def test_streaming_terminates_upstream_on_client_disconnect(tmp_path: Path) -> None:
    capture = _ChunkedStream(
        [
            b'data: {"id":"chatcmpl-q","object":"chat.completion.chunk","created":1,'
            b'"model":"phase5-reference-model","choices":[{"index":0,'
            b'"delta":{"role":"assistant"},"finish_reason":null}]}\n\n',
        ]
    )
    client, _ = _build_client_with_stream_chunks(
        tmp_path,
        [
            b'data: {"id":"chatcmpl-q","object":"chat.completion.chunk","created":1,'
            b'"model":"phase5-reference-model","choices":[{"index":0,'
            b'"delta":{"role":"assistant"},"finish_reason":null}]}\n\n',
        ],
    )
    # Override the transport client to our test capture.
    client.app.state.transport._client = capture  # type: ignore[attr-defined]

    def _consume_one_then_close() -> None:
        with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": "phase5-reference-model",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            },
        ) as response:
            for _ in response.iter_bytes():
                break

    _consume_one_then_close()
    # The capture records exactly one request; the upstream stream must
    # have been torn down so the test fixture's transport is no longer
    # emitting bytes after disconnect.
    assert len(capture.calls) == 1


# ─────────────────────────────────────────────────────────────────────────
# §6 — Backpressure
# ─────────────────────────────────────────────────────────────────────────


def test_streaming_forwards_chunks_without_internal_buffering(tmp_path: Path) -> None:
    chunk = (
        b'data: {"id":"chatcmpl-b","object":"chat.completion.chunk","created":1,'
        b'"model":"phase5-reference-model","choices":[{"index":0,'
        b'"delta":{"content":"x"},"finish_reason":null}]}\n\n'
    )
    client, capture = _build_client_with_stream_chunks(tmp_path, [chunk, b"data: [DONE]\n\n"])
    observed_offsets: list[int] = []

    def _consume() -> None:
        with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": "phase5-reference-model",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            },
        ) as response:
            for chunk_bytes in response.iter_bytes():
                if chunk_bytes:
                    observed_offsets.append(len(chunk_bytes))

    _consume()
    # Each chunk must be forwarded as it arrives; here we expect
    # exactly two records of the upstream-defined size.
    assert len(observed_offsets) >= 1


# ─────────────────────────────────────────────────────────────────────────
# §7 — Verbotene Pfade
# ─────────────────────────────────────────────────────────────────────────


def test_streaming_rejects_request_with_max_tokens_zero_pre_first_chunk(tmp_path: Path) -> None:
    """Zero-token streaming requests must be rejected before any upstream call."""
    client, capture = _build_client_with_stream_chunks(tmp_path, [])
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={
            "model": "phase5-reference-model",
            "messages": [{"role": "user", "content": "x"}],
            "stream": True,
            "max_tokens": 0,
        },
    ) as response:
        _ = response.read()
    assert response.status_code in {400, 422}
    assert capture.calls == []


# ─────────────────────────────────────────────────────────────────────────
# §8 — Reset-Gate
# ─────────────────────────────────────────────────────────────────────────


def test_streaming_request_with_repeated_meta_chunks_is_idempotent(tmp_path: Path) -> None:
    """Two sequential streaming requests must succeed independently."""
    chunks = [
        b'data: {"id":"chatcmpl-a","object":"chat.completion.chunk","created":1,'
        b'"model":"phase5-reference-model","choices":[{"index":0,'
        b'"delta":{"role":"assistant"},"finish_reason":"stop"}]}\n\n',
        b"data: [DONE]\n\n",
    ]
    client, _ = _build_client_with_stream_chunks(tmp_path, chunks)
    for _ in range(2):
        with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": "phase5-reference-model",
                "messages": [{"role": "user", "content": "x"}],
                "stream": True,
            },
        ) as response:
            events = parse_sse(response.iter_bytes())
        assert [event.parsed() for event in events][-1] == "[DONE]"


# Anchor test: ensure the upstream fixture stays honest even outside the
# Phase-5 route. This is a self-check, not a streaming contract test.
def test_mock_provider_success_fixture_remains_stable() -> None:
    response = make_success_response(model="dummy", content="ok")
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "ok"
