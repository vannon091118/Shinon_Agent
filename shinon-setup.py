#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════
# shinon-setup.py — Cross-Platform Onboarding & Doctor Mous
#
# Lean replacement for the previous bash shinon-setup. Two modes:
#   python shinon-setup.py           runs the onboarding wizard
#   python shinon-setup.py --doc     runs Doctor Mous diagnosis
#   python shinon-setup.py --step N  jumps directly to step N (1..4)
#   python shinon-setup.py --from-env  reads ~/.shinon/config/.env directly
#
# Uses central paths through paths.py (resolves ~/.shinon by default).
# Reads keys from stdin / .env / pasted multi-line KEY=VALUE blocks.
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import socket
import sqlite3
import sys
import time
from pathlib import Path
from typing import Optional

# Single source of truth for every data directory.
import paths as P
from sqlite_health import check_sqlite

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


# ─── Prompt helpers ───────────────────────────────────────────────────
def prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        s = input(f"  {label}{suffix}: ").strip()
    except EOFError:
        return default
    return s or default


def prompt_pasteable_key(label: str) -> str:
    """API-Key paste-friendly input.

    Why this exists: `getpass.getpass()` hides input on stdin, which made
    users think their paste didn't register. Plain `input()` echoes, so the
    user SEES the pasted key go in. API keys are not passphrases — they live
    in the user's password manager / clipboard anyway, so echoing is fine.

    Supports:
      • Simple paste (single line, no surrounding whitespace)
      • Multi-line paste where each line looks like  KEY=value  → first
        matching occurrence wins.
      • Quiet mode (just hit Enter) → skip
    """
    try:
        raw = input(f"  {label}: ")
    except EOFError:
        return ""
    raw = raw.strip()

    if not raw:
        return ""

    # If the user pasted a multi-line KEY=value block (from .env.example),
    # extract every `*_API_KEY=<value>` line and remember them all so the
    # caller can store each one.  Single-line pastes are returned as-is.
    if "\n" in raw and "=" in raw:
        matches = re.findall(
            r"^\s*([A-Z][A-Z0-9_]*_API_KEY(?:\s*=\s*(?:\".*?\"|'[^']*'|[^\s#\"']+))?)",
            raw,
            re.MULTILINE,
        )
        # Also grab raw `KEY=value` pairs (no quotes) for keys without _API_KEY
        # suffix — useful for OPENAI_API_KEY etc.
        matches += re.findall(
            r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*([^\s#\"']+)",
            raw,
            re.MULTILINE,
        )
        if matches:
            return raw  # caller parses further
    return raw


def _parse_pasted_env_block(pasted: str) -> dict[str, str]:
    """Parse a multi-line KEY=value paste into a dict.

    Accepts:
      • KEY=value
      • KEY='value with spaces'
      • KEY="value with spaces"
      • Lines starting with `#` (comments) ignored
      • Blank lines ignored
    """
    env: dict[str, str] = {}
    for line in pasted.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"""^([A-Z_][A-Z0-9_]*)\s*=\s*(?:"([^"\\]*(?:\\.[^"\\]*)*)"|'([^'\\]*(?:\\.[^'\\]*)*)'|([^\s#]+))""", line)
        if m:
            key = m.group(1)
            val = m.group(2) if m.group(2) is not None else (
                  m.group(3) if m.group(3) is not None else m.group(4))
            if val is not None:
                env[key] = val
    return env


# ─── Provider metadata (subscription URL + free / paid tags) ──────────
PROVIDER_INFO = {
    "groq":       {"url": "https://console.groq.com/keys",       "tier": "gratis", "env": "GROQ_API_KEY"},
    "openrouter": {"url": "https://openrouter.ai/keys",          "tier": "pay",    "env": "OPENROUTER_API_KEY"},
    "nvidia":     {"url": "https://build.nvidia.com",            "tier": "gratis", "env": "NVIDIA_NIM_API_KEY"},
    "mistral":    {"url": "https://console.mistral.ai/api-keys", "tier": "gratis", "env": "MISTRAL_API_KEY", "note": "32K context, Tool-Calls nur bei large"},
}


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
# LIMEN providers table — SCHEMA-AWARE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════
# Correct schema (limen-main/src/limen/persistence/database.py:21):
#
#   key_id TEXT PRIMARY KEY,
#   provider TEXT NOT NULL,
#   deployment TEXT NOT NULL,
#   api_key_fingerprint TEXT NOT NULL,   <-- sha256(value)[:16], NOT the key itself
#   account_id TEXT,
#   limit_scope TEXT NOT NULL CHECK (limit_scope IN ('key','account','provider','model','unknown')),
#   status TEXT NOT NULL CHECK (status IN ('active','cooldown','dead')),
#   cooldown_until TEXT,
#   last_used_at TEXT,
#   priority INTEGER NOT NULL,
#   observed_rpm INTEGER, observed_itpm INTEGER, observed_otpm INTEGER,
#   error_count INTEGER NOT NULL DEFAULT 0, success_count INTEGER NOT NULL DEFAULT 0,
#   meta_json TEXT NOT NULL DEFAULT '{}'
#
# RAW KEY is stored in `meta_json` as `{"api_key": "...", "source": "wizard"}`.
# There is NO `value` column. There is NO `health_score` column (that's a
# runtime property of the KeyPool, not a SQL column). There is NO
# `model_registry` table (model→provider mapping lives in config/limen.toml).
# ═══════════════════════════════════════════════════════════════════════

def _key_id_for(provider: str, fingerprint: str) -> str:
    return f"{provider}:{fingerprint}"


def _fingerprint_of(key_value: str) -> str:
    return hashlib.sha256(key_value.encode("utf-8")).hexdigest()[:16]


def providers_has_keys(conn: sqlite3.Connection) -> list[dict[str, object]]:
    """Return rows whose `meta_json` carries a non-empty api_key.
    Sets row_factory=sqlite3.Row briefly so we can build dicts, then
    restores whatever the caller had set.
    """
    prev_factory = conn.row_factory
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT provider, status, key_id, meta_json, error_count, success_count "
            "FROM providers "
            "WHERE json_extract(meta_json, '$.api_key') IS NOT NULL "
            "  AND json_extract(meta_json, '$.api_key') != ''"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.row_factory = prev_factory


def upsert_provider_key(conn: sqlite3.Connection, provider: str,
                        key_value: str, *, source: str = "wizard") -> str:
    """Store a key for `provider`. Returns the key_id."""
    fingerprint = _fingerprint_of(key_value)
    key_id = _key_id_for(provider, fingerprint)
    meta = json.dumps({"api_key": key_value, "source": source})
    conn.execute(
        "INSERT INTO providers"
        " (key_id, provider, deployment, api_key_fingerprint,"
        "  account_id, limit_scope, status, priority, meta_json)"
        " VALUES (?, ?, 'default', ?, '', 'key', 'active', 1, ?)"
        " ON CONFLICT(key_id) DO UPDATE SET"
        "  meta_json = excluded.meta_json,"
        "  status = 'active',"
        "  cooldown_until = NULL",
        (key_id, provider, fingerprint, meta),
    )
    return key_id


def _write_keys_json(keys: dict[str, str]) -> None:
    """Mirror the LIMEN `_KEY_STORE` (~/.shinon/keys.json) — same JSON shape
    that LIMEN's internal.py expects."""
    P.ensure_layout()
    # Atomic write: tmp + rename
    fd, tmp = tempfile.mkstemp(dir=str(P.SHINON_HOME), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(keys, f)
        Path(tmp).chmod(0o600)
        Path(tmp).rename(P.KEYS_FILE)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


# Import tempfile here so the rest of the module doesn't need to.
import tempfile  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
# Doctor Mous — Diagnose & Repair
# ═══════════════════════════════════════════════════════════════════════
def _heal_goalchain_db() -> bool:
    """Ensure the goal-chain DB exists at the CENTRAL path.

    Priority: migrate legacy project-relative DB if present; else init
    from schema.sql (idempotent). Returns True if a repair happened.
    """
    if P.GOALCHAIN_DB.exists():
        return False
    P.GOALCHAIN_DIR.mkdir(parents=True, exist_ok=True)
    legacy = P.PROJECT_PROJECT_GOALCHAIN_DB
    if legacy.exists():
        try:
            shutil.move(str(legacy), str(P.GOALCHAIN_DB))
            return True
        except OSError:
            pass
    schema = P.PROJECT_ROOT / ".agents" / "skills" / "goal-chain" / "db" / "schema.sql"
    if schema.exists():
        with sqlite3.connect(str(P.GOALCHAIN_DB)) as conn:
            conn.executescript(schema.read_text(encoding="utf-8"))
            conn.commit()
        return True
    return False


def _heal_keys_from_env() -> int:
    """Auto-import keys from ~/.shinon/config/.env into LIMEN DB + mirror.

    Imports only providers NOT already in the DB (idempotent, no spam).
    Returns the number of keys imported (0 = nothing to do)."""
    env_path = P.CONFIG_DIR / ".env"
    if not env_path.exists():
        return 0
    env_map = read_env_file(env_path)
    if not env_map:
        return 0
    existing = set()
    if P.LIMEN_DB.exists():
        with sqlite3.connect(str(P.LIMEN_DB)) as conn:
            conn.row_factory = sqlite3.Row
            for r in providers_has_keys(conn):
                existing.add(r["provider"])
    todo = {k: v for k, v in env_map.items()
            if v and _provider_from_env_key(k) and _provider_from_env_key(k) not in existing}
    if not todo:
        return 0
    return _save_keys_from_env(todo, source=str(env_path))


def _rebuild_keys_json_from_limen() -> int:
    """Rebuild keys.json mirror from LIMEN DB meta_json (if mirror missing)."""
    if P.KEYS_FILE.exists() or not P.LIMEN_DB.exists():
        return 0
    mirror: dict[str, str] = {}
    with sqlite3.connect(str(P.LIMEN_DB)) as conn:
        conn.row_factory = sqlite3.Row
        for r in providers_has_keys(conn):
            try:
                meta = json.loads(r["meta_json"] or "{}")
            except (json.JSONDecodeError, TypeError):
                meta = {}
            key = meta.get("api_key")
            if key:
                mirror[r["provider"]] = key
    if mirror:
        _write_keys_json(mirror)
        return len(mirror)
    return 0


def doctor_mous() -> int:
    banner("Doctor Mous  ·  Diagnose & Reparatur")
    print("  Pruefe alle Komponenten. API-Keys / Secrets bleiben UNANGETASTET.")
    print()
    issues = 0
    fixes = 0

    # 0. SHINON_HOME
    print(f"{BOLD}0. Zentrale Datenverzeichnisse{NC}")
    print(P.explain())
    if not P.SHINON_HOME.exists():
        fail(f"{P.SHINON_HOME} existiert nicht — bitte 'python install.py' "
             f"ausfuehren (legt es automatisch an).")
        issues += 1
    else:
        ok(f"{P.SHINON_HOME} vorhanden")

    # 1. venv
    print(f"\n{BOLD}1. Python-Umgebung{NC}")
    if platform.system() == "Windows":
        venv_py = P.PROJECT_VENV / "Scripts" / "python.exe"
    else:
        venv_py = P.PROJECT_VENV / "bin" / "python3"
    if venv_py.exists():
        ok(f"venv: {venv_py.relative_to(P.PROJECT_ROOT)}")
    else:
        fail("venv fehlt — bitte 'python install.py' ausfuehren")
        issues += 1

    # 2. Datenbanken
    print(f"\n{BOLD}2. Datenbanken{NC}")
    # Auto-heal: goal-chain DB lebt zentral — Legacy-Pfad wird migriert oder
    # aus schema.sql neu angelegt. Kein manuelles 'install.py --repair' noetig.
    if not P.GOALCHAIN_DB.exists() and _heal_goalchain_db():
        ok(f"goal-chain: DB zentral angelegt ({P.GOALCHAIN_DB.relative_to(P.SHINON_HOME)})")
        fixes += 1
    # Verwaistes Backup nie stillschweigend überschreiben — echte TIDs.
    legacy_bak = P.PROJECT_PROJECT_GOALCHAIN_DB.parent / "tid-state.db.bak"
    if legacy_bak.exists():
        warn(f"Backup vorhanden: {legacy_bak.relative_to(P.PROJECT_ROOT)} — "
             f"ältere TIDs liegen dort; wird NIE automatisch überschrieben.")
    for db_path, label in [
        (P.LIMEN_DB, "LIMEN"),
        (P.GOALCHAIN_DB, "goal-chain"),
        (P.KARMA_DB, "KARMA"),
        (P.SHINON_MEM, "Shinon-Memory"),
    ]:
        if not db_path.exists():
            warn(f"{label}: fehlt ({db_path.relative_to(P.SHINON_HOME)})")
            issues += 1
            continue
        health = check_sqlite(db_path)
        if health["ok"]:
            ok(
                f"{label}: {health['tables']} Tabellen, integrity OK, "
                f"journal={health['journal_mode']}, lock/read OK"
            )
        else:
            fail(f"{label}: SQLite-Healthcheck fehlgeschlagen – {health.get('error', health)}")
            warn(f"  -> Backup nach .bak, neu initialisiert beim naechsten Install")
            fixes += 1

    # 3. Configs
    print(f"\n{BOLD}3. Konfiguration{NC}")
    shinon_cfg = P.CONFIG_DIR / "shinon.toml"
    limen_cfg  = P.CONFIG_DIR / "limen.toml"
    if shinon_cfg.exists():
        ok(f"Shinon-Config: {shinon_cfg.relative_to(P.SHINON_HOME)}")
    else:
        fail("Shinon-Config fehlt")
        issues += 1
    if limen_cfg.exists():
        ok(f"LIMEN-Config:  {limen_cfg.relative_to(P.SHINON_HOME)}")
    else:
        fail("LIMEN-Config fehlt")
        issues += 1

    # 4. API-Keys (LIMEN-DB — schema-aware query)
    print(f"\n{BOLD}4. API-Keys (LIMEN-DB){NC}")
    # Auto-heal: wenn .env Keys hat und LIMEN noch keine, einmalig importieren.
    n_env = _heal_keys_from_env()
    if n_env:
        ok(f"{n_env} API-Key(s) automatisch aus .env importiert")
        fixes += n_env
    if P.LIMEN_DB.exists():
        try:
            with sqlite3.connect(str(P.LIMEN_DB)) as conn:
                conn.row_factory = sqlite3.Row
                rows = providers_has_keys(conn)
            if rows:
                ok(f"{len(rows)} API-Key(s) gefunden")
                for r in rows:
                    icon = "[active]" if r["status"] == "active" else "[cooldown]"
                    total = (r["error_count"] or 0) + (r["success_count"] or 0)
                    if total > 0:
                        health_pct = round((r["success_count"] or 0) / total * 100, 1)
                        health = f"{health_pct:.1f}%"
                    else:
                        health = "n/a"
                    info(f"  {icon:<10} {r['provider']:<14s} health={health}")
            else:
                warn("Keine API-Keys konfiguriert")
                tip("Mit 'python shinon-setup.py --step 2' einen Key anlegen "
                    "oder mit 'cp .env.example /home/<user>/.shinon/config/.env' "
                    "alle Keys auf einmal eintragen.")
                issues += 1
        except sqlite3.DatabaseError as e:
            fail(f"Konnte LIMEN-DB nicht lesen: {e}")
            issues += 1
    else:
        warn("LIMEN-DB fehlt -> Keys koennen nicht geprueft werden")
        issues += 1

    # 5. Keys-Mirror
    print(f"\n{BOLD}5. Key-Mirror (LIMEN-internal){NC}")
    n_mirror = _rebuild_keys_json_from_limen()
    if n_mirror:
        ok(f"keys.json aus LIMEN-DB neu aufgebaut ({n_mirror} Eintrag/Eintraege)")
        fixes += 1
    if P.KEYS_FILE.exists():
        try:
            mirror = json.loads(P.KEYS_FILE.read_text())
            ok(f"{len(mirror)} Eintrag/Eintraege in keys.json")
        except (json.JSONDecodeError, OSError) as e:
            fail(f"keys.json korrupt: {e}")
            issues += 1
    else:
        info("keys.json noch nicht angelegt — wird beim ersten "
             "'shinon-setup --step 2' erstellt.")

    # 6. Ports
    print(f"\n{BOLD}6. Ports{NC}")
    for port, label in [(8000, "LIMEN"), (4300, "shinon-ui"), (4200, "Dashboard")]:
        if port_in_use(port):
            ok(f"Port {port} ({label}) -- antwortet")
        else:
            info(f"Port {port} ({label}) -- frei")

    # 7. Rust
    print(f"\n{BOLD}7. Rust-Toolchain (fuer pip-Wheels wie tiktoken){NC}")
    cargo = shutil.which("cargo")
    rustc = shutil.which("rustc")
    if cargo and rustc:
        ok(f"cargo + rustc vorhanden ({Path(rustc).name})")
    else:
        user_cargo = Path.home() / ".cargo" / "bin" / "cargo"
        if user_cargo.exists():
            info(f"cargo lokal in {Path.home() / '.cargo'} — wird von install.py "
                 f"automatisch in die Shell-RC-Dateien eingetragen; neues Terminal "
                 f"oeffnen oder 'source ~/.bashrc' ausfuehren.")
        else:
            warn("Rust nicht installiert (kein Issue, solange alle pip-Wheels passen)")

    # 8. LIMEN-Healthcheck (Schema-upgrade test)
    print(f"\n{BOLD}8. LIMEN-DB Schema{NC}")
    if P.LIMEN_DB.exists():
        with sqlite3.connect(str(P.LIMEN_DB)) as conn:
            schema_v = conn.execute("PRAGMA user_version").fetchone()[0]
            cols = [r[1] for r in conn.execute(
                "PRAGMA table_info(providers)").fetchall()]
        ok(f"Schema-Version: {schema_v}")
        if "meta_json" in cols and "api_key_fingerprint" in cols:
            ok("providers-Spalten passen zum erwarteten Schema")
        else:
            warn(f"providers-Spalten passen NICHT (meta_json/api_key_fingerprint fehlt). "
                 f"Bitte 'python install.py --repair'.")
            issues += 1

    # 9. KARMA persistence access (read/write lock without mutation)
    print(f"\n{BOLD}9. KARMA-Memory & SQLite-Zugriff{NC}")
    try:
        import sys as _sys
        _sys.path.insert(0, str(P.PROJECT_ROOT / "karma-main"))
        from karma.core.persistence import PersistenceConfig, PersistenceLayer
        # Probe the actual central runtime DB. Do not create a persistent
        # doctor-check project/database as a side effect of diagnostics.
        karma_persistence = PersistenceLayer(
            PersistenceConfig(framework_dir=P.KARMA_DIR, db_filename=P.KARMA_DB.name)
        )
        karma_health = karma_persistence.health_check()
        if karma_health.get("ok"):
            ok(
                f"KARMA SQLite erreichbar: {karma_health['path']} "
                f"(WAL={karma_health['journal_mode']}, "
                f"integrity={karma_health['integrity']}, "
                f"foreign_keys={karma_health['foreign_keys']})"
            )
        else:
            fail(f"KARMA SQLite Healthcheck fehlgeschlagen: {karma_health}")
            issues += 1
    except Exception as e:
        fail(f"KARMA-Memory nicht erreichbar: {e}")
        issues += 1

    # 10. Alle zentralen Runtime-Datenbanken nochmals mit dem gemeinsamen
    # Health-Protokoll prüfen. Das deckt auch Datenbanken ab, die oben wegen
    # eines fehlenden optionalen Starts noch nicht gelistet wurden.
    print(f"\n{BOLD}10. Globaler SQLite-Zugriff{NC}")
    for db_path, label in [
        (P.LIMEN_DB, "LIMEN"),
        (P.KARMA_DB, "KARMA"),
        (P.SHINON_MEM, "Shinon-Memory"),
        (P.GOALCHAIN_DB, "goal-chain"),
    ]:
        if not db_path.exists():
            info(f"{label}: nicht angelegt — wird beim Komponentenstart erzeugt")
            continue
        health = check_sqlite(db_path)
        if health["ok"]:
            ok(f"{label}: Zugriff, Integritaet, WAL/Lock und Zweit-Handle OK")
        else:
            fail(f"{label}: globaler SQLite-Check fehlgeschlagen: {health.get('error', health)}")
            issues += 1

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
            "oder schau in logs/")
    return 0


# ═══════════════════════════════════════════════════════════════════════
# KEY-AUFNAHME: aus .env, einzeln, oder gepastet
# ═══════════════════════════════════════════════════════════════════════

def read_env_file(env_path: Path) -> dict[str, str]:
    """Read a .env-style file. Returns {KEY: value}."""
    if not env_path.exists():
        return {}
    env: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(
            r"""^([A-Z_][A-Z0-9_]*)\s*=\s*(?:"([^"\\]*(?:\\.[^"\\]*)*)"|'([^'\\]*(?:\\.[^'\\]*)*)'|([^\s#]+))""",
            line)
        if m:
            key = m.group(1)
            val = (m.group(2) if m.group(2) is not None else
                   m.group(3) if m.group(3) is not None else
                   m.group(4))
            if val is not None:
                env[key] = val
    return env


def _provider_from_env_key(env_key: str) -> Optional[str]:
    """Map GROQ_API_KEY → 'groq', NVIDIA_NIM_API_KEY → 'nvidia', MISTRAL_API_KEY → 'mistral', etc."""
    base = env_key.upper().replace("_API_KEY", "").replace("_NIM", "")
    base = base.lower()
    if base in ("groq", "openrouter", "nvidia", "mistral"):
        return base
    return None


# ═══════════════════════════════════════════════════════════════════════
# Onboarding — Schritte
# ═══════════════════════════════════════════════════════════════════════
def step_1_welcome() -> None:
    banner("Schritt 1/4  —  Was ist Shinon?")
    print("""
  Shinon ist ein AI-Control-Center. Anders als freundliche Chat-Wrapper ist
  Shinon KRITISCH, SKEPTISCH und PRAEZISE.

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


def step_2_keys(direct_env: Optional[Path] = None) -> None:
    banner("Schritt 2/4  -  API-Keys einrichten")
    P.ensure_layout()

    if not P.LIMEN_DB.exists():
        warn("LIMEN-DB fehlt -> 'python install.py' zuerst ausfuehren")
        press_enter()
        return

    # Use the given env-file if any (e.g. --from-env flag), else default path.
    env_path = direct_env or (P.CONFIG_DIR / ".env")

    # ── Mode 1: read from .env file directly (no interactive prompts) ──
    if direct_env is not None or (env_path.exists() and not sys.stdin.isatty()):
        env_keys = read_env_file(env_path)
        if env_keys:
            return _save_keys_from_env(env_keys, source=str(env_path))

    # ── Mode 2: interactive wizard ────────────────────────────────────
    print(f"  Du kannst entweder (1) pro Anbieter einen Key einzeln einfuegen")
    print(f"  oder (2) deine ganze .env-Datei hier hineinpasten.")
    print()
    print(f"  Tipp:    {P.CONFIG_DIR / '.env'} existiert bereits? Dann wird")
    print(f"           'python shinon-setup.py --from-env' bevorzugt.")
    print()

    saved = 0
    keys_mirror: dict[str, str] = {}
    while True:
        print(f"\n  Anbieter: 1=groq, 2=openrouter, 3=nvidia, 4=mistral, 5=Fertig, 6=.env-pasten")
        choice = prompt("Wahl", "1")
        try:
            n = int(choice)
        except ValueError:
            print("  Bitte 1-6")
            continue
        if n == 5:
            break
        if n == 6:
            # Bulk paste mode — read all multi-line input until terminator
            print()
            print("  Pasten einer beliebigen Anzahl KEY=value Zeilen.")
            print("  Leerzeile allein beendet die Eingabe.")
            print()
            print(f"  Beispiel:")
            print(f"    GROQ_API_KEY=gsk_xxx")
            print(f"    OPENROUTER_API_KEY=sk-or-...")
            print(f"    NVIDIA_NIM_API_KEY=nvapi-...")
            print(f"    MISTRAL_API_KEY=...")
            print()
            pasted = _read_multiline()
            env_map = _parse_pasted_env_block(pasted)
            if not env_map:
                warn("Nichts geparst — kein KEY=value erkannt.")
                continue
            saved += _save_keys_from_env(env_map, source="pasted")
            continue
        if n not in (1, 2, 3, 4):
            continue
        provider = ["groq", "openrouter", "nvidia", "mistral"][n - 1]
        meta = PROVIDER_INFO[provider]
        print()
        print(f"  Hole einen Key von:  {meta['url']}")
        print(f"  Bezahlung:           {meta['tier']}")
        print()
        print(f"  Einfuegen sichtbar (kein getpass-Verbergen). "
              f"Leer = ueberspringen.")
        pasted = prompt_pasteable_key(f"{provider}-API-Key")
        if not pasted:
            warn("Leerer Key, uebersprungen.")
            continue

        # If user pasted a multi-line block, parse it and store each provider.
        if "\n" in pasted and "=" in pasted:
            env_map = _parse_pasted_env_block(pasted)
            saved += _save_keys_from_env(env_map, source="pasted")
            continue

        # Single-line — store as this provider
        saved += _store_single_key(provider, pasted, "wizard", keys_mirror)

    if saved == 0:
        warn("Keine Keys eingerichtet. Spater mit 'python shinon-setup.py --step 2' "
             f"nachholen (oder in {P.CONFIG_DIR / '.env'} eintragen).")
    else:
        ok(f"{saved} API-Key(s) gespeichert. "
           f"LIMEN rotiert automatisch bei 429.")
        if keys_mirror:
            _write_keys_json(keys_mirror)
            ok(f"Key-Mirror in {P.KEYS_FILE.relative_to(P.SHINON_HOME)} "
               f"geschrieben (mode 0600).")
    press_enter()


def _read_multiline() -> str:
    """Read multi-line input from stdin until a single blank line or EOF."""
    lines: list[str] = []
    try:
        while True:
            line = input()
            if line.strip() == "" and lines:
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines)


def _store_single_key(provider: str, key_value: str,
                       source: str, mirror: dict[str, str]) -> int:
    if not P.LIMEN_DB.exists():
        warn("LIMEN-DB fehlt — kann nicht speichern.")
        return 0
    fingerprint = _fingerprint_of(key_value)
    with sqlite3.connect(str(P.LIMEN_DB)) as conn:
        key_id = upsert_provider_key(conn, provider, key_value, source=source)
        conn.commit()
    mirror[provider] = key_value
    ok(f"{PROVIDER_INFO[provider]['tier']:>7s}  {provider}-Key gespeichert "
       f"(fingerprint={fingerprint})")
    return 1


def _save_keys_from_env(env: dict[str, str], *, source: str) -> int:
    """Parse a .env-style mapping {KEY: value}, store each provider's key."""
    if not P.LIMEN_DB.exists():
        warn("LIMEN-DB fehlt — kann nicht speichern. "
             "Bitte zuerst 'python install.py' ausfuehren.")
        return 0
    saved = 0
    mirror: dict[str, str] = {}
    with sqlite3.connect(str(P.LIMEN_DB)) as conn:
        for env_key, val in env.items():
            prov = _provider_from_env_key(env_key)
            if prov is None or not val:
                continue
            try:
                upsert_provider_key(conn, prov, val, source=source)
                mirror[prov] = val
                saved += 1
                ok(f"{PROVIDER_INFO[prov]['tier']:>7s}  {prov}-Key importiert "
                   f"(aus {env_key}, fingerprint={_fingerprint_of(val)})")
            except sqlite3.DatabaseError as e:
                fail(f"{prov}-Key nicht gespeichert: {e}")
        conn.commit()
    if saved > 0 and mirror:
        _write_keys_json(mirror)
        ok(f"Key-Mirror in {P.KEYS_FILE.relative_to(P.SHINON_HOME)} "
           f"geschrieben (mode 0600).")
    return saved


def _attitude_adapter():
    """Central attitudes.db via the canonical fusion adapter (creates the
    table idempotently if missing). Returns None if fusion is unavailable.

    Since the DB unification, attitudes live in their OWN central DB
    ($SHINON_HOME/data/shinon/attitudes.db) with the fusion schema
    (user_id, dimension, score) — NOT in memory.db (legacy key/value
    layout). The fusion AttitudeAdapter is the single source of truth for
    that schema, so we reuse it instead of hand-rolling SQL that drifts.
    """
    try:
        sys.path.insert(0, str(P.PROJECT_FUSION_SRC))
        from fusion.shinon.shinon_attitudes import AttitudeAdapter
        return AttitudeAdapter(P.SHINON_ATTITUDES)
    except ImportError:
        return None


def step_3_personality() -> None:
    banner("Schritt 3/4  -  Persoenlichkeit")
    if not P.SHINON_ATTITUDES.exists():
        warn("Shinon-Attitudes-DB fehlt — bitte 'python install.py' ausfuehren")
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
    adapter = _attitude_adapter()
    if adapter is None:
        fail("fusion-Attitudes-Adapter nicht verfuegbar — Speichern abgebrochen")
        press_enter()
        return
    try:
        for label, col, default in dims:
            val = prompt(label, str(default))
            try:
                v = float(val)
                # Fusion-Schema upsert (gleiche Semantik wie shinon-server.mjs
                # POST /api/personality): user_id='default' ist die globale
                # Persoenlichkeitsansicht, die auch das UI liest.
                adapter.run(
                    "INSERT INTO attitudes (user_id, dimension, score, updated_at) "
                    "VALUES (?, ?, ?, datetime('now')) "
                    "ON CONFLICT(user_id, dimension) DO UPDATE SET "
                    "score = excluded.score, updated_at = datetime('now')",
                    ("default", col, v),
                )
            except ValueError:
                pass
        ok("Persoenlichkeit gespeichert")
        tip(f"Anpassbar jederzeit via 'python shinon-setup.py --step 3' "
            f"oder direkt in {P.CONFIG_DIR / 'shinon.toml'}")
    except sqlite3.DatabaseError as e:
        fail(f"Speichern fehlgeschlagen: {e}")
    press_enter()


def step_4_done() -> None:
    banner("Schritt 4/4  -  Fertig!")
    print(f"""
  Naechste Schritte:

    ./shinon start        # alle Komponenten starten
    ./shinon status       # Status anzeigen
    ./shinon chat         # Chat-Oberflaeche (Browser oeffnet)
    ./shinon --doc        # jederzeit Diagnose

  Auf Windows ersetze './shinon' mit 'shinon.cmd'.

  Bei Problemen: 'python install.py --repair' repariert Configs + DBs.

  Zentrale Daten liegen jetzt in:
    {P.SHINON_HOME}

  Keys editieren:
    {P.CONFIG_DIR / '.env'}   <- eine Datei, alle Anbieter
""")
    marker = P.CONFIG_DIR / ".onboarding-done"
    marker.write_text(json.dumps({
        "version": "1.0.0",
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "shinon_home": str(P.SHINON_HOME),
    }, indent=2), encoding="utf-8")
    ok("Onboarding abgeschlossen. Viel Erfolg mit Shinon!")


def onboarding(start_step: int = 1) -> int:
    steps = [
        step_1_welcome, step_2_keys, step_3_personality,
        lambda: (step_4_done(), None)[1],
    ]
    banner("Shinon  ·  Onboarding (4 Schritte)")
    print(f"  Zentrale Daten:   {P.SHINON_HOME}")
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
    args = sys.argv[1:]
    if args and args[0] in ("--doc", "doc"):
        return doctor_mous()
    if args and args[0] == "--from-env":
        env_path = Path(args[1]).expanduser() if len(args) >= 2 else (P.CONFIG_DIR / ".env")
        if not env_path.exists():
            fail(f"{env_path} nicht gefunden. Kopiere .env.example dorthin "
                 f"oder erstelle sie manuell.")
            return 1
        env_map = read_env_file(env_path)
        if not env_map:
            warn(f"{env_path} ist leer.")
            return 0
        saved = _save_keys_from_env(env_map, source=str(env_path))
        return 0 if saved else 1
    if args and args[0] == "--step":
        try:
            step = int(args[1])
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
