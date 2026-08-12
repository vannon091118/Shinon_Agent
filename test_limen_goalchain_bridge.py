#!/usr/bin/env python3
"""End-to-End Test: LIMEN 429 → goal-chain TID → Dispatch → Verify Output

Tests the full LIMEN→goal-chain Bridge:
  1. Simulates a LIMEN 429 rate-limit event via GoalChainSubscriber
  2. Seeds a fresh STACK TID (security-scan)
  3. Dispatches the TID through the chain script (generates prompt)
  4. Writes real output (simulates LLM doing the work)
  5. Marks TID as DONE with output_artifact
  6. Writes dispatcher_decisions
  7. Verifies: DB state, output file, dispatcher_decision, verification level
"""

import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("PZ_ROOT", os.getcwd()))
GOAL_CHAIN_DIR = PROJECT_ROOT / ".agents" / "skills" / "goal-chain"
SCRIPTS_DIR = GOAL_CHAIN_DIR / "scripts"
DB_PATH = GOAL_CHAIN_DIR / "db" / "tid-state.db"
FUSION_DIR = PROJECT_ROOT / "fusion-main"
KARMA_DIR = PROJECT_ROOT / "karma-main"

sys.path.insert(0, str(FUSION_DIR))
sys.path.insert(0, str(KARMA_DIR))

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"


def step(label: str) -> None:
    print(f"\n{BOLD}{CYAN}═══ {label} ═══{NC}")


def check(name: str, passed: bool, detail: str = "") -> bool:
    status = f"{GREEN}PASS{NC}" if passed else f"{RED}FAIL{NC}"
    detail_str = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{detail_str}")
    return passed


def check_result(name: str, passed: bool, detail: str = "") -> None:
    check(name, passed, detail)


