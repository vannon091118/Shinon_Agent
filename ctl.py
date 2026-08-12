#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════
# ctl.py — Cross-Platform Component Lifecycle Manager
#
# Replaces the bash ctl script. Differences:
#   • Uses Python socket() for port detection (NEVER lsof)
#   • Uses project-relative ./data/ paths (NEVER $HOME or %USERPROFILE%)
#   • Uses single unified ./venv (NOT limen-main/.venv)
#   • Sets LIMEN_CONFIG=$PROJECT/config/limen.toml env-var for LIMEN
#   • Sets SHINON_DATA_DIR=$PROJECT/data/shinon for the front-end
#   • Works identically on Windows, Linux, macOS
#
# Commands:
#   python ctl.py start    [component]   Start one or all components
#   python ctl.py stop     [component]   Stop one or all components
#   python ctl.py restart  [component]   Stop + Start
#   python ctl.py status                 Show running components
#   python ctl.py kill                   Kill everything on control-plane ports
#   python ctl.py deps                   Check dependencies
#   python ctl.py ports                  Show port assignments
#
# Components: limen, shinon-ui, dashboard, all
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent

# ─── Path Constants (central: $SHINON_HOME, project: source code) ───────
# IMPORTANT: After install.py with paths.py, all DATA goes through SHINON_HOME
# (default ~/.shinon on Linux/Mac, %USERPROFILE%\.shinon on Windows). The project
# only houses SOURCE (shinon-server.mjs, venv, submodules). Ctl.py spawns
# subprocesses with env vars pointing at SHINON_HOME, NOT project-rel paths.
import paths as P

DATA_DIR = P.DATA_DIR
LOGS_DIR = P.LOGS_DIR
PIDS_DIR = P.PIDS_DIR
CONFIG_DIR = P.CONFIG_DIR
SHINON_DATA = P.SHINON_DIR
SHINON_CONFIG = P.CONFIG_DIR / "shinon.toml"
LIMEN_CONFIG = P.CONFIG_DIR / "limen.toml"
LIMEN_DB = P.LIMEN_DB
SHINON_SERVER_MJS = PROJECT_ROOT / "shinon-server.mjs"
DASHBOARD_SERVER = PROJECT_ROOT / ".agents" / "skills" / "goal-chain" / "scripts" / "live-dashboard-server.py"

# ─── Port Assignments ─────────────────────────────────────────────────
COMPONENT_PORTS: Dict[str, int] = {
    "limen": 8001,
    "shinon-ui": 4300,
    "dashboard": 4200,
}

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
def header(msg: str) -> None: print(f"\n{BOLD}\u2500\u2500\u2500 {msg} \u2500\u2500\u2500{NC}")


# ─── Python socket port-detection (replaces lsof) ─────────────────────
def port_in_use(port: int) -> Optional[int]:
    """Return PID occupying the port, or None. Uses /proc on Linux/Mac,
    falls back to socket-connect on Windows."""
    # Linux: read /proc/net/tcp (column 2 = local addr, column 10 = inode)
    if platform.system() != "Windows":
        try:
            with open("/proc/net/tcp") as f:
                next(f)  # header
                hex_port = f"{port:04X}"
                for line in f:
                    parts = line.split()
                    local = parts[1]
                    if ":" in local and local.split(":")[1] == hex_port:
                        inode = parts[9]
                        return _pid_for_inode_windows_safe(inode)
        except FileNotFoundError:
            pass

    # Cross-platform: try connecting
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return -1  # port is occupied but we don't know PID
    except (ConnectionRefusedError, socket.timeout, OSError):
        return None


def _pid_for_inode_windows_safe(inode: str) -> Optional[int]:
    """Map a Linux /proc inode → owning PID. Best-effort; returns None if
    the inode is unlinked or we lack permission."""
    for pid_dir in Path("/proc").iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            for fd in (pid_dir / "fd").iterdir():
                link = os.readlink(str(fd))
                if f"socket:[{inode}]" in link:
                    return int(pid_dir.name)
        except (FileNotFoundError, PermissionError, OSError):
            continue
    return None


