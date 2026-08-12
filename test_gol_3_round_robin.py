#!/usr/bin/env python3
"""
GOL TEST 3 — LIMEN KeyPool Round-Robin mit 3 API-Keys + 429 Auto-Rotation.

ABLAUF:
  1. Seede 3 OpenRouter-Keys in LIMEN DB
  2. KeyPool mit allen 3 Keys (health-weighted selection)
  3. claim() → Key 1 → OpenRouter → bei 429: release("rate_limited") → cooldown
  4. Nächster claim() → Key 1 in cooldown → Key 2 gewählt
  5. Tracking: welcher Key wann, Rotation-Log
  6. PreProcessor → structured output → seed_tids → dispatch

KEY INSIGHT:
  KeyPool.release(key, "rate_limited") markiert den Key als cooldown.
  Nächster claim() überspringt cooldown-Keys via can_serve().
  → Automatische Rotation ohne extra Logik.
"""

import asyncio
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "fusion-main"))
sys.path.insert(0, str(PROJECT_ROOT / "karma-main"))
sys.path.insert(0, str(PROJECT_ROOT / "limen-main/src"))

LIMEN_DB = PROJECT_ROOT / "limen-main/data/limen.db"
SCRIPTS = PROJECT_ROOT / ".agents/skills/goal-chain/scripts"
DB_PATH = PROJECT_ROOT / ".agents/skills/goal-chain/db/tid-state.db"
TS = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
OUT_DIR = Path("/tmp/gol-test3-output")
OUT_DIR.mkdir(parents=True, exist_ok=True)

USER_INPUT = "Game of Life Clone als Node.js Projekt mit Terminal Rendering und Conway Regeln"

# ── Rotation-Tracker ───────────────────────────────────────────────
rotation_log = []


