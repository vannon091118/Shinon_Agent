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
import paths as P  # canonical layout — see paths.py

PROJECT_ROOT = P.PROJECT_ROOT
PROJECT_NAME = "Shinon Control Plane"
PROJECT_VERSION = "1.0.0"

# Re-export from paths.py so existing references inside this file work
# unchanged.  New code can `import paths as P` directly.
DATA_DIR    = P.DATA_DIR
SHINON_DATA = P.SHINON_DIR
KARMA_DATA  = P.KARMA_DIR
LOGS_DIR    = P.LOGS_DIR
PIDS_DIR    = P.PIDS_DIR

CONFIG_DIR    = P.CONFIG_DIR
SHINON_CONFIG = P.CONFIG_DIR / "shinon.toml"
LIMEN_CONFIG  = P.CONFIG_DIR / "limen.toml"

LIMEN_DB     = P.LIMEN_DB
GOALCHAIN_DB = P.GOALCHAIN_DB
KARMA_DB     = P.KARMA_DB
SHINON_MEM   = P.SHINON_MEM
SHINON_ATTITUDES = P.SHINON_ATTITUDES

# Where install.py writes its marker (alongside the configs).
MARKER_FILE = P.CONFIG_DIR / ".install-done"
ONBOARD_DONE = P.CONFIG_DIR / ".onboarding-done"

# Where the .env file lives in the central home.
ENV_FILE = P.CONFIG_DIR / ".env"

# Legacy paths kept for --migrate.
LEGACY_LIMEN_DBS = (
    P.PROJECT_LIMEN_DB_LEGACY_A,
    P.PROJECT_LIMEN_DB_LEGACY_B,
    P.PROJECT_PROJECT_LIMEN_DB,
)
LEGACY_FUSION_DBS = (
    P.PROJECT_FUSION_MEM,
    P.PROJECT_FUSION_ATTITUDES,
)
LEGACY_PROJECT_DBS = (
    P.PROJECT_PROJECT_LIMEN_DB,
    P.PROJECT_PROJECT_KARMA_DB,
    P.PROJECT_PROJECT_SHINON_MEM,
    P.PROJECT_PROJECT_GOALCHAIN_DB,
)
LEGACY_PROJECT_LOGS_PIDS = (
    P.PROJECT_PROJECT_LOGS,
    P.PROJECT_PROJECT_PIDS,
)

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
        # Windows-spezifisch: CREATE_NO_WINDOW verhindert, dass ein
        # Konsolenfenster f\u00fcr den Kindprozess kurz aufpoppt (z. B. w\u00e4hrend
        # pip / npm / rustup-install). POSIX kennt das Flag nicht.
        # Windows-spezifische creationflags:
        #   CREATE_NO_WINDOW         verhindert Konsolen-Popup bei subprocess.run
        #                            (sonst blitzt fuer pip / npm / rustup ein
        #                            cmd-Fenster kurz auf)
        #   DETACHED_PROCESS         Kind ueberlebt parent-Ausstieg
        #   CREATE_NEW_PROCESS_GROUP isoliert das Kind in eigener Prozessgruppe,
        #                            sodass taskkill /T sauber wirkt
        # POSIX kennt diese Flags nicht; auf Nicht-Windows bleibt creationflags = 0.
        creationflags = 0
        if OS.current() == OS.WINDOWS:
            try:
                creationflags = (
                    getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    | getattr(subprocess, "DETACHED_PROCESS", 0)
                    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                )
            except AttributeError:
                pass  # \u00e4ltere Python-Versionen (<3.7) ohne die Flags.

        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else str(PROJECT_ROOT),
            env=full_env,
            timeout=timeout,
            capture_output=True,
            text=True,
            shell=(OS.current() == OS.WINDOWS),
            creationflags=creationflags,
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
        # Windows-specific actionable hint (winget is the modern fast path).
        # `--silent` is required for non-interactive use — without it winget
        # asks 'Do you want to install?' which blocks any automated install.
        if OS.current() == OS.WINDOWS:
            console.info("  Windows-Fix (PowerShell, kein Browser n\u00f6tig):")
            console.info("    winget install --id OpenJS.NodeJS.LTS "
                         "--accept-package-agreements --accept-source-agreements "
                         "--silent")
            console.info("  Danach PowerShell schlie\u00dfen + neu \u00f6ffnen (PATH-Reload).")
        else:
            console.info("  Schneller Weg (Linux):  sudo apt install nodejs npm")
            console.info("  macOS:                  brew install node@20")
            console.info("  Manuell:                https://nodejs.org/en/download")

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

    # ─── Windows-spezifische Warnungen (kosmetisch, nicht blockierend) ──
    if OS.current() == OS.WINDOWS:
        # 6) LongPathsEnabled — relevant f\u00fcr npm/node_modules mit tiefen Pfaden
        try:
            import winreg  # type: ignore
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\\CurrentControlSet\\Control\\FileSystem",
            ) as key:
                val, _ = winreg.QueryValueEx(key, "LongPathsEnabled")
                if val == 1:
                    console.ok("LongPathsEnabled: aktiv (Pfade > 260 Zeichen OK)")
                else:
                    console.warn("LongPathsEnabled: AUS \u2013 npm-Build kann bei tiefen "
                                 "Pfaden scheitern (Frontend node_modules). Admin-Fix:")
                    console.info("    Set-ItemProperty -Path "
                                 "'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem' "
                                 "-Name 'LongPathsEnabled' -Value 1")
        except (ImportError, FileNotFoundError, OSError):
            # winreg nicht verf\u00fcgbar (theoretisch nie auf Windows) oder Registry-Key fehlt
            console.debug("LongPathsEnabled-Check \u00fcbersprungen (Registry nicht lesbar)")

        # 7) Windows Defender Exclusion-Hint (always shown — paths are
        # concrete enough to copy-paste regardless of where on the disk
        # the project sits; the old USERPROFILE filter was too narrow).
        console.info("Tipp: Falls pip / npm ungew\u00f6hnlich langsam h\u00e4ngen, "
                     "kann Windows Defender schuld sein. Folgende Ausnahmen helfen:")
        console.info(f"    Add-MpPreference -ExclusionPath \"{PROJECT_ROOT}\"")
        console.info(f"    Add-MpPreference -ExclusionPath \"{PROJECT_ROOT}\\.venv\"")
        console.info(f"    Add-MpPreference -ExclusionPath "
                     f"\"{PROJECT_ROOT}\\ShinonLLM-main\\frontend\\node_modules\"")

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


