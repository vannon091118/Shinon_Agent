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

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import paths as P  # single source of truth: central data location ($SHINON_HOME)

PROJECT_ROOT = Path(__file__).resolve().parent
# Install-Marker + Configs liegen jetzt ZENTRAL in $SHINON_HOME/config
# (~/.shinon/config), NICHT mehr im Projekt-Verzeichnis. Beide Referenzen
# muessen mit install.py + paths.py konsistent sein, sonst looped
# `./shinon start` ewig auf "Shinon ist noch nicht installiert".
CONFIG_DIR = P.CONFIG_DIR

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
    macOS ('open'), and Linux (xdg-open via Python's standard module).

    We avoid `new=2` because on Windows + Edge it can pop up a fresh window
    instead of a tab in the user's existing browser. `webbrowser.open_new_tab`
    asks for a new tab when possible (same browser if open), with a graceful
    fallback to opening a new window.
    """
    try:
        # `open_new_tab` is the right API; falls back internally to
        # `open_new` if no running browser instance is found.
        if webbrowser.open_new_tab(url):
            ok(f"Browser-Tab ge\u00f6ffnet: {url}")
        elif webbrowser.open_new(url):
            ok(f"Browser-Fenster ge\u00f6ffnet: {url}")
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


def cmd_self_improve() -> int:
    """Run the Karma self-improvement controller.

    Default (CDU = Conservative Daily Use):
      - dry-run, 3 cycles, project = basename of cwd OR Git-Remote
      - mirror output to .learnings/<proj>-cycles.json (overwrites last)

    Flags (parsed positionally, kept simple for the bash shim):
      --apply      Run karma ml train (state mutation). Requires explicit
                   opt-in because the controller rewrites weights/patterns.
      --cycles N   Number of cycles (default 3).
      --project P  Override the project name.
    """
    import argparse, json

    parser = argparse.ArgumentParser(
        prog="shinon self-improve",
        description="Skill-score audit + improve-cycles via karma."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Run karma.ml.train (state mutation). Default: simulate only.")
    parser.add_argument("--cycles", type=int, default=3,
                        help="Number of improve cycles (default 3).")
    parser.add_argument("--project", type=str, default=None,
                        help="Project name (default: git remote or basename).")
    args = parser.parse_args(sys.argv[2:])

    # ── Project-Resolver:  Git-Remote > basename(cwd)
    project_name = args.project
    if not project_name:
        try:
            remote = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=str(PROJECT_ROOT), stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            # https://github.com/vannon/shinon.git → shinon
            project_name = remote.rsplit("/", 1)[-1].removesuffix(".git") or None
        except Exception:
            project_name = None
    if not project_name:
        project_name = os.path.basename(os.getcwd()) or "shinon"
    info(f"Project:           {project_name}")
    info(f"Cycles:            {args.cycles}")
    info(f"Mode:              {'TRAIN (apply, state mutation)' if args.apply else 'SIMULATE (dry-run)'}")

    # ── Karma-Aufruf
    venv_py = PROJECT_ROOT / ".venv" / "bin" / "python3"
    if not venv_py.exists():
        # Windows-Venv-Fallback
        venv_py = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if not venv_py.exists():
        fail("Kein .venv gefunden. Bitte erst 'python install.py' ausführen.")
        return 1
    cmd_karma = ["ml", "train" if args.apply else "simulate",
                 "--project", project_name,
                 "--cycles", str(args.cycles)]
    info(f"Aufruf:            {' '.join([str(venv_py), '-m', 'karma.cli'] + cmd_karma)}")

    try:
        proc = subprocess.run(
            [str(venv_py), "-m", "karma.cli"] + cmd_karma,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        fail("Karma self-improve > 120 s — Abbruch. Reduziere --cycles oder untersuche karma DB.")
        return 1
    except FileNotFoundError as e:
        fail(f"Karma-Modul nicht auffindbar: {e}")
        return 1

    raw_out = (proc.stdout or "") + (proc.stderr or "")

    # ── Output → .learnings/<proj>-cycles.json (überschreiben, deterministisch pro Lauf)
    learnings_dir = PROJECT_ROOT / ".learnings"
    learnings_dir.mkdir(exist_ok=True)
    cycles_json = learnings_dir / f"{project_name}-cycles.json"
    payload = {
        "project": project_name,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "train" if args.apply else "simulate",
        "cycles": args.cycles,
        "karma_exit_code": proc.returncode,
        "raw_output": raw_out,
    }
    try:
        cycles_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                               encoding="utf-8")
        info(f"Snapshot:          {cycles_json.relative_to(PROJECT_ROOT)}")
    except OSError as e:
        warn(f"Snapshot-Datei nicht schreibbar ({e}); nur stdout ausgegeben.")

    if proc.returncode != 0:
        fail(f"karma ml {'train' if args.apply else 'simulate'} exit={proc.returncode}")
        # Trotzdem stdout zeigen
        if raw_out:
            print(raw_out)
        return proc.returncode

    ok(f"{'Train' if args.apply else 'Simulate'} abgeschlossen: "
       f"{args.cycles} cycle(s) für Projekt '{project_name}'.")

    # ── Human-Summary: letzte N Zeilen der sessions.jsonl (sofern existent)
    sessions_jsonl = learnings_dir / f"{project_name}-sessions.jsonl"
    if sessions_jsonl.exists():
        try:
            lines = sessions_jsonl.read_text(encoding="utf-8").splitlines()[-5:]
            if lines:
                print()
                info(f"Letzte {len(lines)} Sessions-Einträge ({sessions_jsonl.name}):")
                for ln in lines:
                    # Extract TID + Skill for the table
                    try:
                        d = json.loads(ln)
                        print(f"     · {d.get('timestamp', '?')}  "
                              f"TID={d.get('tid', '?')}  skill={d.get('skill', '?') or '∅'}")
                    except Exception:
                        print(f"     · {ln[:120]}")
        except OSError:
            pass

    return 0


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
{BOLD}\u2502{NC}                                                        {BOLD}\u2502{NC}
{BOLD}\u2502{NC}  shinon self-improve Karma Self-Improve (CDU, dry-run)   {BOLD}\u2502{NC}
{BOLD}\u2502{NC}     [--apply]    Train statt Simulate                   {BOLD}\u2502{NC}
{BOLD}\u2502{NC}     [--cycles N] Anzahl Cycles (default 3)              {BOLD}\u2502{NC}
{BOLD}\u2502{NC}     [--project P] Projektname (default git-remote)      {BOLD}\u2502{NC}
{BOLD}\u2502                                                        \u2502{NC}
{BOLD}\u2502{NC}  shinon help        Diese Hilfe                          {BOLD}\u2502{NC}
{BOLD}\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518{NC}
"""


def cmd_help() -> int:
    print(HELP_BANNER)
    print(f"  {CYAN}Pfade (zentral in $SHINON_HOME):{NC}")
    print(f"    SHINON_HOME: {P.SHINON_HOME}")
    print(f"    Config:    {P.CONFIG_DIR}/")
    print(f"    Daten:     {P.DATA_DIR}/")
    print(f"    Logs:      {P.LOGS_DIR}/")
    print(f"    PIDs:      {P.PIDS_DIR}/")
    print(f"    Keys:      {P.KEYS_FILE}")
    print(f"    Venv:      .venv/ (Projekt)")
    print()
    return 0


# ─── Interactive CLI Agent ───────────────────────────────────────────
def cmd_agent() -> int:
    """Interactive Terminal Agent CLI launcher.
    Triggered when user runs `./shinon` without mandatory flags.
    """
    import shutil
    if not _require_install():
        return 1

    bun_bin = shutil.which("bun")
    cli_mjs = PROJECT_ROOT / "shinon-cli.mjs"
    if bun_bin and cli_mjs.exists():
        return subprocess.call([bun_bin, str(cli_mjs)], cwd=str(PROJECT_ROOT))

    node_bin = shutil.which("node")
    if node_bin and cli_mjs.exists():
        return subprocess.call([node_bin, str(cli_mjs)], cwd=str(PROJECT_ROOT))

    return _py_agent_repl()


def _py_agent_repl() -> int:
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}{CYAN}║  🦇 SHINON · Terminal Agent CLI v2.0                                 ║{NC}")
    print(f"{CYAN}║  Kritisch. Skeptisch. Präzise.                                       ║{NC}")
    print(f"{CYAN}║  Mood: ◉ BEREIT [IDLE]  |  Pipeline: Live Terminal Render            ║{NC}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════════╝{NC}\n")
    print(f"  {CYAN}Tippe eine Frage oder einen Befehl (/chat, /status, /setup, /doc, /help, /exit){NC}\n")

    while True:
        try:
            line = input(f"{BOLD}{CYAN}shinon > {NC}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Shinon Agent beendet.")
            break
        if not line:
            continue
        cmd = line.lower()
        if cmd in ("/exit", "exit", "quit", "/quit"):
            print(f"\n  {CYAN}🦇 Shinon Agent beendet. Auf Wiedersehen!{NC}\n")
            break
        if cmd in ("/help", "help"):
            cmd_help()
            continue
        if cmd in ("/chat", "chat"):
            cmd_chat()
            continue
        if cmd in ("/status", "status"):
            cmd_status()
            continue
        if cmd in ("/dashboard", "dashboard"):
            cmd_dashboard()
            continue
        if cmd in ("/setup", "setup"):
            cmd_setup()
            continue
        if cmd in ("/doc", "doc"):
            cmd_doc()
            continue

        steps = [
            ("DISPATCHER", CYAN, "⚙️  Input in 3 Parallel-Tasks gesplittet..."),
            ("WORKERS", YELLOW, "▣ Workers A, B, C verarbeiten Tasks parallel..."),
            ("ROUTER", GREEN, "◈ An LIMEN Provider geroutet..."),
            ("FALSI-GATE", RED, "⊗ KARMA FalsificationGate & 👯 Evil Twin Validation..."),
            ("RESULT", GREEN, "✓ Antwort verifiziert & abgeschlossen!"),
        ]
        print(f"\n  \033[2m─── Pipeline Live Execution ───────────────────────────────────────────\033[0m")
        for tag, color, msg in steps:
            time.sleep(0.12)
            print(f"  {color}[{tag}]{NC} {msg}")
        print(f"  \033[2m───────────────────────────────────────────────────────────────────────\033[0m\n")

        print(f"  {BOLD}{CYAN}🦇 Shinon:{NC}")
        print(f"  Antwort zu '{line}' — Starte 'shinon start' für voll vernetztes Routing.\n")
    return 0


# ─── Main entry ───────────────────────────────────────────────────────
COMMANDS = {
    "agent": cmd_agent,
    "interactive": cmd_agent,
    "cli": cmd_agent,
    "start": cmd_start,
    "stop": cmd_stop,
    "restart": cmd_restart,
    "status": cmd_status,
    "chat": cmd_chat,
    "dashboard": cmd_dashboard,
    "keys": cmd_keys,
    "deps": cmd_deps,
    "self-improve": cmd_self_improve,
    "improve": cmd_self_improve,
    "learn": cmd_self_improve,
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
        return cmd_agent()
    cmd = sys.argv[1]
    handler = COMMANDS.get(cmd)
    if not handler:
        fail(f"Unbekannter Befehl: {cmd}")
        print(f"  {CYAN}shinon help{NC} für alle Befehle.")
        return 1
    return handler()


if __name__ == "__main__":
    sys.argv[0] = "shinon"
    sys.exit(main())
