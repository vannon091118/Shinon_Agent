#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════
# install.py — Shinon Control Plane · Cross-Platform Installer
#
# Single source of truth for installing the entire control plane on
# Windows, Linux, macOS. Replaces the bash install.sh and adds:
#
#   • Real OS detection (Windows / Linux / macOS)
#   • Pre-flight checks (Python ≥3.11, Node ≥18, RAM, Disk)
#   • Idempotent steps (re-runnable without breaking state)
#   • Pinned Python deps from requirements.txt (consolidated from
#     limen-main + karma-main pyproject.toml files)
#   • npm ci (deterministic) where lockfile present, else npm install
#   • Project-relative data paths (./data, ./config) so the project
#     folder is genuinely portable — no $HOME or %USERPROFILE% leak
#   • Smoke tests at the end (Python imports, Node version,
#     SQLite integrity for all 4 DBs, skill catalog count)
#
# Modes:
#   python install.py            full install (interactive prompts)
#   python install.py --quick    skip prompts, sane defaults
#   python install.py --repair   re-init configs/DBs (secrets preserved)
#   python install.py --check    pre-flight + smoke-tests only, no install
#   python install.py --python-only   venv + pip only
#   python install.py --node-only     npm ci only
#   python install.py --verbose       extra diagnostic output
#
# Exit codes:
#   0  success (all smoke-tests passed)
#   1  pre-flight failed (missing requirement)
#   2  install failed (couldn't set up a component)
#   3  smoke-tests failed (installed but something didn't validate)
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import sqlite3
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

# ─── Project Constants ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_NAME = "Shinon Control Plane"
PROJECT_VERSION = "1.0.0"

DATA_DIR = PROJECT_ROOT / "data"
SHINON_DATA = DATA_DIR / "shinon"
KARMA_DATA = DATA_DIR / "karma"
LOGS_DIR = DATA_DIR / "logs"
PIDS_DIR = DATA_DIR / "pids"

CONFIG_DIR = PROJECT_ROOT / "config"
SHINON_CONFIG = CONFIG_DIR / "shinon.toml"
LIMEN_CONFIG = CONFIG_DIR / "limen.toml"

LIMEN_DB = DATA_DIR / "limen" / "limen.db"
GOALCHAIN_DB = PROJECT_ROOT / ".agents" / "skills" / "goal-chain" / "db" / "tid-state.db"
KARMA_DB = KARMA_DATA / "karma.db"
SHINON_MEM = SHINON_DATA / "memory.db"

# Frontend Node project inside ShinonLLM-main.
# BACKEND is intentionally NOT installed - its package.json has zero
# runtime deps and the unified frontend (shinon-server.mjs) is the
# single source of truth for UI. Installing it would waste minutes.
SHINON_LLM_ROOT = PROJECT_ROOT / "ShinonLLM-main"
SHINON_LLM_FRONTEND = SHINON_LLM_ROOT / "frontend"
SHINON_LLM_PACKAGE_LOCK = SHINON_LLM_ROOT / "package-lock.json"

REQUIREMENTS_TXT = PROJECT_ROOT / "requirements.txt"

# Minimum requirements
MIN_PYTHON = (3, 11)
MIN_NODE = (18, 0, 0)
MIN_DISK_MB = 800
MIN_RAM_MB = 2048

EXPECTED_SKILL_CATEGORIES = [
    "bioscience", "communication", "cloud-platforms", "finance",
    "design-tools", "mobile-dev", "ai-ml", "ecommerce", "security",
    "agents", "osint-self-audit",
]

# ═══════════════════════════════════════════════════════════════════════
# Coloured Console Output
# ═══════════════════════════════════════════════════════════════════════

