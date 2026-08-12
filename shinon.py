#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════
# shinon.py — Cross-Platform User CLI für die Shinon Control Plane
#
# Vereint Start/Stop, Onboarding, Diagnose und Chat unter einem Befehl.
# Replaces the bash `shinon` script. Cross-platform, no $HOME lookups.
#
# Usage:
#   python shinon.py                     shows help
#   python shinon.py start               starts all components
#   python shinon.py stop                stops everything
#   python shinon.py status              shows running components
#   python shinon.py chat                opens the chat UI in browser
#   python shinon.py dashboard           opens the live dashboard
#   python shinon.py --setup             runs the onboarding wizard
#   python shinon.py --doc               runs Doctor Mous diagnosis
#   python shinon.py help                shows the help banner
#
# Thin wrappers in front of this script:
#   Linux/macOS: ./shinon  (bash shim)
#   Windows:     shinon.cmd
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config"

# ─── ANSI Colours ─────────────────────────────────────────────────────
def _supports_colour() -> bool:
    return sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb"


_C = _supports_colour()
RED = "\033[31m" if _C else ""
GREEN = "\033[32m" if _C else ""
YELLOW = "\033[33m" if _C else ""
CYAN = "\033[36m" if _C else ""
BOLD = "\033[1m" if _C else ""
NC = "\033[0m" if _C else ""


def ok(msg: str) -> None: print(f"  {GREEN}\u2705{NC} {msg}")
def warn(msg: str) -> None: print(f"  {YELLOW}\u26a0\ufe0f {NC} {msg}")
def fail(msg: str) -> None: print(f"  {RED}\u274c{NC} {msg}")
def info(msg: str) -> None: print(f"  {CYAN}\u2139{NC}  {msg}")


# ─── Helper: delegate to another python script in the same project ────
def _run(script: str, args: list[str]) -> int:
    py = sys.executable
    cmd = [py, str(PROJECT_ROOT / script), *args]
    return subprocess.call(cmd, cwd=str(PROJECT_ROOT))


def _open_url(url: str) -> None:
    """Open a URL in the user's default browser, cross-platform.

    webbrowser.open works on Windows (os.startfile under the hood),
    macOS ('open'), and Linux (xdg-open via Python's standard module)."""
    try:
        if webbrowser.open(url, new=2):
            ok(f"Browser ge\u00f6ffnet: {url}")
        else:
            info(f"\u00d6ffne manuell: {url}")
    except Exception as e:
        info(f"Konnte Browser nicht \u00f6ffnen ({e}). URL: {url}")


# ─── Pre-flight: ensure install ran ───────────────────────────────────
def _require_install() -> bool:
    marker = CONFIG_DIR / ".install-done"
    if marker.exists():
        return True
    warn("Shinon ist noch nicht installiert.")
    info("Starte Installation mit: python install.py --quick")
    if not sys.stdin.isatty():
        fail("Kein TTY \u2013 starte install.py direkt im selben Schritt.")
        return _run("install.py", ["--quick"]) == 0 and marker.exists()
    try:
        ans = input("  Jetzt installieren? (J/n): ").strip().lower()
    except EOFError:
        return False
    if ans in ("n", "no"):
        return False
    rc = _run("install.py", [])
    return rc == 0 and marker.exists()


# ─── Subcommands ──────────────────────────────────────────────────────
def cmd_start() -> int:
    if not _require_install():
        return 1
    return _run("ctl.py", ["start", "all"])


def cmd_stop() -> int:
    return _run("ctl.py", ["stop", "all"])


def cmd_restart() -> int:
    return _run("ctl.py", ["restart", "all"])


def cmd_status() -> int:
    return _run("ctl.py", ["status"])


def cmd_chat() -> int:
    if not _require_install():
        return 1
    _run("ctl.py", ["start", "limen"])
    time.sleep(1)
    _run("ctl.py", ["start", "shinon-ui"])
    time.sleep(1)
    ok("Chat verf\u00fcgbar unter: http://127.0.0.1:4300")
    _open_url("http://127.0.0.1:4300")
    return 0


def cmd_dashboard() -> int:
    if not _require_install():
        return 1
    _run("ctl.py", ["start", "dashboard"])
    time.sleep(1)
    ok("Dashboard verf\u00fcgbar unter: http://127.0.0.1:4200")
    _open_url("http://127.0.0.1:4200")
    return 0


