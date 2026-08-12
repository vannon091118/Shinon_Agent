"""Tests for local request analysis and model registry configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from limen.config import ConfigError, load_config
from limen.routing.registry import ProviderRegistry
from limen.routing.scanner import scan_request
from limen.schemas import ChatCompletionRequest


def _request(content: str, *, max_tokens: int | None = None) -> ChatCompletionRequest:
    payload: dict[str, object] = {
        "model": "explicit-model",
        "messages": [{"role": "user", "content": content}],
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    return ChatCompletionRequest.model_validate(payload)


def test_scan_request_is_local_and_reports_size_and_complexity() -> None:
    scan = scan_request(
        _request("```python\ndef answer():\n    return {'ok': True}\n```", max_tokens=512)
    )

    assert scan.estimated_input_tokens > 1
    assert scan.estimated_output_tokens == 512
    assert scan.context_tokens == scan.estimated_input_tokens + 512
    assert scan.message_count == 1
    assert scan.code_ratio > 0
    assert scan.json_or_tool_complexity > 0
    assert 0 <= scan.score <= 100
    assert scan.category in {"small", "medium", "large", "reasoning"}


def test_scan_request_is_deterministic_for_same_request() -> None:
    request = _request("Explain this plainly.")
    assert scan_request(request) == scan_request(request)


def test_model_registry_rejects_unknown_provider(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[models.orphan]
provider = "missing"
model_id = "orphan-model"
""",
        encoding="utf-8",
    )
    config_path.chmod(0o600)

    try:
        load_config(config_path)
    except ConfigError as exc:
        assert "unknown provider" in str(exc)
    else:
        raise AssertionError("unknown model provider must be rejected")


def test_model_registry_builds_one_deployment_per_model(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[providers.groq]
enabled = true
base_url = "https://api.groq.example/v1"
keys = ["test-key"]
capabilities = ["chat"]

[models.fast]
provider = "groq"
model_id = "llama-fast"
free = true
priority = 4
max_context_tokens = 8192
capabilities = ["chat", "code"]

[models.reasoning]
provider = "groq"
model_id = "llama-reasoning"
free = true
priority = 8
max_context_tokens = 32768
capabilities = ["chat", "reasoning"]
escalation_group = "default"
""",
        encoding="utf-8",
    )
    config_path.chmod(0o600)

    registry = ProviderRegistry(load_config(config_path))

    assert [deployment.model for deployment in registry.deployments] == [
        "llama-fast",
        "llama-reasoning",
    ]
    assert registry.deployments[0].free is True
    assert registry.deployments[0].max_context_tokens == 8192
    assert registry.deployments[1].capabilities == ("chat", "reasoning")


def test_enabled_models_includes_declarative_models(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[providers.groq]
enabled = true
priority = 10

[models.fast]
provider = "groq"
model_id = "fast-model"
priority = 1
""",
        encoding="utf-8",
    )
    config_path.chmod(0o600)

    assert load_config(config_path).enabled_models == ["fast-model"]
