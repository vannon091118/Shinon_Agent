"""Configuration foundation tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from limen.config import ConfigError, load_config


def write_config(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)


def test_config_rejects_invalid_local_bind(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    write_config(config_path, '[server]\nhost = "0.0.0.0"\n')

    with pytest.raises(ConfigError, match="127.0.0.1"):
        load_config(config_path)


def test_config_extracts_enabled_models(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    write_config(
        config_path,
        """
[providers.primary]
enabled = true
priority = 1
models = ["model-a", "model-a", "model-b"]
""",
    )

    config = load_config(config_path)

    assert config.enabled_models == ["model-a", "model-b"]


def test_config_rejects_empty_model_name(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    write_config(
        config_path,
        """
[providers.primary]
enabled = true
models = [""]
""",
    )

    with pytest.raises(ConfigError, match="empty names"):
        load_config(config_path)


def test_config_rejects_insecure_permissions(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("[server]\nhost = \"127.0.0.1\"\n", encoding="utf-8")
    config_path.chmod(0o644)

    with pytest.raises(ConfigError, match="owner-only"):
        load_config(config_path)


# ── Slice FA-B: ${ENV_VAR} resolution + fallback to ~/.limen/keys.json ──


def test_config_env_var_substitution_uses_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit env var wins; the literal does not leak into the rendered config."""
    monkeypatch.setenv("FAKE_PROVIDER_KEY", "live-token-from-env")
    config_path = tmp_path / "config.toml"
    write_config(
        config_path,
        """
[providers.fake]
enabled = true
priority = 1
keys = ["${FAKE_PROVIDER_KEY}"]
models = ["fake-model"]
""",
    )
    config = load_config(config_path)
    assert config.providers["fake"].keys == ["live-token-from-env"]


def test_config_env_var_falls_back_to_keys_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the env var is absent, the loader reads ``~/.limen/keys.json``.

    Provider name is derived from the env-var name: lower-cased, with the
    ``_API_KEY`` and ``_NIM`` suffixes stripped, e.g.
    ``NVIDIA_NIM_API_KEY`` → ``nvidia``.
    """
    from limen.config.loader import _resolve_env_vars

    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    keys_dir = tmp_path / ".limen"
    keys_dir.mkdir()
    (keys_dir / "keys.json").write_text('{"nvidia": "from-key-store"}', encoding="utf-8")
    resolved = _resolve_env_vars("${NVIDIA_NIM_API_KEY}")
    assert resolved == "from-key-store"


def test_config_env_var_kept_literal_when_neither_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Neither env nor key store → placeholder is preserved (caller can decide)."""
    from limen.config.loader import _resolve_env_vars

    monkeypatch.delenv("TOTALLY_UNKNOWN_KEY", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    resolved = _resolve_env_vars("${TOTALLY_UNKNOWN_KEY}")
    assert resolved == "${TOTALLY_UNKNOWN_KEY}"