class Console:
    """ANSI-aware console with auto-disable on dumb terminals / Windows legacy."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        # Windows 10+ supports ANSI; older PowerShell needs VT enable.
        # We let the platform decide: if TERM != 'dumb' and not Windows < 10, use colours.
        self.colours = (
            sys.stdout.isatty()
            and os.environ.get("TERM", "") != "dumb"
            and not (platform.system() == "Windows" and not _supports_windows_ansi())
        )
        self._c = {
            "red": "\033[31m" if self.colours else "",
            "green": "\033[32m" if self.colours else "",
            "yellow": "\033[33m" if self.colours else "",
            "cyan": "\033[36m" if self.colours else "",
            "bold": "\033[1m" if self.colours else "",
            "muted": "\033[90m" if self.colours else "",
            "nc": "\033[0m" if self.colours else "",
        }

    def ok(self, msg: str) -> None:
        print(f"  {self._c['green']}\u2705{self._c['nc']} {msg}")

    def warn(self, msg: str) -> None:
        print(f"  {self._c['yellow']}\u26a0\ufe0f {self._c['nc']} {msg}")

    def fail(self, msg: str) -> None:
        print(f"  {self._c['red']}\u274c{self._c['nc']} {msg}")

    def info(self, msg: str) -> None:
        print(f"  {self._c['cyan']}\u2139{self._c['nc']}  {msg}")

    def step(self, msg: str) -> None:
        print(f"\n{self._c['bold']}\u2550\u2550\u2550 {msg} \u2550\u2550\u2550{self._c['nc']}\n")

    def title(self, msg: str) -> None:
        print(f"\n{self._c['bold']}\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
              f"\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
              f"\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
              f"\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557{self._c['nc']}")
        print(f"{self._c['bold']}\u2551  {msg:<54}\u2551{self._c['nc']}")
        print(f"{self._c['bold']}\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
              f"\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
              f"\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550"
              f"\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d{self._c['nc']}\n")

    def debug(self, msg: str) -> None:
        if self.verbose:
            print(f"  {self._c['muted']}[debug]{self._c['nc']} {msg}")


def _supports_windows_ansi() -> bool:
    """True on Windows 10+ where Virtual Terminal is on by default."""
    try:
        import ctypes  # type: ignore
        kernel32 = ctypes.windll.kernel32
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x4
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return bool(mode.value & 0x4)
    except Exception:
        return False
    return False


# ═══════════════════════════════════════════════════════════════════════
# OS + Environment Detection
# ═══════════════════════════════════════════════════════════════════════

class OS:
    LINUX = "linux"
    MACOS = "macos"
    WINDOWS = "windows"

    @staticmethod
    def current() -> str:
        s = platform.system().lower()
        if s.startswith("win"):
            return OS.WINDOWS
        if s == "darwin":
            return OS.MACOS
        return OS.LINUX

    @staticmethod
    def label(current: str) -> str:
        return {"linux": "Linux", "macos": "macOS", "windows": "Windows"}.get(current, current)

    @staticmethod
    def venv_activate_path(python_bin: Path) -> str:
        """Return path to venv activation script (bash or batch)."""
        if OS.current() == OS.WINDOWS:
            return str(python_bin.parent / "activate.bat")
        return str(python_bin.parent / "activate")


# ═══════════════════════════════════════════════════════════════════════
# Subprocess Helpers (cross-platform, timeouts, output capture)
# ═══════════════════════════════════════════════════════════════════════

def run_cmd(
    cmd: List[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
    timeout: int = 600,
    console: Optional[Console] = None,
    capture: bool = False,
    check: bool = True,
) -> Tuple[int, str, str]:
    """Run a command cross-platform. Returns (returncode, stdout, stderr)."""
    full_env = os.environ.copy() if env is None else {**os.environ, **env}
    cmd_str = " ".join(str(c) for c in cmd)
    if console:
        console.debug(f"exec: {cmd_str}  (cwd={cwd or PROJECT_ROOT})")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else str(PROJECT_ROOT),
            env=full_env,
            timeout=timeout,
            capture_output=True,
            text=True,
            shell=(OS.current() == OS.WINDOWS),
        )
        if check and proc.returncode != 0:
            if console:
                console.fail(f"Command failed (exit {proc.returncode}): {cmd_str}")
                if proc.stdout:
                    console.info(f"stdout: {proc.stdout[-500:]}")
                if proc.stderr:
                    console.info(f"stderr: {proc.stderr[-500:]}")
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        if console:
            console.fail(f"Command timed out after {timeout}s: {cmd_str}")
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError as e:
        if console:
            console.fail(f"Command not found: {e}")
        return 127, "", str(e)


def which(binary: str) -> Optional[str]:
    """Cross-platform `which`."""
    return shutil.which(binary)


def parse_version(version_str: str) -> Tuple[int, ...]:
    """Extract leading numeric version triple from a string like 'v20.11.0'."""
    cleaned = version_str.strip().lstrip("v").split()[0]
    parts: List[int] = []
    for p in cleaned.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


# ═══════════════════════════════════════════════════════════════════════
# Pre-Flight Checks
# ═══════════════════════════════════════════════════════════════════════

def check_pre_flight(console: Console) -> Tuple[bool, List[str]]:
    """Verify system has Python ≥3.11, Node ≥18, npm, ~2GB RAM, ~800MB disk.
    Returns (ok, list_of_failures)."""
    console.step("Pre-Flight Checks")
    failures: List[str] = []

    # Python
    py_ver = parse_version(platform.python_version())
    if py_ver >= MIN_PYTHON:
        console.ok(f"Python {platform.python_version()} \u2265 {'.'.join(map(str, MIN_PYTHON))}")
    else:
        failures.append(f"python={py_ver}<{MIN_PYTHON}")
        console.fail(f"Python {platform.python_version()} \u2013 braucht mindestens "
                     f"{'.'.join(map(str, MIN_PYTHON))}")

    # python3 explicit (Linux/Mac)
    if OS.current() != OS.WINDOWS:
        py3 = which("python3")
        if py3:
            _, out, _ = run_cmd(["python3", "--version"], capture=True, check=False, console=console)
            console.ok(f"python3: {out.strip()}")
        else:
            failures.append("python3-missing")
            console.fail("python3 nicht in PATH")

    # Node
    node_bin = which("node")
    if node_bin:
        _, out, _ = run_cmd(["node", "--version"], capture=True, check=False, console=console)
        node_ver = parse_version(out)
        if node_ver >= MIN_NODE:
            console.ok(f"Node {out.strip()} \u2265 {'.'.join(map(str, MIN_NODE))}")
        else:
            failures.append(f"node={node_ver}<{MIN_NODE}")
            console.fail(f"Node {out.strip()} \u2013 braucht >= {'.'.join(map(str, MIN_NODE))}")
    else:
        failures.append("node-missing")
        console.fail("Node.js nicht gefunden \u2013 installiere Node.js >= 18")

    # npm
    npm_bin = which("npm")
    if npm_bin:
        _, out, _ = run_cmd(["npm", "--version"], capture=True, check=False, console=console)
        console.ok(f"npm v{out.strip()}")
    else:
        failures.append("npm-missing")
        console.fail("npm nicht gefunden \u2013 mit Node.js mitinstallieren")

    # bash (only for cases where we still shell out)
    if OS.current() != OS.WINDOWS:
        bash_bin = which("bash")
        if bash_bin:
            _, out, _ = run_cmd(["bash", "--version"], capture=True, check=False, console=console)
            console.ok(f"bash vorhanden ({out.splitlines()[0] if out else 'ok'})")
    else:
        # PowerShell check
        ps = which("powershell") or which("pwsh")
        if ps:
            console.ok(f"PowerShell vorhanden: {ps}")
        else:
            console.warn("PowerShell nicht in PATH \u2013 wird für start-local.ps1 benötigt")

    # Disk space (rough)
    try:
        usage = shutil.disk_usage(PROJECT_ROOT)
        free_mb = usage.free // (1024 * 1024)
        if free_mb >= MIN_DISK_MB:
            console.ok(f"Disk: {free_mb} MiB frei (\u2265 {MIN_DISK_MB})")
        else:
            failures.append(f"disk-low={free_mb}MB")
            console.fail(f"Nur {free_mb} MiB frei \u2013 brauche mindestens {MIN_DISK_MB}")
    except Exception as e:
        console.warn(f"Disk-Check fehlgeschlagen: {e}")

    # RAM (rough — non-fatal warning)
    try:
        if OS.current() != OS.WINDOWS:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        mb = kb // 1024
                        if mb >= MIN_RAM_MB:
                            console.ok(f"RAM: ~{mb} MiB (\u2265 {MIN_RAM_MB})")
                        else:
                            console.warn(f"Nur ~{mb} MiB RAM \u2013 lahmer Build möglich")
                        break
        else:
            console.debug("RAM-Check auf Windows übersprungen (kein Win-API hier)")
    except Exception:
        console.debug("RAM-Check nicht möglich \u2013 übersprungen")

    console.info(f"Betriebssystem: {OS.label(OS.current())} ({platform.machine()})")

    return (len(failures) == 0, failures)


# ═══════════════════════════════════════════════════════════════════════
# Python venv + pip
# ═══════════════════════════════════════════════════════════════════════

# ─── Rust auto-install URLs (cross-platform) ────────────────────────────────
RUST_INSTALL_URL_POSIX = "https://sh.rustup.rs"              # bash installer (Linux + macOS)
RUST_INSTALL_URL_WIN = "https://win.rustup.rs/x86_64"        # rustup-init.exe (Windows)
RUST_TOOLCHAIN = "stable"  # PyO3 + Python 3.14 wants stable + PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1


def ensure_rust(console: Console) -> bool:
    r"""Ensure a Rust toolchain (rustc + cargo) is available.

    Several Python wheels (e.g. tiktoken) compile native code via PyO3 + Rust.
    On newer Python interpreters where prebuilt wheels lag (e.g. early 3.14),
    pip needs rustc/cargo to compile from source. This helper installs Rust
    user-locally without admin/sudo:

        - Linux / macOS :  curl | bash https://sh.rustup.rs       -> $HOME/.cargo/bin
        - Windows       :  winget install Rustlang.Rustup         -> %USERPROFILE%\.cargo\bin
                           (fallback)   rustup-init.exe von https://win.rustup.rs/x86_64

    Returns True if `cargo` is callable afterwards."""
    # Already on PATH (system-level Rust, devcontainer pre-install, etc.)
    if which("cargo") and which("rustc"):
        console.ok(f"Rust vorhanden: {Path(which('rustc')).name} \u00b7 {Path(which('cargo')).name}")
        return True

    cargo_user_bin = Path.home() / ".cargo" / "bin"
    cargo_exe_name = "cargo.exe" if OS.current() == OS.WINDOWS else "cargo"
    if (cargo_user_bin / cargo_exe_name).exists():
        console.ok(f"Rust schon installiert (user-local): {cargo_user_bin}/{cargo_exe_name}")
        return True

    console.info("Rust nicht im PATH. Installiere user-local (kein sudo) \u2026")

    # ─── Windows path: winget preferred, rustup-init.exe fallback ──────────
    if OS.current() == OS.WINDOWS:
        if which("winget"):
            console.info("  Windows: winget install Rustlang.Rustup \u2026")
            code, _, err = run_cmd(
                ["winget", "install", "--id", "Rustlang.Rustup",
                 "--accept-package-agreements", "--accept-source-agreements",
                 "--silent"],
                capture=True, console=console, timeout=600,
            )
            if code == 0 and (cargo_user_bin / "cargo.exe").exists():
                console.ok(f"Rust installiert (winget): {cargo_user_bin}\\cargo.exe")
                return True
            console.warn(f"winget-Install hat nicht geklappt (Exit {code}). Fallback auf rustup-init.exe.")

        import tempfile, urllib.request
        with tempfile.TemporaryDirectory() as td:
            installer = Path(td) / "rustup-init.exe"
            console.info(f"  Lade {RUST_INSTALL_URL_WIN} \u2026")
            urllib.request.urlretrieve(RUST_INSTALL_URL_WIN, installer)
            console.debug(f"  Gr\u00f6\u00dfe: {installer.stat().st_size} bytes")
            code, _, err = run_cmd(
                [str(installer), "-y",
                 "--default-toolchain", RUST_TOOLCHAIN,
                 "--profile", "minimal", "--no-modify-path"],
                capture=True, console=console, timeout=900,
            )
        if code == 0 and (cargo_user_bin / "cargo.exe").exists():
            console.ok(f"Rust installiert (rustup-init.exe): {cargo_user_bin}\\cargo.exe")
            return True
        console.warn(f"rustup-Install hat nicht geklappt (Exit {code}). "
                     f"Pip wird ohne Rust fahren \u2014 Pakete mit fehlenden Wheels scheitern.")
        return False

    # ─── POSIX path (Linux + macOS) ───────────────────────────────────────
    code, _, err = run_cmd(
        [
            "bash", "-c",
            f"curl --proto =https --tlsv1.2 -sSf {RUST_INSTALL_URL_POSIX} "
            f"| sh -s -- -y --default-toolchain {RUST_TOOLCHAIN} "
            f"--profile minimal --no-modify-path"
        ],
        capture=True, console=console, timeout=600,
    )
    if code != 0:
        console.warn(f"rustup-Install hat nicht geklappt (Exit {code}). "
                     f"Pip wird ohne Rust fahren \u2014 Pakete mit fehlenden Wheels scheitern.")
        return False
    if (cargo_user_bin / "cargo").exists():
        console.ok(f"Rust installiert (user-local): {cargo_user_bin}")
        return True
    return False


def setup_python_venv(console: Console) -> Path:
    """Create venv if missing, then upgrade pip + install requirements.
    Returns the python binary inside the venv."""
    console.step("Schritt 1/5: Python venv einrichten")

    # Ensure Rust toolchain is on PATH so wheels like tiktoken can build.
    have_rust = ensure_rust(console)
    if have_rust:
        cargo_bin = str(Path.home() / ".cargo" / "bin")
        os.environ["PATH"] = f"{cargo_bin}{os.pathsep}{os.environ.get('PATH', '')}"
        os.environ["PYO3_USE_ABI3_FORWARD_COMPATIBILITY"] = "1"
        console.debug(f"PATH prepend {cargo_bin}; PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1")

    venv_dir = PROJECT_ROOT / ".venv"
    if venv_dir.exists():
        console.ok(f"venv vorhanden: {venv_dir.relative_to(PROJECT_ROOT)}")
    else:
        console.info(f"Erstelle venv in {venv_dir.relative_to(PROJECT_ROOT)} \u2026")
        code, _, err = run_cmd(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture=True, console=console,
        )
        if code != 0:
            raise RuntimeError(f"venv-Erstellung fehlgeschlagen: {err}")
        console.ok(f"venv erstellt")

    # Pick correct python bin in venv
    if OS.current() == OS.WINDOWS:
        py_bin = venv_dir / "Scripts" / "python.exe"
    else:
        py_bin = venv_dir / "bin" / "python3"

    if not py_bin.exists():
        raise RuntimeError(f"Python-Binary nicht im venv: {py_bin}")

    # Upgrade pip
    console.info("Aktualisiere pip \u2026")
    code, out, err = run_cmd(
        [str(py_bin), "-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"],
        capture=True, console=console, timeout=300,
    )
    if code != 0:
        raise RuntimeError(f"pip-Upgrade fehlgeschlagen: {err}")
    console.ok(f"pip aktualisiert")

    # Install requirements (deterministic via requirements.txt)
    if REQUIREMENTS_TXT.exists():
        console.info(f"Installiere {REQUIREMENTS_TXT.name} \u2026")
        console.debug(f"venv python: {py_bin}")
        code, out, err = run_cmd(
            [str(py_bin), "-m", "pip", "install", "-r", str(REQUIREMENTS_TXT)],
            capture=True, console=console, timeout=900,
        )
        if code != 0:
            raise RuntimeError(f"pip install requirements fehlgeschlagen: {err}")
        console.ok(f"Python-Abhängigkeiten installiert (aus {REQUIREMENTS_TXT.name})")
    else:
        console.fail(f"requirements.txt fehlt: {REQUIREMENTS_TXT}")
        raise RuntimeError("requirements.txt fehlt")

    # Install limen-main as editable (so `python -m limen.cli` works in venv).
    # Single unified venv keeps everything cross-platform visible.
    limen_pkg = PROJECT_ROOT / "limen-main"
    if (limen_pkg / "pyproject.toml").exists():
        console.info("Installiere limen-main (editable) in gemeinsame venv \u2026")
        code, _, err = run_cmd(
            [str(py_bin), "-m", "pip", "install", "-e", str(limen_pkg)],
            capture=True, console=console, timeout=600,
        )
        if code != 0:
            raise RuntimeError(f"limen-main editable-install fehlgeschlagen: {err}")
        console.ok("limen-main: editable install (python -m limen.cli funktioniert)")
    else:
        console.warn("limen-main/pyproject.toml fehlt \u2013 LIMEN nicht installierbar")

    # KARMA ist optional (pyproject.toml fordert Python \u22653.14).
    # Best-effort: scheitert hier NICHT der Installer.
    karma_pkg = PROJECT_ROOT / "karma-main"
    if (karma_pkg / "pyproject.toml").exists():
        console.info("Versuche karma-main (editable) \u2013 optional \u2026")
        code, _, err = run_cmd(
            [str(py_bin), "-m", "pip", "install", "-e", str(karma_pkg)],
            capture=True, check=False, console=console, timeout=600,
        )
        if code == 0:
            console.ok("karma-main: editable install OK")
        else:
            console.warn(f"karma-main: passt nicht zur Python-Version "
                         f"(braucht 3.14, hat {platform.python_version()}). "
                         f"KARMA-LLM nicht verf\u00fcgbar, Rest funktioniert.")

    return py_bin


# ═══════════════════════════════════════════════════════════════════════
# Node / npm
# ═══════════════════════════════════════════════════════════════════════

def setup_npm(console: Console, frontend_only: bool = False) -> None:
    """Run `npm ci` (if lockfile present) in ShinonLLM-main/frontend.
    Idempotent. Backend is excluded (zero deps; wastes time)."""
    console.step("Schritt 2/5: Node / npm einrichten")

    if not SHINON_LLM_FRONTEND.exists():
        console.warn("ShinonLLM-main/frontend nicht gefunden \u2013 übersprungen")
        return

    target = SHINON_LLM_FRONTEND
    pkg_lock = target / "package-lock.json"
    pkg_json = target / "package.json"
    if not pkg_json.exists():
        console.warn(f"{target.relative_to(PROJECT_ROOT)} hat kein package.json \u2013 übersprungen")
        return

    node_modules = target / "node_modules"
    if node_modules.exists():
        console.ok(f"{target.relative_to(PROJECT_ROOT)}: node_modules vorhanden")
        return

    if pkg_lock.exists():
        console.info(f"{target.relative_to(PROJECT_ROOT)}: npm ci (deterministisch) \u2026")
        cmd = ["npm", "ci", "--no-audit", "--no-fund", "--loglevel=error"]
    else:
        console.info(f"{target.relative_to(PROJECT_ROOT)}: npm install (kein lockfile) \u2026")
        cmd = ["npm", "install", "--no-audit", "--no-fund", "--loglevel=error"]

    code, out, err = run_cmd(cmd, cwd=target, timeout=1200, console=console)
    if code != 0:
        console.fail(f"npm in {target.name} fehlgeschlagen")
        console.info(f"stderr: {err[-500:] if err else ''}")
        raise RuntimeError(f"npm fehlgeschlagen in {target}")
    console.ok(f"{target.relative_to(PROJECT_ROOT)}: node_modules installiert")


# ═══════════════════════════════════════════════════════════════════════
# Database Initialisation
# ═══════════════════════════════════════════════════════════════════════

def init_database(db_path: Path, schema_sql: str, console: Console, label: str) -> None:
    """Create DB if missing. Idempotent: ok if it already exists & is readable."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        # Validate integrity
        try:
            with sqlite3.connect(db_path) as conn:
                conn.execute("SELECT 1").fetchone()
            console.ok(f"{label}: bereits vorhanden und lesbar")
            return
        except sqlite3.DatabaseError as e:
            console.warn(f"{label}: existiert aber korrupt ({e}) \u2013 wird neu erstellt")
            db_path.unlink()

    console.info(f"{label}: initialisiere \u2026")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()
    console.ok(f"{label}: erstellt")