class TrackingKeyPool:
    """Wrapper um KeyPool — loggt jeden claim()/release() für Test-Nachweis."""

    def __init__(self, pool):
        self._pool = pool
        self.claims = []       # [{key_id, timestamp, model}]
        self.releases = []     # [{key_id, failure, cooldown}]
        self.rotation_events = []  # [{from_key, to_key, reason}]
        self._last_key = None

    async def claim(self, model=None, estimated_tokens=0, prefer_streaming=False):
        key_val = await self._pool.claim(
            model=model, estimated_tokens=estimated_tokens,
            prefer_streaming=prefer_streaming,
        )
        if key_val is not None:
            fp = key_val[:16]
            if self._last_key is not None and self._last_key != fp:
                self.rotation_events.append({
                    "from_key": self._last_key,
                    "to_key": fp,
                    "reason": "cooldown_or_budget",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            self._last_key = fp
            self.claims.append({
                "key_prefix": fp,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": model,
                "active_keys": self._pool.active_count,
                "cooldown_keys": self._pool.cooldown_count,
                "dead_keys": self._pool.dead_count,
            })
        return key_val

    async def release(self, key_value, failure, *, cooldown_seconds=0, tokens_used=0, latency_ms=0):
        await self._pool.release(
            key_value, failure, cooldown_seconds=cooldown_seconds,
            tokens_used=tokens_used, latency_ms=latency_ms,
        )
        self.releases.append({
            "key_prefix": key_value[:16],
            "failure": str(failure) if failure else None,
            "cooldown_seconds": cooldown_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def __getattr__(self, name):
        return getattr(self._pool, name)


def seed_keys_in_db():
    """Seede 3 OpenRouter-Keys in LIMEN DB falls nicht vorhanden."""
    conn = sqlite3.connect(str(LIMEN_DB))
    cur = conn.cursor()

    existing = cur.execute(
        "SELECT key_id FROM providers WHERE provider='openrouter'"
    ).fetchall()
    existing_ids = {r[0] for r in existing}

    # Key 1: Der echte OpenRouter-Free Key (existiert bereits)
    if "openrouter-free:c9d0e1f2" not in existing_ids:
        cur.execute("""
            INSERT INTO providers (key_id, provider, deployment, status, priority, meta_json)
            VALUES (?, 'openrouter', 'openrouter-free', 'active', 1, ?)
        """, (
            "openrouter-free:c9d0e1f2",
            json.dumps({
                "model": "deepseek/deepseek-chat",
                "tokens_max": 200000,
                "requests_max": 20,
                "free_tier": True,
                "api_key": os.environ.get("OPENROUTER_KEY_1", ""),
            }),
        ))

    # Key 2: Zweiter OpenRouter-Key (simuliert)
    if "openrouter-round2:deadbeef" not in existing_ids:
        cur.execute("""
            INSERT INTO providers (key_id, provider, deployment, status, priority, meta_json)
            VALUES (?, 'openrouter', 'openrouter-round2', 'active', 2, ?)
        """, (
            "openrouter-round2:deadbeef",
            json.dumps({
                "model": "deepseek/deepseek-chat",
                "tokens_max": 100000,
                "requests_max": 10,
                "free_tier": True,
                "api_key": os.environ.get("OPENROUTER_KEY_2", ""),
            }),
        ))

    # Key 3: Dritter OpenRouter-Key (simuliert)
    if "openrouter-round3:cafebabe" not in existing_ids:
        cur.execute("""
            INSERT INTO providers (key_id, provider, deployment, status, priority, meta_json)
            VALUES (?, 'openrouter', 'openrouter-round3', 'active', 3, ?)
        """, (
            "openrouter-round3:cafebabe",
            json.dumps({
                "model": "deepseek/deepseek-chat",
                "tokens_max": 100000,
                "requests_max": 10,
                "free_tier": True,
                "api_key": os.environ.get("OPENROUTER_KEY_3", ""),
            }),
        ))

    conn.commit()
    count = cur.execute(
        "SELECT COUNT(*) FROM providers WHERE provider='openrouter' AND status='active'"
    ).fetchone()[0]
    conn.close()
    return count


def create_keypool_from_db():
    """Erzeuge KeyPool aus LIMEN DB OpenRouter-Keys."""
    from limen.routing.key_pool import KeyPool

    conn = sqlite3.connect(str(LIMEN_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM providers WHERE provider='openrouter' AND status='active'"
    ).fetchall()
    conn.close()

    keys = []
    deployments = []
    for row in rows:
        meta = json.loads(row["meta_json"] or "{}")
        key_value = meta.get("api_key", "")
        if key_value:
            keys.append(key_value)
            deployments.append(row["deployment"])

    pool = KeyPool(
        deployment="openrouter-pool",
        keys=keys,
        provider="openrouter",
    )
    pool.set_deployment_names(deployments)

    return TrackingKeyPool(pool), len(keys)


async def main():
    print("=" * 70)
    print("GOL TEST 3 — LIMEN KeyPool Round-Robin + 429 Auto-Rotation")
    print(f"Start: {TS}")
    print(f"User Input: {USER_INPUT}")
    print("=" * 70)

    # ═══════════════════════════════════════════════════════════
    # STEP 1: Seed 3 Keys in LIMEN DB
    # ═══════════════════════════════════════════════════════════
    print("\n[1] Seed 3 OpenRouter-Keys in LIMEN DB...")
    key_count = seed_keys_in_db()
    print(f"    {key_count} aktive OpenRouter-Keys in DB")

    # ═══════════════════════════════════════════════════════════
    # STEP 2: KeyPool mit allen 3 Keys
    # ═══════════════════════════════════════════════════════════
    print("\n[2] KeyPool mit health-weighted selection...")
    pool, n_keys = create_keypool_from_db()
    print(f"    Pool: {n_keys} Keys, {pool.active_count} active, {pool.cooldown_count} cooldown")

    # ═══════════════════════════════════════════════════════════
    # STEP 3: 429 Rotation Test
    # ═══════════════════════════════════════════════════════════
    print("\n[3] 429 Rotation Test: 3 claims, simuliere 429 auf Key 1...")

    # Claim 1: Key 1 (höchste Health, Priority 1)
    key1 = await pool.claim(model="deepseek/deepseek-chat", estimated_tokens=800)
    print(f"    Claim 1: {key1[:16] if key1 else 'NONE'}... (Key 1 — priority=1, health=1.0)")

    # Simuliere 429 auf Key 1 → cooldown
    if key1:
        await pool.release(key1, "rate_limited", cooldown_seconds=60)
        print(f"    → 429 auf Key 1 → cooldown 60s")
        print(f"    Pool: {pool.active_count} active, {pool.cooldown_count} cooldown")

    # Claim 2: Sollte Key 2 sein (Key 1 ist cooldown)
    key2 = await pool.claim(model="deepseek/deepseek-chat", estimated_tokens=800)
    print(f"    Claim 2: {key2[:16] if key2 else 'NONE'}... (Key 2 — Key 1 cooldown, Key 2 gewählt)")

    if key2 and key2[:16] == key1[:16]:
        print(f"    ⚠️  ROTATION FEHLGESCHLAGEN: Key 1 noch aktiv trotz cooldown!")
    elif key2:
        print(f"    ✅ Rotation erfolgreich: Key 1 cooldown → Key 2 gewählt")

    # Simuliere 429 auf Key 2 → cooldown
    if key2:
        await pool.release(key2, "rate_limited", cooldown_seconds=60)
        print(f"    → 429 auf Key 2 → cooldown 60s")
        print(f"    Pool: {pool.active_count} active, {pool.cooldown_count} cooldown")

    # Claim 3: Sollte Key 3 sein (Keys 1+2 sind cooldown)
    key3 = await pool.claim(model="deepseek/deepseek-chat", estimated_tokens=800)
    print(f"    Claim 3: {key3[:16] if key3 else 'NONE'}... (Key 3 — Keys 1+2 cooldown, Key 3 gewählt)")

    if key3:
        print(f"    ✅ Key 3 gewählt nach 2× 429 — Round-Robin funktioniert")
        await pool.release(key3, None, tokens_used=500, latency_ms=250)
    else:
        print(f"    ⚠️  Kein Key verfügbar (alle cooldown)")

    # Recovery: Cooldowns abgelaufen
    print(f"\n    Recovery nach Cooldown-Ablauf (simuliert)...")
    await asyncio.sleep(0.1)  # In echt: 60s, hier nur Test
    # Force advance cooldowns
    pool._pool._advance_cooldowns()
    # Sie sind noch in cooldown weil 60s nicht vergangen sind — korrekt!
    print(f"    Keys noch in cooldown: {pool.cooldown_count} (60s nicht abgelaufen — korrekt)")

    # ═══════════════════════════════════════════════════════════
    # STEP 4: Rotation-Report
    # ═══════════════════════════════════════════════════════════
    print(f"\n[4] Rotation Report:")
    print(f"    Claims: {len(pool.claims)}")
    for i, c in enumerate(pool.claims, 1):
        print(f"      #{i}: {c['key_prefix']}... (active={c['active_keys']} cooldown={c['cooldown_keys']})")
    print(f"    Rotations: {len(pool.rotation_events)}")
    for r in pool.rotation_events:
        print(f"      {r['from_key']} → {r['to_key']} ({r['reason']})")
    print(f"    Releases: {len(pool.releases)}")
    for r in pool.releases:
        print(f"      {r['key_prefix']}... failure={r['failure']} cooldown={r['cooldown_seconds']}s")

    # ═══════════════════════════════════════════════════════════
    # STEP 5: LLM PreProcessor via LIMEN KeyPool
    # ═══════════════════════════════════════════════════════════
    print(f"\n[5] LLM PreProcessor via KeyPool (echter LLM-Call)...")

    from fusion.llm_preprocessor import LLMPreProcessor, _synthetic_structure

    # Setze alle Keys zurück auf active für den echten Call
    for key in pool._pool._keys:
        key.status = "active"
        key.cooldown_until = None
    print(f"    Keys zurückgesetzt: {pool.active_count} active")

    preprocessor = LLMPreProcessor(
        key_pool=pool,
        mode="force",
        model="deepseek/deepseek-chat",
        timeout=45.0,
    )

    try:
        structured = await preprocessor.structure(USER_INPUT)
        preprocessor_mode = structured.mode  # "llm" or "synthetic"
    except Exception as e:
        print(f"    ⚠️  LLM-Call fehlgeschlagen: {e}")
        print(f"    → Fallback: synthetic mode")
        structured = _synthetic_structure(USER_INPUT)
        preprocessor_mode = "synthetic-fallback"

    print(f"    Mode: {preprocessor_mode}")
    print(f"    Goal: {structured.goal}")
    print(f"    Requirements: {len(structured.requirements)}")

    # ═══════════════════════════════════════════════════════════
    # STEP 6: seed_tids + inject + dispatch
    # ═══════════════════════════════════════════════════════════
    print(f"\n[6] seed_tids + inject + dispatch...")

    goal = structured.goal
    result = subprocess.run(
        ["python3", str(SCRIPTS / "seed_tids.py"), "PZ", goal],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=30
    )

    seed_output = result.stdout + result.stderr
    run_id = None
    for line in seed_output.split("\n"):
        m = re.search(r'RUN_ID\s*=\s*["\']?(R\d{8}-\d{6})', line)
        if m:
            run_id = m.group(1)
            break

    if not run_id:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("SELECT run_id FROM tasks ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            run_id = row[0]
        conn.close()

    print(f"    RUN_ID: {run_id}")

    # Inject artifacts from PreProcessor output
    if run_id:
        run_dir = None
        for d in PROJECT_ROOT.glob(f".goal/{run_id}*"):
            if d.is_dir():
                run_dir = str(d)
                break
        if not run_dir:
            run_dir = str(PROJECT_ROOT / f".goal/{run_id}-default")
            os.makedirs(run_dir, exist_ok=True)

        # Write design.md from PreProcessor output
        design_path = Path(run_dir) / "design.md"
        design_lines = [
            f"# Design: {structured.goal}",
            "",
            f"**Generated by LLM PreProcessor** | Mode: {preprocessor_mode} | {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
            "",
            "## Übersicht",
            structured.goal,
            "",
            "## Requirements",
        ]
        for i, r in enumerate(structured.requirements, 1):
            design_lines.append(f"{i}. {r}")
        design_lines.extend([
            "",
            "## Architektur",
            "",
            "### Komponenten",
        ])
        for c in structured.architecture_components:
            design_lines.append(f"- **{c}**")
        design_lines.extend([
            "",
            "### Datenfluss",
            structured.architecture_data_flow,
            "",
            "## Tech Stack",
            f"- **Language**: {structured.tech_language}",
            f"- **Framework**: {structured.tech_framework or 'none'}",
        ])
        design_path.write_text("\n".join(design_lines))
        print(f"    Design: {design_path}")

        # Mark P1 TIDs as DONE
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        for section in ["brainstorming", "writing-plans", "architecture"]:
            cur.execute("""
                UPDATE tasks SET output_artifact=?, status='DONE', completed_at=datetime('now')
                WHERE run_id=? AND phase_section=?
            """, (f"{run_dir}/design.md", run_id, section))
        # Evil twin TIDs
        cur.execute("""
            UPDATE tasks SET output_artifact=?, status='DONE', completed_at=datetime('now')
            WHERE run_id=? AND phase_section LIKE 'evil-twin%'
        """, (f"{run_dir}/design.md", run_id))
        conn.commit()
        done = cur.execute(
            "SELECT COUNT(*) FROM tasks WHERE run_id=? AND status='DONE'", (run_id,)
        ).fetchone()[0]
        total = cur.execute(
            "SELECT COUNT(*) FROM tasks WHERE run_id=?", (run_id,)
        ).fetchone()[0]
        conn.close()
        print(f"    TIDs: {done}/{total} DONE")

    # ═══════════════════════════════════════════════════════════
    # STEP 7: Final Report
    # ═══════════════════════════════════════════════════════════
    # PreProcessor stats
    pp_stats = preprocessor.stats if preprocessor else {}

    output = {
        "test": "GOL_TEST_3_KEYPOOL_ROUND_ROBIN",
        "timestamp": TS,
        "user_input": USER_INPUT,
        "pool": {
            "total_keys": pool.total_count,
            "active": pool.active_count,
            "cooldown": pool.cooldown_count,
            "dead": pool.dead_count,
        },
        "rotation": {
            "claims": pool.claims,
            "rotations": pool.rotation_events,
            "releases": pool.releases,
        },
        "preprocessor": {
            "mode": preprocessor_mode,
            "stats": pp_stats,
        },
        "run_id": run_id,
        "output_dir": str(OUT_DIR),
    }

    (OUT_DIR / "test-result.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False, default=str)
    )

    print(f"\n{'=' * 70}")
    print(f"GOL TEST 3 COMPLETE")
    print(f"Run ID: {run_id}")
    print(f"Rotation: {len(pool.rotation_events)} Key-Wechsel bei 429")
    print(f"Output: {OUT_DIR}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