def _short(p: Path) -> str:
    """Show a path shortened to "within SHINON_HOME" if it lives there, else absolute."""
    try:
        return str(p.relative_to(P.SHINON_HOME))
    except ValueError:
        return str(p)


def init_all_databases(console: Console) -> None:
    """Initialise all 4 control-plane databases at the central SHINON_HOME."""
    console.step("Schritt 3/5: Datenbanken initialisieren")

    # LIMEN \u2014 schema versioniert LIMEN selbst beim ersten Start
    # (siehe limen-main/src/limen/persistence/database.py:17  SCHEMA_VERSION).
    # Wir legen die DB nur an; LIMEN macht den Rest.
    P.ensure_layout()
    if LIMEN_DB.exists():
        try:
            with sqlite3.connect(str(LIMEN_DB)) as conn:
                conn.execute("SELECT 1").fetchone()
            console.ok(f"LIMEN @ {_short(LIMEN_DB)}: bereits vorhanden")
        except sqlite3.DatabaseError:
            console.warn(f"LIMEN-DB korrupt - wird beim ersten LIMEN-Start neu initialisiert")
    else:
        console.info(f"LIMEN-DB wird beim ersten LIMEN-Start angelegt ({_short(LIMEN_DB)})")

    # KARMA
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
    """, console, f"KARMA @ {_short(KARMA_DB)}")

    # Shinon-Memory  (auch Attitude-Tabelle, weil das fusion-main sie hier pflegt)
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
    """, console, f"Shinon-Memory @ {_short(SHINON_MEM)}")

    # Goal-chain DB \u2014 call its existing db-init.sh which knows the schema.
    # The init script writes into $SHINON_HOME/data/goal-chain/tid-state.db
    # because install.py exports SHINON_HOME before spawning it.
    P.GOALCHAIN_DIR.mkdir(parents=True, exist_ok=True)
    init_script = (PROJECT_ROOT / ".agents" / "skills" / "goal-chain" / "scripts" / "db-init.sh")
    if init_script.exists():
        console.info(f"goal-chain: rufe bestehendes db-init.sh \u2026")
        # Tell the script where to write its DB so we keep it central.
        env_with_shinon_home = {"SHINON_GOALCHAIN_DB": str(P.GOALCHAIN_DB),
                                "SHINON_HOME": str(P.SHINON_HOME)}
        code, _, err = run_cmd(["bash", str(init_script)],
                               env=env_with_shinon_home, console=console, timeout=60)
        if code == 0:
            console.ok(f"goal-chain @ {_short(GOALCHAIN_DB)}")
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
# Zentral unter $SHINON_HOME (= ~/.shinon auf Linux/macOS).
# Bewusst ausserhalb des limen-main Submoduls, damit ein zukuenftiges
# `git submodule update` deine Daten nicht ueberschreibt.
# Install.py setzt hier den absoluten Pfad ein, weil LIMEN
# `OSError` wirft wenn das DB-Verzeichnis nicht existiert.
# path = "<wird beim Install eingesetzt>"