# ─── Cross-platform process helpers ───────────────────────────────────
def is_running(pid: int) -> bool:
    """Cross-platform process-alive check (no `ps`, no `kill -0` shell-out)."""
    if pid <= 0:
        return False
    if platform.system() == "Windows":
        import ctypes  # type: ignore
        PROCESS_QUERY_LIMITED = 0x1000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
        if handle == 0:
            return False
        STILL_ACTIVE = 259
        code = ctypes.c_uint32()
        kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return code.value == STILL_ACTIVE
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def stop_pid(pid: int, force: bool = False) -> bool:
    """Cross-platform kill. Returns True if process is gone."""
    try:
        if platform.system() == "Windows":
            import ctypes  # type: ignore
            PROCESS_TERMINATE = 0x1
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if handle:
                kernel32.TerminateProcess(handle, 1 if force else 0)
                kernel32.CloseHandle(handle)
            return True
        else:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
            return True
    except (OSError, ProcessLookupError):
        return False


# ─── PID & Log file management ────────────────────────────────────────
def pid_file(component: str) -> Path:
    return PIDS_DIR / f"{component}.pid"


def log_file(component: str) -> Path:
    return LOGS_DIR / f"{component}.log"


def read_pid(component: str) -> Optional[int]:
    pf = pid_file(component)
    if not pf.exists():
        return None
    try:
        return int(pf.read_text().strip())
    except (ValueError, OSError):
        return None


def write_pid(component: str, pid: int) -> None:
    PIDS_DIR.mkdir(parents=True, exist_ok=True)
    pid_file(component).write_text(str(pid))


def clear_pid(component: str) -> None:
    pf = pid_file(component)
    if pf.exists():
        pf.unlink()


def component_running(component: str) -> bool:
    pid = read_pid(component)
    if pid is None:
        # Maybe a stale process is on the port
        port = COMPONENT_PORTS.get(component)
        if port and port_in_use(port) is not None:
            return True
        return False
    return is_running(pid)


# ─── Environment for spawned components ───────────────────────────────
def component_env() -> dict:
    """Standard env all control-plane components receive:
    - SHINON_HOME    points to ~/.shinon (single source of truth for state)
    - LIMEN_CONFIG   points to $SHINON_HOME/config/limen.toml
    - SHINON_CONFIG  points to $SHINON_HOME/config/shinon.toml
    - SHINON_DATA_DIR  alias for $SHINON_HOME/data
    - SHINON_PROJECT_ROOT points back at the source directory (venv, modules)
    - LIMEN_KEY_STORE points to $SHINON_HOME/keys.json (LIMEN's key-store)
    """
    env = os.environ.copy()
    env["SHINON_HOME"] = str(P.SHINON_HOME)
    env["SHINON_DATA_DIR"] = str(P.DATA_DIR)
    env["SHINON_CONFIG"] = str(SHINON_CONFIG)
    env["LIMEN_CONFIG"] = str(LIMEN_CONFIG)
    env["SHINON_PROJECT_ROOT"] = str(PROJECT_ROOT)
    # Set LIMEN_KEY_STORE too (LIMEN picks it up preferentially over
    # ~/.shinon/key_store resolver) — defense in depth.
    env["LIMEN_KEY_STORE"] = str(P.KEYS_FILE)
    return env


def venv_python() -> Path:
    """Path to the unified ./venv Python binary."""
    if platform.system() == "Windows":
        return PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    return PROJECT_ROOT / ".venv" / "bin" / "python3"


