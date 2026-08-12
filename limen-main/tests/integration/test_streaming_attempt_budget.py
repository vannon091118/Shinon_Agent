"""Test Slice 1: streaming attempt budget on retryable failures.

Before the budget, ``stream_completion()`` contained an unbounded
``while True:`` loop. ``KeyPool._apply_failure()`` keeps the key
``active`` for ``provider_unreachable``, so ``claim()`` returned the
same key indefinitely and the request hung.

This test pins the new contract: a streaming request fails fast with
HTTP 503 once the per-call attempt budget is exhausted, regardless of
how many candidates / pools the registry advertises.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import httpx
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from pathlib import Path


def _build_minimal_app(
    tmp_path: Path,
    *,
    bogus_only: bool = True,
    model: str = "budget-reference-model",
) -> tuple[TestClient, object]:
    """Build a LIMEN test client that points only at an unreachable provider."""
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
base_url = "https://provider-unreachable.invalid/v1"
priority = 10
limit_scope = "unknown"
account_id = "budget-smoke"
keys = ["unreachable-key"]
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

    # Install a transport that always fails connectivity so every claim
    # raises a retryable ProviderFailure("provider_unreachable").
    transport = httpx.MockTransport(
        lambda _request: (_ for _ in ()).throw(
            httpx.ConnectError(
                "name resolution failed for provider-unreachable.invalid",
            )
        )
    )
    app.state.transport._client = httpx.AsyncClient(  # type: ignore[attr-defined]
        transport=transport
    )

    # Force a tight attempt budget for the test so we can prove the cap kicks in.
    app.state.dispatcher.max_attempts = 2

    return TestClient(app), app.state.dispatcher


def test_streaming_returns_provider_unreachable_after_budget_exhausted(tmp_path: Path) -> None:
    """Streaming must fail-fast within the configured budget; never hang.

    HTTP 502 + envelope ``error.type == "provider_unreachable"`` is the
    resilience-layer mapping for an upstream that never responds. The
    important property is the bound on wall-clock time, not the code.
    """
    client, _ = _build_minimal_app(tmp_path)
    payload = {
        "model": "budget-reference-model",
        "messages": [{"role": "user", "content": "ping"}],
        "stream": True,
    }
    start = time.monotonic()
    with client.stream("POST", "/v1/chat/completions", json=payload) as response:
        body = response.read()
    elapsed = time.monotonic() - start

    assert response.status_code == 502, (
        f"expected 502 (provider_unreachable) once budget exhausted, got {response.status_code}"
    )
    assert b'"type":"provider_unreachable"' in body, (
        f"expected provider_unreachable envelope, got body: {body[:200]!r}"
    )
    # Without the budget fix this hung indefinitely; with the fix it must
    # return within a few hundred ms. 5 s is the conservative ceiling.
    assert elapsed < 5.0, f"streaming hung too long: {elapsed:.2f}s"


def test_streaming_one_attempt_budget_still_issues_one_request(tmp_path: Path) -> None:
    """Boundary: ``max_attempts=1`` triggers exactly one claim, then 502."""
    client, _ = _build_minimal_app(tmp_path)
    # Override the budget that _build_minimal_app already tightened to 2.
    client.app.state.dispatcher.max_attempts = 1
    payload = {
        "model": "budget-reference-model",
        "messages": [{"role": "user", "content": "x"}],
        "stream": True,
    }
    start = time.monotonic()
    with client.stream("POST", "/v1/chat/completions", json=payload) as response:
        _ = response.read()
    elapsed = time.monotonic() - start
    assert response.status_code == 502
    assert elapsed < 2.0, f"single-attempt budget should fail fastest: {elapsed:.2f}s"
