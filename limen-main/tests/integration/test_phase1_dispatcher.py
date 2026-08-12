"""Phase 1 single-provider dispatcher and resilience gates."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from pathlib import Path

from limen.api.app import create_app
from limen.config import load_config
from tests.fixtures.mock_provider import (
    make_error_response,
    make_success_response,
)


def _write_config(
    path: Path,
    *,
    enabled: bool,
    base_url: str | None,
    models: list[str],
    api_key: str | None,
) -> None:
    lines = []
    lines.append("[database]")
    lines.append(f'path = "{path.parent / "state.db"}"')
    lines.append("[providers.primary]")
    lines.append(f"enabled = {str(enabled).lower()}")
    if base_url is not None:
        lines.append(f'base_url = "{base_url}"')
    if api_key is not None:
        lines.append(f"keys = [\"{api_key}\"]")
    else:
        lines.append("keys = []")
    lines.append(f"models = {models!r}")
    lines.append('capabilities = ["chat"]')
    path.write_text("\n".join(lines), encoding="utf-8")
    path.chmod(0o600)


def _build_app_with_mock(
    tmp_path: Path,
    *,
    transport_handler: _Recorder,
    enabled: bool,
    base_url: str | None,
    models: list[str],
    api_key: str | None,
) -> TestClient:
    config_path = tmp_path / "config.toml"
    _write_config(
        config_path,
        enabled=enabled,
        base_url=base_url,
        models=models,
        api_key=api_key,
    )
    _ = base_url  # silence unused-override warning while keeping the public signature.
    config = load_config(config_path)
    app = create_app(config)

    class _ProviderClient(httpx.AsyncClient):
        async def post(self, url, **kwargs):
            request = httpx.Request("POST", url, **kwargs)
            response = transport_handler.handle(request)
            return response

        async def aclose(self) -> None:
            return None

    real_transport = app.state.transport
    real_transport._client = _ProviderClient()
    return TestClient(app)


class _Recorder:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.calls: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        return self.response


def test_chat_completion_happy_path(tmp_path: Path) -> None:
    recorder = _Recorder(
        make_success_response(model="reference-model", content="hello dispatcher", usage={
            "prompt_tokens": 4,
            "completion_tokens": 6,
            "total_tokens": 10,
        })
    )
    with _build_app_with_mock(
        tmp_path,
        transport_handler=recorder,
        enabled=True,
        base_url="https://provider.example.test/v1",
        models=["reference-model"],
        api_key="gsk-test-key",
    ) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "reference-model",
                "messages": [{"role": "user", "content": "hi"}],
                "temperature": 0.5,
            },
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "hello dispatcher"
    assert body["model"] == "reference-model"
    assert body["object"] == "chat.completion"
    assert body["usage"]["total_tokens"] == 10
    request = recorder.calls[-1]
    assert request.headers["Authorization"] == "Bearer gsk-test-key"
    assert request.headers["X-Proxy-Request-Id"]
    assert "X-Limen" not in response.headers
    assert "X-Routed-By" not in response.headers


def test_unknown_model_falls_back_to_auto_routing(tmp_path: Path) -> None:
    """Any model not advertised by a deployment is treated like 'auto' —
    all capability-matching deployments are candidates.  This lets CLI
    agents send arbitrary model IDs without LIMEN needing a hardcoded
    alias list."""
    recorder = _Recorder(make_success_response(model="only-this-model", content="auto-routed"))
    with _build_app_with_mock(
        tmp_path,
        transport_handler=recorder,
        enabled=True,
        base_url="https://provider.example.test/v1",
        models=["only-this-model"],
        api_key="gsk-test-key",
    ) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "other-model", "messages": [{"role": "user", "content": "x"}]},
        )
    assert response.status_code == 200
    assert response.json()["model"] == "only-this-model"


def test_chat_completion_streaming_is_accepted(tmp_path: Path) -> None:
    """Phase 5: streaming is enabled — stream=true returns 200 with SSE body."""
    recorder = _Recorder(make_success_response(model="reference-model", content=""))
    with _build_app_with_mock(
        tmp_path,
        transport_handler=recorder,
        enabled=True,
        base_url="https://provider.example.test/v1",
        models=["reference-model"],
        api_key="gsk-test-key",
    ) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "reference-model",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        )
    assert response.status_code == 200


def test_no_enabled_provider_returns_503(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"[database]\npath = \"{tmp_path / 'state.db'}\"\n",
        encoding="utf-8",
    )
    config_path.chmod(0o600)
    config = load_config(config_path)
    with TestClient(create_app(config)) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "any-model", "messages": [{"role": "user", "content": "x"}]},
        )
    assert response.status_code == 503
    envelope = response.json()["error"]
    assert envelope["type"] == "no_available_deployment"


def test_rate_limited_returns_429_with_retry_after(tmp_path: Path) -> None:
    recorder = _Recorder(
        httpx.Response(
            429,
            headers={"retry-after": "7"},
            json={"error": {"message": "slow down", "type": "rate_limit_error"}},
        )
    )
    with _build_app_with_mock(
        tmp_path,
        transport_handler=recorder,
        enabled=True,
        base_url="https://provider.example.test/v1",
        models=["reference-model"],
        api_key="gsk-test-key",
    ) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "reference-model", "messages": [{"role": "user", "content": "x"}]},
        )
    assert response.status_code == 429
    assert response.headers["retry-after"] == "7"
    body = response.json()
    assert body["error"]["type"] == "rate_limited"


def test_unauthorized_returns_401(tmp_path: Path) -> None:
    recorder = _Recorder(
        make_error_response(401, {"error": {"message": "bad key"}})
    )
    with _build_app_with_mock(
        tmp_path,
        transport_handler=recorder,
        enabled=True,
        base_url="https://provider.example.test/v1",
        models=["reference-model"],
        api_key="gsk-test-key",
    ) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "reference-model", "messages": [{"role": "user", "content": "x"}]},
        )
    assert response.status_code == 401
    assert response.json()["error"]["type"] == "key_revoked"


def test_server_error_returns_502(tmp_path: Path) -> None:
    recorder = _Recorder(
        make_error_response(503, {"error": {"message": "upstream down"}})
    )
    with _build_app_with_mock(
        tmp_path,
        transport_handler=recorder,
        enabled=True,
        base_url="https://provider.example.test/v1",
        models=["reference-model"],
        api_key="gsk-test-key",
    ) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "reference-model", "messages": [{"role": "user", "content": "x"}]},
        )
    assert response.status_code == 502
    assert response.json()["error"]["type"] == "provider_unreachable"


def test_response_does_not_leak_upstream_headers(tmp_path: Path) -> None:
    recorder = _Recorder(
        httpx.Response(200, headers={"X-Provider-Stuff": "secret"}, json={
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 1_700_000_000,
            "model": "reference-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
        })
    )
    with _build_app_with_mock(
        tmp_path,
        transport_handler=recorder,
        enabled=True,
        base_url="https://provider.example.test/v1",
        models=["reference-model"],
        api_key="gsk-test-key",
    ) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "reference-model", "messages": [{"role": "user", "content": "x"}]},
        )
    assert response.status_code == 200
    for header in ("X-Provider-Stuff", "X-Routed-By", "X-Limen", "X-Provider-Health"):
        assert header not in response.headers


def _build_provider_client(handler):
    class _ProviderClient(httpx.AsyncClient):
        async def post(self, url, **kwargs):  # pragma: no cover - exercised in test
            request = httpx.Request("POST", url, **kwargs)
            return handler(request)

        async def aclose(self) -> None:
            return None

    return _ProviderClient()


@pytest.fixture
def ensure_transport_factory():
    return _build_provider_client