# ─── Component starters ───────────────────────────────────────────────
def start_limen() -> bool:
    """LIMEN: python -m limen.cli start --config ./config/limen.toml"""
    component = "limen"
    port = COMPONENT_PORTS[component]

    if component_running(component):
        warn(f"LIMEN l\u00e4uft bereits (Port {port})")
        return True

    if port_in_use(port) is not None:
        warn(f"Port {port} belegt \u2013 versuche Cleanup")
        _kill_port(port)
        time.sleep(0.5)
        # Re-check; if still occupied (Windows system service like IIS or
        # World Wide Web Publishing is hard-coded to skip-kill), tell the
        # user how to remap the port.
        if port_in_use(port) is not None:
            fail(f"Port {port} immer noch belegt nach Cleanup.")
            if platform.system() == "Windows":
                info("  Windows-Tipp: h\u00e4ufig belegt durch IIS oder WWW-Publishing.")
                info("  Diagnose:  Get-NetTCPConnection -LocalPort 8000 -State Listen")
                info("  Workaround: in config\\limen.toml den [server]-Port \u00e4ndern")
                info(f"             (z. B. port = {port + 65}) und neu starten.")
            else:
                info(f"  Diagnose:  lsof -i :{port}   oder   sudo fuser {port}/tcp")
                info(f"  Workaround: in config/limen.toml den [server]-Port \u00e4ndern")
            return False

    py = venv_python()
    if not py.exists():
        fail(f"venv fehlt: {py}. Bitte zuerst 'python install.py' ausf\u00fchren.")
        return False

    if not LIMEN_CONFIG.exists():
        fail(f"LIMEN-Config fehlt: {LIMEN_CONFIG}")
        return False

    PIDS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    info(f"Starte LIMEN auf Port {port} \u2026")
    try:
        creationflags = 0
        if platform.system() == "Windows":
            # CREATE_NO_WINDOW: kein Konsolen-Popup f\u00fcr limen-CLI.
            # DETACHED_PROCESS: Kindprozess \u00fcberlebt ctl.py-Ausstieg.
            creationflags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            )
        with open(log_file(component), "ab") as logf:
            proc = subprocess.Popen(
                [str(py), "-m", "limen.cli", "start", "--config", str(LIMEN_CONFIG)],
                cwd=str(PROJECT_ROOT),
                env=component_env(),
                stdout=logf,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                # Detach on POSIX so we exit independently. On Windows,
                # DETACHED_PROCESS / CREATE_NEW_PROCESS_GROUP keep the child alive.
                close_fds=(platform.system() != "Windows"),
                creationflags=creationflags,
            )
    except OSError as e:
        fail(f"LIMEN konnte nicht gestartet werden: {e}")
        return False

    write_pid(component, proc.pid)

    # Wait for /health
    for _ in range(20):
        if _http_health("http://127.0.0.1:" + str(port) + "/health", timeout=0.5):
            ok(f"LIMEN gestartet (PID {proc.pid}, Port {port})")
            return True
        time.sleep(0.5)
    warn(f"LIMEN gestartet (PID {proc.pid}, Port {port}), /health noch nicht erreichbar")
    return True


def start_shinon_ui() -> bool:
    """shinon-ui: node shinon-server.mjs (the unified Frontend/Stats/Settings)."""
    component = "shinon-ui"
    port = COMPONENT_PORTS[component]

    if component_running(component):
        warn(f"shinon-ui l\u00e4uft bereits (Port {port})")
        return True

    if port_in_use(port) is not None:
        warn(f"Port {port} belegt \u2013 versuche Cleanup")
        _kill_port(port)
        time.sleep(0.5)

    node = shutil.which("node")
    if not node:
        fail("Node.js nicht im PATH \u2013 installiere Node.js >=18")
        return False

    if not SHINON_SERVER_MJS.exists():
        fail(f"shinon-server.mjs fehlt: {SHINON_SERVER_MJS}")
        return False

    PIDS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    info(f"Starte shinon-ui (node) auf Port {port} \u2026")
    try:
        creationflags = 0
        if platform.system() == "Windows":
            creationflags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            )
        with open(log_file(component), "ab") as logf:
            proc = subprocess.Popen(
                [node, str(SHINON_SERVER_MJS), str(port)],
                cwd=str(PROJECT_ROOT),
                env=component_env(),
                stdout=logf,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                close_fds=(platform.system() != "Windows"),
                creationflags=creationflags,
            )
    except OSError as e:
        fail(f"shinon-ui konnte nicht gestartet werden: {e}")
        return False

    write_pid(component, proc.pid)

    # Wait for HTTP respond
    for _ in range(20):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.5) as r:
                if r.status == 200:
                    ok(f"shinon-ui gestartet (PID {proc.pid}, Port {port})")
                    return True
        except Exception:
            time.sleep(0.5)
    warn(f"shinon-ui gestartet (PID {proc.pid}, Port {port}), HTTP noch nicht antwortend")
    return True