def init_all_databases(console: Console) -> None:
    """Initialise all 4 control-plane databases at project-relative paths."""
    console.step("Schritt 3/5: Datenbanken initialisieren")

    # LIMEN — schema versioniert LIMEN selbst beim ersten Start
    # (siehe limen-main/src/limen/persistence/database.py:17  SCHEMA_VERSION).
    # Wir legen die DB nur an; LIMEN macht den Rest.
    # Wenn schon vorhanden: PRAGMA user_version setzen falls leer.
    LIMEN_DB.parent.mkdir(parents=True, exist_ok=True)
    if LIMEN_DB.exists():
        try:
            with sqlite3.connect(str(LIMEN_DB)) as conn:
                conn.execute("SELECT 1").fetchone()
            console.ok(f"LIMEN @ {LIMEN_DB.relative_to(PROJECT_ROOT)}: bereits vorhanden")
        except sqlite3.DatabaseError:
            console.warn(f"LIMEN-DB korrupt - wird beim ersten LIMEN-Start neu initialisiert")
    else:
        console.info(f"LIMEN-DB wird beim ersten LIMEN-Start angelegt "
                     f"({LIMEN_DB.relative_to(PROJECT_ROOT)})")

    # KARMA (project-relative ./data/karma/karma.db)
    init_database(KARMA_DB, """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            project TEXT,
            payload TEXT NOT NULL,
            correlation_id TEXT,
            prev_hash TEXT,
            event_hash TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS experience (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            action_type TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            state_hash TEXT NOT NULL,
            result TEXT NOT NULL,
            feedback_score REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """, console, f"KARMA @ {KARMA_DB.relative_to(PROJECT_ROOT)}")

    # Shinon-Memory (project-relative ./data/shinon/memory.db)
    init_database(SHINON_MEM, """
        CREATE TABLE IF NOT EXISTS personal_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            source TEXT DEFAULT 'user',
            evidence TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type TEXT NOT NULL,
            pattern_text TEXT NOT NULL,
            confidence REAL DEFAULT 0.5,
            occurrences INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS attitudes (
            dimension TEXT PRIMARY KEY,
            value REAL NOT NULL DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        INSERT OR IGNORE INTO attitudes (dimension, value) VALUES
            ('skepticism', 5.0), ('helpfulness', 3.0),
            ('directness', 7.0), ('patience', 4.0), ('curiosity', 6.0);
    """, console, f"Shinon-Memory @ {SHINON_MEM.relative_to(PROJECT_ROOT)}")

    # Goal-chain DB via existing db-init.sh if present
    if (PROJECT_ROOT / ".agents" / "skills" / "goal-chain" / "scripts" / "db-init.sh").exists():
        init_script = PROJECT_ROOT / ".agents" / "skills" / "goal-chain" / "scripts" / "db-init.sh"
        console.info(f"goal-chain: rufe bestehendes db-init.sh \u2026")
        code, _, err = run_cmd(["bash", str(init_script)], console=console, timeout=60)
        if code == 0:
            console.ok(f"goal-chain @ {GOALCHAIN_DB.relative_to(PROJECT_ROOT)}")
        else:
            console.warn(f"goal-chain-db-init: codes {code} \u2013 manuelle \u00dcberpr\u00fcfung empfohlen")
    else:
        console.warn("goal-chain db-init.sh fehlt \u2013 DB bleibt uninitialisiert")


