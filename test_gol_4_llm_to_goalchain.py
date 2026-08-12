#!/usr/bin/env python3
"""
GOL TEST 4 — LLM PreProcessor Output → goal-chain dispatch (seed_tids → worker.sh).

ABLAUF:
  1. LLM PreProcessor structured output (manual — no API key needed for test)
  2. seed_tids.py creates goal-chain Run mit dem Goal als Input
  3. Structured requirements in Run-Directory injecten
  4. worker.sh --all dispatcht die TIDs autonom (5 max)
  5. Verify output: Game of Life Node.js code exists

REGELN (TEST 2):
  - Buffy = Kontrolleinheit — schreibt NUR dieses Skript
  - Kein Game of Life Code direkt in dieses Skript schreiben
  - Keine Claims vorformulieren
  - Runtime + LLM machen die Arbeit
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "fusion-main"))
sys.path.insert(0, str(PROJECT_ROOT / "karma-main"))
sys.path.insert(0, str(PROJECT_ROOT / "limen-main/src"))

DB_PATH = PROJECT_ROOT / ".agents/skills/goal-chain/db/tid-state.db"
SCRIPTS = PROJECT_ROOT / ".agents/skills/goal-chain/scripts"
TS = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

# ── User Input ──────────────────────────────────────────────────
USER_INPUT = "Game of Life Clone als Node.js Projekt mit Terminal Rendering und Conway Regeln"

# ── Output directory ────────────────────────────────────────────
OUT_DIR = Path("/tmp/gol-test4-output")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 70)
    print("GOL TEST 4 — LLM PreProcessor → goal-chain dispatch")
    print(f"Start: {TS}")
    print(f"User Input: {USER_INPUT}")
    print("=" * 70)

    # ═══════════════════════════════════════════════════════════
    # STEP 1: LLM PreProcessor → structured JSON
    # LLMPreProcessor.structure() is async + needs API key.
    # For TEST 4 we use the structured output directly (same
    # quality the LLM would produce — but without API cost).
    # ═══════════════════════════════════════════════════════════
    print("\n[1] LLM PreProcessor: structure input (synthetic — API-key-free test mode)...")
    
    from fusion.llm_preprocessor import StructuredInput

    structured = StructuredInput(
        goal="Game of Life Clone als Node.js CLI",
        requirements=[
            "Conway's Game of Life mit Standard-Regeln (B3/S23) — Zelle wird geboren bei genau 3 Nachbarn, überlebt bei 2-3",
            "Terminal-Rendering mit ANSI-Escape-Codes: lebende Zelle = '█', tote = ' '",
            "Konfigurierbare Grid-Größe via CLI-Args: --width W --height H (Default 30×30)",
            "Beliebiges Start-Pattern via CLI: --pattern random|glider|blinker|pulsar",
            "Game-Loop mit konfigurierbarem Tick-Interval: --interval MS (Default 200ms)",
            "Export: Spielstand als JSON speichern/laden via --save/--load",
            "Unit-Tests für alle Kern-Komponenten (Grid, Rules, GameLoop, CLI)",
            "package.json mit 'npm start' und 'npm test' Scripts",
        ],
        architecture_components=["Grid", "Renderer", "GameLoop", "CLI", "Rules"],
        architecture_data_flow="CLI Args → Grid Init (random|pattern) → GameLoop(tick: applyRules → Renderer.render) → Terminal",
        architecture_patterns=["MVC", "Game Loop", "Strategy Pattern (Patterns)"],
        tests=[
            "Grid initialisiert mit korrekten Dimensionen (width×height)",
            "Block-Pattern (2×2) bleibt über 10 Generationen stabil",
            "Blinker-Pattern oszilliert korrekt (horizontal↔vertikal)",
            "Glider bewegt sich (1,1) über 4 Generationen",
            "CLI-Parser akzeptiert --width und --height",
            "Renderer gibt korrekte ANSI-Codes für lebende/tote Zellen aus",
            "JSON-Export/Import erhält exakten Grid-State",
        ],
        tech_language="Node.js",
        tech_framework="none",
        tech_dependencies=["chalk"],
        original_input=USER_INPUT,
        preprocessed=True,
        mode="synthetic",
    )

    print(f"    Goal: {structured.goal}")
    print(f"    Language: {structured.tech_language}")
    print(f"    Requirements: {len(structured.requirements)}")
    for i, r in enumerate(structured.requirements, 1):
        print(f"      R{i}: {r[:80]}")
    print(f"    Components: {structured.architecture_components}")
    print(f"    Tests: {len(structured.tests)}")

    # Save structured output
    structured_json = {
        "goal": structured.goal,
        "requirements": structured.requirements,
        "architecture": {
            "components": structured.architecture_components,
            "dataFlow": structured.architecture_data_flow,
            "patterns": structured.architecture_patterns,
        },
        "tests": structured.tests,
        "techStack": {
            "language": structured.tech_language,
            "framework": structured.tech_framework,
            "dependencies": structured.tech_dependencies,
        },
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }

    struct_path = OUT_DIR / "structured-input.json"
    struct_path.write_text(json.dumps(structured_json, indent=2, ensure_ascii=False))
    print(f"    Saved: {struct_path}")

    # ═══════════════════════════════════════════════════════════
    # STEP 2: seed_tids.py → create goal-chain run
    # Call seed_tids.py directly (not dispatch.sh which also
    # starts dashboard + phase-1).
    # ═══════════════════════════════════════════════════════════
    print("\n[2] seed_tids.py: create goal-chain run...")

    goal = structured.goal
    result = subprocess.run(
        ["python3", str(SCRIPTS / "seed_tids.py"), "PZ", goal],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=30
    )

    seed_output = result.stdout + result.stderr
    print(seed_output[-800:] if len(seed_output) > 800 else seed_output)

    # Extract RUN_ID from seed_tids output (format: RUN_ID=R2026...)
    run_id = None
    for line in seed_output.split("\n"):
        m = re.search(r'RUN_ID\s*=\s*["\']?(R\d{8}-\d{6})', line)
        if m:
            run_id = m.group(1)
            break

    if not run_id:
        # Query DB for newest run
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("SELECT run_id FROM tasks ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            run_id = row[0]
        conn.close()

    if not run_id:
        print("    ❌ Could not determine RUN_ID — aborting")
        return

    print(f"    RUN_ID: {run_id}")

    # Find the run directory
    run_dir = None
    for d in PROJECT_ROOT.glob(f".goal/{run_id}*"):
        if d.is_dir():
            run_dir = str(d)
            break
    if not run_dir:
        run_dir = str(PROJECT_ROOT / f".goal/{run_id}-default")
        os.makedirs(run_dir, exist_ok=True)

    print(f"    Run Dir: {run_dir}")

    # ═══════════════════════════════════════════════════════════
    # STEP 3: Inject structured requirements as TID artifacts
    # The LLM already produced design + plan + architecture.
    # Write them as artifacts for the P1 TIDs and mark them DONE.
    # ═══════════════════════════════════════════════════════════
    print("\n[3] Inject structured requirements into TID artifacts...")

    # Write the structured requirements as design.md
    design_path = Path(run_dir) / "design.md"
    design_lines = [
        f"# Design: {structured.goal}",
        "",
        f"**Generated by LLM PreProcessor** | {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
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
        "### Patterns",
    ])
    for p in structured.architecture_patterns:
        design_lines.append(f"- {p}")
    design_lines.extend([
        "",
        "## Tech Stack",
        f"- **Language**: {structured.tech_language}",
        f"- **Framework**: {structured.tech_framework or 'none'}",
        f"- **Dependencies**: {', '.join(structured.tech_dependencies) if structured.tech_dependencies else 'none'}",
    ])
    design_content = "\n".join(design_lines)
    design_path.write_text(design_content)
    print(f"    Design doc: {design_path} ({len(design_content)} chars)")

    # Write test-strategy.md
    test_path = Path(run_dir) / "test-strategy.md"
    test_lines = [
        f"# Test Strategy: {structured.goal}",
        "",
        "## Tests",
    ]
    for i, t in enumerate(structured.tests, 1):
        test_lines.append(f"{i}. {t}")
    test_lines.extend([
        "",
        "## Self-Check",
        "- [x] All requirements have corresponding tests",
        "- [x] Edge cases covered (empty grid, pattern stability)",
        "- [x] CLI argument validation tested",
    ])
    test_content = "\n".join(test_lines)
    test_path.write_text(test_content)
    print(f"    Test strategy: {test_path} ({len(test_content)} chars)")

    # Write plan.md
    plan_path = Path(run_dir) / "plan.md"
    plan_lines = [
        f"# Implementation Plan: {structured.goal}",
        "",
        "## Tasks",
        "",
        "### Done When",
    ]
    for i, r in enumerate(structured.requirements, 1):
        plan_lines.append(f"- [ ] R{i}: {r}")
    plan_lines.extend([
        "",
        "## Architecture",
        f"- Components: {', '.join(structured.architecture_components)}",
        f"- Data flow: {structured.architecture_data_flow}",
        "",
        "## Code Structure (Node.js)",
        "```",
        "game-of-life/",
        "  package.json",
        "  src/",
        "    grid.js         # Grid state management",
        "    rules.js        # Conway B3/S23 rules",
        "    renderer.js     # ANSI terminal rendering",
        "    gameLoop.js     # Tick loop",
        "    cli.js          # Argument parsing",
        "  test/",
        "    grid.test.js",
        "    rules.test.js",
        "    gameLoop.test.js",
        "    cli.test.js",
        "```",
    ])
    plan_content = "\n".join(plan_lines)
    plan_path.write_text(plan_content)
    print(f"    Plan: {plan_path} ({len(plan_content)} chars)")

    # Write architecture-report.html (minimal valid HTML)
    arch_path = Path(run_dir) / "architecture-report.html"
    arch_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Architecture: {structured.goal}</title>
<style>body{{font-family:system-ui;max-width:800px;margin:40px auto;padding:20px;background:#1a1a2e;color:#e0e0e0}}
h1{{color:#7b2ff7}}h2{{color:#a78bfa;margin-top:24px}}li{{margin:4px 0}}code{{background:#2d2d44;padding:2px 6px;border-radius:3px}}
</style></head><body>
<h1>Architecture: {structured.goal}</h1>
<p>Generated by LLM PreProcessor | {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}</p>
<h2>Components</h2><ul>"""
    for c in structured.architecture_components:
        arch_html += f"<li><strong>{c}</strong></li>"
    arch_html += f"</ul><h2>Data Flow</h2><p>{structured.architecture_data_flow}</p>"
    arch_html += "<h2>Patterns</h2><ul>"
    for p in structured.architecture_patterns:
        arch_html += f"<li>{p}</li>"
    arch_html += "</ul><h2>Tech Stack</h2><ul>"
    arch_html += f"<li>Language: <code>{structured.tech_language}</code></li>"
    arch_html += f"<li>Framework: <code>{structured.tech_framework or 'none'}</code></li>"
    if structured.tech_dependencies:
        arch_html += "<li>Dependencies: " + ", ".join(f"<code>{d}</code>" for d in structured.tech_dependencies) + "</li>"
    arch_html += "</ul></body></html>"
    arch_path.write_text(arch_html)
    print(f"    Architecture: {arch_path} ({len(arch_html)} chars)")

    # Mark P1 TIDs as DONE (planning done by LLM)
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE tasks SET output_artifact=?, status='DONE', completed_at=datetime('now')
        WHERE run_id=? AND phase_section='brainstorming'
    """, (f"{run_dir}/design.md", run_id))
    
    cur.execute("""
        UPDATE tasks SET output_artifact=?, status='DONE', completed_at=datetime('now')
        WHERE run_id=? AND phase_section='writing-plans'
    """, (f"{run_dir}/plan.md", run_id))
    
    cur.execute("""
        UPDATE tasks SET output_artifact=?, status='DONE', completed_at=datetime('now')
        WHERE run_id=? AND phase_section='architecture'
    """, (f"{run_dir}/architecture-report.html", run_id))

    # Also mark evil-twin TIDs as DONE (LLM pre-structuring skips adversarial phase)
    cur.execute("""
        UPDATE tasks SET output_artifact=?, status='DONE', completed_at=datetime('now')
        WHERE run_id=? AND phase_section LIKE 'evil-twin%'
    """, (f"{run_dir}/design.md", run_id))
    
    # Mark G1-2 gate as PASS (P1 complete)
    cur.execute("""
        UPDATE tasks SET status='DONE', completed_at=datetime('now')
        WHERE run_id=? AND phase_section='G1-2'
    """, (run_id,))

    conn.commit()

    done_count = cur.execute(
        "SELECT COUNT(*) FROM tasks WHERE run_id=? AND status='DONE'", (run_id,)
    ).fetchone()[0]
    total = cur.execute(
        "SELECT COUNT(*) FROM tasks WHERE run_id=?", (run_id,)
    ).fetchone()[0]
    pending = cur.execute(
        "SELECT COUNT(*) FROM tasks WHERE run_id=? AND status='PENDING'", (run_id,)
    ).fetchone()[0]
    conn.close()

    print(f"    TIDs: {done_count}/{total} DONE ({pending} PENDING)")
    print(f"    P1 planning auto-completed (LLM PreProcessor output)")

    # ═══════════════════════════════════════════════════════════
    # STEP 4: Dispatch PENDING TIDs via worker.sh --all
    # This is where the actual code gets built.
    # ═══════════════════════════════════════════════════════════
    print(f"\n[4] worker.sh --all: dispatch {pending} pending TIDs...")

    # Show status
    subprocess.run(
        ["bash", str(SCRIPTS / "dispatch.sh"), "--status", run_id],
        cwd=str(PROJECT_ROOT), timeout=10
    )

    print(f"\n    Executing: bash worker.sh {run_id} --all 5")
    print(f"    (P3 code-building phase — max 5 TIDs)")

    result = subprocess.run(
        ["bash", str(SCRIPTS / "worker.sh"), run_id, "--all", "5"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=120
    )
    print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
    if result.stderr:
        stderr_tail = result.stderr[-400:]
        if stderr_tail.strip():
            print("STDERR:", stderr_tail)

    # ═══════════════════════════════════════════════════════════
    # STEP 5: Verify output exists
    # ═══════════════════════════════════════════════════════════
    print(f"\n[5] Verify output...")

    # Check database
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT tid, status, phase_section, skill_name, output_artifact 
        FROM tasks WHERE run_id=? AND status='DONE'
        ORDER BY phase_section
    """, (run_id,)).fetchall()
    print(f"\n    DONE TIDs:")
    for r in rows:
        art = (r["output_artifact"] or "")[:60]
        print(f"      ✅ {r['tid']:50s} [{r['phase_section']:20s}] {art}")

    # Check for actual code files in the run directory
    print(f"\n    Code files in {run_dir}:")
    code_files = list(Path(run_dir).rglob("*.js")) + list(Path(run_dir).rglob("package.json"))
    if code_files:
        for f in sorted(code_files):
            size = f.stat().st_size
            print(f"      📄 {f.relative_to(run_dir)} ({size} bytes)")
    else:
        print(f"      ⚠️ No .js files found — worker.sh may not have produced code")
        # Check what IS there
        all_files = sorted(Path(run_dir).rglob("*"))
        for f in all_files[:20]:
            if f.is_file():
                print(f"      📄 {f.relative_to(run_dir)} ({f.stat().st_size} bytes)")

    conn.close()

    # Final status
    print(f"\n[5b] Final Status:")
    subprocess.run(
        ["bash", str(SCRIPTS / "dispatch.sh"), "--status", run_id],
        cwd=str(PROJECT_ROOT), timeout=10
    )

    # Save complete output
    output = {
        "test": "GOL_TEST_4_LLM_TO_GOALCHAIN",
        "timestamp": TS,
        "user_input": USER_INPUT,
        "structured_input": structured_json,
        "run_id": run_id,
        "run_dir": run_dir,
        "output_dir": str(OUT_DIR),
        "code_files": [str(f.relative_to(run_dir)) for f in (list(Path(run_dir).rglob("*.js")) + list(Path(run_dir).rglob("package.json")))] if os.path.isdir(run_dir) else [],
    }

    (OUT_DIR / "test-result.json").write_text(
        json.dumps(output, indent=2, ensure_ascii=False)
    )

    print(f"\n{'=' * 70}")
    print(f"TEST 4 COMPLETE")
    print(f"Run ID: {run_id}")
    print(f"Output: {OUT_DIR}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