def start_dashboard() -> bool:
    """Dashboard: python3 .agents/skills/goal-chain/scripts/live-dashboard-server.py"""
    component = "dashboard"
    port = COMPONENT_PORTS[component]

    if component_running(component):
        warn(f"dashboard l\u00e4uft bereits (Port {port})")
        return True

    if port_in_use(port) is not None:
        warn(f"Port {port} belegt \u2013 versuche Cleanup")
        _kill_port(port)
        time.sleep(0.5)

    py = venv_python()
    if not py.exists():
        fail(f"venv fehlt: {py}. Bitte zuerst 'python install.py' ausf\u00fchren.")
        return False

    if not DASHBOARD_SERVER.exists():
        fail(f"Dashboard-Server fehlt: {DASHBOARD_SERVER}")
        return False

    PIDS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    info(f"Starte dashboard auf Port {port} \u2026")
    try:
        creationflags = 0
        if platform.system() == "Windows":
            creationflags = (
                getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "DETACHED_PROCESS", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            )
        with open(log_file(component), "ab") as logf:
            # live-dashboard-server.py expects port as first positional arg
            proc = subprocess.Popen(
                [str(py), str(DASHBOARD_SERVER), str(port)],
                cwd=str(PROJECT_ROOT),
                env=component_env(),
                stdout=logf,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                close_fds=(platform.system() != "Windows"),
                creationflags=creationflags,
            )
    except OSError as e:
        fail(f"dashboard konnte nicht gestartet werden: {e}")
        return False

    write_pid(component, proc.pid)
    time.sleep(1)
    if is_running(proc.pid):
        ok(f"dashboard gestartet (PID {proc.pid}, Port {port})")
        return True
    fail(f"dashboard-Prozess sofort gestorben \u2013 siehe {log_file(component)}")
    clear_pid(component)
    return False


def stop_component(component: str) -> bool:
    if component == "all":
        ok_all = True
        for c in COMPONENT_PORTS:
            ok_all &= stop_component(c)
        return ok_all

    if component not in COMPONENT_PORTS:
        fail(f"Unbekannte Komponente: {component}")
        return False

    pid = read_pid(component)
    if pid is None or not is_running(pid):
        info(f"{component}: bereits gestoppt")
        clear_pid(component)
        return True

    info(f"Stoppe {component} (PID {pid}) \u2026")
    stop_pid(pid, force=False)
    for _ in range(10):
        if not is_running(pid):
            break
        time.sleep(0.3)
    if is_running(pid):
        warn(f"{component}: SIGTERM hat nicht gereicht, sende SIGKILL")
        stop_pid(pid, force=True)
        time.sleep(0.5)
    clear_pid(component)
    if not is_running(pid):
        ok(f"{component} gestoppt")
        return True
    fail(f"{component}: konnte nicht gestoppt werden")
    return False


def kill_all() -> None:
    header("Prozess-Cleanup (alle Control-Plane-Ports)")
    for comp, port in COMPONENT_PORTS.items():
        if port_in_use(port) is not None:
            _kill_port(port, comp)
    # Clean stale pid files
    for f in PIDS_DIR.glob("*.pid"):
        try:
            pid = int(f.read_text().strip())
            if not is_running(pid):
                f.unlink()
        except (ValueError, OSError):
            f.unlink()


def _kill_port(port: int, label: str = "") -> None:
    """Best-effort: kill anything listening on `port`. Cross-platform."""
    # On Linux, /proc/net/tcp gives PID via socket inode → fd → exe path.
    if platform.system() != "Windows":
        try:
            with open("/proc/net/tcp") as f:
                next(f)
                hex_port = f"{port:04X}"
                killed = 0
                for line in f:
                    parts = line.split()
                    if parts[1].split(":")[1] == hex_port:
                        inode = parts[9]
                        pid = _pid_for_inode_windows_safe(inode)
                        if pid and stop_pid(pid, force=False):
                            killed += 1
                if killed:
                    info(f"{label or 'port ' + str(port)}: {killed} Prozess(e) beendet")
                    return
        except FileNotFoundError:
            pass

    # Windows / fallback: kill what's in our pid/ that we started
    for f in PIDS_DIR.glob("*.pid"):
        try:
            pid = int(f.read_text().strip())
            if is_running(pid):
                stop_pid(pid, force=False)
        except (ValueError, OSError):
            pass


