#!/usr/bin/env python3
"""LIMEN Launcher — detect, prompt, swap, back up, start.

Usage:
    scripts/launch_limen.py list           # show detected agents only
    scripts/launch_limen.py --dry-run     # plan a swap, do not write
    scripts/launch_limen.py swap <name>   # patch a single agent, then start LIMEN
    scripts/launch_limen.py start         # launch LIMEN without touching any agent
    scripts/launch_limen.py restore <name> # restore the most recent backup of <name>

The script never writes a configuration file without the user typing ``y``.
Every patch creates a timestamped backup of the original on disk before any
mutation; the backup naming follows the AGENTS.md convention:

* YAML / JSON / TOML configs are backed up to ``<file>.bak.<unix-ts>``.
* Environment files (``*.env``) are backed up to ``<file>.env.bak.<unix-ts>``.

Detection covers:

============== ============================================ =====================
Agent          Binary Fingerprint                            Config Fingerprint
============== ============================================ =====================
Goose          ``goose``                                     ``~/.config/goose/config.yaml``
Claude Code    ``claude``                                     ``~/.claude/settings.json``
Interpreter    ``interpreter``                                ``~/.config/interpreter/config.json``
Aider          ``aider``                                     ``~/.aider.conf.{yml,yaml}``
Continue (opt) ``continue`` launcher or ``~/.continue``      ``~/.continue/config.json``
opencode       ``opencode``                                   ``~/.config/opencode/config.json``
LM Studio      ``lms`` CLI                                    (no file; runtime check)
Ollama         ``ollama`` CLI                                 (no file; runtime check)
============== ============================================ =====================

The full inventory is printed regardless of which agents are present
because other agents may need to be installed manually before LIMEN
can act as their backend.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import stat
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable  # noqa: TC003 — runtime-resolved annotations.
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
except ImportError as exc:  # pragma: no cover - yaml is part of the dev toolchain.
    raise SystemExit(
        "scripts/launch_limen.py requires PyYAML. Install with `uv pip install pyyaml` "
        "or `python3 -m pip install --user pyyaml`."
    ) from exc

LIMEN_DEFAULT_MODEL = "llama-3.3-70b-versatile"
LIMEN_DEFAULT_BASE_URL = "http://127.0.0.1:8000/v1"
LIMEN_API_KEY_PLACEHOLDER = "limen-local"
PROMPT_YES = {"y", "yes", "j", "ja"}


# ─────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AgentProfile:
    """Description of one supported agent integration."""

    name: str
    description: str
    binary_candidates: tuple[str, ...]
    config_search_paths: tuple[Path, ...]
    backup_suffix: str  # appended to original file path on backup
    patcher: Callable[[Path, dict[str, Any], dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class DetectionResult:
    """Single row in the agent inventory table."""

    name: str
    installed: bool
    binary_path: str | None
    config_path: Path | None
    config_exists: bool
    notes: tuple[str, ...] = field(default_factory=tuple)


# ─────────────────────────────────────────────────────────────────────────
# Patchers (one per agent)
# ─────────────────────────────────────────────────────────────────────────


def _patch_goose(path: Path, options: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    """Add or overwrite a ``limen_local`` provider entry in Goose config."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    data = yaml.safe_load(text) if text.strip() else {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: not a YAML mapping at top level")
    providers = data.setdefault("providers", {})
    if not isinstance(providers, dict):
        raise ValueError(f"{path}: 'providers' is not a mapping")
    provider_name = options.get("provider_name", "limen_local")
    providers[provider_name] = {
        "enabled": True,
        "model": options["model"],
        "configured": True,
        "host": options["base_url"].rsplit("/v1", 1)[0],
    }
    rendered = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    summary["provider_name"] = provider_name
    summary["previous_providers"] = sorted(providers.keys())
    return {"render": rendered, "write_path": path}


