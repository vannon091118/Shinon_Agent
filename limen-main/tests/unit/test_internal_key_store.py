"""Unit tests for the persisted key-store helpers in ``internal.py``.

Slice FA-A: atomic write, mode 600, corrupt-resilience on read.
"""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003

import pytest


@pytest.fixture
def key_store_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``_KEY_STORE`` to a tmp directory for the test."""
    from limen.api.routes import internal

    target = tmp_path / "keys.json"
    monkeypatch.setattr(internal, "_KEY_STORE", target)
    return target


# ── _write_key_store ────────────────────────────────────────────────────


def test_write_key_store_creates_file_with_dotted_payload(key_store_path: Path) -> None:
    from limen.api.routes.internal import _write_key_store

    _write_key_store({"groq": "gsk_abc", "openrouter": "sk-or-v1-def"})

    assert key_store_path.exists(), "key store file should exist after write"
    payload = json.loads(key_store_path.read_text())
    assert payload == {"groq": "gsk_abc", "openrouter": "sk-or-v1-def"}


def test_write_key_store_sets_owner_only_permissions(key_store_path: Path) -> None:
    """The persisted file must be mode 600 — no group/other access for secrets."""
    from limen.api.routes.internal import _write_key_store

    _write_key_store({"groq": "gsk_xyz"})

    stat_result = key_store_path.stat()
    # 0o600 = owner read+write; we want no group/other bits set.
    assert stat_result.st_mode & 0o077 == 0, (
        f"expected owner-only mode 600, got {oct(stat_result.st_mode & 0o777)}"
    )


def test_write_key_store_replaces_previous_payload_atomically(key_store_path: Path) -> None:
    """A second write must overwrite without leaving ``*.tmp`` debris."""
    from limen.api.routes.internal import _write_key_store

    _write_key_store({"groq": "first"})
    _write_key_store({"groq": "second", "extra": "third"})

    payload = json.loads(key_store_path.read_text())
    assert payload == {"groq": "second", "extra": "third"}

    # No leftover tmp files from the atomic-rename dance.
    siblings = [p.name for p in key_store_path.parent.iterdir()]
    assert siblings == ["keys.json"], (
        f"expected only keys.json, found siblings: {siblings}"
    )


# ── _read_key_store ────────────────────────────────────────────────────


def test_read_key_store_returns_empty_dict_when_missing(key_store_path: Path) -> None:
    """A missing store must not raise — callers fall through to env resolution."""
    from limen.api.routes.internal import _read_key_store

    # key_store_path does not exist yet.
    assert not key_store_path.exists()
    assert _read_key_store() == {}


def test_read_key_store_returns_empty_dict_on_corrupt_json(key_store_path: Path) -> None:
    """Corrupt JSON must not crash the /v1/_internal/keys endpoint."""
    from limen.api.routes.internal import _read_key_store

    key_store_path.write_text("{not valid json,,,", encoding="utf-8")
    assert _read_key_store() == {}


def test_read_key_store_returns_empty_dict_when_root_is_not_an_object(
    key_store_path: Path,
) -> None:
    """A non-object (e.g. a JSON array) at the root must be treated as empty."""
    from limen.api.routes.internal import _read_key_store

    key_store_path.write_text('["not", "an", "object"]', encoding="utf-8")
    assert _read_key_store() == {}


def test_read_key_store_round_trip_preserves_data(key_store_path: Path) -> None:
    """Write → read returns identical content."""
    from limen.api.routes.internal import _read_key_store, _write_key_store

    source = {"groq": "gsk_a", "nvidia": "nvapi_b", "openrouter": "sk-or-v1_c"}
    _write_key_store(source)
    assert _read_key_store() == source


# ── resolve_key_from_store ─────────────────────────────────────────────


def test_resolve_key_prefers_env_over_store(
    key_store_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the env var is set, the store value must be ignored entirely."""
    from limen.api.routes.internal import _write_key_store, resolve_key_from_store

    _write_key_store({"groq": "from-store"})
    monkeypatch.setenv("GROQ_API_KEY", "from-env")
    assert resolve_key_from_store("groq", "GROQ_API_KEY") == "from-env"


def test_resolve_key_falls_back_to_store_when_env_missing(
    key_store_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the env var is unset, the key store entry is returned."""
    from limen.api.routes.internal import _write_key_store, resolve_key_from_store

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    _write_key_store({"groq": "from-store"})
    assert resolve_key_from_store("groq", "GROQ_API_KEY") == "from-store"


def test_resolve_key_returns_none_when_neither_present(
    key_store_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both env and store empty → ``None`` so the loader keeps the literal placeholder."""
    from limen.api.routes.internal import resolve_key_from_store

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert resolve_key_from_store("groq", "GROQ_API_KEY") is None
