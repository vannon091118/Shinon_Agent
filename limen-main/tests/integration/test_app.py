"""FastAPI foundation integration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

if TYPE_CHECKING:
    from pathlib import Path

from limen.api import create_app
from limen.config import load_config


def test_app_exposes_health_models_and_ui(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"""
[database]
path = "{tmp_path / 'state.db'}"

[providers.primary]
enabled = true
priority = 1
models = ["model-a"]
""",
        encoding="utf-8",
    )
    config_path.chmod(0o600)
    app = create_app(load_config(config_path))

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert health.json()["db_writable"] is True
        assert client.get("/v1/models").json()["data"][0]["id"] == "model-a"
        page = client.get("/")
        assert "LIMEN Leitstand" in page.text
        assert 'lang="de"' in page.text
        assert "Jede Anfrage hinterlässt eine Spur." in page.text
        assert 'id="latency-canvas"' in page.text
        assert "drawLatencyScatter" in page.text
        assert 'id="factory-pipeline"' in page.text
        assert "worker.claimed" in page.text
        assert "routing-grid" in page.text
        assert "Auto-Routing" in page.text
        assert "startSimulation" in page.text
        assert "stopSimulation" in page.text


def test_app_rejects_oversized_request_header(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"[database]\npath = \"{tmp_path / 'state.db'}\"\n\n[server]\nmax_body_size_kb = 1\n",
        encoding="utf-8",
    )
    config_path.chmod(0o600)

    with TestClient(create_app(load_config(config_path))) as client:
        response = client.get("/health", headers={"content-length": "2048"})
        assert response.status_code == 413
        assert client.get("/health", headers={"content-length": "invalid"}).status_code == 400


def test_app_reports_degraded_without_enabled_provider(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"[database]\npath = \"{tmp_path / 'state.db'}\"\n",
        encoding="utf-8",
    )
    config_path.chmod(0o600)

    with TestClient(create_app(load_config(config_path))) as client:
        assert client.get("/health").json()["status"] == "degraded"