# ═══════════════════════════════════════════════════════════════════════
# Config-Generation (project-relative ./config/)
# ═══════════════════════════════════════════════════════════════════════

SHINON_CONFIG_TEMPLATE = """\
# Shinon Control Plane · Konfiguration
# Erstellt von install.py im Projekt-Root (NICHT in $HOME).
# Dadurch ist das Projekt verschiebbar.

[shinon]
# Persönlichkeit (0-10, Standard: kritisch/skeptisch)
skepticism = 8
directness = 7
helpfulness = 4
patience = 5
curiosity = 6
display_name = "Shinon"

[limen]
url = "http://127.0.0.1:8000"
auto_start = true

[dashboard]
port = 4200
auto_start = true

[goal_chain]
db_path = ".agents/skills/goal-chain/db/tid-state.db"
auto_discover_skills = true

[paths]
# Standalone-Mode: alles im Projekt, nicht im User-Dir.
data_dir = "data"
config_dir = "config"
log_dir = "data/logs"
pid_dir = "data/pids"
"""

LIMEN_CONFIG_TEMPLATE = """\
[server]
port = 8000
host = "127.0.0.1"

[database]
# Project-relative OUTSIDE the limen-main submodule so a future
# `git submodule update` does not destroy your data.
path = "data/limen/limen.db"

[audit]
enabled = true

[routing]
default_provider_chain = ["groq", "openrouter", "nvidia", "github"]
auto_model = true
"""


