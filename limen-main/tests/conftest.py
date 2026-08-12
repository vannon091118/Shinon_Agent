"""Shared fixtures and path configuration for the LIMEN test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))


# ── Shared test helpers ───────────────────────────────────────────────


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Create a minimal valid config.toml in a temp directory.

    Returns the config path. Tests can modify the file before loading.
    """
    db_path = tmp_path / "state.db"
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f"""[server]
host = "127.0.0.1"
port = 18300

[database]
path = "{db_path}"

[providers]
""",
        encoding="utf-8",
    )
    config_path.chmod(0o600)
    return config_path


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Create and return a path to a state.db that will be cleaned up."""
    return tmp_path / "state.db"
