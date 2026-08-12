#!/bin/bash
# phase-4-learnings.sh — Self-Improvement (Phase 4.3)
#
# Koppelt die zwei Self-Improve-Schichten im Projekt:
#   1. Agent-side:  .learnings/{LEARNINGS,ERRORS,FEATURE_REQUESTS}.md
#                   (promoted via activator.sh / error-detector.sh hooks)
#   2. Engine-side: karma ml simulate (deterministisch, safe-by-construction)
#
# Reihenfolge (verbindlich, dokumentiert im goal-chain Skill):
#   Evil-Twin-Gate → G2 ✅ → Phase 4 starten
#     ↳ Phase 4.3 leitet Agent zu Manual-Logging an
#     ↳ Phase 4.3 ruft danach karma ml simulate (deterministisch)
#     ↳ Output landet in .learnings/<proj>-cycles.json (für Audit + Dashboard)
#
# 1/3-RegeI "Self-Improve MUSS nach jedem Task automatisch laufen"
# wird vollständig erfüllt durch:
#   - complete.sh:   karma ml simulate --cycles 1   (cheap, post-TID)
#   - phase-4 (hier): karma ml simulate --cycles 3   (gründlich, post-EvilTwin)
#   - kar.cli train: explizit bei ./shinon self-improve  (user-driven)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-4-learnings.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")

agent_header "$TID" "Phase 4.3 Self-Improvement"
emit_user_input_start "phase-4-learnings.sh"
cat <<INSTRUCTION

## Input Finish-Log: $INPUT_ARTIFACT
## Goal: $GOAL
## Skill: $SKILL

## Aufgabe (Agent-Side)
1. Lade `meta/self-improvement`-Skill.
2. Evaluiere Learnings aus Phase 3.
3. Log errors, learnings, feature-requests nach:
   - .learnings/ERRORS.md         (Schema: ERR-YYYYMMDD-XXX)
   - .learnings/LEARNINGS.md      (Schema: LRN-YYYYMMDD-XXX)
   - .learnings/FEATURE_REQUESTS.md (Schema: FEAT-YYYYMMDD-XXX)
4. Self-Check: Promotion Rule (Recurrence ≥ 3 + 2 tasks + 30 d).
5. Beantworte die 3 Self-Score-Fragen pro verwendetem Skill:
   - Q1: Wie sehr hat der Skill in der Vergangenheit geholfen?
   - Q2: Wie sehr hat der Skill in DIESEM Task Impact erzielt?
   - Q3: Belassen / verbessern / neuen Skill extrahieren?
   → Output: $OUTPUT_FILE (Markdown)
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"

# ─── Engine-Side Self-Improvement (deterministisch, automatisch) ───────
# Findet Karma-CLI: venv-Python bevorzugt, sonst System-Python als Fallback.
PROJECT_NAME="$(basename "$(pwd)")"
LEARNINGS_DIR=".learnings"
CYCLES_JSON="$LEARNINGS_DIR/${PROJECT_NAME}-cycles.json"
mkdir -p "$LEARNINGS_DIR"

# Python-Resolver: venv → sonst system python3 (für CI/sandbox-Container)
KARMA_PY=".venv/bin/python3"
[ -x "$KARMA_PY" ] || KARMA_PY="$(command -v python3 || echo python3)"

echo ""
echo "── KARMA SELF-IMPROVE (post-EvilTwin) ───────────────────────────"
echo "  project:   $PROJECT_NAME"
echo "  cycles:    3  (simulate, dry-run = safe)"
echo "  dump:      $CYCLES_JSON"

CYCLE_OUTPUT=$("$KARMA_PY" -m karma.cli ml simulate \
    --project "$PROJECT_NAME" \
    --cycles 3 2>&1 || true)

# Snapshot schreiben (Überschreiben erlaubt: ist deterministisch pro Phase)
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
{
    printf '{\n'
    printf '  "project": "%s",\n'   "$PROJECT_NAME"
    printf '  "run_id":  "%s",\n'   "$RUN_ID"
    printf '  "tid":     "%s",\n'   "$TID"
    printf '  "timestamp": "%s",\n' "$TIMESTAMP"
    printf '  "skill_under_review": "%s",\n' "$SKILL"
    printf '  "cycles_requested": 3,\n'
    printf '  "mode": "simulate (dry-run, no state mutation)",\n'
    printf '  "raw_output":\n'
    # Indent raw_output by 4 spaces inside the JSON string
    printf '%s' "$CYCLE_OUTPUT" | sed 's/^/    /' || true
    printf '\n}\n'
} > "$CYCLES_JSON"

echo "  → $CYCLES_JSON geschrieben ($(wc -c < "$CYCLES_JSON") bytes)"
echo "─────────────────────────────────────────────────────────────────"

notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