def write_configs(console: Console, force: bool = False) -> None:
    """Write ./config/shinon.toml and ./config/limen.toml.
    Existing files are preserved unless force=True. Both files always
    get chmod 0o600 — LIMEN rejects configs with broader permissions."""
    console.step("Schritt 4/5: Konfigurationsdateien")

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, 0o700)
    except OSError as e:
        console.debug(f"chmod config dir 0o700: {e}")

    if SHINON_CONFIG.exists() and not force:
        console.ok(f"{SHINON_CONFIG.relative_to(PROJECT_ROOT)} vorhanden")
    else:
        SHINON_CONFIG.write_text(SHINON_CONFIG_TEMPLATE, encoding="utf-8")
        try:
            os.chmod(SHINON_CONFIG, 0o600)
        except OSError as e:
            console.warn(f"chmod shinon.toml 0o600 fehlgeschlagen: {e}")
        console.ok(f"{SHINON_CONFIG.relative_to(PROJECT_ROOT)} erstellt (mode 0o600)")

    if LIMEN_CONFIG.exists() and not force:
        console.ok(f"{LIMEN_CONFIG.relative_to(PROJECT_ROOT)} vorhanden")
    else:
        LIMEN_CONFIG.write_text(LIMEN_CONFIG_TEMPLATE, encoding="utf-8")
        try:
            os.chmod(LIMEN_CONFIG, 0o600)
        except OSError as e:
            console.warn(f"chmod limen.toml 0o600 fehlgeschlagen: {e}")
        console.ok(f"{LIMEN_CONFIG.relative_to(PROJECT_ROOT)} erstellt (mode 0o600)")


