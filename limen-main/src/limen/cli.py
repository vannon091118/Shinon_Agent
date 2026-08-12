"""Command-line entrypoints for LIMEN foundation operations."""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import uvicorn

from limen import __version__
from limen.api import create_app
from limen.config import ConfigError, load_config
from limen.persistence import Database

DEFAULT_CONFIG_PATH = Path("~/.config/limen/config.toml").expanduser()
OPENCODE_CONFIG_PATH = Path("~/.config/opencode/config.json").expanduser()
CLAUDE_CONFIG_PATH = Path("~/.claude/settings.json").expanduser()
CLAUDE_INSTALL_DIR = Path("~/.limen/claude-code").expanduser()
CLAUDE_WRAPPER_PATH = Path("~/.limen/bin/claude").expanduser()
CODEX_CONFIG_PATH = Path("~/.codex/config.toml").expanduser()

# Latest Claude Code version we've tested against. Bump this when
# Anthropic releases a new version and you've verified the gateway
# integration still works.
_CLAUDE_PINNED_VERSION = "2.1.226"


def _kill_port(port: int) -> None:
    """Kill any process listening on *port* (Linux only)."""
    try:
        result = subprocess.run(  # noqa: S603 — fixed args, local dev helper
            ["fuser", "-k", f"{port}/tcp"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            print(f"  (alten Prozess auf Port {port} beendet)")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def _open_browser(url: str) -> None:
    """Launch Chromium (or fallback browser) pointing at *url*."""
    candidates = ["chromium", "chromium-browser", "google-chrome", "google-chrome-stable"]
    for binary in candidates:
        resolved = shutil.which(binary)
        if resolved:
            subprocess.Popen(  # noqa: S603 — resolved via shutil.which, local only
                [resolved, url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
    # Fallback: xdg-open
    subprocess.Popen(  # noqa: S603 — local URL, known system binary
        ["xdg-open", url],  # noqa: S607
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(prog="limen", description="Local LIMEN router")
    subparsers = parser.add_subparsers(dest="command")

    for command in ("init", "start"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument(
            "--config",
            type=Path,
            default=DEFAULT_CONFIG_PATH,
            help=f"TOML config path (default: {DEFAULT_CONFIG_PATH})",
        )
        if command == "start":
            command_parser.add_argument(
                "--dev",
                action="store_true",
                help="verbose logging + open browser to Control Center",
            )
    opencode_parser = subparsers.add_parser(
        "opencode",
        help="configure OpenCode CLI to use LIMEN as backend",
    )
    opencode_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="LIMEN port (default: 8000)",
    )
    claude_parser = subparsers.add_parser(
        "claude",
        help="manage Claude Code integration (config, install, update)",
    )
    claude_subs = claude_parser.add_subparsers(dest="claude_action")

    # limen claude (no subcommand) — write config only
    claude_subs.add_parser("config", help="write ~/.claude/settings.json")
    claude_install = claude_subs.add_parser(
        "install", help="install pinned Claude Code via npm"
    )
    claude_install.add_argument(
        "--version",
        type=str,
        default=None,
        help="override pinned version (default: latest tested)",
    )
    claude_subs.add_parser("update", help="update Claude Code to latest")
    claude_subs.add_parser("version", help="show installed Claude Code version")

    claude_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="LIMEN port (default: 8000)",
    )

    codex_parser = subparsers.add_parser(
        "codex",
        help="configure Codex CLI to use LIMEN as backend",
    )
    codex_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="LIMEN port (default: 8000)",
    )
    return parser


def _run_init(config_path: Path) -> int:
    config = load_config(config_path)
    database = Database(
        config.database.path,
        busy_timeout_ms=config.database.busy_timeout_ms,
        sync_mode=config.database.sync_mode,
    )
    try:
        database.open()
    finally:
        database.close()
    print(f"Initialized LIMEN database: {config.database.path}")
    return 0


def _run_opencode(port: int) -> int:
    """Write an OpenCode config that points at the local LIMEN instance."""
    import json as _json

    config = {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            "limen": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "LIMEN v" + __version__ + " — Auto-Routing",
                "options": {
                    "baseURL": "http://127.0.0.1:" + str(port) + "/v1",
                    "apiKey": "limen-no-auth-required",
                },
                "models": {
                    "auto": {},
                },
            }
        },
    }
    OPENCODE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENCODE_CONFIG_PATH.write_text(_json.dumps(config, indent=2) + "\n")
    print(f"OpenCode config written: {OPENCODE_CONFIG_PATH}")
    print(f"  Provider: limen → http://127.0.0.1:{port}/v1")
    print("  Model:    auto (LIMEN wählt selbstständig)")
    print("  API-Key:  beliebiger Wert (keine Auth)")
    print("\n  Starte LIMEN mit: limen start --dev")
    print("  Dann OpenCode mit: opencode")
    return 0


def _run_claude(port: int) -> int:
    """Write a Claude Code config that points at the local LIMEN instance."""
    import json as _json

    config = {
        "env": {
            "ANTHROPIC_BASE_URL": "http://127.0.0.1:" + str(port),
            "ANTHROPIC_API_KEY": "limen-no-auth-required",
            "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1",
        },
    }
    CLAUDE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_CONFIG_PATH.write_text(_json.dumps(config, indent=2) + "\n")
    print(f"Claude Code config written: {CLAUDE_CONFIG_PATH}")
    print(f"  Gateway:   http://127.0.0.1:{port}")
    print("  Model:     alle via [anthropic] config (default: auto-Fallback)")
    print("  API-Key:   beliebiger Wert (keine Auth)")
    print("  Discovery: aktiv (Claude Code fragt LIMENs /v1/models ab)")
    print("\n  Starte LIMEN mit: limen start --dev")
    print("  Dann Claude Code mit: claude")
    return 0


def _claude_binary_path() -> Path:
    """Return the path to the LIMEN-managed Claude Code binary."""
    return CLAUDE_INSTALL_DIR / "node_modules" / ".bin" / "claude"


def _run_claude_install(version: str | None = None) -> int:
    """Install Claude Code in a LIMEN-managed directory via npm.

    Installs ``@anthropic-ai/claude-code`` at a pinned version into
    ``~/.limen/claude-code/`` and writes a wrapper script to
    ``~/.limen/bin/claude`` that forces LIMEN as the gateway.
    """
    import stat as _stat

    pinned = version or _CLAUDE_PINNED_VERSION
    pkg = f"@anthropic-ai/claude-code@{pinned}"

    CLAUDE_INSTALL_DIR.parent.mkdir(parents=True, exist_ok=True)

    print(f"Installing {pkg} → {CLAUDE_INSTALL_DIR} …")
    npm_bin = shutil.which("npm")
    if npm_bin is None:
        print("npm not found — please install Node.js + npm first", file=sys.stderr)
        return 2

    try:
        subprocess.run(  # noqa: S603 — resolved via shutil.which
            [
                npm_bin,
                "install",
                "--prefix",
                str(CLAUDE_INSTALL_DIR),
                "--no-save",
                "--no-audit",
                "--no-fund",
                pkg,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"npm install failed: {exc.stderr}", file=sys.stderr)
        return 2


    # ── Write wrapper script ──
    binary = _claude_binary_path()
    wrapper = CLAUDE_WRAPPER_PATH
    wrapper.parent.mkdir(parents=True, exist_ok=True)

    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        "# LIMEN-managed Claude Code wrapper — regenerated by 'limen claude install'\n"
        f"export ANTHROPIC_BASE_URL='http://127.0.0.1:${{LIMEN_PORT:-8000}}'\n"
        "export ANTHROPIC_API_KEY='limen-no-auth-required'\n"
        "export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1\n"
        f'exec "{binary}" "$@"\n'
    )
    wrapper.chmod(wrapper.stat().st_mode | _stat.S_IXUSR | _stat.S_IXGRP | _stat.S_IXOTH)

    print(f"  ✓ Claude Code {pinned} installed")
    print(f"  ✓ Wrapper: {wrapper}")
    print(f"  ✓ Config:  {CLAUDE_CONFIG_PATH}")
    print("\n  Write config: limen claude")
    print("  Ensure ~/.limen/bin is on your PATH:")
    print('    export PATH="$HOME/.limen/bin:$PATH"')
    print("\n  Start LIMEN: limen start --dev")
    print("  Then run:    claude")
    return 0


def _run_claude_update() -> int:
    """Update the managed Claude Code installation to @latest."""
    return _run_claude_install(version="latest")


def _run_claude_version() -> int:
    """Print the installed Claude Code version, if any."""
    binary = _claude_binary_path()
    if not binary.exists():
        print("Claude Code is not installed via limen.")
        print("  Run: limen claude install")
        return 1
    try:
        result = subprocess.run(  # noqa: S603 — fixed path, known binary
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        print(f"Claude Code: {result.stdout.strip()}")
        print(f"  Installed at: {binary}")
        print(f"  Pinned:       {_CLAUDE_PINNED_VERSION}")
        return 0
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        print(f"Cannot determine version: {exc}", file=sys.stderr)
        return 1


def _run_codex(port: int) -> int:
    """Write a Codex config that points at the local LIMEN instance."""

    CODEX_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = (
        f"# Generated by limen codex\n"
        f"[api]\n"
        f'base_url = "http://127.0.0.1:{port}"\n'
        f'wire_api = "responses"\n'
        f'env_key = "limen-no-auth-required"\n'
    )
    CODEX_CONFIG_PATH.write_text(config)
    print(f"Codex config written: {CODEX_CONFIG_PATH}")
    print(f"  Gateway:   http://127.0.0.1:{port}/v1/responses")
    print("  Wire API:  responses")
    print("  API-Key:   beliebiger Wert (keine Auth)")
    print("\n  Starte LIMEN mit: limen start --dev")
    print("  Dann Codex mit: codex")
    return 0


def _run_start(config_path: Path, *, dev: bool = False) -> int:
    config = load_config(config_path)
    app = create_app(config)
    host, port = config.server.host, config.server.port
    log_level = "info" if dev else config.server.log_level

    if dev:
        _kill_port(port)
        url = f"http://{host}:{port}"
        print("\n  LIMEN Dev-Modus")
        print(f"  Backend:  {url}")
        print(f"  Leitstand: {url}")
        print(f"  Log-Level: {log_level}\n")
        # Open browser after a short delay to let uvicorn bind
        import threading

        threading.Timer(1.2, lambda: _open_browser(url)).start()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        workers=1,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and execute one CLI command."""
    args = build_parser().parse_args(argv)

    # Default: no subcommand → dev mode
    if args.command is None:
        return _run_start(DEFAULT_CONFIG_PATH, dev=True)

    try:
        if args.command == "init":
            return _run_init(args.config)
        if args.command == "start":
            return _run_start(args.config, dev=getattr(args, "dev", False))
        if args.command == "opencode":
            return _run_opencode(getattr(args, "port", 8000))
        if args.command == "claude":
            action = getattr(args, "claude_action", None)
            if action == "install":
                return _run_claude_install(getattr(args, "version", None))
            if action == "update":
                return _run_claude_update()
            if action == "version":
                return _run_claude_version()
            # No subcommand or "config" → write config
            return _run_claude(getattr(args, "port", 8000))
        if args.command == "codex":
            return _run_codex(getattr(args, "port", 8000))
    except (ConfigError, OSError, sqlite3.DatabaseError) as exc:
        print(f"limen: {exc}", file=sys.stderr)
        return 2
    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