def _http_health(url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:
        return False


# ─── Status display ───────────────────────────────────────────────────
def show_status() -> None:
    print()
    print(f"{BOLD}\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
          f"\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
          f"\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
          f"\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557{NC}")
    print(f"{BOLD}\u2551  Control-Plane \u2014 Komponenten-Status              \u2551{NC}")
    print(f"{BOLD}\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
          f"\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
          f"\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
          f"\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d{NC}")
    print()
    print(f"  {'KOMPONENTE':<14} {'PORT':<6} {'PID':<8} STATUS")
    print(f"  {'\u2500' * 14} {'\u2500' * 6} {'\u2500' * 8} {'\u2500' * 14}")
    for comp, port in COMPONENT_PORTS.items():
        pid = read_pid(comp)
        running = component_running(comp)
        if running:
            status = f"{GREEN}\u25b6 RUNNING{NC}"
            pid_str = str(pid) if pid else "?"
        else:
            status = f"\u25a0 STOPPED"
            pid_str = "\u2014"
        print(f"  {comp:<14} {port:<6} {pid_str:<8} {status}")

    print()
    urls = [
        ("limen", "LIMEN API + Leitstand"),
        ("shinon-ui", "Chat + Stats + Settings"),
        ("dashboard", "Live-Dashboard"),
    ]
    print(f"  {CYAN}URLs:{NC}")
    for comp, label in urls:
        if component_running(comp):
            print(f"    http://127.0.0.1:{COMPONENT_PORTS[comp]}/  \u2192  {label}  [{comp}]")
    print()


def check_deps() -> None:
    header("Dependency-Check")
    py = venv_python()
    print(f"  Python (unified venv): {'\u2705' if py.exists() else '\u274c'} {py}")
    print(f"  Node.js: {'\u2705' if shutil.which('node') else '\u274c'} {shutil.which('node') or 'fehlt'}")
    print(f"  npm: {'\u2705' if shutil.which('npm') else '\u274c'} {shutil.which('npm') or 'fehlt'}")
    if py.exists():
        for pkg in ["fastapi", "uvicorn", "httpx", "pydantic", "click", "rich", "yaml"]:
            r = subprocess.run([str(py), "-c", f"import {pkg}"], capture_output=True)
            mark = "\u2705" if r.returncode == 0 else "\u26a0\ufe0f"
            print(f"  {mark} {pkg}")
    print()


def show_ports() -> None:
    print()
    print(f"  {BOLD}Port-Zuweisungen:{NC}")
    print()
    for comp, port in COMPONENT_PORTS.items():
        in_use = port_in_use(port) is not None
        marker = f"{RED}belegt{NC}" if in_use else f"{GREEN}frei{NC}"
        print(f"  {comp:<14} :{port:<5}  [{marker}]")
    print()


# ─── Main entry point ────────────────────────────────────────────────
COMPONENTS = list(COMPONENT_PORTS.keys())

STARTERS = {
    "limen": start_limen,
    "shinon-ui": start_shinon_ui,
    "dashboard": start_dashboard,
}


def main() -> int:
    p = argparse.ArgumentParser(
        prog="ctl.py",
        description="Cross-platform component lifecycle for Shinon Control Plane.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    for action in ("start", "stop", "restart"):
        sp = sub.add_parser(action, help=f"{action.title()} eine oder alle Komponenten")
        sp.add_argument("component", nargs="?", default="all",
                        choices=COMPONENTS + ["all"],
                        help="Komponente (default: all)")

    sub.add_parser("status", help="Komponenten-Status")
    sub.add_parser("kill", help="Alle Control-Plane-Prozesse beenden")
    sub.add_parser("deps", help="Abhängigkeiten prüfen")
    sub.add_parser("ports", help="Port-Belegung zeigen")

    args = p.parse_args()

    if args.cmd == "start":
        if args.component == "all":
            ok_all = True
            for comp in COMPONENTS:
                ok_all &= STARTERS[comp]()
            show_status()
            return 0 if ok_all else 1
        return 0 if STARTERS[args.component]() else 1

    if args.cmd == "stop":
        if args.component == "all":
            ok_all = True
            for comp in COMPONENTS:
                ok_all &= stop_component(comp)
            return 0 if ok_all else 1
        return 0 if stop_component(args.component) else 1

    if args.cmd == "restart":
        stop_component(args.component)
        time.sleep(1)
        if args.component == "all":
            ok_all = True
            for comp in COMPONENTS:
                ok_all &= STARTERS[comp]()
            return 0 if ok_all else 1
        return 0 if STARTERS[args.component]() else 1

    if args.cmd == "status":
        show_status()
        return 0

    if args.cmd == "kill":
        kill_all()
        show_ports()
        return 0

    if args.cmd == "deps":
        check_deps()
        return 0

    if args.cmd == "ports":
        show_ports()
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