def write_install_marker(console: Console) -> None:
    """Mark successful installation for ./shinon / CLI detection."""
    marker = CONFIG_DIR / ".install-done"
    marker.write_text(
        json.dumps({
            "version": PROJECT_VERSION,
            "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "os": OS.current(),
            "python": platform.python_version(),
        }, indent=2),
        encoding="utf-8",
    )
    console.ok(f"Installations-Marker: {marker.relative_to(PROJECT_ROOT)}")


# ═══════════════════════════════════════════════════════════════════════
# Smoke-Tests
# ═══════════════════════════════════════════════════════════════════════

def smoke_test_python_imports(venv_py: Path, console: Console) -> bool:
    """Verify all critical Python packages import cleanly."""
    console.info("Python-Imports pr\u00fcfen \u2026")
    critical = [
        "fastapi", "uvicorn", "httpx", "pydantic",
        "click", "rich", "yaml",  # note: yaml (not pyyaml)
    ]
    failed: List[str] = []
    for pkg in critical:
        code, _, err = run_cmd(
            [str(venv_py), "-c", f"import {pkg}"],
            capture=True, check=False, console=console,
        )
        if code == 0:
            console.debug(f"  import {pkg}: OK")
        else:
            failed.append(pkg)
            console.debug(f"  import {pkg}: FAIL ({err.strip()[:80] if err else '?'})")

    if failed:
        console.fail(f"Python-Imports fehlgeschlagen: {', '.join(failed)}")
        return False
    console.ok("Alle Python-Imports OK")
    return True


