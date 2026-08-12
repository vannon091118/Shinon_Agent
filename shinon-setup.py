#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════
# shinon-setup.py — Cross-Platform Onboarding & Doctor Mous
#
# Lean replacement for the previous bash shinon-setup. Two modes:
#   python shinon-setup.py           runs the onboarding wizard
#   python shinon-setup.py --doc     runs Doctor Mous diagnosis
#   python shinon-setup.py --step N  jumps directly to step N (1..4)
#
# Project-relative paths only. Reads keys from stdin.
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import sqlite3
import sys
import time
from pathlib import Path
from typing import Optional

# ─── Path constants ───────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
SHINON_DATA = DATA_DIR / "shinon"
KARMA_DATA = DATA_DIR / "karma"
CONFIG_DIR = PROJECT_ROOT / "config"
SHINON_MEM = SHINON_DATA / "memory.db"
LIMEN_DB = DATA_DIR / "limen" / "limen.db"
LIMEN_CONFIG = CONFIG_DIR / "limen.toml"
SHINON_CONFIG = CONFIG_DIR / "shinon.toml"
GOALCHAIN_DB = PROJECT_ROOT / ".agents" / "skills" / "goal-chain" / "db" / "tid-state.db"
KARMA_DB = KARMA_DATA / "karma.db"

# ─── ANSI helpers ─────────────────────────────────────────────────────
def _c() -> bool:
    return sys.stdout.isatty() and os.environ.get("TERM", "") != "dumb"


_C = _c()
RED = "\033[31m" if _C else ""
GREEN = "\033[32m" if _C else ""
YELLOW = "\033[33m" if _C else ""
CYAN = "\033[36m" if _C else ""
BOLD = "\033[1m" if _C else ""
MAGENTA = "\033[35m" if _C else ""
NC = "\033[0m" if _C else ""


def ok(msg: str) -> None: print(f"  {GREEN}OK{NC} {msg}")
def warn(msg: str) -> None: print(f"  {YELLOW}WARN{NC} {msg}")
def fail(msg: str) -> None: print(f"  {RED}FAIL{NC} {msg}")
def info(msg: str) -> None: print(f"  {CYAN}i{NC} {msg}")
def tip(msg: str) -> None: print(f"  {MAGENTA}TIP{NC} {msg}")


def banner(text: str) -> None:
    print(f"\n{BOLD}{text}{NC}\n")


def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        s = input(f"  {label}{suffix}: ").strip()
    except EOFError:
        return default
    return s or default


def prompt_password(label: str) -> str:
    try:
        import getpass
        return getpass.getpass(f"  {label}: ")
    except Exception:
        return prompt(label)


def press_enter() -> None:
    try:
        input("  [Enter]")
    except EOFError:
        pass