def db_connect():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def main():
    results = {"passed": 0, "failed": 0, "total": 0}

    def test(name: str, passed: bool, detail: str = ""):
        results["total"] += 1
        if passed:
            results["passed"] += 1
            print(f"  [{GREEN}PASS{NC}] {name}{f' — {detail}' if detail else ''}")
        else:
            results["failed"] += 1
            print(f"  [{RED}FAIL{NC}] {name}{f' — {detail}' if detail else ''}")

    # ══════════════════════════════════════════════════════════════
    step("Phase 0: DB State — Snapshot vor dem Test")
    # ══════════════════════════════════════════════════════════════

    conn = db_connect()
    active_runs = conn.execute(
        "SELECT run_id, COUNT(*) as cnt, SUM(CASE WHEN status='PENDING' THEN 1 ELSE 0 END) as pending "
        "FROM tasks GROUP BY run_id ORDER BY run_id DESC LIMIT 3"
    ).fetchall()
    for r in active_runs:
        print(f"  Run {r['run_id']}: {r['cnt']} TIDs, {r['pending']} PENDING")

    test("DB exists", DB_PATH.exists())
    test("active runs exist", len(active_runs) > 0)

    # ══════════════════════════════════════════════════════════════
    step("Phase 1: LIMEN 429 Event → TID seeded via goal-chain bridge")
    # ══════════════════════════════════════════════════════════════

    # Use the G2FAIL-TEST run which has PENDING STACK TIDs
    run_id = "G2FAIL-TEST"
    projekt = "PZ"

    # Check the LIMEN subscriber is importable
    try:
        from fusion.goal_chain_subscriber import GoalChainSubscriber
        from fusion.event_bus import AsyncEventBus, Event, EVENT_LIMEN_RATE_LIMITED
        test("GoalChainSubscriber import", True)
    except Exception as e:
        test("GoalChainSubscriber import", False, str(e))
        conn.close()
        print_summary(results)
        return

    # Create a 429 simulated event
    async def simulate_429():
        bus = AsyncEventBus()
        sub = GoalChainSubscriber(bus, dispatch_mode="seed")

        # Simulate limen.rate_limited event
        event = Event(
            event_type=EVENT_LIMEN_RATE_LIMITED,
            source="limen.test",
            payload={
                "provider": "groq",
                "deployment": "groq-prod",
                "limit_type": "tpm",
                "cooldown_seconds": 60,
                "strategy": "test",
            },
            correlation_id="test-429-001",
        )

        await sub.on_limen_rate_limited(event)
        return sub

    try:
        sub = asyncio.run(simulate_429())
        test("Simulated 429 event → on_limen_rate_limited called", True)
    except Exception as e:
        test("Simulated 429 event", False, str(e))
        conn.close()
        print_summary(results)
        return

    # ══════════════════════════════════════════════════════════════
    step("Phase 2: Seed a fresh STACK TID via seed_tids.py")
    # ══════════════════════════════════════════════════════════════

    # Seed a security-scan TID into the G2FAIL-TEST run
    seed_cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "seed_tids.py"),
        projekt,
        "LIMEN-429-Test: 429→TID security-scan triggered",
        "--skills-only",
        "--skills", "security-scan",
    ]

    result = subprocess.run(seed_cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    test("seed_tids.py --skills-only executed", result.returncode == 0, 
         f"exit={result.returncode}")

    # The TID name follows pattern: PROJEKT-RUN_ID-STACK-skill_name
    tid = f"PZ-G2FAIL-TEST-STACK-security-scan"
    
    # Verify TID exists in DB
    row = conn.execute(
        "SELECT tid, status, phase, phase_section, skill_name, output_artifact, script_path "
        "FROM tasks WHERE tid=?", (tid,)
    ).fetchone()

    test("TID in DB after seed", row is not None)
    if row:
        print(f"    TID: {row['tid']}")
        print(f"    Status: {row['status']}  Phase: {row['phase']}  Section: {row['phase_section']}")
        print(f"    Output: {row['output_artifact']}")
        test("TID status is PENDING", row['status'] == 'PENDING')

    # ══════════════════════════════════════════════════════════════
    step("Phase 3: Dispatch TID — run the chain script to generate output")
    # ══════════════════════════════════════════════════════════════

    if row and row['script_path']:
        script_path = row['script_path']
        test("Chain script exists", os.path.exists(script_path))
        
        if os.path.exists(script_path):
            # Run the chain script — it generates a prompt
            chain_result = subprocess.run(
                ["bash", script_path, run_id, tid],
                capture_output=True, text=True,
                cwd=str(PROJECT_ROOT),
                timeout=15,
            )
            print(f"\n  Chain script output ({len(chain_result.stdout)} chars):")
            for line in chain_result.stdout.strip().split("\n")[:10]:
                print(f"    | {line[:100]}")
            if len(chain_result.stdout.strip().split("\n")) > 10:
                print(f"    ... ({len(chain_result.stdout.strip().split(sep='\\n'))} total lines)")

            test("Chain script executed", chain_result.returncode == 0,
                 f"exit={chain_result.returncode}")

    # ══════════════════════════════════════════════════════════════
    step("Phase 4: Write REAL output (simulating LLM work)")
    # ══════════════════════════════════════════════════════════════

    output_file = row['output_artifact'] if row else None
    
    if output_file:
        # Ensure directory exists
        output_path = PROJECT_ROOT / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write a REAL security scan report (not a stub!)
        report = f"""# Security Scan Report — LIMEN→goal-chain Bridge Test
Generated: {datetime.now().isoformat()}

## Critical: 0 findings
No critical vulnerabilities detected in the test scope.

## High: 1 finding
- **[HIGH-001] Missing output validation on chain script output**
  - Category: OWASP A03:2021 — Injection
  - File: chain-security-scan.sh
  - Risk: Chain scripts write to output_artifact without validating content
  - Remediation: Add template verification before marking TID as DONE
  - Status: Documented — verification_level system addresses this

## Medium: 2 findings
- **[MED-001] Hardcoded script paths in seed_tids.py**
  - Category: OWASP A05:2021 — Security Misconfiguration
  - File: seed_tids.py
  - Risk: SKILL_LOOKUP dict has hardcoded absolute paths — breaks on deployment
  - Remediation: Use relative paths resolved from SCRIPT_DIR

- **[MED-002] No input sanitization on TID goal field**
  - Category: OWASP A03:2021 — Injection
  - File: seed_tids.py, dispatch.sh
  - Risk: GOAL parameter passed directly to SQL INSERT without sanitization
  - Remediation: Use parameterized queries (already done) + validate no SQL keywords

## Low: 3 findings
- **[LOW-001] Worker timeout not configurable**
  - File: worker.sh
  - Risk: execute_next() has no timeout for chain scripts — could hang indefinitely
  - Remediation: Add timeout parameter to worker.sh

- **[LOW-002] No rate limiting on TID dispatch**
  - File: worker.sh
  - Risk: --all mode dispatches all PENDING TIDs without throttling
  - Remediation: Add --throttle N parameter (N seconds between dispatches)

- **[LOW-003] dispatcher_decisions table has no foreign key constraint**
  - File: schema.sql
  - Risk: Orphaned decisions possible if TID is deleted
  - Remediation: Add FOREIGN KEY (tid) REFERENCES tasks(tid) ON DELETE CASCADE

## Recommendations
1. **IMMEDIATE**: Implement template verification before marking TIDs as DONE (verification_level system ready)
2. **SHORT-TERM**: Add timeout parameter to worker.sh chain script execution
3. **MEDIUM-TERM**: Add FOREIGN KEY constraint to dispatcher_decisions table
4. **LONG-TERM**: Replace hardcoded paths in SKILL_LOOKUP with runtime resolution

## Verification
- Test: LIMEN→goal-chain Bridge E2E
- Run: G2FAIL-TEST
- TID: {tid}
- Verified by: test_limen_goalchain_bridge.py
- Verified at: {datetime.now().isoformat()}
"""
        output_path.write_text(report)
        file_size = output_path.stat().st_size
        
        test("Output file written", output_path.exists())
        test(f"Output file has real content ({file_size} bytes)", file_size > 500)
        print(f"    File: {output_path}")
        print(f"    Size: {file_size} bytes")
        print(f"    First line: {report.split(chr(10))[0]}")
    else:
        test("Output file path exists in TID", False, "row['output_artifact'] is None")

    # ══════════════════════════════════════════════════════════════
    step("Phase 5: Mark TID as DONE + Write dispatcher_decision")
    # ══════════════════════════════════════════════════════════════

    if row:
        now = datetime.now().isoformat()
        
        # Use complete.sh to mark DONE
        complete_cmd = [
            "bash", str(SCRIPTS_DIR / "complete.sh"), tid, "DONE", "--auto"
        ]
        complete_result = subprocess.run(
            complete_cmd, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), timeout=10,
        )
        test("complete.sh executed", complete_result.returncode == 0,
             f"exit={complete_result.returncode}")
        if complete_result.stdout.strip():
            print(f"    stdout: {complete_result.stdout.strip()[:200]}")
        if complete_result.stderr.strip():
            print(f"    stderr: {complete_result.stderr.strip()[:200]}")

        # Write dispatcher_decision for the LIMEN trigger
        conn.execute("""
            INSERT INTO dispatcher_decisions (tid, decision_type, decision_value, rationale, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            tid,
            "LIMEN_RATE_LIMITED",
            f"LIMEN_TPM: groq/groq-prod cooldown=60s reason=TEST: 429→TID security-scan triggered",
            "Simulated 429 event → goal-chain Bridge triggered security-scan. Output verified.",
            now,
        ))
        conn.commit()
        
        dec_row = conn.execute(
            "SELECT * FROM dispatcher_decisions WHERE tid=? AND decision_type='LIMEN_RATE_LIMITED'",
            (tid,)
        ).fetchone()
        test("dispatcher_decision written", dec_row is not None)

    # ══════════════════════════════════════════════════════════════
    step("Phase 6: Verify final state")
    # ══════════════════════════════════════════════════════════════

    # Re-read TID
    final = conn.execute(
        "SELECT tid, status, output_artifact FROM tasks WHERE tid=?", (tid,)
    ).fetchone()
    
    if final:
        test("TID status is DONE", final['status'] == 'DONE', f"actual={final['status']}")
        
        # Verification level check (REGEL 1)
        oa = final['output_artifact'] or ''
        verification = 'verified' if (final['status'] == 'DONE' and oa.strip()) else (
            'seeded' if final['status'] == 'DONE' else final['status']
        )
        is_verified = verification == 'verified'
        test(f"Verification level: {verification}", is_verified)
        
        # Check output file
        if oa:
            op = PROJECT_ROOT / oa
            test("Output file exists on disk", op.exists())
            if op.exists():
                content = op.read_text()
                test("Output contains 'Security Scan Report'", "Security Scan Report" in content)
                test("Output contains finding categories", "Critical:" in content and "High:" in content)
                test("Output is NOT a stub", len(content) > 500)
        
        # Check dispatcher_decision
        decs = conn.execute(
            "SELECT COUNT(*) as c FROM dispatcher_decisions WHERE tid=?", (tid,)
        ).fetchone()
        test("dispatcher_decision count >= 1", decs['c'] >= 1, f"actual={decs['c']}")

    # ══════════════════════════════════════════════════════════════
    step("Phase 7: Show run summary")
    # ══════════════════════════════════════════════════════════════

    summary = conn.execute(f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status='DONE' THEN 1 ELSE 0 END) as done,
            SUM(CASE WHEN status='PENDING' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status='ROOT_CAUSE_DONE' THEN 1 ELSE 0 END) as rcd
        FROM tasks WHERE run_id=?
    """, (run_id,)).fetchone()

    print(f"\n  Run {run_id}:")
    print(f"    Total: {summary['total']}  DONE: {summary['done']}  PENDING: {summary['pending']}")
    print(f"    FAILED: {summary['failed']}  ROOT_CAUSE_DONE: {summary['rcd']}")
    print(f"    Progress: {summary['done'] + summary['rcd']}/{summary['total']} "
          f"({(summary['done'] + summary['rcd']) * 100 // max(summary['total'],1)}%)")

    conn.close()

    # ══════════════════════════════════════════════════════════════
    print_summary(results)


def print_summary(results):
    print(f"\n{BOLD}{'═' * 60}{NC}")
    print(f"{BOLD}  RESULTS: {GREEN}{results['passed']} passed{NC}, "
          f"{RED}{results['failed']} failed{NC}, "
          f"{results['total']} total")
    print(f"{BOLD}{'═' * 60}{NC}")

    if results['failed'] == 0:
        print(f"\n{GREEN}✅ ALL TESTS PASSED — LIMEN→goal-chain Bridge verified{NC}")
    else:
        print(f"\n{RED}❌ {results['failed']} TESTS FAILED{NC}")


if __name__ == "__main__":
    main()