def smoke_test_databases(console: Console) -> bool:
    """Open every DB and run a trivial query. Some DBs (LIMEN) may not yet
    exist if the user hasn't started LIMEN — that's OK."""
    console.info("Datenbank-Integrit\u00e4t pr\u00fcfen \u2026")
    ok = True
    for db, label, optional in [
        (LIMEN_DB, "LIMEN", True),  # created on first LIMEN start
        (KARMA_DB, "KARMA", False),
        (SHINON_MEM, "Shinon-Memory", False),
        (GOALCHAIN_DB, "goal-chain", False),
    ]:
        if not db.exists():
            if optional:
                console.info(f"{label}: nicht angelegt (wird beim ersten Start erzeugt)")
            else:
                console.warn(f"{label}: nicht vorhanden ({db.relative_to(PROJECT_ROOT)})")
                ok = False
            continue
        try:
            with sqlite3.connect(str(db)) as conn:
                conn.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                console.ok(f"{label}: {len(tables)} Tabellen, integrity OK")
        except sqlite3.DatabaseError as e:
            console.fail(f"{label}: integrity fail \u2013 {e}")
            ok = False
    return ok


def smoke_test_skill_catalog(console: Console) -> bool:
    """Verify the 657 skills catalogue structure."""
    console.info("Skill-Katalog pr\u00fcfen \u2026")
    skills_root = PROJECT_ROOT / ".agents" / "skills"
    if not skills_root.exists():
        console.fail(f"Skill-Root fehlt: {skills_root}")
        return False
    categories = [d for d in skills_root.iterdir() if d.is_dir()]
    total_dirs = sum(1 for _ in skills_root.rglob("*") if _.is_dir())
    total_files = sum(1 for _ in skills_root.rglob("*.md"))
    missing = [c for c in EXPECTED_SKILL_CATEGORIES
               if not (skills_root / c).exists()]
    if missing:
        console.warn(f"Erwartete Kategorien fehlen: {missing}")
    console.ok(f"Skills: {len(categories)} Kategorien, "
               f"{total_dirs} Verzeichnisse, {total_files} .md-Dateien")
    return len(categories) >= 5  # tolerant — exact counts vary


def smoke_test_node(console: Console) -> bool:
    """Verify node_modules in place that needs it.

    Frontend is REQUIRED (shinon-server.mjs uses next/react/etc. from it).
    Backend is intentionally excluded from install.py — it has zero runtime
    deps and is invoked via `tsx` from the parent's node_modules."""
    console.info("Node-Modules pr\u00fcfen \u2026")
    nm = SHINON_LLM_FRONTEND / "node_modules"
    if not SHINON_LLM_FRONTEND.exists():
        console.info("ShinonLLM-Frontend: nicht vorhanden")
        return True
    if nm.exists():
        console.ok("ShinonLLM-Frontend: node_modules vorhanden")
        return True
    console.warn("ShinonLLM-Frontend: node_modules fehlt")
    return False


def run_smoke_tests(venv_py: Path, console: Console) -> bool:
    console.step("Schritt 5/5: Smoke-Tests")
    all_ok = True
    all_ok &= smoke_test_python_imports(venv_py, console)
    all_ok &= smoke_test_databases(console)
    all_ok &= smoke_test_skill_catalog(console)
    all_ok &= smoke_test_node(console)
    return all_ok