[audit]
enabled = true

[routing]
default_provider_chain = ["groq", "openrouter", "nvidia", "github"]
auto_model = true
"""


def _set_owner_only_acl(path: Path, console: Console) -> None:
    """Apply owner-only permissions to a config file (mode 0o600 / NTFS owner).

    POSIX path:   os.chmod(path, 0o600)        (owner = read+write)
    Windows path: icacls ... /inheritance:r /grant:r %USERNAME%:(R,W)
                                          + remove 'Users' group inherited ACE

    The two are NOT equivalent on a shared-file-hostile Windows box — POSIX
    chmod just sets the read-only flag bit that NTFS ignores; icacls is the
    real thing. LIMEN's startup check requires 'mode 600 or stricter', which
    on Windows maps to 'only the current user has explicit rights, no
    inheritance, no group permissions'.
    """
    if OS.current() == OS.WINDOWS:
        # icacls via list-args (no cmd /c shell-string) so paths with spaces
        # don't get double-parsed. The grammar:
        #   /inheritance:r       strip inherited ACEs (only explicit remain)
        #   /grant:r <user>:(R,W) REPLACE the ACL with explicit grant for
        #                        current user only = owner-only equivalent.
        # We deliberately do NOT pass /remove "Users" — it matches the
        # principal 'BUILTIN\Users' unreliably across locales (on German
        # Windows it's 'VORDEFINIERT\Benutzer'), and is redundant once
        # /grant:r has replaced the explicit ACEs anyway.
        user = os.environ.get("USERNAME") or os.environ.get("USER") or "%USERNAME%"
        code, _, err = run_cmd(
            ["icacls", str(path),
             "/inheritance:r",
             "/grant:r", f"{user}:(R,W)"],
            capture=True, check=False, console=console,
        )
        if code == 0:
            console.debug(f"icacls owner-only OK: {path.name}")
        else:
            console.warn(
                f"icacls owner-only f\u00fcr {path.name} hat nicht geklappt "
                f"(Exit {code}). LIMEN-Start k\u00f6nnte scheitern weil "
                f"ACL 'Everyone:Read' weiterhin gilt. Manuell: "
                f"`icacls \"{path}\" /inheritance:r /grant:r \"%USERNAME%:(R,W)\"`"
            )
        return

    # POSIX path.
    try:
        os.chmod(path, 0o600)
        console.debug(f"chmod 0o600: {path.name}")
    except OSError as e:
        console.warn(f"chmod {path.name} 0o600 fehlgeschlagen: {e}")


def write_configs(console: Console, force: bool = False) -> None:
    """Write ./.shinon/config/{shinon,limen}.toml  +  copy .env.example.
    Existing files are preserved unless force=True. Both TOML files always
    get owner-only ACL (mode 0o600 on POSIX, icacls inheritance-strip +
    user-only grant on Windows) \u2014 LIMEN rejects configs with broader
    permissions.

    All configs + the .env file live under $SHINON_HOME (= ~/.shinon on
    Linux/macOS, %USERPROFILE%\\.shinon on Windows).  Install.py points
    ctl.py/shinon.py at this central location via SHINON_DATA_DIR / SHINON_CONFIG
    environment variables on subprocess spawn.
    """
    console.step("Schritt 4/5: Konfigurationsdateien")

    P.ensure_layout()

    # Lock down the dir too (POSIX only \u2014 Windows dir-ACL is inherited).
    if OS.current() != OS.WINDOWS:
        try:
            os.chmod(P.CONFIG_DIR, 0o700)
        except OSError as e:
            console.debug(f"chmod config dir 0o700: {e}")
    else:
        # Strip inheritance + grant current user Modify on the directory.
        # Same list-args pattern as _set_owner_only_acl (no cmd /c shell).
        # "(R,W,M)" = Read + Write + Modify-children \u2014 full control of the
        # dir without giving out rights to anyone else.
        user = os.environ.get("USERNAME") or "%USERNAME%"
        code, _, err = run_cmd(
            ["icacls", str(P.CONFIG_DIR),
             "/inheritance:r",
             "/grant:r", f"{user}:(R,W,M)"],
            capture=True, check=False, console=console,
        )
        if code == 0:
            console.debug(f"config/-Dir: icacls inheritance stripped, owner-only OK")
        else:
            console.warn(f"config/-Dir: icacls fehlgeschlagen (Exit {code}) \u2014 "
                         f"neue Configs erben m\u00f6glicherweise \"Users\"-Rechte.")

    if SHINON_CONFIG.exists() and not force:
        console.ok(f"{SHINON_CONFIG.relative_to(P.SHINON_HOME)} vorhanden")
    else:
        SHINON_CONFIG.write_text(SHINON_CONFIG_TEMPLATE, encoding="utf-8")
        _set_owner_only_acl(SHINON_CONFIG, console)
        console.ok(f"{SHINON_CONFIG.relative_to(P.SHINON_HOME)} erstellt "
                   f"(owner-only{' via icacls' if OS.current()==OS.WINDOWS else ' mode 0o600'})")

    if LIMEN_CONFIG.exists() and not force:
        console.ok(f"{LIMEN_CONFIG.relative_to(P.SHINON_HOME)} vorhanden")
    else:
        # Inject the absolute DB path so LIMEN finds its DB regardless of
        # which CWD it was started from.
        limen_config_text = LIMEN_CONFIG_TEMPLATE.replace(
            "# path = \"<wird beim Install eingesetzt>\"",
            f"path = \"{P.LIMEN_DB}\"",
        )
        LIMEN_CONFIG.write_text(limen_config_text, encoding="utf-8")
        _set_owner_only_acl(LIMEN_CONFIG, console)
        console.ok(f"{LIMEN_CONFIG.relative_to(P.SHINON_HOME)} erstellt "
                   f"(owner-only{' via icacls' if OS.current()==OS.WINDOWS else ' mode 0o600'}, "
                   f"datenbank -> {P.LIMEN_DB.relative_to(P.SHINON_HOME) if P.SHINON_HOME in P.LIMEN_DB.parents else P.LIMEN_DB})")

    # Always lay down .env from .env.example if missing \u2014 one file,
    # all keys.  Even if user adds keys later through onboarding,
    # this .env serves as the canonical quick-edit spot.
    env_example = PROJECT_ROOT / ".env.example"
    if not ENV_FILE.exists():
        if env_example.exists():
            ENV_FILE.write_text(env_example.read_text(), encoding="utf-8")
            try:
                os.chmod(ENV_FILE, 0o600)
            except OSError:
                pass
            console.ok(f"{ENV_FILE.relative_to(P.SHINON_HOME)} aus .env.example erstellt "
                       f"(mode 0600) \u2014 Keys dort eintragen, "
                       f"`python shinon-setup.py --from-env` uebernimmt sie.")
            console.info(f"  Oder interaktiv: 'python shinon-setup.py --step 2'")
        else:
            console.warn(f"{env_example.relative_to(PROJECT_ROOT)} fehlt \u2014 "
                         f".env nicht angelegt. Manuell anlegen unter {ENV_FILE}")


def write_install_marker(console: Console) -> None:
    """Mark successful installation for ./shinon / CLI detection."""
    MARKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    MARKER_FILE.write_text(
        json.dumps({
            "version": PROJECT_VERSION,
            "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "os": OS.current(),
            "python": platform.python_version(),
            "shinon_home": str(P.SHINON_HOME),
        }, indent=2),
        encoding="utf-8",
    )
    console.ok(f"Installations-Marker: {_short(MARKER_FILE)}")


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
# --migrate:  Bestehende fragmentierte Daten in SHINON_HOME verschieben
# ═══════════════════════════════════════════════════════════════════════
def migrate_legacy_data(console: Console) -> int:
    """Verschiebt vorhandene Daten aus PROJEKT-RELATIVEN PfaDEN und der
    LIMEN-eigenen ~/.limen/keys.json in den zentralen SHINON_HOME.

    Idempotent: ueberspringt, was schon da ist. Logger via console.{ok,warn,info,fail}.
    """
    P.ensure_layout()

    conflicts: List[Tuple[Path, Path]] = []  # (src, dst) wenn dst schon was hat
    moved: List[Tuple[Path, Path]] = []

    def _move_db(src: Path, dst: Path) -> None:
        if not src.exists():
            return
        if src.resolve() == dst.resolve():
            console.debug(f"  bereits zentral: {src}")
            return
        if dst.exists():
            conflicts.append((src, dst))
            return
        src_bytes = src.stat().st_size
        try:
            shutil.move(str(src), str(dst))
            moved.append((src, dst))
            console.ok(f"  {src}  \u2192  {dst}  ({src_bytes // 1024} KiB)")
        except OSError as e:
            console.warn(f"  Verschieben {src} -> {dst} fehlgeschlagen: {e}")

    # 1. ~/.limen/keys.json  ->  SHINON_HOME/keys.json  (Inhalt mergen)
    legacy_keys_file = Path("~/.limen/keys.json").expanduser()
    if legacy_keys_file.exists():
        try:
            legacy_keys = json.loads(legacy_keys_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            console.warn(f"  ~/.limen/keys.json nicht lesbar ({e}) \u2014 \u00fcbersprungen")
            legacy_keys = None
        if legacy_keys:
            existing = {}
            if P.KEYS_FILE.exists():
                try:
                    existing = json.loads(P.KEYS_FILE.read_text())
                except (json.JSONDecodeError, OSError):
                    pass
            merged = {**legacy_keys, **{k: v for k, v in existing.items()
                                          if k not in legacy_keys}}
            try:
                P.KEYS_FILE.write_text(json.dumps(merged, indent=2))
                os.chmod(P.KEYS_FILE, 0o600)
                console.ok(f"  {legacy_keys_file}  (in JSON gemerged)  \u2192  {P.KEYS_FILE}")
                console.info(f"    keys.json enthaelt jetzt: {sorted(merged.keys())}")
            except OSError as e:
                console.warn(f"  keys.json schreiben fehlgeschlagen: {e}")
        # Don't delete legacy_keys_file automatically \u2014 user decides.
        console.info(f"  Hinweis: alte Datei bleibt unter {legacy_keys_file} unangetastet.")

    # 2. LIMEN-DBs (mehrere Kandidaten \u2014 limen-main/data/* und data/limen/*)
    for src in LEGACY_LIMEN_DBS + (P.PROJECT_PROJECT_LIMEN_DB,):
        if src.exists() and src != P.LIMEN_DB:
            _move_db(src, P.LIMEN_DB)

    # 3. KARMA-DB
    for src in (P.PROJECT_PROJECT_KARMA_DB,):
        if src.exists() and src != P.KARMA_DB:
            _move_db(src, P.KARMA_DB)

    # 4. Shinon-Memory (falls zentral noch nicht da)
    for src in (P.PROJECT_PROJECT_SHINON_MEM, P.PROJECT_FUSION_MEM):
        if src.exists() and src != P.SHINON_MEM:
            _move_db(src, P.SHINON_MEM)

    # 5. Shinon-Attitudes (falls es eine eigene DB gibt)
    for src in (P.PROJECT_FUSION_ATTITUDES,):
        if src.exists() and src != P.SHINON_ATTITUDES:
            _move_db(src, P.SHINON_ATTITUDES)

    # 6. Goal-chain: vorhandene tid-state.db in neues Layout
    src_chain_db = P.PROJECT_PROJECT_GOALCHAIN_DB
    if src_chain_db.exists() and src_chain_db != P.GOALCHAIN_DB:
        _move_db(src_chain_db, P.GOALCHAIN_DB)

    # 7. Logs + PIDs (nur verschieben wenn Ctl noch NICHTS laeuft)
    # (laeuft etwas, lassen wir die user-side logs drinnen).
    # Sanity: keine pid-Dateien unter data/pids die noch aktiv waeren.
    if P.PROJECT_PROJECT_LOGS.exists() and not any(P.PROJECT_PROJECT_LOGS.glob("*.pid")):
        for f in P.PROJECT_PROJECT_LOGS.iterdir():
            if f.is_file():
                _move_db(f, P.LOGS_DIR / f.name)

    # Konflikt-Zusammenfassung
    if conflicts:
        console.warn(f"\n{len(conflicts)} Konflikt(e) \u2014 Ziel war schon befuellt, NICHT ueberschrieben:")
        for src, dst in conflicts:
            console.info(f"  {src}  \u2192  {dst}  (dst existiert schon)")
        console.info("  Loesung:  python install.py --reset   (WIPE + neu)")
    if not moved and not conflicts:
        console.info("Nichts zu migrieren \u2014 Daten sind schon zentral oder es gibt keine Altlasten.")
    elif moved:
        console.ok(f"\n{len(moved)} Datei(en) erfolgreich in SHINON_HOME verschoben.")
        console.info("Heute neu starten: `./shinon start`")
    return 0


# ═══════════════════════════════════════════════════════════════════════
# --reset:  Alles platt machen (zentral + legacy)
# ═══════════════════════════════════════════════════════════════════════
def _confirm_destructive(console: Console, paths: List[str]) -> bool:
    """Ask an explicit interactive question. Returns True iff user says yes."""
    console.fail("\nAchtung \u2014 folgende Daten werden ENDGUELTIG geloescht:")
    for p in paths:
        console.info(f"  {p}")
    try:
        ans = input("\n  Wirklich loeschen? Tippe 'ja, weg damit' zum Bestaetigen: ").strip()
    except EOFError:
        ans = ""
    return ans == "ja, weg damit"


def reset_all(console: Console, *, force: bool = False) -> int:
    """WIPE core data (LimDB, Karma, ShinonMem, Goalchain, keys, configs).

    Always SKIPS:
      \u00b7 ~/.limen/  (legacy-LIMEN-Homedir, falls andere Tools es nutzen)
      \u00b7 .venv (rebuildable via install.py)
      \u00b7 node_modules (slow, rebuildable)
      \u00b7 Skills catalogue (.agents/skills/**)
      \u00b7 Source code (PROJECT_ROOT files)

    Targets:
      \u00b7 $SHINON_HOME/  (central)
      \u00b7 Project-relative ./config/, ./data/ (older layouts)
    """
    targets: List[Path] = [
        P.SHINON_HOME,
        P.PROJECT_PROJECT_LIMEN_DB.parent if P.PROJECT_PROJECT_LIMEN_DB.exists() else P.PROJECT_ROOT / "data" / "limen",
        P.PROJECT_ROOT / "data" / "karma",
        P.PROJECT_ROOT / "data" / "shinon",
        P.PROJECT_ROOT / "data",
        P.PROJECT_ROOT / "config",
    ]
    # Drop non-existing
    targets = [t for t in targets if t.exists()]

    readable = "\n    ".join(str(t) for t in targets)
    if not force:
        if not _confirm_destructive(console, [str(t) for t in targets]):
            console.warn("Abgebrochen \u2014 nichts geloescht.")
            return 1

    for target in targets:
        try:
            if target.is_file() or target.is_symlink():
                target.unlink()
            else:
                shutil.rmtree(target, ignore_errors=True)
            console.ok(f"  geloescht: {target}")
        except OSError as e:
            console.warn(f"  konnte {target} nicht loeschen: {e}")

    # Sanity: keys.json also raus (sicherheitshalber)
    if P.KEYS_FILE.exists():
        try:
            P.KEYS_FILE.unlink()
            console.ok("  ~/.shinon/keys.json geloescht (war getrennt vom SHINON_HOME.shinon_file)")
        except OSError:
            pass

    console.ok("\nReset fertig. Jetzt: `python install.py` fuer eine frische Installation.")
    return 0


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
        Zentrale Daten (EIN Ort statt verstreut):

          SHINON_HOME:  {P.SHINON_HOME}
          Config:       {P.CONFIG_DIR.relative_to(P.SHINON_HOME) if P.SHINON_HOME in P.CONFIG_DIR.parents else P.CONFIG_DIR}/
          Datenbanken:  {P.DATA_DIR.relative_to(P.SHINON_HOME) if P.SHINON_HOME in P.DATA_DIR.parents else P.DATA_DIR}/
          Keys:         {P.KEYS_FILE.relative_to(P.SHINON_HOME) if P.SHINON_HOME in P.KEYS_FILE.parents else P.KEYS_FILE}
          Logs:         {P.LOGS_DIR.relative_to(P.SHINON_HOME) if P.SHINON_HOME in P.LOGS_DIR.parents else P.LOGS_DIR}/
          PIDs:         {P.PIDS_DIR.relative_to(P.SHINON_HOME) if P.SHINON_HOME in P.PIDS_DIR.parents else P.PIDS_DIR}/

        Source (verschiebbares Projekt-Verzeichnis):

          Projekt:      {PROJECT_ROOT}
          Venv:         .venv/

        N\u00e4chste Schritte:

          Linux/macOS:  ./shinon --setup      (Onboarding-Wizard) ODER
                        python shinon-setup.py --from-env
                        (liesst {ENV_FILE} direkt)
          Windows:      shinon.cmd --setup

          Oder direkt:  ./shinon start         (alle Komponenten starten)
                        ./shinon status        (Status anzeigen)
                        ./shinon chat          (Chat-UI)

        Keys an einem Ort editieren:

          {ENV_FILE}   <- eine Datei, alle Anbieter

        Bei Problemen:  python install.py --check    oder  ./shinon --doc
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
              python install.py --migrate    fragmentierte Alt-Daten -> SHINON_HOME
              python install.py --reset      ALLES platt machen (zentral + legacy) **ACHTUNG**
              python install.py --python-only   nur venv + pip
              python install.py --node-only     nur npm ci
              python install.py --verbose    mit Diagnose-Output
        """),
    )
    p.add_argument("--quick", action="store_true", help="\u00dcberspringe R\u00fcckfragen")
    p.add_argument("--repair", action="store_true", help="DBs und Configs neu schreiben")
    p.add_argument("--check", action="store_true", help="Nur Pre-Flight + Smoke-Tests")
    p.add_argument("--migrate", action="store_true",
                   help="Alt-Daten aus Projekt + ~/.limen/ nach SHINON_HOME verschieben")
    p.add_argument("--reset", action="store_true",
                   help="Zentrale Daten + Projekt-Daten loeschen (mit Bestaetigung). "
                        "--reset --yes ueberspringt die Bestaetigung.")
    p.add_argument("--yes", "-y", action="store_true",
                   help="Bestaetigung fuer --reset ueberspringen (VORSICHT)")
    p.add_argument("--python-only", action="store_true", help="Nur Python-venv + pip")
    p.add_argument("--node-only", action="store_true", help="Nur npm ci")
    p.add_argument("--verbose", action="store_true", help="Mehr Diagnose-Output")
    return p


def main() -> int:
    args = build_argparser().parse_args()
    console = Console(verbose=args.verbose)

    console.title(f"{PROJECT_NAME} v{PROJECT_VERSION} \u00b7 Installer")
    console.info(f"Projekt-Root: {PROJECT_ROOT}")
    console.info(f"SHINON_HOME:  {P.SHINON_HOME}")
    console.info(f"OS: {OS.label(OS.current())} ({platform.release()})")
    console.info(f"Python: {platform.python_version()} @ {sys.executable}")

    try:
        if args.check:
            return mode_check_only(console)

        if args.reset:
            return reset_all(console, force=args.yes)

        if args.migrate:
            return migrate_legacy_data(console)

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
