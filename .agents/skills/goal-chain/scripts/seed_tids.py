#!/usr/bin/env python3
"""Seed TIDs v3 — with templates, alternative paths, user checkpoints, --skills-only mode.

Full mode:
  python3 seed_tids.py PZ "Build OAuth2 login"
  → Seeds all 63 TIDs (P1-P4 phases + STACK tools) into a new run.

Skills-only mode (used by GoalChainSubscriber for KARMA-triggered TIDs):
  python3 seed_tids.py PZ "KARMA refuted auth claim" --skills-only --skills security-scan,validation
  → Seeds only the specified STACK TIDs within the ACTIVE run (no new run created).
"""
import sqlite3, sys, os, re
from datetime import datetime

def _resolve_db_path():
    """Zentral-first: $SHINON_HOME/data/goal-chain/tid-state.db falls vorhanden,
    sonst Legacy-Pfad. Ein Ort fuer TID-State, kein Fragmentieren."""
    env = os.environ.get("SHINON_GOALCHAIN_DB")
    if env:
        return env
    shinon_home = os.environ.get("SHINON_HOME") or os.path.expanduser("~/.shinon")
    central = os.path.join(shinon_home, "data", "goal-chain", "tid-state.db")
    if os.path.exists(central):
        return central
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'db', 'tid-state.db')

DB_PATH = _resolve_db_path()

if len(sys.argv) < 3:
    print("Usage: seed_tids.py PROJEKT GOAL [--skills-only --skills sk1,sk2,...]")
    sys.exit(1)

PROJEKT = sys.argv[1]
GOAL = sys.argv[2]

# ─── Parse flags ──────────────────────────────────────────────────────
SKILLS_ONLY = False
TARGET_SKILLS = []

args = sys.argv[3:]
i = 0
while i < len(args):
    if args[i] == "--skills-only":
        SKILLS_ONLY = True
        i += 1
    elif args[i] == "--skills" and i + 1 < len(args):
        TARGET_SKILLS = [s.strip() for s in args[i + 1].split(",") if s.strip()]
        i += 2
    else:
        i += 1

if SKILLS_ONLY and not TARGET_SKILLS:
    print("Error: --skills-only requires --skills", file=sys.stderr)
    sys.exit(1)

