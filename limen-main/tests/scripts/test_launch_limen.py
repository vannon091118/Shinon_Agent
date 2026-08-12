"""Pytest-Suite für ``scripts/launch_limen.py``.

Zwei Test-Schichten:

1. **Modul-Direkt-Tests** — importieren das Skript mit isoliertem ``HOME``
   pro Test und prüfen interne Helfer (``perform_swap``, ``restore_backup``,
   Patcher) deterministisch. ``_confirm`` wird gemockt, sodass keine
   TTY-Eingaben nötig sind.
2. **CLI-Subprocess-Tests** — starten ``python3 scripts/launch_limen.py``
   isoliert (eigene ``HOME``-Variable) und prüfen Exit-Code, stdout und
   Argument-Parsing. ``dry-run`` ist der einzige Modus, der ohne
   stdin-Bestätigung wirklich Schritt für Schritt geprüft werden kann.

Pro Agent wird ein Golden-Sample definiert; nach ``swap`` + ``restore``
muss die Datei byte-identisch zur Golden-Sample sein.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
import uuid
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "scripts" / "launch_limen.py"

# ─────────────────────────────────────────────────────────────────────────
# Golden-Samples pro Agent (Pre-Swap-Inhalt, der nach restore byte-identisch
# wieder auftauchen muss).
# ─────────────────────────────────────────────────────────────────────────

GOOSE_GOLDEN = textwrap.dedent(
    """\
    extensions:
      todo:
        enabled: true
        bundled: true
    providers:
      nvidia:
        enabled: true
        configured: true
      openrouter:
        enabled: true
        configured: true
    GOOSE_TELEMETRY_ENABLED: true
    """
)

CLAUDE_GOLDEN = (
    json.dumps(
        {
            "model": "claude-default",
            "permissions": {"allow": ["Bash"]},
            "env": {"ANTHROPIC_LOG": "error"},
        },
        indent=2,
    )
    + "\n"
)

INTERPRETER_GOLDEN = (
    json.dumps(
        {
            "profile": "default",
            "language": "python",
            "auto_run": True,
            "profiles": [
                {
                    "id": "openai:gpt-4o",
                    "name": "OpenAI",
                    "provider": "openai",
                },
            ],
        },
        indent=2,
    )
    + "\n"
)

AIDER_GOLDEN = textwrap.dedent(
    """\
    # Old Aider config (will be swapped out).
    model: gpt-4o
    weak-model: gpt-4o-mini
    """
)

CONTINUE_GOLDEN = (
    json.dumps(
        {
            "models": [
                {
                    "title": "Old",
                    "provider": "openai",
                    "model": "gpt-4o",
                },
            ],
            "tabAutocompleteModel": {
                "title": "Old autocomplete",
                "provider": "openai",
                "model": "gpt-4o",
            },
        },
        indent=2,
    )
    + "\n"
)

OPENCODE_GOLDEN = json.dumps({"theme": "system", "keymap": "default"}, indent=2) + "\n"


GOLDEN_BY_AGENT: dict[str, tuple[str, str]] = {
    "goose": (GOOSE_GOLDEN, "yaml"),
    "claude": (CLAUDE_GOLDEN, "json"),
    "interpreter": (INTERPRETER_GOLDEN, "json"),
    "aider": (AIDER_GOLDEN, "yaml"),
    "continue": (CONTINUE_GOLDEN, "json"),
    "opencode": (OPENCODE_GOLDEN, "json"),
}

AGENT_NAMES = sorted(GOLDEN_BY_AGENT.keys())


# ─────────────────────────────────────────────────────────────────────────
# Loader für das Launcher-Modul mit isoliertem HOME und LIMEN_CONFIG.
# ─────────────────────────────────────────────────────────────────────────


def _load_launcher(
    home: Path,
) -> Any:
    """Lade ``scripts/launch_limen.py`` mit deterministischem HOME.

    LIMEN_CONFIG wird **nicht** angefasst — Tests setzen es selbst via
    ``monkeypatch.setenv``, damit der Cleanup-Zyklus von pytest greift.
    """

    saved_env: dict[str, str | None] = {
        "HOME": os.environ.get("HOME"),
        "XDG_CONFIG_HOME": os.environ.get("XDG_CONFIG_HOME"),
    }
    os.environ["HOME"] = str(home)
    os.environ["XDG_CONFIG_HOME"] = str(home / ".config")
    try:
        unique_name = f"launch_limen_test_{uuid.uuid4().hex[:12]}"
        spec = importlib.util.spec_from_file_location(unique_name, LAUNCHER)
        assert spec and spec.loader, f"cannot load spec for {LAUNCHER}"
        module = importlib.util.module_from_spec(spec)
        sys.modules[unique_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.fixture
def launcher_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """Frisches Launcher-Modul mit ``HOME=<tmp_path>`` und ohne LIMEN_CONFIG."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
    monkeypatch.delenv("LIMEN_CONFIG", raising=False)
    for cached in list(sys.modules):
        if cached.startswith("launch_limen_test_"):
            del sys.modules[cached]
    return _load_launcher(tmp_path)


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _golden_path(launcher: Any, agent_name: str) -> Path:
    """Liefert den ersten (und einzigen) ``config_search_paths`` des Profils."""
    profile = next(p for p in launcher.PROFILES if p.name == agent_name)
    return Path(profile.config_search_paths[0])


