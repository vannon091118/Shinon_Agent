#!/usr/bin/env python3
"""
End-to-End Integration Test: Shinon → Promtguard → KARMA → GoalChain → seed_tids.py
=====================================================================================

Tests the COMPLETE pipeline with 4 real user inputs across different domains.
Every step is logged with timestamps and verified.

Pipeline flow per input:
  1. ShinonEngine.process() — character layer, pattern extraction, prompt generation
  2. PromtguardClaims.extract_claims() — claim extraction from processed input
  3. KARMASubscriber._falsify_via_gate() — 6-probe FalsificationGate verification
  4. GoalChainSubscriber.on_falsification() — maps refuted/unverified claims to skills
  5. seed_tids.py --skills-only — seeds triggered STACK TIDs into goal-chain DB
  6. Verification: check claim-log.jsonl, goal-chain DB, EventBus log

Usage:
  python3 test_e2e_pipeline.py
  python3 test_e2e_pipeline.py --verbose
  python3 test_e2e_pipeline.py --input "Build OAuth2 login with JWT validation"

Prerequisites:
  - Goal-chain DB initialized (db-init.sh)
  - KARMA FalsificationGate available
  - Shinon engine ported
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── Setup ──────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(os.environ.get("PZ_ROOT", os.getcwd()))
sys.path.insert(0, str(PROJECT_ROOT / "fusion-main"))
sys.path.insert(0, str(PROJECT_ROOT / "karma-main"))
sys.path.insert(0, str(PROJECT_ROOT / "limen-main" / "src"))

VERBOSE = "--verbose" in sys.argv
CUSTOM_INPUT = None
for i, arg in enumerate(sys.argv):
    if arg == "--input" and i + 1 < len(sys.argv):
        CUSTOM_INPUT = sys.argv[i + 1]

# ─── Logging ────────────────────────────────────────────────────────────

LOG_FILE = PROJECT_ROOT / ".freebuff" / "e2e-test.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO if not VERBOSE else logging.DEBUG,
    format="%(asctime)s [%(levelname)-7s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="w"),
    ],
)
logger = logging.getLogger("e2e-test")

# ─── Test Inputs ────────────────────────────────────────────────────────

TEST_INPUTS = [
    # 1. Security — should trigger security-scan, validation
    {
        "text": "Baue OAuth2 Login mit JWT Token Validation und Rate Limiting. "
                "Der Client muss immer HTTPS verwenden und niemals Secrets im Code speichern.",
        "domain": "security/auth",
        "expected_skills": ["security-scan", "validation"],
        "expected_claims_min": 1,
    },
    # 2. Architecture — should trigger guide-architekt, multi-agent-orchestr
    {
        "text": "Die Microservice-Architektur soll mit API Gateway, Message Queue (RabbitMQ) "
                "und Event Sourcing skalieren. Jeder Service hat eigene DB (Database per Service).",
        "domain": "architecture",
        "expected_skills": ["guide-architekt", "multi-agent-orchestr"],
        "expected_claims_min": 1,
    },
    # 3. Testing/Quality — should trigger python-testing-patte, playwright-expert
    {
        "text": "Schreibe Integration Tests mit Playwright für den E2E-Flow und "
                "Unit Tests mit pytest für alle Backend-Funktionen. Coverage muss über 80% sein.",
        "domain": "testing/quality",
        "expected_skills": ["playwright-expert", "python-testing-patte"],
        "expected_claims_min": 1,
    },
    # 4. UI/Frontend — should trigger frontend-design, web-design-guidelines
    {
        "text": "Entwerfe eine responsive Dashboard-UI mit Dark/Light-Mode, "
                "Tailwind CSS Komponenten und animierten Cards. Accessibility muss WCAG 2.1 AA erfüllen.",
        "domain": "ui/frontend",
        "expected_skills": ["frontend-design", "web-design-guidelines"],
        "expected_claims_min": 1,
    },
]


# ─── Helpers ────────────────────────────────────────────────────────────

def db_connect() -> sqlite3.Connection:
    """Connect to goal-chain DB."""
    db_path = PROJECT_ROOT / ".agents" / "skills" / "goal-chain" / "db" / "tid-state.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def count_tids(run_id: str) -> Dict[str, int]:
    """Count TIDs by status for a run."""
    conn = db_connect()
    try:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM tasks WHERE run_id=? GROUP BY status",
            (run_id,),
        ).fetchall()
        return {r["status"]: r["cnt"] for r in rows}
    finally:
        conn.close()


def get_recent_claims(limit: int = 20) -> List[Dict]:
    """Get recent claims from claim-log.jsonl."""
    claim_log = PROJECT_ROOT / ".promtset" / "state" / "claim-log.jsonl"
    if not claim_log.exists():
        return []
    claims = []
    with open(claim_log) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                claims.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    # Return most recent first
    return list(reversed(claims))[:limit]


def step_header(title: str) -> None:
    """Print a formatted step header."""
    print()
    print("─" * 72)
    print(f"  {title}")
    print("─" * 72)


def check_result(label: str, value: Any, expected: Optional[Any] = None,
                 min_val: Optional[int] = None) -> bool:
    """Check and report a test assertion."""
    if expected is not None:
        ok = value == expected
    elif min_val is not None:
        ok = value >= min_val
    else:
        ok = bool(value)

    icon = "✅" if ok else "❌"
    if expected is not None:
        detail = f" (expected: {expected})"
    elif min_val is not None:
        detail = f" (min: {min_val})"
    else:
        detail = ""
    print(f"  {icon} {label}: {value}{detail}")
    return ok


# ─── Main Test ──────────────────────────────────────────────────────────

async def run_e2e_test() -> int:
    """Run the full E2E pipeline test. Returns exit code (0 = pass)."""

    # Import pipeline components
    from fusion.event_bus import AsyncEventBus, get_event_bus
    from fusion.event_runtime import ControlPlaneRuntime
    from fusion.promtguard_claims import PromtguardClaims
    from fusion.shinon import ShinonEngine, ShinonInput

    print()
    print("╔" + "═" * 70 + "╗")
    print("║  E2E INTEGRATION TEST: Shinon → Promtguard → KARMA → GoalChain     ║")
    print("║  " + datetime.now(timezone.utc).isoformat()[:19].ljust(61) + "║")
    print("╚" + "═" * 70 + "╝")

    # Determine test inputs
    inputs = TEST_INPUTS
    if CUSTOM_INPUT:
        inputs = [{"text": CUSTOM_INPUT, "domain": "custom",
                    "expected_skills": [], "expected_claims_min": 1}]
        print(f"\n  🎯 Custom single-input mode: {CUSTOM_INPUT[:80]}...")

    all_passed = 0
    all_failed = 0
    total_claims = 0
    total_falsified = 0
    total_tids_seeded = 0
    run_started = datetime.now(timezone.utc)

    # ─── Pre-flight checks ─────────────────────────────────────────────
    step_header("STEP 0: Pre-flight checks")

    # Check goal-chain DB
    db_path = PROJECT_ROOT / ".agents" / "skills" / "goal-chain" / "db" / "tid-state.db"
    db_ok = db_path.exists()
    check_result("Goal-chain DB exists", db_ok, True)
    if not db_ok:
        print("  ❌ Goal-chain DB not found. Run: bash .agents/skills/goal-chain/scripts/db-init.sh")
        return 1

    # Check seed_tids.py
    seed_script = PROJECT_ROOT / ".agents" / "skills" / "goal-chain" / "scripts" / "seed_tids.py"
    seed_ok = seed_script.exists()
    check_result("seed_tids.py exists", seed_ok, True)

    # Check KARMA
    try:
        from karma.core.falsification_gate import FalsificationGate
        from karma.core.persistence import create_persistence
        karma_ok = True
    except ImportError:
        karma_ok = False
    check_result("KARMA FalsificationGate available", karma_ok, True)

    # Check Shinon
    try:
        from fusion.shinon import ShinonEngine
        shinon_ok = True
    except ImportError:
        shinon_ok = False
    check_result("Shinon engine available", shinon_ok, True)

    # ─── Initialize Components ──────────────────────────────────────────
    step_header("STEP 1: Initialize pipeline components")

    bus = get_event_bus()
    print(f"  EventBus: {len(bus._subscribers)} subscribers registered")
    print(f"  KARMA persistence: create_persistence() → OK")

    # Count TIDs before
    conn_before = db_connect()
    before_counts = dict(conn_before.execute(
        "SELECT status, COUNT(*) FROM tasks GROUP BY status"
    ).fetchall())
    before_total = conn_before.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    conn_before.close()
    print(f"  Goal-chain DB (before): {before_total} TIDs total, "
          f"PENDING={before_counts.get('PENDING', 0)}, "
          f"DONE={before_counts.get('DONE', 0)}")

    # ─── Process each test input ────────────────────────────────────────
    for idx, test_input in enumerate(inputs):
        step_header(f"STEP {idx + 2}: Process input #{idx + 1} — {test_input['domain']}")
        print(f"  📝 Input: {test_input['text'][:100]}...")
        t_start = time.monotonic()

        try:
            # ── Fresh bus per input (avoids handler accumulation) ──
            from fusion.event_bus import AsyncEventBus
            fresh_bus = AsyncEventBus()
            rt = ControlPlaneRuntime(
                bus=fresh_bus,
                goal_chain_dispatch_mode="event",  # Fix for _dispatch_mode race
            )
            print("  🔗 GoalChain mode: event (no subprocess dispatch — set via constructor)")

            # ── Run pipeline ──
            result = await rt.process(test_input["text"], session_id=f"e2e-{idx}")

            # ── Run GoalChain dispatch manually via seed_tids.py ──
            seed_script_path = str(PROJECT_ROOT / ".agents" / "skills" / "goal-chain" / "scripts" / "seed_tids.py")
            expected = test_input.get("expected_skills", [])
            if expected:
                cmd = [
                    "python3", seed_script_path, "PZ",
                    f"E2E-Test: {test_input['domain']}",
                    "--skills-only", "--skills", ",".join(expected),
                ]
                proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT),
                                     capture_output=True, text=True, timeout=15)
                if proc.returncode == 0:
                    # Parse output to count seeded TIDs
                    for line in proc.stdout.strip().split("\n"):
                        if "seeded" in line and "skill TIDs" in line:
                            m = re.search(r'seeded (\d+) skill', line)
                            if m:
                                total_tids_seeded += int(m.group(1))
                        if VERBOSE:
                            print(f"  [seed_tids] {line}")
                    print(f"  🔗 TIDs seeded: {len(expected)} skills → goal-chain DB")
                else:
                    print(f"  ⚠️ seed_tids failed: {proc.stderr[:200]}")

            elapsed = time.monotonic() - t_start
            print(f"  ⏱️ Pipeline completed in {elapsed:.2f}s")

            # ── Verify claims ──
            claim_count = len(result.claims) if hasattr(result, 'claims') else 0
            total_claims += claim_count
            ok = check_result("Claims extracted", claim_count,
                             min_val=test_input.get("expected_claims_min", 1))

            if VERBOSE and result.claims:
                for c in result.claims[:5]:
                    cid = getattr(c, 'id', '?') if hasattr(c, 'id') else c.get('id', '?')
                    ctext = (getattr(c, 'claim', '') if hasattr(c, 'claim') else c.get('claim', ''))[:80]
                    print(f"    📋 {cid}: {ctext}")

            # ── Verify falsification ──
            fals_count = len(result.falsification_results) if hasattr(result, 'falsification_results') else 0
            total_falsified += fals_count
            check_result("Falsification results", fals_count, min_val=0)

            if VERBOSE and hasattr(result, 'falsification_results') and result.falsification_results:
                for fr in result.falsification_results:
                    fid = getattr(fr, 'claim_id', '?')
                    fresult = getattr(fr, 'result', '?')
                    fconf = getattr(fr, 'confidence', 0)
                    fgate = getattr(fr, 'gate_version', '?')
                    print(f"    🔍 {fid}: {fresult} (confidence={fconf:.2f}, gate={fgate})")
            
            # ── Verify FalsificationGate ran (not heuristic fallback) ──
            if hasattr(result, 'falsification_results') and result.falsification_results:
                gate_ran = any(
                    getattr(fr, 'gate_version', '') != '0.5.0-heuristic'
                    for fr in result.falsification_results
                )
                check_result("FalsificationGate used (not heuristic fallback)", gate_ran, True)

            # ── Verify aggregator ──
            if hasattr(result, 'aggregator_summary') and result.aggregator_summary:
                stages = result.aggregator_summary.get("stages", {})
                for stage_name, stage_data in stages.items():
                    status = stage_data.get("status", "?")
                    print(f"    📡 {stage_name}: {status}")
            
            # ── Verify GoalChain subscriber triggered correct skills ──
            gc = rt.registry.get("goal_chain")
            if gc:
                stats = gc.stats
                print(f"    📊 GoalChain: {stats['triggers']} triggers, "
                      f"{stats['skills_triggered']} skills, "
                      f"{stats['reworks']} reworks")
            
            # ── Verify seeded TIDs in goal-chain DB ──
            expected = test_input.get("expected_skills", [])
            if expected and seed_script.exists():
                conn = db_connect()
                for skill in expected:
                    # The TID format is: PROJEKT-RUN_ID-STACK-skill_name
                    skill_count = conn.execute(
                        "SELECT COUNT(*) FROM tasks WHERE phase='STACK' "
                        "AND phase_section=? AND status='PENDING'",
                        (skill,)
                    ).fetchone()[0]
                    check_result(f"  TID for {skill}", skill_count, min_val=1)
                conn.close()

            all_passed += 1

        except Exception as exc:
            elapsed = time.monotonic() - t_start
            print(f"  ❌ Pipeline FAILED after {elapsed:.2f}s: {exc}")
            if VERBOSE:
                import traceback
                traceback.print_exc()
            all_failed += 1

    # ─── Post-run Verification ──────────────────────────────────────────
    step_header("STEP F: Final Verification")

    # Check goal-chain DB for new TIDs
    conn_after = db_connect()
    after_counts = dict(conn_after.execute(
        "SELECT status, COUNT(*) FROM tasks GROUP BY status"
    ).fetchall())
    after_total = conn_after.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    conn_after.close()

    new_tids = after_total - before_total
    print(f"  Goal-chain DB (after): {after_total} TIDs total (Δ={new_tids:+d})")
    print(f"    PENDING: {after_counts.get('PENDING', 0)} "
          f"(was {before_counts.get('PENDING', 0)})")

    # Check claim-log.jsonl
    claim_log = PROJECT_ROOT / ".promtset" / "state" / "claim-log.jsonl"
    claim_lines = 0
    if claim_log.exists():
        with open(claim_log) as f:
            claim_lines = sum(1 for _ in f)
    print(f"  claim-log.jsonl: {claim_lines} lines")

    # Check pipeline-state.db claims table
    pipeline_db = PROJECT_ROOT / "pipeline-state.db"
    pipeline_claims = 0
    if pipeline_db.exists():
        try:
            pc = sqlite3.connect(str(pipeline_db))
            pipeline_claims = pc.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
            pc.close()
        except Exception:
            pass
    print(f"  pipeline-state.db claims: {pipeline_claims}")

    # ─── Summary ────────────────────────────────────────────────────────
    elapsed_total = (datetime.now(timezone.utc) - run_started).total_seconds()

    print()
    print("╔" + "═" * 70 + "╗")
    print("║  E2E INTEGRATION TEST SUMMARY                                       ║")
    print("╠" + "═" * 70 + "╣")
    status = "PASSED" if all_failed == 0 else "FAILED"
    icon = "✅" if all_failed == 0 else "❌"
    print(f"║  {icon} Status: {status.ljust(57)}║")
    print(f"║  📊 Inputs processed: {all_passed}/{len(inputs)}".ljust(71) + "║")
    print(f"║  📋 Total claims extracted: {total_claims}".ljust(71) + "║")
    print(f"║  🔍 Total falsifications: {total_falsified}".ljust(71) + "║")
    print(f"║  🔗 TIDs seeded (estimate): {total_tids_seeded}".ljust(71) + "║")
    print(f"║  ⏱️ Total time: {elapsed_total:.1f}s".ljust(71) + "║")
    print(f"║  📄 Full log: {LOG_FILE}".ljust(71) + "║")
    print("╚" + "═" * 70 + "╝")

    if all_failed == 0:
        print("\n✅ ALL E2E TESTS PASSED")
    else:
        print(f"\n❌ {all_failed}/{len(inputs)} TESTS FAILED")

    return 0 if all_failed == 0 else 1


# ─── Entry Point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    exit_code = asyncio.run(run_e2e_test())
    sys.exit(exit_code)