# ─── Skill Lookup Table (section → (skill_name, chain_script, output_artifact, template_id)) ──
# Used by skills-only mode. Must match the STACK entries in the `tids` list below.
S = '.agents/skills/goal-chain/scripts'
SKILL_LOOKUP = {
    # Row 21-36
    "autorun":                ("agents/autorun",                             f"{S}/chain-autorun.sh",                  "autorun-decision.md",            "decision-log-v1"),
    "guide-architekt":        ("agents/guide-architekt",                     f"{S}/chain-guide-architekt.sh",           "architekt-guide.md",             "decision-log-v1"),
    "executing-plans":        ("web-dev/superpowers/executing-plans",        f"{S}/chain-executing-plans.sh",           "execution-log.md",               "execution-log-v1"),
    "multi-agent-orchestr":   ("agents/multi-agent-orchestrator",            f"{S}/chain-multi-agent-orchestrator.sh",  "orchestration-plan.md",          "orchestration-plan-v1"),
    "security-scan":          ("security/codex-security/security-scan",      f"{S}/chain-security-scan.sh",             "security-report.md",             "security-report-v1"),
    "track-findings":         ("security/codex-security/track-findings",     f"{S}/chain-track-findings.sh",            "findings-tracker.md",            "findings-tracker-v1"),
    "web-design-guidelines":  ("design/web-design-guidelines",               f"{S}/chain-web-design-guidelines.sh",     "design-guidelines-check.md",     "guidelines-check-v1"),
    "validation":             ("security/codex-security/validation",         f"{S}/chain-validation.sh",               "validation-report.md",           "validation-report-v1"),
    "python-testing-patte":   ("development/python-testing-patterns",        f"{S}/chain-python-testing-patterns.sh",   "test-strategy.md",               "test-strategy-v1"),
    "playwright-expert":      ("testing/playwright-expert",                  f"{S}/chain-playwright-expert.sh",        "playwright-tests.md",            "playwright-tests-v1"),
    "community-deep-resea":   ("research/community-deep-research",           f"{S}/chain-community-deep-research.sh",  "deep-research.md",               "research-report-v1"),
    "frontend-design":        ("design/frontend-design",                     f"{S}/chain-frontend-design.sh",          "frontend-design.md",             "decision-log-v1"),
    "canvas-design":          ("design/canvas-design",                       f"{S}/chain-canvas-design.sh",            "canvas-design.md",               "decision-log-v1"),
    "media-generation":       ("media/media-generation",                     f"{S}/chain-media-generation.sh",         "media-assets.md",                "decision-log-v1"),
    "consolidate-memory":     ("claude-tools/consolidate-memory",            f"{S}/chain-consolidate-memory.sh",       "memory-consolidation.md",        "consolidation-v1"),
    "receiving-code-review":  ("development/receiving-code-review",          f"{S}/chain-receiving-code-review.sh",     "code-review-processing.md",      "review-processing-v1"),
    # Row 37-63
    "clerk-webhooks":         ("agents/clerk-webhooks",                       f"{S}/chain-clerk-webhooks.sh",            "clerk-webhooks.md",              "decision-log-v1"),
    "delivery-tracking":      ("agents/delivery-tracking",                   f"{S}/chain-delivery-tracking.sh",         "delivery-tracking.md",           "decision-log-v1"),
    "sub-agent-prompts":      ("agents/sub-agent-prompts",                   f"{S}/chain-sub-agent-prompts.sh",         "sub-agent-prompts.md",           "decision-log-v1"),
    "docx":                   ("claude-tools/docx",                          f"{S}/chain-docx.sh",                      "docx-output.md",                 "decision-log-v1"),
    "pdf":                    ("claude-tools/pdf",                           f"{S}/chain-pdf.sh",                       "pdf-output.md",                  "decision-log-v1"),
    "pptx":                   ("claude-tools/pptx",                          f"{S}/chain-pptx.sh",                      "pptx-output.md",                 "decision-log-v1"),
    "xlsx":                   ("claude-tools/xlsx",                          f"{S}/chain-xlsx.sh",                      "xlsx-output.md",                 "decision-log-v1"),
    "schedule":               ("claude-tools/schedule",                      f"{S}/chain-schedule.sh",                  "schedule.md",                    "decision-log-v1"),
    "morning":                ("claude-tools/morning",                       f"{S}/chain-morning.sh",                   "morning-plan.md",                "decision-log-v1"),
    "explain-usage":          ("claude-tools/explain-usage",                 f"{S}/chain-explain-usage.sh",             "explain-usage.md",               "decision-log-v1"),
    "setup-cowork":           ("claude-tools/setup-cowork",                  f"{S}/chain-setup-cowork.sh",              "setup-cowork.md",                "decision-log-v1"),
    "document-tools":         ("documents/document-tools",                   f"{S}/chain-document-tools.sh",            "document-tools.md",              "decision-log-v1"),
    "pdf-tools":              ("documents/pdf-tools",                        f"{S}/chain-pdf-tools.sh",                 "pdf-tools.md",                   "decision-log-v1"),
    "presentation-tools":     ("documents/presentation-tools",               f"{S}/chain-presentation-tools.sh",        "presentation-tools.md",          "decision-log-v1"),
    "spreadsheet-tools":      ("documents/spreadsheet-tools",                f"{S}/chain-spreadsheet-tools.sh",         "spreadsheet-tools.md",           "decision-log-v1"),
    "canvas":                 ("design/canvas",                              f"{S}/chain-canvas.sh",                    "canvas-rendering.md",            "decision-log-v1"),
    "performance":            ("design/performance",                         f"{S}/chain-performance.sh",               "perf-optimization.md",           "decision-log-v1"),
    "tailwind-design-system": ("design/tailwind-design-system",              f"{S}/chain-tailwind-design-system.sh",     "tailwind-system.md",             "decision-log-v1"),
    "python-perf":            ("development/python-performance-optimization",f"{S}/chain-python-performance-optimization.sh","python-perf.md",          "decision-log-v1"),
    "typescript-expert":      ("development/typescript-expert",              f"{S}/chain-typescript-expert.sh",         "typescript-quality.md",          "decision-log-v1"),
    "upgrade-react-native":   ("development/upgrade-react-native",           f"{S}/chain-upgrade-react-native.sh",      "rn-upgrade-plan.md",             "decision-log-v1"),
    "audio-transcription":    ("media/audio-transcription",                  f"{S}/chain-audio-transcription.sh",       "audio-transcript.md",            "decision-log-v1"),
    "desktop-automation":     ("media/desktop-automation",                   f"{S}/chain-desktop-automation.sh",        "desktop-automation.md",          "decision-log-v1"),
    "screenshot-tools":       ("media/screenshot-tools",                     f"{S}/chain-screenshot-tools.sh",          "screenshot-tools.md",            "decision-log-v1"),
    "lua-game-systems":       ("games/lua-game-systems",                     f"{S}/chain-lua-game-systems.sh",          "lua-game-systems.md",            "decision-log-v1"),
    "playcanvas-engine":      ("games/playcanvas-engine",                    f"{S}/chain-playcanvas-engine.sh",         "playcanvas-engine.md",           "decision-log-v1"),
    "evil-twin-protocol":     ("evil-twin-protocol",                          f"{S}/chain-evil-twin-protocol.sh",        "evil-twin-standalone.md",        "evil-twin-v1"),
}