def _seed_golden(launcher: Any, agent_name: str, golden: str, fmt: str) -> Path:
    """Schreibt das Golden-Sample an den Profil-Pfad. Liefert den Pfad."""
    path = _golden_path(launcher, agent_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(golden, encoding="utf-8")
    return path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _force_options(
    *,
    model: str = "limen-test-model",
    base_url: str = "http://127.0.0.1:8000/v1",
    api_key: str = "limen-local",
    provider_name: str = "limen_local",
) -> dict[str, Any]:
    """Synthetische LIMEN-Optionen für Tests."""
    return {
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
        "provider_name": provider_name,
    }


# ─────────────────────────────────────────────────────────────────────────
# Modul-Surface
# ─────────────────────────────────────────────────────────────────────────


class TestModuleSurface:
    def test_module_loads(self, launcher_module: Any) -> None:
        """Das Skript muss ohne Side-Effects importieren."""
        assert launcher_module is not None
        assert hasattr(launcher_module, "PROFILES")
        assert hasattr(launcher_module, "perform_swap")
        assert hasattr(launcher_module, "restore_backup")

    def test_profiles_cover_six_agents(self, launcher_module: Any) -> None:
        names = {profile.name for profile in launcher_module.PROFILES}
        assert names == set(AGENT_NAMES)

    def test_profiles_point_at_home(self, launcher_module: Any, tmp_path: Path) -> None:
        """Nach Isolierung zeigen alle Profile-Cfg-Pfade unterhalb ``tmp_path``."""
        for profile in launcher_module.PROFILES:
            for cfg in profile.config_search_paths:
                assert cfg.parent == tmp_path / cfg.parent.name or (
                    str(cfg).startswith(str(tmp_path))
                ), f"{profile.name} leaked to {cfg}"


# ─────────────────────────────────────────────────────────────────────────
# Patcher-Direkt-Tests — die fünf Date-Formate müssen parsen.
# ─────────────────────────────────────────────────────────────────────────


class TestPatchersParse:
    @pytest.mark.parametrize("agent_name", AGENT_NAMES)
    def test_patcher_renders_parseable_output(
        self, launcher_module: Any, agent_name: str, tmp_path: Path
    ) -> None:
        golden, fmt = GOLDEN_BY_AGENT[agent_name]
        target = _seed_golden(launcher_module, agent_name, golden, fmt)
        profile = next(p for p in launcher_module.PROFILES if p.name == agent_name)
        summary: dict[str, Any] = {}
        result = profile.patcher(target, _force_options(), summary)
        rendered = result["render"]
        if fmt == "yaml":
            data = yaml.safe_load(rendered)
            assert isinstance(data, dict)
        else:
            data = json.loads(rendered)
            assert isinstance(data, dict)
        assert "provider_name" in summary


class TestLimenOptions:
    def test_defaults_when_no_config_and_empty_repo_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ohne LIMEN_CONFIG-env und ohne ``config.toml.example`` im repo_root greifen Defaults."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("LIMEN_CONFIG", raising=False)
        module = _load_launcher(tmp_path)
        opts = module._read_limen_options(tmp_path)
        assert opts["model"] == module.LIMEN_DEFAULT_MODEL
        assert opts["base_url"].endswith("/v1")
        assert opts["api_key"] == module.LIMEN_API_KEY_PLACEHOLDER

    def test_does_not_double_v1_suffix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Eine bereits mit ``/v1`` endende base_url wird **nicht** verdoppelt."""
        config = tmp_path / "limen.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            textwrap.dedent(
                """\
                [providers.test_provider]
                enabled = true
                base_url = "http://example.test/v1"
                models = ["llama-test"]
                """
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LIMEN_CONFIG", str(config))
        module = _load_launcher(tmp_path)
        opts = module._read_limen_options(tmp_path)
        assert opts["base_url"] == "http://example.test/v1"
        assert opts["model"] == "llama-test"

    def test_appends_v1_when_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Eine base_url ohne ``/v1`` bekommt es angehängt."""
        config = tmp_path / "limen.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            textwrap.dedent(
                """\
                [providers.test_provider]
                enabled = true
                base_url = "http://example.test"
                models = ["llama-test"]
                """
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LIMEN_CONFIG", str(config))
        module = _load_launcher(tmp_path)
        opts = module._read_limen_options(tmp_path)
        assert opts["base_url"] == "http://example.test/v1"

    def test_ignores_disabled_providers(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Deaktivierte Provider werden übersprungen — Defaults bleiben aktiv."""
        config = tmp_path / "limen.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            textwrap.dedent(
                """\
                [providers.disabled_one]
                enabled = false
                base_url = "http://disabled.test"
                models = ["offline-model"]

                [providers.also_disabled]
                enabled = false
                """
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("LIMEN_CONFIG", str(config))
        module = _load_launcher(tmp_path)
        opts = module._read_limen_options(tmp_path)
        assert opts["model"] == module.LIMEN_DEFAULT_MODEL


# ─────────────────────────────────────────────────────────────────────────
# Dry-Run — darf keinen einzigen File-Write auslösen.
# ─────────────────────────────────────────────────────────────────────────


class TestDryRunNoSideEffect:
    @pytest.mark.parametrize("agent_name", AGENT_NAMES)
    def test_dry_run_writes_nothing(
        self,
        launcher_module: Any,
        agent_name: str,
    ) -> None:
        golden, fmt = GOLDEN_BY_AGENT[agent_name]
        target = _seed_golden(launcher_module, agent_name, golden, fmt)
        profile = next(p for p in launcher_module.PROFILES if p.name == agent_name)
        before_sha = _sha256(target.read_bytes())
        before_dir = sorted(target.parent.iterdir())

        summary = launcher_module.perform_swap(
            profile,
            target,
            _force_options(),
            dry_run=True,
        )
        assert summary["status"] == "dry-run"
        # File-Inhalt byte-identisch.
        assert _sha256(target.read_bytes()) == before_sha
        # Keine Backup-Datei angelegt.
        assert sorted(target.parent.iterdir()) == before_dir


# ─────────────────────────────────────────────────────────────────────────
# Round-Trip swap + restore pro Agent (Golden-Restore-Vergleich).
# ─────────────────────────────────────────────────────────────────────────


class TestGoldenSwapRestore:
    @pytest.mark.parametrize("agent_name", AGENT_NAMES)
    def test_swap_then_restore_yields_byte_identical_golden(
        self,
        launcher_module: Any,
        agent_name: str,
    ) -> None:
        golden, fmt = GOLDEN_BY_AGENT[agent_name]
        target = _seed_golden(launcher_module, agent_name, golden, fmt)
        profile = next(p for p in launcher_module.PROFILES if p.name == agent_name)
        golden_sha = _sha256(target.read_bytes())

        # Swap-Pfad ohne Bestätigungs-Prompt.
        original_confirm = launcher_module._confirm
        launcher_module._confirm = lambda _plan: True
        try:
            swap_summary = launcher_module.perform_swap(
                profile,
                target,
                _force_options(),
                dry_run=False,
            )
        finally:
            launcher_module._confirm = original_confirm

        assert swap_summary["status"] == "applied"
        # Backup-Pfad ist deterministisch (Clock mockt SekundenTicks).
        backup_path = Path(swap_summary["backup"])
        assert backup_path.exists(), f"backup not written: {backup_path}"
        assert _sha256(backup_path.read_bytes()) == golden_sha
        # Gepatched-Version **darf** nicht byte-identisch zum Golden sein.
        assert _sha256(target.read_bytes()) != golden_sha

        # Strukturelle Sanity-Checks pro Agent.
        post_swap = target.read_text(encoding="utf-8")
        if fmt == "yaml":
            data = yaml.safe_load(post_swap)
        else:
            data = json.loads(post_swap)
        assert isinstance(data, dict)

        # Restore liest jüngste .bak.* und kopiert sie zurück.
        rc = launcher_module.restore_backup(agent_name)
        assert rc == 0, f"restore_backup({agent_name}) returned {rc}"
        # Nach Restore byte-gleich zur Pre-Swap-Golden.
        assert _sha256(target.read_bytes()) == golden_sha

    @pytest.mark.parametrize("agent_name", AGENT_NAMES)
    def test_declined_swap_writes_nothing(
        self,
        launcher_module: Any,
        agent_name: str,
    ) -> None:
        """Wenn `_confirm` Nein liefert, kein Write, kein Backup."""
        golden, fmt = GOLDEN_BY_AGENT[agent_name]
        target = _seed_golden(launcher_module, agent_name, golden, fmt)
        profile = next(p for p in launcher_module.PROFILES if p.name == agent_name)
        golden_sha = _sha256(target.read_bytes())
        before_dir = sorted(target.parent.iterdir())

        original_confirm = launcher_module._confirm
        launcher_module._confirm = lambda _plan: False
        try:
            summary = launcher_module.perform_swap(
                profile,
                target,
                _force_options(),
                dry_run=False,
            )
        finally:
            launcher_module._confirm = original_confirm

        assert summary["status"] == "declined"
        assert _sha256(target.read_bytes()) == golden_sha
        assert sorted(target.parent.iterdir()) == before_dir


class TestConfigMissing:
    """Wenn die Config-Datei fehlt, legt der Patcher sie neu an."""

    @pytest.mark.parametrize(
        "agent_name", ["aider", "continue", "opencode", "interpreter", "claude", "goose"]
    )
    def test_patcher_creates_missing_config(
        self,
        launcher_module: Any,
        agent_name: str,
    ) -> None:
        target = _golden_path(launcher_module, agent_name)
        if target.exists():
            target.unlink()

        profile = next(p for p in launcher_module.PROFILES if p.name == agent_name)

        original_confirm = launcher_module._confirm
        launcher_module._confirm = lambda _plan: True
        try:
            summary = launcher_module.perform_swap(
                profile,
                target,
                _force_options(),
                dry_run=False,
            )
        finally:
            launcher_module._confirm = original_confirm

        assert summary["status"] == "applied"
        assert target.exists(), "Patcher did not create config"
        assert target.stat().st_size > 0
        # perform_swap schreibt eine leere Backup-Datei (vor der Write-Aktion),
        # damit restore_backup() sie findet und beim Rollback den Pre-Swap-
        # Zustand wiederherstellt.
        backup_path = Path(summary["backup"])
        assert backup_path.exists()
        assert backup_path.read_bytes() == b""


# ─────────────────────────────────────────────────────────────────────────
# Detection-Tests — gemockt, damit kein Real-Binary-Lookup stattfindet.
# ─────────────────────────────────────────────────────────────────────────


class TestDetection:
    def test_detect_all_with_no_binaries_lists_agents(
        self, launcher_module: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mit gemocktem ``_which`` zeigt detect_all() alle Profile mit ``installed: no``."""
        monkeypatch.setattr(launcher_module, "_which", lambda _names: None)
        results = launcher_module.detect_all()
        assert len(results) == len(launcher_module.PROFILES)
        for result in results:
            assert result.installed is False
            assert result.binary_path is None

    def test_detect_all_with_one_binary(
        self, launcher_module: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Mindestens eine Detection liefert ein Binary."""

        def fake_which(candidates: tuple[str, ...]) -> str | None:
            return "/fake/path/goose" if "goose" in candidates else None

        monkeypatch.setattr(launcher_module, "_which", fake_which)
        results = launcher_module.detect_all()
        goose_result = next(r for r in results if r.name == "goose")
        assert goose_result.installed is True
        assert goose_result.binary_path == "/fake/path/goose"
        other = next(r for r in results if r.name == "claude")
        assert other.installed is False

    def test_format_inventory_contains_all_names(
        self, launcher_module: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(launcher_module, "_which", lambda _names: None)
        text = launcher_module._format_inventory(launcher_module.detect_all())
        for name in AGENT_NAMES:
            assert name in text


# ─────────────────────────────────────────────────────────────────────────
# Restore-Fehlerpfade
# ─────────────────────────────────────────────────────────────────────────


class TestRestoreFailure:
    def test_unknown_agent_exits_1(self, launcher_module: Any) -> None:
        rc = launcher_module.restore_backup("does-not-exist")
        assert rc == 1

    def test_no_backup_found_exits_1(self, launcher_module: Any) -> None:
        """Existiert der Agent, aber ohne bak-File, muss rc=1 sein."""
        rc = launcher_module.restore_backup("goose")
        assert rc == 1


# ─────────────────────────────────────────────────────────────────────────
# CLI-Subprocess-Tests: argparse, Exit-Codes, Dry-Run, list.
# Diese Tests sind headless-fähig, weil `dry-run` keine Bestätigung
# verlangt und so echt durchläuft.
# ─────────────────────────────────────────────────────────────────────────


def _run_launcher(
    args: list[str], *, home: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    full_env["HOME"] = str(home)
    full_env["XDG_CONFIG_HOME"] = str(home / ".config")
    full_env.pop("LIMEN_CONFIG", None)
    if env:
        full_env.update(env)
    return subprocess.run(  # noqa: S603 — controlled launcher invocation in tests.
        [sys.executable, str(LAUNCHER), *args],
        capture_output=True,
        text=True,
        check=False,
        env=full_env,
        timeout=20,
    )


class TestRestoreMissingTarget:
    """Wenn die Original-Config gefehlt hat, muss ``restore_backup`` die
    gepatchedete Datei wieder **löschen** (statt leeren)."""

    @pytest.mark.parametrize("agent_name", AGENT_NAMES)
    def test_restore_unlinks_file_when_original_was_missing(
        self,
        launcher_module: Any,
        agent_name: str,
    ) -> None:
        target = _golden_path(launcher_module, agent_name)
        if target.exists():
            target.unlink()
        profile = next(p for p in launcher_module.PROFILES if p.name == agent_name)

        original_confirm = launcher_module._confirm
        launcher_module._confirm = lambda _plan: True  # noqa: ARG005 — stub.
        try:
            swap_summary = launcher_module.perform_swap(
                profile,
                target,
                _force_options(),
                dry_run=False,
            )
        finally:
            launcher_module._confirm = original_confirm

        assert swap_summary["status"] == "applied"
        assert target.exists()
        assert target.stat().st_size > 0
        backup_path = Path(swap_summary["backup"])
        assert backup_path.read_bytes() == b""

        rc = launcher_module.restore_backup(agent_name)
        assert rc == 0
        assert not target.exists(), (
            "restore_backup muss die neu erzeugte Datei löschen, "
            "wenn die Original-Config gefehlt hat."
        )


class TestCliSubprocesses:
    def test_help_exits_zero(self, tmp_path: Path) -> None:
        result = _run_launcher(["--help"], home=tmp_path)
        assert result.returncode == 0
        assert "LIMEN launcher" in result.stdout

    def test_list_exits_zero_with_table(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "shutil.which",
            lambda name: f"/bin/{name}" if name == "goose" else None,
        )
        result = _run_launcher(["list"], home=tmp_path)
        assert result.returncode == 0
        assert "goose" in result.stdout

    def test_dry_run_unknown_agent_exits_nonzero(self, tmp_path: Path) -> None:
        result = _run_launcher(["dry-run", "does-not-exist"], home=tmp_path)
        assert result.returncode != 0
        assert "unknown agent" in result.stderr or ("unknown agent" in result.stdout)

    def test_dry_run_known_agent_no_side_effect(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Dry-run schreibt keine Files — bestätigt durch SHA-Vergleich."""
        monkeypatch.setattr(
            "shutil.which",
            lambda name: f"/bin/{name}" if name == "goose" else None,
        )
        golden_target = tmp_path / ".config" / "goose" / "config.yaml"
        golden_target.parent.mkdir(parents=True, exist_ok=True)
        golden_target.write_text(GOOSE_GOLDEN, encoding="utf-8")
        golden_sha = _sha256(golden_target.read_bytes())
        before_dir = sorted(golden_target.parent.iterdir())

        result = _run_launcher(["dry-run", "goose"], home=tmp_path)
        assert result.returncode == 0
        assert "dry-run" in result.stdout
        # Kein Side-Effect am File-System.
        assert _sha256(golden_target.read_bytes()) == golden_sha
        assert sorted(golden_target.parent.iterdir()) == before_dir

    def test_restore_unknown_agent_exits_1(self, tmp_path: Path) -> None:
        result = _run_launcher(["restore", "does-not-exist"], home=tmp_path)
        assert result.returncode == 1