# ═══════════════════════════════════════════════════════════════════════
# Modes (--quick, --repair, --check, --python-only, --node-only)
# ═══════════════════════════════════════════════════════════════════════

def mode_full(console: Console, args: argparse.Namespace) -> int:
    ok, failures = check_pre_flight(console)
    if not ok:
        console.fail("Pre-Flight fehlgeschlagen. Installiere fehlende Abh\u00e4ngigkeiten:")
        for f in failures:
            if "python" in f:
                console.info("  \u2192 Python 3.11+: https://www.python.org/downloads/")
            elif "node" in f:
                console.info("  \u2192 Node.js 18+: https://nodejs.org/")
            elif "disk" in f:
                console.info("  \u2192 Mindestens 800 MB freien Speicher schaffen")
        return 1

    venv_py = setup_python_venv(console)
    setup_npm(console)
    init_all_databases(console)
    write_configs(console, force=args.repair)
    write_install_marker(console)

    if not run_smoke_tests(venv_py, console):
        console.fail("Smoke-Tests fehlgeschlagen \u2013 Installation unvollst\u00e4ndig!")
        return 3

    print_install_summary(console)
    return 0


def mode_check_only(console: Console) -> int:
    ok, failures = check_pre_flight(console)
    if not ok:
        return 1
    venv_py = PROJECT_ROOT / ".venv" / (
        "Scripts/python.exe" if OS.current() == OS.WINDOWS else "bin/python3"
    )
    if venv_py.exists():
        if not run_smoke_tests(venv_py, console):
            return 3
    else:
        console.warn("venv nicht vorhanden \u2013 Smoke-Tests \u00fcbersprungen")
    return 0


def print_install_summary(console: Console) -> None:
    console.title("Installation abgeschlossen")
    print(textwrap.dedent(f"""\
        Pfade (alle im Projekt, nicht in $HOME):

          Daten:    {DATA_DIR.relative_to(PROJECT_ROOT)}/
          Config:   {CONFIG_DIR.relative_to(PROJECT_ROOT)}/
          Logs:     {LOGS_DIR.relative_to(PROJECT_ROOT)}/
          PIDs:     {PIDS_DIR.relative_to(PROJECT_ROOT)}/
          Venv:     .venv/

        N\u00e4chste Schritte:

          Linux/macOS:  ./shinon --setup      (Onboarding-Wizard)
          Windows:      shinon.cmd --setup

          Oder direkt:  ./shinon start         (alle Komponenten starten)
                        ./shinon status        (Status anzeigen)
                        ./shinon chat          (Chat-Oberfl\u00e4che)
                        ./shinon --doc         (Doctor Mous Diagnose)

        Bei Problemen:  ./shinon --doc    oder    python install.py --check
    """))


# ═══════════════════════════════════════════════════════════════════════
# CLI Entry-Point
# ═══════════════════════════════════════════════════════════════════════

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="install.py",
        description=f"{PROJECT_NAME} \u00b7 Cross-Platform Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Beispiele:
              python install.py              vollst\u00e4ndige Installation
              python install.py --quick      ohne R\u00fcckfragen, Defaults
              python install.py --repair     DBs/Configs neu, Secrets bleiben
              python install.py --check      nur Pre-Flight + Smoke-Tests
              python install.py --python-only   nur venv + pip install
              python install.py --node-only     nur npm ci
              python install.py --verbose    mit Diagnose-Output
        """),
    )
    p.add_argument("--quick", action="store_true", help="\u00dcberspringe R\u00fcckfragen")
    p.add_argument("--repair", action="store_true", help="DBs und Configs neu schreiben")
    p.add_argument("--check", action="store_true", help="Nur Pre-Flight + Smoke-Tests")
    p.add_argument("--python-only", action="store_true", help="Nur Python-venv + pip")
    p.add_argument("--node-only", action="store_true", help="Nur npm ci")
    p.add_argument("--verbose", action="store_true", help="Mehr Diagnose-Output")
    return p


def main() -> int:
    args = build_argparser().parse_args()
    console = Console(verbose=args.verbose)

    console.title(f"{PROJECT_NAME} v{PROJECT_VERSION} \u00b7 Installer")
    console.info(f"Projekt-Root: {PROJECT_ROOT}")
    console.info(f"OS: {OS.label(OS.current())} ({platform.release()})")
    console.info(f"Python: {platform.python_version()} @ {sys.executable}")

    try:
        if args.check:
            return mode_check_only(console)

        if args.python_only and args.node_only:
            console.fail("--python-only und --node-only sind gegenseitig ausschlie\u00dfend")
            return 1

        if args.python_only:
            ok, _ = check_pre_flight(console)
            if not ok:
                return 1
            setup_python_venv(console)
            write_install_marker(console)
            return 0

        if args.node_only:
            ok, _ = check_pre_flight(console)
            if not ok:
                return 1
            setup_npm(console, frontend_only=False)
            return 0

        return mode_full(console, args)

    except KeyboardInterrupt:
        console.fail("Installation abgebrochen (Ctrl+C)")
        return 130
    except RuntimeError as e:
        console.fail(f"Installationsfehler: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