TS = datetime.now().strftime('%Y%m%d-%H%M%S')
RUN_ID = f'R{TS}'

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ─── Skills-only mode: append to active run ───────────────────────────
if SKILLS_ONLY:
    active = cur.execute(
        "SELECT run_id FROM tasks WHERE status='PENDING' AND phase='STACK' ORDER BY updated_at DESC LIMIT 1"
    ).fetchone()
    
    if not active:
        active = cur.execute(
            "SELECT run_id FROM tasks ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
    
    if not active:
        print("Error: No active run found — cannot seed skills-only", file=sys.stderr)
        conn.close()
        sys.exit(1)
    
    RUN_ID = active[0]
    print(f"[seed_tids] skills-only mode: appending to active run {RUN_ID}")
    print(f"[seed_tids] target skills: {TARGET_SKILLS}")
    
    max_seq = cur.execute(
        "SELECT MAX(phase_seq) FROM tasks WHERE run_id=?", (RUN_ID,)
    ).fetchone()[0] or 63
    
    seeded_count = 0
    for skill_name in TARGET_SKILLS:
        if skill_name not in SKILL_LOOKUP:
            print(f"[seed_tids] WARNING: unknown skill '{skill_name}' — skipping")
            continue
        
        skill_path, script, output, template_id = SKILL_LOOKUP[skill_name]
        max_seq += 1
        tid = f"{PROJEKT}-{RUN_ID}-STACK-{skill_name}"
        
        cur.execute("""INSERT OR REPLACE INTO tasks
            (tid, projekt, run_id, task, goal, phase, phase_section, phase_seq,
             skill_name, script_path, input_artifacts, output_artifact, template_id, requires_approval)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tid, PROJEKT, RUN_ID, skill_name, GOAL, "STACK", skill_name, max_seq,
             skill_path, script, "", output, template_id, 0))
        
        seeded_count += 1
        print(f"[seed_tids]   ✅ {tid}")
    
    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM tasks WHERE run_id=?", (RUN_ID,)).fetchone()[0]
    print(f"[seed_tids] seeded {seeded_count} skill TIDs → run {RUN_ID} (total: {count} TIDs)")
    print(f"RUN_ID={RUN_ID}")
    print(f"TID_COUNT={seeded_count}")
    print(f"TEMPLATE_MARKERS=0")
    print(f"ALT_PATHS=0")
    conn.close()
    sys.exit(0)

# ─── Full mode: create new run ────────────────────────────────────────

slug = re.sub(r'[^a-z0-9]', '-', GOAL.lower())
slug = re.sub(r'--+', '-', slug).strip('-')[:40]

S = '.agents/skills/goal-chain/scripts'
RUN_DIR = f'.goal/{RUN_ID}-{slug}'
os.makedirs(f'{RUN_DIR}/docs', exist_ok=True)
os.makedirs(f'{RUN_DIR}/wiki', exist_ok=True)
os.makedirs(f'{RUN_DIR}/learnings', exist_ok=True)

# ─── All TIDs with (tid, phase, section, seq, skill, script, output, input, template_id, requires_approval) ───
tids = [
    # Phase 1: Planen
    (f"{PROJEKT}-{RUN_ID}-P1-brainstorming",     "P1","brainstorming",       1,"web-dev/superpowers/brainstorming",              f"{S}/phase-1-brainstorming.sh",    f"{RUN_DIR}/design.md",                    "",                                             "design-doc-v1",                     1),
    (f"{PROJEKT}-{RUN_ID}-P1-evil-twin-1",       "P1","evil-twin-1",         2,"evil-twin-protocol",                             f"{S}/phase-1-evil-twin.sh",         f"{RUN_DIR}/evil-twin-1.md",               f"{RUN_DIR}/design.md",                        "evil-twin-v1",                     0),
    (f"{PROJEKT}-{RUN_ID}-P1-writing-plans",      "P1","writing-plans",       3,"development/writing-plans",                      f"{S}/phase-1-writing-plans.sh",    f"{RUN_DIR}/plan.md",                      f"{RUN_DIR}/design.md",                        "implementation-plan-v1",           0),
    (f"{PROJEKT}-{RUN_ID}-P1-evil-twin-2",        "P1","evil-twin-2",         4,"evil-twin-protocol",                             f"{S}/phase-1-evil-twin.sh",         f"{RUN_DIR}/evil-twin-2.md",               f"{RUN_DIR}/plan.md",                         "evil-twin-v1",                     0),
    (f"{PROJEKT}-{RUN_ID}-P1-architecture",        "P1","architecture",        5,"development/improve-codebase-architecture",      f"{S}/phase-1-architecture.sh",     f"{RUN_DIR}/architecture-report.html",     f"{RUN_DIR}/plan.md",                         "architecture-report-v1",           0),
    (f"{PROJEKT}-{RUN_ID}-P1-evil-twin-3",        "P1","evil-twin-3",         6,"evil-twin-protocol",                             f"{S}/phase-1-evil-twin.sh",         f"{RUN_DIR}/evil-twin-3.md",               f"{RUN_DIR}/architecture-report.html",        "evil-twin-v1",                     0),
    # Gate 1→2
    (f"{PROJEKT}-{RUN_ID}-G1-2-verify",            "G1-2","verification",       7,"web-dev/superpowers/verification-before-completion",f"{S}/gate-1-2.sh",                f"{RUN_DIR}/gate-1-2-result.txt",          f"{RUN_DIR}/plan.md",                         "gate-result-v1",                  1),
    # Phase 2
    (f"{PROJEKT}-{RUN_ID}-P2-writing-plans-v2",    "P2","writing-plans-v2",   8,"development/writing-plans",                      f"{S}/phase-2-writing-plans-v2.sh",  f"{RUN_DIR}/plan_v2.md",                   f"{RUN_DIR}/plan.md",                         "implementation-plan-v1",           0),
    (f"{PROJEKT}-{RUN_ID}-P2-evil-twin-4",         "P2","evil-twin-4",        9,"evil-twin-protocol",                             f"{S}/phase-1-evil-twin.sh",         f"{RUN_DIR}/evil-twin-4.md",               f"{RUN_DIR}/plan_v2.md",                      "evil-twin-v1",                     0),
    (f"{PROJEKT}-{RUN_ID}-P2-debugging",            "P2","systematic-debugging",10,"development/systematic-debugging",               f"{S}/phase-2-debugging.sh",         f"{RUN_DIR}/debug_root_cause.md",          f"{RUN_DIR}/plan_v2.md",                      "root-cause-v1",                    0),
    (f"{PROJEKT}-{RUN_ID}-P2-evil-twin-5",         "P2","evil-twin-5",        11,"evil-twin-protocol",                            f"{S}/phase-1-evil-twin.sh",         f"{RUN_DIR}/evil-twin-5.md",               f"{RUN_DIR}/debug_root_cause.md",             "evil-twin-v1",                     0),
    # Gate 2→3
    (f"{PROJEKT}-{RUN_ID}-G2-3-verify",            "G2-3","verification",      12,"web-dev/superpowers/verification-before-completion",f"{S}/gate-2-3.sh",                f"{RUN_DIR}/gate-2-3-result.txt",          f"{RUN_DIR}/plan_v2.md",                      "gate-result-v1",                  1),
    # Phase 3
    (f"{PROJEKT}-{RUN_ID}-P3-implementer",          "P3","subagent-dev",      13,"web-dev/superpowers/subagent-driven-development",f"{S}/phase-3-implementer.sh",       f"{RUN_DIR}/phase3_implementation.log",   f"{RUN_DIR}/plan_v2.md",                      "implementation-log-v1",            0),
    (f"{PROJEKT}-{RUN_ID}-P3-evil-twin-6",          "P3","evil-twin-6",       14,"evil-twin-protocol",                             f"{S}/phase-3-evil-twin.sh",         f"{RUN_DIR}/evil-twin-6.md",               f"{RUN_DIR}/phase3_implementation.log",       "evil-twin-v1",                     0),
    (f"{PROJEKT}-{RUN_ID}-P3-reviewer",              "P3","reviewer",          15,"web-dev/superpowers/dispatching-parallel-agents",f"{S}/phase-3-reviewer.sh",          f"{RUN_DIR}/phase3_review.log",            f"{RUN_DIR}/phase3_implementation.log",       "review-log-v1",                   0),
    (f"{PROJEKT}-{RUN_ID}-P3-finishing",             "P3","finishing",         16,"web-dev/superpowers/finishing-a-development-branch",f"{S}/phase-3-finishing.sh",      f"{RUN_DIR}/phase3_finish.log",            f"{RUN_DIR}/phase3_review.log",               "finish-log-v1",                   1),
    # Phase 4
    (f"{PROJEKT}-{RUN_ID}-P4-docs",                  "P4","documentation-writer",17,"agents/documentation-writer",                   f"{S}/phase-4-docs.sh",              f"{RUN_DIR}/docs/documentation.md",        f"{RUN_DIR}/phase3_finish.log",               "diataxis-docs-v1",                0),
    (f"{PROJEKT}-{RUN_ID}-P4-wiki",                  "P4","wiki-system",       18,"research/wiki-system",                           f"{S}/phase-4-wiki.sh",              f"{RUN_DIR}/wiki/wiki_update.md",          f"{RUN_DIR}/phase3_finish.log",               "wiki-update-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-P4-learnings",             "P4","self-improvement",  19,"meta/self-improvement",                          f"{S}/phase-4-learnings.sh",         f"{RUN_DIR}/learnings/learnings.md",       f"{RUN_DIR}/phase3_finish.log",               "learnings-v1",                    0),
    (f"{PROJEKT}-{RUN_ID}-P4-evil-twin-7",           "P4","evil-twin-7",       20,"evil-twin-protocol",                             f"{S}/phase-1-evil-twin.sh",         f"{RUN_DIR}/evil-twin-7.md",               f"{RUN_DIR}/docs/documentation.md",           "evil-twin-v1",                     1),
    # STACK-Tools (seq 21-36)
    (f"{PROJEKT}-{RUN_ID}-STACK-autorun",            "STACK","autorun",            21,"agents/autorun",                                 f"{S}/chain-autorun.sh",             f"{RUN_DIR}/autorun-decision.md",          "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-guide-architekt",    "STACK","guide-architekt",    22,"agents/guide-architekt",                         f"{S}/chain-guide-architekt.sh",      f"{RUN_DIR}/architekt-guide.md",           "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-executing-plans",    "STACK","executing-plans",    23,"web-dev/superpowers/executing-plans",            f"{S}/chain-executing-plans.sh",      f"{RUN_DIR}/execution-log.md",             "",                                             "execution-log-v1",                 0),
    (f"{PROJEKT}-{RUN_ID}-STACK-multi-agent-orch",   "STACK","multi-agent-orch",   24,"agents/multi-agent-orchestrator",                f"{S}/chain-multi-agent-orchestrator.sh",f"{RUN_DIR}/orchestration-plan.md",      "",                                             "orchestration-plan-v1",            0),
    (f"{PROJEKT}-{RUN_ID}-STACK-security-scan",      "STACK","security-scan",      25,"security/codex-security/security-scan",          f"{S}/chain-security-scan.sh",        f"{RUN_DIR}/security-report.md",           "",                                             "security-report-v1",               0),
    (f"{PROJEKT}-{RUN_ID}-STACK-track-findings",     "STACK","track-findings",     26,"security/codex-security/track-findings",         f"{S}/chain-track-findings.sh",       f"{RUN_DIR}/findings-tracker.md",          "",                                             "findings-tracker-v1",              0),
    (f"{PROJEKT}-{RUN_ID}-STACK-web-design-guidelines","STACK","web-design-guidelines",27,"design/web-design-guidelines",                f"{S}/chain-web-design-guidelines.sh",f"{RUN_DIR}/design-guidelines-check.md",   "",                                             "guidelines-check-v1",              0),
    (f"{PROJEKT}-{RUN_ID}-STACK-validation",         "STACK","validation",         28,"security/codex-security/validation",              f"{S}/chain-validation.sh",          f"{RUN_DIR}/validation-report.md",         "",                                             "validation-report-v1",             0),
    (f"{PROJEKT}-{RUN_ID}-STACK-python-testing",     "STACK","python-testing",     29,"development/python-testing-patterns",             f"{S}/chain-python-testing-patterns.sh",f"{RUN_DIR}/test-strategy.md",           "",                                             "test-strategy-v1",                 0),
    (f"{PROJEKT}-{RUN_ID}-STACK-playwright-expert",  "STACK","playwright-expert",  30,"testing/playwright-expert",                       f"{S}/chain-playwright-expert.sh",   f"{RUN_DIR}/playwright-tests.md",          "",                                             "playwright-tests-v1",              0),
    (f"{PROJEKT}-{RUN_ID}-STACK-community-research", "STACK","community-research", 31,"research/community-deep-research",                f"{S}/chain-community-deep-research.sh",f"{RUN_DIR}/deep-research.md",          "",                                             "research-report-v1",               0),
    (f"{PROJEKT}-{RUN_ID}-STACK-frontend-design",    "STACK","frontend-design",    32,"design/frontend-design",                         f"{S}/chain-frontend-design.sh",     f"{RUN_DIR}/frontend-design.md",           "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-canvas-design",      "STACK","canvas-design",      33,"design/canvas-design",                           f"{S}/chain-canvas-design.sh",       f"{RUN_DIR}/canvas-design.md",             "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-media-generation",   "STACK","media-generation",   34,"media/media-generation",                         f"{S}/chain-media-generation.sh",    f"{RUN_DIR}/media-assets.md",              "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-consolidate-memory", "STACK","consolidate-memory", 35,"claude-tools/consolidate-memory",                f"{S}/chain-consolidate-memory.sh",  f"{RUN_DIR}/memory-consolidation.md",      "",                                             "consolidation-v1",                 0),    (f"{PROJEKT}-{RUN_ID}-STACK-receiving-code-review","STACK","receiving-code-review",36,"development/receiving-code-review",         f"{S}/chain-receiving-code-review.sh",f"{RUN_DIR}/code-review-processing.md",    "",                                             "review-processing-v1",             0),
    # STACK-Tools v2 (seq 37-63) — raw skills migrated
    (f"{PROJEKT}-{RUN_ID}-STACK-clerk-webhooks",     "STACK","clerk-webhooks",     37,"agents/clerk-webhooks",                        f"{S}/chain-clerk-webhooks.sh",       f"{RUN_DIR}/clerk-webhooks.md",            "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-delivery-tracking",  "STACK","delivery-tracking",  38,"agents/delivery-tracking",                     f"{S}/chain-delivery-tracking.sh",    f"{RUN_DIR}/delivery-tracking.md",         "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-sub-agent-prompts",  "STACK","sub-agent-prompts",  39,"agents/sub-agent-prompts",                     f"{S}/chain-sub-agent-prompts.sh",    f"{RUN_DIR}/sub-agent-prompts.md",         "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-docx",               "STACK","docx",               40,"claude-tools/docx",                            f"{S}/chain-docx.sh",                 f"{RUN_DIR}/docx-output.md",               "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-pdf",                "STACK","pdf",                41,"claude-tools/pdf",                             f"{S}/chain-pdf.sh",                  f"{RUN_DIR}/pdf-output.md",                "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-pptx",               "STACK","pptx",               42,"claude-tools/pptx",                            f"{S}/chain-pptx.sh",                 f"{RUN_DIR}/pptx-output.md",               "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-xlsx",               "STACK","xlsx",               43,"claude-tools/xlsx",                            f"{S}/chain-xlsx.sh",                 f"{RUN_DIR}/xlsx-output.md",               "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-schedule",           "STACK","schedule",           44,"claude-tools/schedule",                        f"{S}/chain-schedule.sh",             f"{RUN_DIR}/schedule.md",                  "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-morning",            "STACK","morning",            45,"claude-tools/morning",                         f"{S}/chain-morning.sh",              f"{RUN_DIR}/morning-plan.md",              "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-explain-usage",      "STACK","explain-usage",      46,"claude-tools/explain-usage",                   f"{S}/chain-explain-usage.sh",        f"{RUN_DIR}/explain-usage.md",             "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-setup-cowork",       "STACK","setup-cowork",       47,"claude-tools/setup-cowork",                    f"{S}/chain-setup-cowork.sh",         f"{RUN_DIR}/setup-cowork.md",              "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-document-tools",     "STACK","document-tools",     48,"documents/document-tools",                     f"{S}/chain-document-tools.sh",       f"{RUN_DIR}/document-tools.md",            "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-pdf-tools",          "STACK","pdf-tools",          49,"documents/pdf-tools",                          f"{S}/chain-pdf-tools.sh",            f"{RUN_DIR}/pdf-tools.md",                 "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-presentation-tools", "STACK","presentation-tools", 50,"documents/presentation-tools",                 f"{S}/chain-presentation-tools.sh",   f"{RUN_DIR}/presentation-tools.md",        "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-spreadsheet-tools",  "STACK","spreadsheet-tools",  51,"documents/spreadsheet-tools",                  f"{S}/chain-spreadsheet-tools.sh",    f"{RUN_DIR}/spreadsheet-tools.md",         "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-canvas",             "STACK","canvas",             52,"design/canvas",                                f"{S}/chain-canvas.sh",               f"{RUN_DIR}/canvas-rendering.md",          "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-performance",        "STACK","performance",        53,"design/performance",                           f"{S}/chain-performance.sh",          f"{RUN_DIR}/perf-optimization.md",         "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-tailwind-design-system","STACK","tailwind-design-system",54,"design/tailwind-design-system",          f"{S}/chain-tailwind-design-system.sh",f"{RUN_DIR}/tailwind-system.md",          "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-python-perf",        "STACK","python-perf",        55,"development/python-performance-optimization",   f"{S}/chain-python-performance-optimization.sh",f"{RUN_DIR}/python-perf.md",        "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-typescript-expert",   "STACK","typescript-expert",  56,"development/typescript-expert",                 f"{S}/chain-typescript-expert.sh",    f"{RUN_DIR}/typescript-quality.md",        "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-upgrade-react-native","STACK","upgrade-react-native",57,"development/upgrade-react-native",            f"{S}/chain-upgrade-react-native.sh", f"{RUN_DIR}/rn-upgrade-plan.md",           "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-audio-transcription","STACK","audio-transcription",58,"media/audio-transcription",                   f"{S}/chain-audio-transcription.sh",  f"{RUN_DIR}/audio-transcript.md",          "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-desktop-automation", "STACK","desktop-automation", 59,"media/desktop-automation",                     f"{S}/chain-desktop-automation.sh",   f"{RUN_DIR}/desktop-automation.md",        "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-screenshot-tools",   "STACK","screenshot-tools",   60,"media/screenshot-tools",                       f"{S}/chain-screenshot-tools.sh",     f"{RUN_DIR}/screenshot-tools.md",          "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-lua-game-systems",   "STACK","lua-game-systems",   61,"games/lua-game-systems",                       f"{S}/chain-lua-game-systems.sh",     f"{RUN_DIR}/lua-game-systems.md",          "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-playcanvas-engine",  "STACK","playcanvas-engine",  62,"games/playcanvas-engine",                      f"{S}/chain-playcanvas-engine.sh",    f"{RUN_DIR}/playcanvas-engine.md",         "",                                             "decision-log-v1",                  0),
    (f"{PROJEKT}-{RUN_ID}-STACK-evil-twin-protocol",  "STACK","evil-twin-protocol",63,"evil-twin-protocol",                          f"{S}/chain-evil-twin-protocol.sh",   f"{RUN_DIR}/evil-twin-standalone.md",      "",                                             "evil-twin-v1",                     0),
]    

# Insert
for tid, phase, section, seq, skill, script, output, inp, template_id, requires_approval in tids:
    cur.execute("""INSERT OR REPLACE INTO tasks 
        (tid, projekt, run_id, task, goal, phase, phase_section, phase_seq,
         skill_name, script_path, input_artifacts, output_artifact, template_id, requires_approval)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (tid, PROJEKT, RUN_ID, section, GOAL, phase, section, seq, skill, script, inp, output, template_id, requires_approval))

# Pre-task dependencies
deps = [
    (f"{PROJEKT}-{RUN_ID}-P1-evil-twin-1",   f"{PROJEKT}-{RUN_ID}-P1-brainstorming"),
    (f"{PROJEKT}-{RUN_ID}-P1-writing-plans",  f"{PROJEKT}-{RUN_ID}-P1-evil-twin-1"),
    (f"{PROJEKT}-{RUN_ID}-P1-evil-twin-2",    f"{PROJEKT}-{RUN_ID}-P1-writing-plans"),
    (f"{PROJEKT}-{RUN_ID}-P1-architecture",    f"{PROJEKT}-{RUN_ID}-P1-evil-twin-2"),
    (f"{PROJEKT}-{RUN_ID}-P1-evil-twin-3",    f"{PROJEKT}-{RUN_ID}-P1-architecture"),
    (f"{PROJEKT}-{RUN_ID}-G1-2-verify",       f"{PROJEKT}-{RUN_ID}-P1-evil-twin-3"),
    (f"{PROJEKT}-{RUN_ID}-P2-writing-plans-v2", f"{PROJEKT}-{RUN_ID}-G1-2-verify"),
    (f"{PROJEKT}-{RUN_ID}-P2-evil-twin-4",    f"{PROJEKT}-{RUN_ID}-P2-writing-plans-v2"),
    (f"{PROJEKT}-{RUN_ID}-P2-debugging",       f"{PROJEKT}-{RUN_ID}-P2-evil-twin-4"),
    (f"{PROJEKT}-{RUN_ID}-P2-evil-twin-5",    f"{PROJEKT}-{RUN_ID}-P2-debugging"),
    (f"{PROJEKT}-{RUN_ID}-G2-3-verify",       f"{PROJEKT}-{RUN_ID}-G1-2-verify"),
    (f"{PROJEKT}-{RUN_ID}-P3-implementer",     f"{PROJEKT}-{RUN_ID}-G2-3-verify"),
    (f"{PROJEKT}-{RUN_ID}-P3-evil-twin-6",    f"{PROJEKT}-{RUN_ID}-P3-implementer"),
    (f"{PROJEKT}-{RUN_ID}-P3-reviewer",        f"{PROJEKT}-{RUN_ID}-P3-evil-twin-6"),
    (f"{PROJEKT}-{RUN_ID}-P3-finishing",       f"{PROJEKT}-{RUN_ID}-P3-reviewer"),
    (f"{PROJEKT}-{RUN_ID}-P4-docs",            f"{PROJEKT}-{RUN_ID}-P3-finishing"),
    (f"{PROJEKT}-{RUN_ID}-P4-wiki",            f"{PROJEKT}-{RUN_ID}-P3-finishing"),
    (f"{PROJEKT}-{RUN_ID}-P4-learnings",       f"{PROJEKT}-{RUN_ID}-P3-finishing"),
    (f"{PROJEKT}-{RUN_ID}-P4-evil-twin-7",    f"{PROJEKT}-{RUN_ID}-P4-docs"),
]
for tid, pre_tid in deps:
    cur.execute("INSERT OR IGNORE INTO pre_tasks (tid, pre_tid) VALUES (?, ?)", (tid, pre_tid))

# ─── Multi-Way Alternative Paths ────────────────────────────────────
# After P1-brainstorming: choose research-first vs design-first vs ui-first
alt_paths = [
    # After brainstorming: 3 alternative next paths
    (f"{PROJEKT}-{RUN_ID}-P1-brainstorming", f"{PROJEKT}-{RUN_ID}-P1-evil-twin-1", "A",
     "Standard: design → plan → architecture",
     "Default-Flow. Geht direkt zu writing-plans.",
     0),
    (f"{PROJEKT}-{RUN_ID}-P1-brainstorming", f"{PROJEKT}-{RUN_ID}-STACK-community-research", "B",
     "Research-First: erst Deep-Recherche vor Plan",
     "Mehr Kontext, langsamer. Für komplexe/neue Domains.",
     1),
    (f"{PROJEKT}-{RUN_ID}-P1-brainstorming", f"{PROJEKT}-{RUN_ID}-STACK-frontend-design", "C",
     "UI-First: erst Mockups/Designs vor Backend-Plan",
     "Wenn hauptsächlich UI/UX-Driven. Überspringt architecture-Review.",
     2),
    # After G1-2 verify: PASS → auto-Phase-2, FAIL → loop oder continue
    (f"{PROJEKT}-{RUN_ID}-G1-2-verify", f"{PROJEKT}-{RUN_ID}-P2-writing-plans-v2", "A",
     "FAIL detected → Phase 2 zur Gap-Schließung",
     "Automatisch wenn Output 'FAIL' enthält.",
     0),
    # After P3-finishing: choose merge strategy
    (f"{PROJEKT}-{RUN_ID}-P3-finishing", f"{PROJEKT}-{RUN_ID}-P4-docs", "A",
     "Standard: Docs → Wiki → Learnings parallel",
     "Default-Flow. Alle drei Docs parallel.",
     0),
    (f"{PROJEKT}-{RUN_ID}-P3-finishing", f"{PROJEKT}-{RUN_ID}-STACK-security-scan", "B",
     "Security-First: security-scan VOR Doku",
     "Wenn Code öffentlich wird. Fügt Security-Check zwischen Implementation und Doku ein.",
     1),
]
for source, target, label, rationale, tradeoffs, ranking in alt_paths:
    cur.execute("""INSERT OR REPLACE INTO alternative_paths
        (source_tid, target_tid, path_label, rationale, tradeoffs, ranking)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (source, target, label, rationale, tradeoffs, ranking))

# ─── Template Markers (DRIFT-DETECTION RULES) ───────────────────────

templates = {
    "design-doc-v1": [
        ("SECTION_HEADER", r"^# Design:.*", "ERROR", "Title H1 with 'Design:'"),
        ("SECTION_HEADER", r"^## Übersicht", "ERROR", "Section: Übersicht"),
        ("SECTION_HEADER", r"^## Architektur", "ERROR", "Section: Architektur"),
        ("SECTION_HEADER", r"^## Komponenten", "ERROR", "Section: Komponenten"),
        ("SECTION_HEADER", r"^## Datenmodell", "ERROR", "Section: Datenmodell"),
        ("SECTION_HEADER", r"^## Schnittstellen", "ERROR", "Section: Schnittstellen"),
        ("SECTION_HEADER", r"^## Risiken", "ERROR", "Section: Risiken & Annahmen"),
        ("SECTION_HEADER", r"^## Offene Fragen", "WARNING", "Section: Offene Fragen"),
        ("TAG_PATTERN", r"\{\{[^}]+\}\}", "ERROR", "Placeholder {{...}} muss gefüllt sein"),
    ],
    "implementation-plan-v1": [
        ("SECTION_HEADER", r"^# Implementation Plan:.*", "ERROR", "Title H1 with 'Implementation Plan:'"),
        ("SECTION_HEADER", r"^## Tasks", "ERROR", "Section: Tasks"),
        ("SECTION_HEADER", r"^## Done When", "ERROR", "Section: Done When / Acceptance Criteria"),
        ("MARKER_LINE", r"\[ \] ", "WARNING", "Mindestens eine Task-Checkbox"),
        ("TAG_PATTERN", r"\{\{[^}]+\}\}", "ERROR", "Placeholder {{...}} muss gefüllt sein"),
    ],
    "gate-result-v1": [
        ("MARKER_LINE", r"^(PASS|FAIL)$", "ERROR", "Erste Zeile MUSS PASS oder FAIL sein"),
        ("SECTION_HEADER", r"^# Gate", "WARNING", "Gate-Title"),
    ],
    "evil-twin-v1": [
        # v3.0: Die WIDERSPRUCH-Datei (.md) enthält nur noch die gerenderte
        # Prosa (result.prose.text). Die Prosa trägt den Verdict
        # (FUNDAMENTAL/OBERFLÄCHLICH) über render_critique's system_state —
        # das ist der einzige verbleibende Marker. Die Struktur
        # (verdict/objections) lebt in <output>.result.json und wird vom Gate
        # konsumiert, NICHT aus der Prosa geparst.
        ("MARKER_LINE", r"FUNDAMENTAL|OBERFLÄCHLICH", "ERROR", "Verdict muss in der Prosa stehen"),
    ],
    "root-cause-v1": [
        ("SECTION_HEADER", r"^# Root-Cause", "ERROR", "Title H1 mit Root-Cause"),
        ("SECTION_HEADER", r"^## Gap \d+:", "ERROR", "Mindestens ein Gap mit Root-Cause"),
    ],
    "implementation-log-v1": [
        ("SECTION_HEADER", r"^# Phase 3 Implementation Log", "ERROR", "Title"),
        ("SECTION_HEADER", r"^## Task \d+", "WARNING", "Mindestens ein Task dokumentiert"),
    ],
    "review-log-v1": [
        ("SECTION_HEADER", r"^# Phase 3 Review Log", "ERROR", "Title"),
        ("MARKER_LINE", r"PASS|FAIL", "ERROR", "Reviews mit PASS/FAIL markiert"),
    ],
    "finish-log-v1": [
        ("SECTION_HEADER", r"^# Phase 3 Finish Log", "ERROR", "Title"),
        ("SECTION_HEADER", r"^## Test-Ergebnisse", "ERROR", "Test results documented"),
        ("SECTION_HEADER", r"^## Merge-Optionen", "ERROR", "Merge options listed"),
    ],
    "diataxis-docs-v1": [
        ("SECTION_HEADER", r"^# Tutorial:|^# How-To:|^# Reference:|^# Explanation:", "ERROR", "Diátaxis section required"),
    ],
    "wiki-update-v1": [
        ("SECTION_HEADER", r"^# Wiki Update", "WARNING", "Title"),
    ],
    "learnings-v1": [
        ("SECTION_HEADER", r"^# Learnings", "ERROR", "Title"),
        ("SECTION_HEADER", r"^## Errors|^## Learnings|^## Feature Requests", "ERROR", "Sections required"),
    ],
    "decision-log-v1": [
        ("SECTION_HEADER", r"^# .* Decision|^# .* Guide|^# .* Plan|^# Frontend|^# Canvas|^# Media|^# Architecture", "ERROR", "Title H1"),
    ],
    "execution-log-v1": [
        ("SECTION_HEADER", r"^# .* Execution|^# Plan Execution", "ERROR", "Title"),
        ("MARKER_LINE", r"DONE|FAILED", "WARNING", "Tasks mit DONE/FAILED markiert"),
    ],
    "orchestration-plan-v1": [
        ("SECTION_HEADER", r"^# Multi-Agent Orchestration Plan", "ERROR", "Title"),
        ("MARKER_LINE", r"\| Agent \|", "ERROR", "Tabelle mit Agents"),
    ],
    "security-report-v1": [
        ("SECTION_HEADER", r"^# Security Scan Report", "ERROR", "Title"),
        ("SECTION_HEADER", r"^## Critical|^## High|^## Medium|^## Low", "ERROR", "Severity sections"),
    ],
    "findings-tracker-v1": [
        ("SECTION_HEADER", r"^# Findings Tracker", "ERROR", "Title"),
        ("MARKER_LINE", r"\| ID \|", "ERROR", "Tabelle mit Finding-IDs"),
    ],
    "guidelines-check-v1": [
        ("SECTION_HEADER", r"^# Design Guidelines", "ERROR", "Title"),
    ],
    "validation-report-v1": [
        ("SECTION_HEADER", r"^# Validation Report", "ERROR", "Title"),
    ],
    "test-strategy-v1": [
        ("SECTION_HEADER", r"^# Test Strategy", "ERROR", "Title"),
    ],
    "playwright-tests-v1": [
        ("SECTION_HEADER", r"^# Playwright Test Suite", "ERROR", "Title"),
    ],
    "research-report-v1": [
        ("SECTION_HEADER", r"^# Deep Research", "ERROR", "Title"),
    ],
    "consolidation-v1": [
        ("SECTION_HEADER", r"^# Memory Consolidation", "ERROR", "Title"),
    ],
    "review-processing-v1": [
        ("SECTION_HEADER", r"^# Code Review Processing", "ERROR", "Title"),
    ],
}

# Insert all template markers
for tid_idx, (tid, phase, section, seq, skill, script, output, inp, template_id, requires_approval) in enumerate(tids):
    if template_id in templates:
        for mtype, pattern, severity, desc in templates[template_id]:
            cur.execute("""INSERT OR IGNORE INTO template_markers
                (template_id, marker_type, pattern, severity, description)
                VALUES (?, ?, ?, ?, ?)""",
                (template_id, mtype, pattern, severity, desc))

conn.commit()
count = cur.execute("SELECT COUNT(*) FROM tasks WHERE run_id=?", (RUN_ID,)).fetchone()[0]
template_count = cur.execute("SELECT COUNT(*) FROM template_markers").fetchone()[0]
alt_count = cur.execute("SELECT COUNT(*) FROM alternative_paths").fetchone()[0]
conn.close()

print(f"RUN_ID={RUN_ID}")
print(f"RUN_DIR={RUN_DIR}")
print(f"TID_COUNT={count}")
print(f"TEMPLATE_MARKERS={template_count}")
print(f"ALT_PATHS={alt_count}")