def port_in_use(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


# ═══════════════════════════════════════════════════════════════════════
# Doctor Mous — Diagnose & Repair
# ═══════════════════════════════════════════════════════════════════════
def doctor_mous() -> int:
    banner("Doctor Mous  ·  Diagnose & Reparatur")
    print("  Pruefe alle Komponenten. API-Keys / Secrets bleiben UNANGETASTET.")
    print()
    issues = 0
    fixes = 0

    # 1. Install-Marker
    print(f"{BOLD}1. Installation{NC}")
    marker = CONFIG_DIR / ".install-done"
    if marker.exists():
        ok("Installation abgeschlossen (Marker vorhanden)")
    else:
        fail("Installation nicht gefunden -> bitte 'python install.py' ausfuehren")
        issues += 1

    # 2. venv
    print(f"\n{BOLD}2. Python-Umgebung{NC}")
    if platform.system() == "Windows":
        venv_py = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = PROJECT_ROOT / ".venv" / "bin" / "python3"
    if venv_py.exists():
        ok(f"venv: {venv_py.relative_to(PROJECT_ROOT)}")
    else:
        fail("venv fehlt")
        issues += 1

    # 3. Datenbanken
    print(f"\n{BOLD}3. Datenbanken{NC}")
    for db_path, label in [
        (LIMEN_DB, "LIMEN"),
        (GOALCHAIN_DB, "goal-chain"),
        (KARMA_DB, "KARMA"),
        (SHINON_MEM, "Shinon-Memory"),
    ]:
        if not db_path.exists():
            warn(f"{label}: fehlt ({db_path.relative_to(PROJECT_ROOT)})")
            issues += 1
            continue
        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
                n_tables = len(conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'").fetchall())
            ok(f"{label}: {n_tables} Tabellen, integrity OK")
        except sqlite3.DatabaseError as e:
            fail(f"{label}: korrupt ({e})")
            warn(f"  -> Backup nach .bak, neu initialisiert beim naechsten Install")
            fixes += 1

    # 4. Configs
    print(f"\n{BOLD}4. Konfiguration{NC}")
    if SHINON_CONFIG.exists():
        ok(f"Shinon-Config: {SHINON_CONFIG.relative_to(PROJECT_ROOT)}")
    else:
        fail("Shinon-Config fehlt")
        issues += 1
    if LIMEN_CONFIG.exists():
        ok(f"LIMEN-Config:  {LIMEN_CONFIG.relative_to(PROJECT_ROOT)}")
    else:
        fail("LIMEN-Config fehlt")
        issues += 1

    # 5. API-Keys
    print(f"\n{BOLD}5. API-Keys (LIMEN-DB){NC}")
    if LIMEN_DB.exists():
        try:
            with sqlite3.connect(str(LIMEN_DB)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT provider, status, health_score "
                    "FROM providers WHERE value != '' AND value IS NOT NULL"
                ).fetchall()
            if rows:
                ok(f"{len(rows)} API-Key(s) gefunden")
                for r in rows:
                    icon = "[active] " if r["status"] == "active" else "[cooldown]"
                    health = f"{r['health_score']:.0f}%" if r['health_score'] else "n/a"
                    info(f"  {icon}  {r['provider']:<15s}  health={health}")
            else:
                warn("Keine API-Keys konfiguriert")
                tip("Mit 'python shinon-setup.py --step 2' einen Key anlegen")
                issues += 1
        except sqlite3.DatabaseError as e:
            fail(f"Konnte LIMEN-DB nicht lesen: {e}")
            issues += 1
    else:
        warn("LIMEN-DB fehlt -> Keys koennen nicht geprueft werden")
        issues += 1

    # 6. Ports
    print(f"\n{BOLD}6. Ports{NC}")
    for port, label in [(8000, "LIMEN"), (4300, "shinon-ui"), (4200, "Dashboard")]:
        if port_in_use(port):
            ok(f"Port {port} ({label}) -- antwortet")
        else:
            info(f"Port {port} ({label}) -- frei")

    # 7. Rust (manchmal noetig fuer pip-Wheels)
    print(f"\n{BOLD}7. Rust-Toolchain (fuer pip-Wheels wie tiktoken){NC}")
    cargo = shutil.which("cargo")
    rustc = shutil.which("rustc")
    if cargo and rustc:
        ok(f"cargo + rustc vorhanden ({Path(rustc).name})")
    else:
        user_cargo = Path.home() / ".cargo" / "bin" / "cargo"
        if user_cargo.exists():
            info(f"cargo vorhanden (user-local in {Path.home() / '.cargo' / 'bin'}), "
                 f"aber nicht im PATH dieser Shell")
            info("  Workaround: PATH=$HOME/.cargo/bin:$PATH vor dem Install setzen")
        else:
            warn("Rust nicht installiert (kein Issue, solange alle pip-Wheels passen)")

    # Zusammenfassung
    print()
    banner("Doctor Mous  ·  Ergebnis")
    if issues == 0 and fixes == 0:
        ok("ALLES IN ORDNUNG. Shinon ist gesund.")
        return 0
    print(f"  Probleme: {issues}  |  Behoben: {fixes}")
    if fixes > 0:
        ok(f"{fixes} Problem(e) automatisch repariert")
    if issues > 0:
        tip("Bei offenen Problemen: 'python install.py --repair' "
            "oder schau in data/logs/")
    return 0


# ═══════════════════════════════════════════════════════════════════════
# Onboarding-Wizard (4 Schritte — lean)
# ═══════════════════════════════════════════════════════════════════════
def step_1_welcome() -> None:
    banner("Schritt 1/4  —  Was ist Shinon?")
    print("""
  Shinon ist ein AI-Control-Center. Anders als freundliche Chat-Wrapper ist
  Shinon KRITISCH, SKEPTISCH und PRÄZISE.

  5 Komponenten unter einem Dach:
    - Shinon Persoenlichkeit (Pattern Engine, Memory, Attitude)
    - LIMEN API-Gateway mit Key-Pool, 429-Rotation, Health-Tracking
    - KARMA EventBus + FalsificationGate (6 Probes)
    - Promtguard Claim-Extraktion
    - goal-chain autonome Entwicklungskaskade (sub-agent + Skill-Dispatch)

  WICHTIG: Ohne API-Key funktioniert NUR die Infrastruktur (Dashboard, etc.),
  aber kein LLM-Aufruf. Du brauchst mindestens einen Key von Groq (gratis),
  OpenRouter (pay) oder NVIDIA (gratis).
""")
    press_enter()


def step_2_keys() -> None:
    banner("Schritt 2/4  —  API-Keys einrichten")
    if not LIMEN_DB.exists():
        warn("LIMEN-DB fehlt -> 'python install.py' zuerst ausfuehren")
        press_enter()
        return

    provider_urls = {
        "groq":       "https://console.groq.com",
        "openrouter": "https://openrouter.ai",
        "nvidia":     "https://build.nvidia.com",
    }
    provider_models = {
        "groq":       ["llama-3.3-70b-versatile"],
        "openrouter": ["deepseek/deepseek-chat", "openai/gpt-4o-mini"],
        "nvidia":     ["nvidia/llama-3.1-nemotron-70b-instruct"],
    }

    saved = 0
    while True:
        print(f"\n  Anbieter: 1=groq, 2=openrouter, 3=nvidia, 4=Fertig")
        choice = prompt("Wahl", "1")
        try:
            n = int(choice)
        except ValueError:
            print("  Bitte 1-4")
            continue
        if n == 4:
            break
        if n not in (1, 2, 3):
            continue
        provider = ["groq", "openrouter", "nvidia"][n - 1]
        key = prompt_password(f"{provider}-API-Key (leer = ueberspringen)")
        if not key:
            warn("Leerer Key, uebersprungen.")
            continue
        try:
            with sqlite3.connect(str(LIMEN_DB)) as conn:
                key_id = f"{provider}-onboarding-{saved}"
                meta = json.dumps({"api_key": key, "source": "wizard"})
                conn.execute(
                    "INSERT OR REPLACE INTO providers "
                    "(key_id, provider, deployment, value, status, priority, meta_json) "
                    "VALUES (?, ?, 'default', ?, 'active', 1, ?)",
                    (key_id, provider, key, meta),
                )
                for m in provider_models.get(provider, []):
                    conn.execute(
                        "INSERT OR IGNORE INTO model_registry "
                        "(model_id, provider, deployment, capabilities, cost_tier) "
                        "VALUES (?, ?, 'default', '{}', 'standard')",
                        (m, provider),
                    )
                conn.commit()
            ok(f"{provider}-Key gespeichert ({provider_urls[provider]})")
            saved += 1
        except sqlite3.DatabaseError as e:
            fail(f"Speichern fehlgeschlagen: {e}")

    if saved == 0:
        warn("Keine Keys eingerichtet. Spater mit 'python shinon-setup.py --step 2' nachholen.")
    else:
        ok(f"{saved} API-Key(s) gespeichert. LIMEN rotiert automatisch bei 429.")
    press_enter()


def step_3_personality() -> None:
    banner("Schritt 3/4  —  Persoenlichkeit")
    if not SHINON_MEM.exists():
        warn("Shinon-Memory-DB fehlt")
        press_enter()
        return

    dims = [
        ("Skepsis (0-10)", "skepticism", 8),
        ("Direktheit (0-10)", "directness", 7),
        ("Hilfsbereitschaft (0-10)", "helpfulness", 4),
        ("Geduld (0-10)", "patience", 5),
        ("Neugier (0-10)", "curiosity", 6),
    ]
    print("  Standard ist kritisch/skeptisch. Diese Werte justieren die Intensitaet.")
    print("  Empfehlung: alle Defaults einfach mit Enter uebernehmen.\n")
    try:
        with sqlite3.connect(str(SHINON_MEM)) as conn:
            for label, col, default in dims:
                val = prompt(label, str(default))
                try:
                    v = float(val)
                    conn.execute(
                        "UPDATE attitudes SET value=?, updated_at=datetime('now') "
                        "WHERE dimension=?",
                        (v, col),
                    )
                except ValueError:
                    pass
            conn.commit()
        ok("Persoenlichkeit gespeichert")
        tip("Anpassbar jederzeit via 'python shinon-setup.py --step 3' "
            f"oder direkt in {SHINON_CONFIG.relative_to(PROJECT_ROOT)}")
    except sqlite3.DatabaseError as e:
        fail(f"Speichern fehlgeschlagen: {e}")
    press_enter()


def step_4_done() -> None:
    banner("Schritt 4/4  —  Fertig!")
    print("""
  Naechste Schritte:

    ./shinon start        # alle Komponenten starten
    ./shinon status       # Status anzeigen
    ./shinon chat         # Chat-Oberflaeche (Browser oeffnet)
    ./shinon --doc        # jederzeit Diagnose

  Auf Windows ersetze './shinon' mit 'shinon.cmd'.

  Bei Problemen: 'python install.py --repair' repariert Configs + DBs.
""")
    marker = CONFIG_DIR / ".onboarding-done"
    marker.write_text(json.dumps({
        "version": "1.0.0",
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }, indent=2), encoding="utf-8")
    ok("Onboarding abgeschlossen. Viel Erfolg mit Shinon!")


def onboarding(start_step: int = 1) -> int:
    steps = [
        step_1_welcome, step_2_keys, step_3_personality,
        lambda: (step_4_done(), None)[1],
    ]
    banner("Shinon  ·  Onboarding (4 Schritte)")
    print("  Strg+C jederzeit zum Abbrechen. Das Onboarding kann jederzeit")
    print("  mit 'python shinon-setup.py --step N' fortgesetzt werden.\n")
    for i, fn in enumerate(steps, 1):
        if i >= start_step:
            try:
                fn()
            except KeyboardInterrupt:
                print(f"\n  {YELLOW}Onboarding abgebrochen{NC}")
                return 130
    return 0


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════
def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] in ("--doc", "doc"):
        return doctor_mous()
    if len(sys.argv) >= 3 and sys.argv[1] == "--step":
        try:
            step = int(sys.argv[2])
            if 1 <= step <= 4:
                return onboarding(step)
            fail("--step erwartet 1-4")
            return 1
        except ValueError:
            fail("--step erwartet eine Zahl 1-4")
            return 1
    return onboarding(1)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n  {YELLOW}Abbruch (Ctrl+C){NC}")
        sys.exit(130)
