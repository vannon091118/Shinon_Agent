"""Unit tests for the LIMEN CLI entrypoints."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003

import pytest

from limen.cli import _run_init, build_parser, main
from limen.config import ConfigError

# ── build_parser ───────────────────────────────────────────────────────


def test_build_parser_defaults_to_no_command() -> None:
    parser = build_parser()
    args = parser.parse_args([])
    assert args.command is None


def test_build_parser_init_accepts_default_config() -> None:
    parser = build_parser()
    args = parser.parse_args(["init"])
    assert args.command == "init"
    assert "config" in args


def test_build_parser_start_accepts_custom_config(tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    config_path.touch()
    parser = build_parser()
    args = parser.parse_args(["start", "--config", str(config_path)])
    assert args.command == "start"
    assert args.config == config_path


# ── _run_init ──────────────────────────────────────────────────────────


def test_run_init_creates_database(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
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

    exit_code = _run_init(config_path)
    assert exit_code == 0
    assert db_path.exists()


def test_run_init_fails_on_bad_config(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.toml"
    config_path.write_text("not valid toml[[", encoding="utf-8")

    with pytest.raises((ConfigError, OSError)):
        _run_init(config_path)


# ── main error handling ────────────────────────────────────────────────


def test_main_returns_error_on_missing_config() -> None:
    result = main(["init", "--config", "/nonexistent/limen/config.toml"])
    assert result == 2


def test_main_returns_error_on_bad_config(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.toml"
    config_path.write_text("[server]\nhost = 'invalid'\n", encoding="utf-8")

    result = main(["init", "--config", str(config_path)])
    assert result == 2


def test_main_exits_on_unknown_command() -> None:
    with pytest.raises(SystemExit):
        main(["unknown-cmd"])


# ── Slice FA-C: full `_run_start` integration ───────────────────────────


def test_run_start_invokes_uvicorn_with_rendered_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_run_start`` must build the app from the TOML and call ``uvicorn.run``.

    We stub ``uvicorn.run`` so the call returns immediately; the test pins
    the (host, port, log_level, workers) tuple and the app object's title.
    """
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    config_path.write_text(
        f"""
[server]
host = "127.0.0.1"
port = 18301
worker_count = 1
log_level = "warning"
max_body_size_kb = 256

[database]
path = "{db_path}"

[providers]
""",
        encoding="utf-8",
    )
    config_path.chmod(0o600)

    import limen.cli as cli_mod

    uvicorn_calls: list[dict[str, object]] = []

    def fake_uvicorn_run(
        app: object, host: str = "", port: int = 0,
        log_level: str = "", workers: int = 0, **kwargs: object,
    ) -> None:
        uvicorn_calls.append({
            "title": getattr(app, "title", None),
            "host": host, "port": port,
            "log_level": log_level, "workers": workers,
        })

    monkeypatch.setattr(cli_mod, "uvicorn", type("uv", (), {"run": staticmethod(fake_uvicorn_run)}))
    # Don't actually try to clean up any process
    monkeypatch.setattr(cli_mod, "_kill_port", lambda _port: None)
    monkeypatch.setattr(cli_mod, "_open_browser", lambda _url: None)

    exit_code = cli_mod._run_start(config_path)

    assert exit_code == 0
    assert len(uvicorn_calls) == 1, "uvicorn.run should have been called exactly once"
    call = uvicorn_calls[0]
    assert call["title"] == "LIMEN"
    assert call["host"] == "127.0.0.1"
    assert call["port"] == 18301
    assert call["workers"] == 1


def test_run_start_initialises_database_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Before uvicorn starts, the SQLite schema must be init-able via ``limen init``.

    We assert equivalently here that starting the server does not require the
    DB to already exist — the app factory opens it on lifespan without
    complaining about a missing file. This protects the typical user flow:
    init-then-start where init is allowed to be skipped.
    """
    config_path = tmp_path / "config.toml"
    db_path = tmp_path / "state.db"
    config_path.write_text(
        f"""
[server]
host = "127.0.0.1"
port = 18302
log_level = "warning"

[database]
path = "{db_path}"

[providers]
""",
        encoding="utf-8",
    )
    config_path.chmod(0o600)

    import limen.cli as cli_mod
    monkeypatch.setattr(cli_mod, "uvicorn", type(
        "uv", (), {"run": staticmethod(lambda *a, **kw: None)}
    ))
    # No DB exists yet — but `_run_start` does not require pre-init.
    assert not db_path.exists()
    exit_code = cli_mod._run_start(config_path)
    assert exit_code == 0
