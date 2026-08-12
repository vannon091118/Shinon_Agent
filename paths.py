#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════
# paths.py — Single source of truth for Shinon data directories.
#
# Why this exists:  The Shinon install used to scatter data across
#   ~/.limen/keys.json
#   <project>/data/limen/limen.db
#   <project>/limen-main/data/limen-prod.db
#   <project>/limen-main/data/providers.db
#   <project>/data/shinon/memory.db
#   <project>/fusion-main/data/shinon_memory.db
#   <project>/.agents/skills/goal-chain/db/tid-state.db
#   <project>/data/{logs,pids}/
#   <project>/config/*.toml
#
# Everything now lives under a single directory:
#   $SHINON_HOME  (default: $HOME/.shinon on Linux/Mac,
#                            %USERPROFILE%\\.shinon on Windows)
#
#   $SHINON_HOME/
#     config/                    <- shinon.toml, limen.toml, .env
#     keys.json                  <- API keys (0600)
#     data/
#       limen/limen.db
#       karma/karma.db
#       shinon/memory.db         <- fusion-Schema (personal_facts/patterns/pattern_links)
#       shinon/attitudes.db      <- fusion-Schema (attitudes/attitude_history)
#       goal-chain/tid-state.db
#     logs/
#     pids/
#
# Override priority:
#   1. SHINON_HOME env var  (highest — useful for testing / CI / multi-install)
#   2. $HOME/.shinon         (default on Linux + macOS)
#   3. %USERPROFILE%\.shinon (default on Windows)
#
# Project-relative paths are also still exposed (PROJECT_*) for install / lint /
# CLI scripts that need to know where the code repo lives.  *Runtime* data never
# lives there — only source.
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

# ─── Project root (where the source lives) ────────────────────────────
# paths.py sits at the project root (next to shinon.py / install.py).
PROJECT_ROOT = Path(__file__).resolve().parent


# ─── Default SHINON_HOME: ~/.shinon  (cross-platform) ─────────────────
def _default_shinon_home() -> Path:
    """Pick the default central location.

    Linux/macOS: $HOME/.shinon  (resolves to /home/<user>/.shinon)
    Windows:     %USERPROFILE%\\.shinon  (resolves to C:\\Users\\<user>\\.shinon)
    Fallback for stale env (CI, sandboxed):  <project>/.shinon-fallback
    """
    explicit = os.environ.get("SHINON_HOME")
    if explicit:
        return Path(explicit).expanduser().resolve()

    if platform.system() == "Windows":
        userprofile = os.environ.get("USERPROFILE") or os.environ.get("HOME")
        if userprofile:
            return Path(userprofile) / ".shinon"
    home = os.environ.get("HOME")
    if home:
        return Path(home) / ".shinon"

    # No $HOME at all — extremely rare.  Last resort: project-local fallback,
    # so we never silently write to "/" or the process cwd.
    return PROJECT_ROOT / ".shinon-fallback"


SHINON_HOME = _default_shinon_home()

# Central layout
CONFIG_DIR     = SHINON_HOME / "config"
KEYS_FILE      = SHINON_HOME / "keys.json"          # 0600, owned by user
DATA_DIR       = SHINON_HOME / "data"
LIMEN_DIR      = DATA_DIR / "limen"
LIMEN_DB       = LIMEN_DIR / "limen.db"
KARMA_DIR      = DATA_DIR / "karma"
KARMA_DB       = KARMA_DIR / "karma.db"
SHINON_DIR     = DATA_DIR / "shinon"
SHINON_MEM     = SHINON_DIR / "memory.db"
SHINON_ATTITUDES = SHINON_DIR / "attitudes.db"
GOALCHAIN_DIR  = DATA_DIR / "goal-chain"
GOALCHAIN_DB   = GOALCHAIN_DIR / "tid-state.db"
LOGS_DIR       = SHINON_HOME / "logs"
PIDS_DIR       = SHINON_HOME / "pids"
MODELS_DIR     = SHINON_HOME / "models"
BIN_DIR        = SHINON_HOME / "bin"