def cmd_keys() -> int:
    if not _require_install():
        return 1
    _run("ctl.py", ["start", "limen"])
    time.sleep(1)
    ok("Key-Management: http://127.0.0.1:8000/leitstand")
    _open_url("http://127.0.0.1:8000/leitstand")
    return 0


def cmd_setup() -> int:
    if not _require_install():
        return 1
    return _run("shinon-setup.py", [])


def cmd_doc() -> int:
    return _run("shinon-setup.py", ["--doc"])


def cmd_deps() -> int:
    return _run("ctl.py", ["deps"])


# ─── Help & banner ───────────────────────────────────────────────────
HELP_BANNER = f"""{BOLD}
\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
\u2551  \U0001f987 SHINON \u2014 Control Plane CLI (cross-platform)         \u2551
\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d
{NC}

Kritisch. Skeptisch. Pr\u00e4zise.
Dein AI-Control-Center f\u00fcr Prompt-Engineering und API-Management.

{BOLD}\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510{NC}
{BOLD}\u2502  Befehle:                                              \u2502{NC}
{BOLD}\u2502                                                        \u2502{NC}
{BOLD}\u2502{NC}  shinon start       alle Komponenten starten              {BOLD}\u2502{NC}
{BOLD}\u2502{NC}  shinon stop        alle Komponenten stoppen               {BOLD}\u2502{NC}
{BOLD}\u2502{NC}  shinon restart     Neustart                              {BOLD}\u2502{NC}
{BOLD}\u2502{NC}  shinon status      Status aller Komponenten              {BOLD}\u2502{NC}
{BOLD}\u2502                                                        \u2502{NC}
{BOLD}\u2502{NC}  shinon chat        Chat-Oberfl\u00e4che \u00f6ffnen (:4300)        {BOLD}\u2502{NC}
{BOLD}\u2502{NC}  shinon dashboard   Live-Dashboard \u00f6ffnen (:4200)         {BOLD}\u2502{NC}
{BOLD}\u2502{NC}  shinon keys        API-Key-Management (:8000/leitstand)  {BOLD}\u2502{NC}
{BOLD}\u2502                                                        \u2502{NC}
{BOLD}\u2502{NC}  shinon --setup     Onboarding-Wizard                    {BOLD}\u2502{NC}
{BOLD}\u2502{NC}  shinon --doc       Doctor Mous \u00b7 Diagnose & Reparatur  {BOLD}\u2502{NC}
{BOLD}\u2502{NC}  shinon deps        Abh\u00e4ngigkeiten pr\u00fcfen               {BOLD}\u2502{NC}
{BOLD}\u2502                                                        \u2502{NC}
{BOLD}\u2502{NC}  shinon help        Diese Hilfe                          {BOLD}\u2502{NC}
{BOLD}\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518{NC}
"""


def cmd_help() -> int:
    print(HELP_BANNER)
    print(f"  {CYAN}Pfade (im Projekt, nicht in $HOME):{NC}")
    print(f"    Config:    {CONFIG_DIR.relative_to(PROJECT_ROOT)}/")
    print(f"    Daten:     {(PROJECT_ROOT / 'data').relative_to(PROJECT_ROOT)}/")
    print(f"    Logs:      {(PROJECT_ROOT / 'data' / 'logs').relative_to(PROJECT_ROOT)}/")
    print(f"    PIDs:      {(PROJECT_ROOT / 'data' / 'pids').relative_to(PROJECT_ROOT)}/")
    print(f"    Venv:      .venv/")
    print()
    return 0


# ─── Main entry ───────────────────────────────────────────────────────
COMMANDS = {
    "start": cmd_start,
    "stop": cmd_stop,
    "restart": cmd_restart,
    "status": cmd_status,
    "chat": cmd_chat,
    "dashboard": cmd_dashboard,
    "keys": cmd_keys,
    "deps": cmd_deps,
    "--setup": cmd_setup,
    "setup": cmd_setup,
    "--doc": cmd_doc,
    "doc": cmd_doc,
    "help": cmd_help,
    "--help": cmd_help,
    "-h": cmd_help,
}


def main() -> int:
    if len(sys.argv) < 2:
        return cmd_help()
    cmd = sys.argv[1]
    handler = COMMANDS.get(cmd)
    if not handler:
        fail(f"Unbekannter Befehl: {cmd}")
        print(f"  {CYAN}shinon help{NC} f\u00fcr alle Befehle.")
        return 1
    return handler()


if __name__ == "__main__":
    sys.exit(main())