def _patch_claude(path: Path, options: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    """Patch ``~/.claude/settings.json`` to route the next chat through LIMEN."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    data = json.loads(text) if text.strip() else {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: not a JSON object at top level")
    provider_name = options.get("provider_name", "limen_local")
    target_model = f"{provider_name}/{options['model']}"
    previous_model = data.get("model")
    data["model"] = target_model
    data.setdefault("env", {})
    env_block = data["env"]
    if not isinstance(env_block, dict):
        raise ValueError(f"{path}: 'env' must be a JSON object")
    env_block["ANTHROPIC_BASE_URL"] = options["base_url"]
    env_block["ANTHROPIC_API_KEY"] = options["api_key"]
    summary["provider_name"] = provider_name
    summary["previous_model"] = previous_model
    summary["target_model"] = target_model
    return {
        "render": json.dumps(data, indent=2) + "\n",
        "write_path": path,
    }


def _patch_interpreter(
    path: Path, options: dict[str, Any], summary: dict[str, Any]
) -> dict[str, Any]:
    """Add a ``limen-local`` profile to Open Interpreter's config."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    data = json.loads(text) if text.strip() else {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: not a JSON object at top level")
    profiles = data.setdefault("profiles", [])
    if not isinstance(profiles, list):
        raise ValueError(f"{path}: 'profiles' is not an array")
    provider_name = options.get("provider_name", "limen_local")
    profile_id = f"limen:{provider_name}"
    new_profile = {
        "id": profile_id,
        "name": f"LIMEN {options['model']}",
        "provider": "api",
        "modelId": options["model"],
        "apiKey": options["api_key"],
        "apiFormat": "openai",
        "baseURL": options["base_url"],
        "isBuiltin": False,
    }
    summary["provider_name"] = provider_name
    summary["profile_id"] = profile_id
    summary["previous_profiles"] = [p.get("id") for p in profiles if isinstance(p, dict)]
    profiles.append(new_profile)
    return {
        "render": json.dumps(data, indent=2) + "\n",
        "write_path": path,
    }


def _patch_aider(path: Path, options: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    """Render an Aider-friendly YAML config pointing at LIMEN."""
    provider_name = options.get("provider_name", "limen_local")
    body = {
        "model": f"openai/{options['model']}",
        "openai-api-base": options["base_url"],
        "openai-api-key": options["api_key"],
        "extra-env": f"LIMEN_PROVIDER={provider_name}",
    }
    rendered_lines = [f"# LIMEN launcher @ {_dt.datetime.now().isoformat(timespec='seconds')}"]
    for key, value in body.items():
        rendered_lines.append(f"{key}: {json.dumps(value)}")
    summary["provider_name"] = provider_name
    summary["rendered_keys"] = sorted(body.keys())
    return {"render": "\n".join(rendered_lines) + "\n", "write_path": path}


def _patch_continue(path: Path, options: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    """Render a minimal Continue config that points at LIMEN as the default model."""
    provider_name = options.get("provider_name", "limen_local")
    data = {
        "models": [
            {
                "title": f"LIMEN {options['model']}",
                "provider": "openai",
                "model": options["model"],
                "apiBase": options["base_url"],
                "apiKey": options["api_key"],
            }
        ],
        "tabAutocompleteModel": {
            "title": f"LIMEN {options['model']} autocomplete",
            "provider": "openai",
            "model": options["model"],
            "apiBase": options["base_url"],
            "apiKey": options["api_key"],
        },
        "metadata": {
            "limen_provider": provider_name,
            "managed_by": "scripts/launch_limen.py",
        },
    }
    summary["provider_name"] = provider_name
    summary["rendered_keys"] = sorted(data.keys())
    return {"render": json.dumps(data, indent=2) + "\n", "write_path": path}


def _patch_opencode(path: Path, options: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    """Render a minimal opencode config that toggles the LIMEN provider on."""
    provider_name = options.get("provider_name", "limen_local")
    data: dict[str, Any] = {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            provider_name: {
                "npm": "@ai-sdk/openai-compatible",
                "name": f"LIMEN ({options['model']})",
                "options": {
                    "baseURL": options["base_url"],
                    "apiKey": options["api_key"],
                },
                "models": {
                    options["model"]: {},
                },
            }
        },
    }
    summary["provider_name"] = provider_name
    summary["rendered_keys"] = sorted(data.keys())
    return {"render": json.dumps(data, indent=2) + "\n", "write_path": path}


# ─────────────────────────────────────────────────────────────────────────
# Profile registry (order = display order)
# ─────────────────────────────────────────────────────────────────────────

HOME = Path(os.environ.get("HOME", str(Path.home())))


PROFILES: tuple[AgentProfile, ...] = (
    AgentProfile(
        name="goose",
        description="Block's Goose desktop client (YAML, ~/.config/goose/config.yaml).",
        binary_candidates=("goose",),
        config_search_paths=(HOME / ".config" / "goose" / "config.yaml",),
        backup_suffix=".bak",
        patcher=_patch_goose,
    ),
    AgentProfile(
        name="claude",
        description="Anthropic Claude Code CLI (JSON, ~/.claude/settings.json).",
        binary_candidates=("claude",),
        config_search_paths=(HOME / ".claude" / "settings.json",),
        backup_suffix=".bak",
        patcher=_patch_claude,
    ),
    AgentProfile(
        name="interpreter",
        description="Open Interpreter desktop/runtime (JSON, ~/.config/interpreter/config.json).",
        binary_candidates=("interpreter",),
        config_search_paths=(HOME / ".config" / "interpreter" / "config.json",),
        backup_suffix=".bak",
        patcher=_patch_interpreter,
    ),
    AgentProfile(
        name="aider",
        description="Aider chat CLI (YAML, ~/.aider.conf.yml).",
        binary_candidates=("aider",),
        config_search_paths=(
            HOME / ".aider.conf.yml",
            HOME / ".aider.conf.yaml",
        ),
        backup_suffix=".bak",
        patcher=_patch_aider,
    ),
    AgentProfile(
        name="continue",
        description="Continue.dev VS Code/JetBrains extension (JSON, ~/.continue/config.json).",
        binary_candidates=("continue",),
        config_search_paths=(HOME / ".continue" / "config.json",),
        backup_suffix=".bak",
        patcher=_patch_continue,
    ),
    AgentProfile(
        name="opencode",
        description="opencode CLI/editor (JSON, ~/.config/opencode/config.json).",
        binary_candidates=("opencode",),
        config_search_paths=(HOME / ".config" / "opencode" / "config.json",),
        backup_suffix=".bak",
        patcher=_patch_opencode,
    ),
)


# ─────────────────────────────────────────────────────────────────────────
# Detection helpers
# ─────────────────────────────────────────────────────────────────────────


def _which(candidates: Iterable[str]) -> str | None:
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    return None


def _first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def detect_agent(profile: AgentProfile) -> DetectionResult:
    """Compute a DetectionResult for a single agent profile."""
    binary = _which(profile.binary_candidates)
    config = _first_existing(profile.config_search_paths)
    notes: list[str] = []
    if binary is None and config is None:
        notes.append("not installed")
    elif binary is None:
        notes.append("binary missing — install first")
    elif config is None:
        notes.append("no config file yet — patch will create one")
    return DetectionResult(
        name=profile.name,
        installed=binary is not None,
        binary_path=binary,
        config_path=config or profile.config_search_paths[0],
        config_exists=config is not None,
        notes=tuple(notes),
    )


def detect_all() -> list[DetectionResult]:
    return [detect_agent(profile) for profile in PROFILES]


# ─────────────────────────────────────────────────────────────────────────
# Render / display helpers
# ─────────────────────────────────────────────────────────────────────────


def _format_inventory(results: list[DetectionResult]) -> str:
    """Build a human-readable table of detected agents."""
    rows: list[str] = []
    rows.append("agent            installed  binary                                    config")
    rows.append(
        "---------------  ---------  ----------------------------------------  -------------------"
    )  # noqa: E501 — fixed-width inventory header.
    for index, result in enumerate(results, start=1):
        binary = result.binary_path or "—"
        config = str(result.config_path) if result.config_path else "—"
        config_marker = "(exists)" if result.config_exists else "(missing — would create)"
        rows.append(
            f"[{index}] {result.name:<13}  "
            f"{'yes' if result.installed else 'no ':<10}  "
            f"{binary:<38}  {config} {config_marker}"
        )
    return "\n".join(rows)


def _read_limen_options(repo_root: Path) -> dict[str, Any]:
    """Read LIMEN's effective config (or fall back to safe defaults)."""
    config_path = Path(
        os.environ.get("LIMEN_CONFIG", str(Path.home() / ".config" / "limen" / "config.toml"))
    )
    defaults: dict[str, Any] = {
        "model": LIMEN_DEFAULT_MODEL,
        "base_url": LIMEN_DEFAULT_BASE_URL,
        "api_key": LIMEN_API_KEY_PLACEHOLDER,
        "provider_name": "limen_local",
    }
    if not config_path.exists():
        return defaults
    candidate_paths: list[Path] = [config_path, repo_root / "config.toml.example"]
    for path in candidate_paths:
        if not path.exists():
            continue
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        providers = data.get("providers", {})
        if not isinstance(providers, dict):
            continue
        for name in sorted(providers.keys()):
            provider = providers[name]
            if not isinstance(provider, dict) or not provider.get("enabled", False):
                continue
            models = provider.get("models") or []
            if models:
                defaults["model"] = models[0]
                defaults["provider_name"] = name
                base_url = provider.get("base_url")
                if isinstance(base_url, str) and base_url:
                    stripped = base_url.rstrip("/")
                    if not stripped.endswith("/v1"):
                        stripped = stripped + "/v1"
                    defaults["base_url"] = stripped
                break
        break
    return defaults


# ─────────────────────────────────────────────────────────────────────────
# Backup / patch workflow
# ─────────────────────────────────────────────────────────────────────────


def _backup_target(profile: AgentProfile, target: Path) -> Path:
    """Compute the timestamped backup path for ``target``."""
    timestamp = _dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    if target.suffix and target.suffix.lower() == ".env":
        return target.with_suffix(f".env{profile.backup_suffix}.{timestamp}")
    if profile.backup_suffix.startswith("."):
        return target.with_name(f"{target.name}{profile.backup_suffix}.{timestamp}")
    return target.with_suffix(f"{target.suffix}{profile.backup_suffix}.{timestamp}")


def _confirm(plan: str) -> bool:
    """Prompt the user with ``plan`` and require a 'y' to proceed."""
    print(plan)
    sys.stdout.write("Proceed? [y/N]: ")
    sys.stdout.flush()
    answer = sys.stdin.readline().strip().lower()
    return answer in PROMPT_YES


def perform_swap(
    profile: AgentProfile,
    target: Path,
    options: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    """Run backup + patch for a given agent. Returns a human-readable summary dict."""
    summary: dict[str, Any] = {
        "agent": profile.name,
        "target": str(target),
        "options": dict(options),
    }
    backup = _backup_target(profile, target)
    summary["backup"] = str(backup)
    if target.exists():
        original_mode = stat.S_IMODE(target.stat().st_mode)
    else:
        original_mode = 0o600  # LIMEN standard for created files.
    summary["original_mode"] = f"{original_mode:04o}"

    plan_lines = [
        f"[plan] Agent            : {profile.name}",
        f"[plan] Target           : {target}",
        f"[plan] Backup →         : {backup}",
        f"[plan] Provider name    : {options.get('provider_name', 'limen_local')}",
        f"[plan] Model            : {options['model']}",
        f"[plan] Base URL         : {options['base_url']}",
        f"[plan] API key          : {options['api_key']} (placeholder; Phase 1 has no auth check)",  # noqa: E501
    ]
    if not target.exists():
        plan_lines.append("[plan] Note             : config file missing — LIMEN creates it.")
    if not dry_run and not _confirm("\n".join(plan_lines)):
        summary["status"] = "declined"
        return summary

    summary["status"] = "dry-run" if dry_run else "applied"
    if dry_run:
        return summary

    backup.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        with open(target, "rb") as source:
            original_bytes = source.read()
        backup.write_bytes(original_bytes)
    else:
        # Fehlende Config: leerer Backup — Patcher erzeugt die Datei neu.
        backup.write_bytes(b"")
    os.chmod(backup, original_mode if original_mode else 0o600)

    patch_summary: dict[str, Any] = {}
    render_result = profile.patcher(target, options, patch_summary)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_result["render"], encoding="utf-8")
    os.chmod(target, original_mode if original_mode else 0o600)

    summary["patch"] = patch_summary
    summary["rendered_size"] = target.stat().st_size
    return summary


# ─────────────────────────────────────────────────────────────────────────
# LIMEN lifecycle helpers
# ─────────────────────────────────────────────────────────────────────────


def _health_ready(base_url: str, timeout_seconds: float = 5.0) -> bool:
    """Poll ``/health`` on the running LIMEN process for readiness."""
    deadline = _dt.datetime.now() + _dt.timedelta(seconds=timeout_seconds)
    health_url = base_url.replace("/v1", "/health")  # noqa: S310 — localhost only.
    while _dt.datetime.now() < deadline:
        try:
            with urllib.request.urlopen(  # noqa: S310 — localhost only.
                health_url, timeout=1.5
            ) as response:
                if 200 <= response.status < 300:
                    return True
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
    return False


def start_limen(base_url: str, config_path: Path | None) -> int:
    """Spawn ``limen start`` as a background process and verify /health."""
    cmd: list[str] = ["python3", "-m", "limen.cli", "start"]
    if config_path is not None:
        cmd.extend(["--config", str(config_path)])
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", "src")
    print(f"[start] {' '.join(cmd)}")
    process = subprocess.Popen(cmd, env=env)  # noqa: S603 — local process under our CLI only.
    try:
        if _health_ready(base_url):
            print(f"[start] LIMEN /health reachable at {base_url.replace('/v1', '/health')}")
            return int(process.pid)
        print("[start] LIMEN did not respond within timeout", file=sys.stderr)
        return int(process.pid)
    finally:
        # Detach: do not wait; let caller decide how long to monitor.
        pass


def restore_backup(name: str) -> int:
    """Restore the most recent timestamped backup of ``name``'s primary config."""
    for profile in PROFILES:
        if profile.name != name:
            continue
        candidates: list[Path] = []
        for path in profile.config_search_paths:
            glob_pattern = f"{path.name}{profile.backup_suffix}.*"
            candidates.extend(sorted(path.parent.glob(glob_pattern)))
            glob_pattern = f"{path.stem}*.bak.*"
            candidates.extend(sorted(path.parent.glob(glob_pattern)))
        if not candidates:
            print(f"[restore] no backup found for {name}")
            return 1
        latest = candidates[-1]
        target = profile.config_search_paths[0]
        if latest.read_bytes() == b"" and target.exists():
            # Backup einer ursprünglich nicht-existenten Config: nach dem
            # Patcher-Schritt muss die Datei weg, nicht leerer Inhalt.
            target.unlink()
            print(f"[restore] {latest} → {target} (unlinked)")
        else:
            shutil.copy2(latest, target)
            print(f"[restore] {latest} → {target}")
        return 0
    print(f"[restore] unknown agent: {name}")
    return 1


# ─────────────────────────────────────────────────────────────────────────
# CLI plumbing
# ─────────────────────────────────────────────────────────────────────────


def _selected_profile(choice_text: str, results: list[DetectionResult]) -> AgentProfile:
    lookup = {result.name: profile for profile, result in zip(PROFILES, results, strict=True)}
    if choice_text.isdigit():
        index = int(choice_text)
        if 1 <= index <= len(results):
            return PROFILES[index - 1]
    if choice_text in lookup:
        return lookup[choice_text]
    raise SystemExit(f"unknown agent: {choice_text!r}")


def _ask_for_choice(results: list[DetectionResult]) -> AgentProfile | None:
    """Prompt the user for a numbered agent choice; returns None for ``0``."""
    print(_format_inventory(results))
    print(
        "\nChoose the agent whose config LIMEN should exchange. "
        "Enter 0 to skip swap and just start LIMEN."
    )
    sys.stdout.write("choice [0]: ")
    sys.stdout.flush()
    raw = sys.stdin.readline().strip() or "0"
    if raw == "0":
        return None
    return _selected_profile(raw, results)


def _mode_list(args: argparse.Namespace) -> int:
    print(_format_inventory(detect_all()))
    return 0


def _mode_dry_run(args: argparse.Namespace) -> int:
    results = detect_all()
    profile = _selected_profile(args.agent, results) if args.agent else _ask_for_choice(results)
    if profile is None:
        print("[dry-run] no swap requested.")
        return 0
    options = _read_limen_options(Path.cwd())
    summary = perform_swap(profile, profile.config_search_paths[0], options, dry_run=True)
    print("[dry-run] no files modified.")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def _mode_swap(args: argparse.Namespace) -> int:
    results = detect_all()
    if args.agent:
        profile = _selected_profile(args.agent, results)
    else:
        chosen = _ask_for_choice(results)
        if chosen is None:
            print("[swap] skipping exchange; starting LIMEN only.")
            return _mode_start(args)
        profile = chosen
    options = _read_limen_options(Path.cwd())
    summary = perform_swap(
        profile,
        profile.config_search_paths[0],
        options,
        dry_run=False,
    )
    if summary.get("status") != "applied":
        print(f"[swap] not applied: {summary.get('status')}")
        return 2
    print(f"[swap] applied → {summary['target']}")
    print(f"[swap] backup   ← {summary['backup']}")
    if args.start:
        start_limen(options["base_url"], args.config)
    return 0


def _mode_start(args: argparse.Namespace) -> int:
    options = _read_limen_options(Path.cwd())
    start_limen(options["base_url"], args.config)
    return 0


def _mode_restore(args: argparse.Namespace) -> int:
    return restore_backup(args.agent)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="launch_limen.py",
        description="LIMEN launcher with auto-detection, backup, and agent swap.",
    )
    sub = parser.add_subparsers(dest="mode", required=True)
    list_parser = sub.add_parser("list", help="show detected agents only")
    list_parser.set_defaults(func=_mode_list)
    dry_parser = sub.add_parser("dry-run", help="plan a swap without writing any files")
    dry_parser.add_argument("agent", nargs="?", help="agent name to plan")
    dry_parser.set_defaults(func=_mode_dry_run)
    swap_parser = sub.add_parser("swap", help="swap a single agent's config to LIMEN")
    swap_parser.add_argument("agent", nargs="?", help="agent name (interactive if absent)")
    swap_parser.add_argument("--start", action="store_true", help="start LIMEN after swap")
    swap_parser.add_argument("--config", type=Path, default=None, help="path to limen config.toml")
    swap_parser.set_defaults(func=_mode_swap)
    start_parser = sub.add_parser("start", help="start LIMEN without touching any agent")
    start_parser.add_argument("--config", type=Path, default=None, help="path to limen config.toml")
    start_parser.set_defaults(func=_mode_start)
    restore = sub.add_parser("restore", help="restore the most recent backup of an agent")
    restore.add_argument("agent", help="agent whose backup should be restored")
    restore.set_defaults(func=_mode_restore)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