# ─── Project layout (source — never moves) ────────────────────────────
PROJECT_VENV     = PROJECT_ROOT / ".venv"
PROJECT_LIMEN_SRC = PROJECT_ROOT / "limen-main"
PROJECT_KARMA_SRC = PROJECT_ROOT / "karma-main"
PROJECT_FUSION_SRC = PROJECT_ROOT / "fusion-main"
PROJECT_LIMEN_PKG = PROJECT_ROOT / "limen-main"          # editable install root
PROJECT_LIMEN_DB_LEGACY_A = PROJECT_ROOT / "limen-main" / "data" / "limen-prod.db"
PROJECT_LIMEN_DB_LEGACY_B = PROJECT_ROOT / "limen-main" / "data" / "providers.db"
PROJECT_FUSION_MEM         = PROJECT_ROOT / "fusion-main" / "data" / "shinon_memory.db"
PROJECT_FUSION_ATTITUDES   = PROJECT_ROOT / "fusion-main" / "data" / "shinon_attitudes.db"
PROJECT_PROJECT_LIMEN_DB   = PROJECT_ROOT / "data" / "limen" / "limen.db"
PROJECT_PROJECT_KARMA_DB   = PROJECT_ROOT / "data" / "karma" / "karma.db"
PROJECT_PROJECT_SHINON_MEM = PROJECT_ROOT / "data" / "shinon" / "memory.db"
PROJECT_PROJECT_GOALCHAIN_DB = (
    PROJECT_ROOT / ".agents" / "skills" / "goal-chain" / "db" / "tid-state.db"
)
PROJECT_PROJECT_LOGS = PROJECT_ROOT / "data" / "logs"
PROJECT_PROJECT_PIDS = PROJECT_ROOT / "data" / "pids"

# Old key store paths LIMEN has hard-coded (we'll migrate these out)
LEGACY_KEY_STORE_PATHS = (
    Path("~/.limen/keys.json").expanduser(),
)

# ─── Helper: build the central layout on demand ───────────────────────
def ensure_layout() -> None:
    """Create the central directories (idempotent). Owner-only perms on POSIX."""
    for d in (CONFIG_DIR, LIMEN_DIR, KARMA_DIR, SHINON_DIR, GOALCHAIN_DIR,
              LOGS_DIR, PIDS_DIR, MODELS_DIR, BIN_DIR, SHINON_HOME):
        d.mkdir(parents=True, exist_ok=True)
        if platform.system() != "Windows":
            try:
                d.chmod(0o700)
            except OSError:
                # Best-effort. The dir might exist with broader perms we can't
                # narrow without sudo; that's fine — the *files* inside will
                # still be 0600.
                pass


def explain() -> str:
    """Human-readable summary for status / diagnostic output."""
    return (
        f"  Central home: {SHINON_HOME}\n"
        f"  Config:       {CONFIG_DIR.relative_to(SHINON_HOME) if SHINON_HOME in CONFIG_DIR.parents else CONFIG_DIR}\n"
        f"  Keys:         {KEYS_FILE.relative_to(SHINON_HOME) if SHINON_HOME in KEYS_FILE.parents else KEYS_FILE}\n"
        f"  DBs:          {DATA_DIR.relative_to(SHINON_HOME) if SHINON_HOME in DATA_DIR.parents else DATA_DIR}/\n"
        f"                  ├─ limen/   {LIMEN_DB.name}\n"
        f"                  ├─ karma/   {KARMA_DB.name}\n"
        f"                  ├─ shinon/  {SHINON_MEM.name}\n"
        f"                  └─ goal-chain/  {GOALCHAIN_DB.name}\n"
        f"  Logs:         {LOGS_DIR.relative_to(SHINON_HOME) if SHINON_HOME in LOGS_DIR.parents else LOGS_DIR}\n"
        f"  PIDs:         {PIDS_DIR.relative_to(SHINON_HOME) if SHINON_HOME in PIDS_DIR.parents else PIDS_DIR}\n"
        f"  Models:       {MODELS_DIR.relative_to(SHINON_HOME) if SHINON_HOME in MODELS_DIR.parents else MODELS_DIR}/\n"
        f"  Bin:          {BIN_DIR.relative_to(SHINON_HOME) if SHINON_HOME in BIN_DIR.parents else BIN_DIR}/\n"
        f"  Project root: {PROJECT_ROOT}\n"
    )


def main() -> int:
    """`python paths.py` — show the layout + sanity-check directory perms."""
    ensure_layout()
    print(f"Shinon paths (resolved)")
    print(explain())
    # Quick sanity-check
    writable = os.access(str(SHINON_HOME), os.W_OK)
    if not writable:
        print(f"  \u26a0\ufe0f  WARN: {SHINON_HOME} ist nicht schreibbar!", file=sys.stderr)
        return 1
    print(f"  \u2705  Layout ready (writable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
