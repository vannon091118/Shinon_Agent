#!/bin/bash
# phase-3-reviewer.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-3-reviewer.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")

agent_header "$TID" "Phase 3.2 Code Review"
emit_user_input_start "phase-3-reviewer.sh"
cat <<INSTRUCTION

## Input Implementierungs-Log: $INPUT_ARTIFACT
## Goal: $GOAL
## Skill: $SKILL

## Aufgabe
1. Lade dispatching-parallel-agents Skill.
2. ZWEI Reviewer parallel:
   a. spec-reviewer: passt Code zur Spec?
   b. code-quality-reviewer: patterns, errors, quality, tests
3. Bei FAIL: zurueck zu implementer, RE-REVIEW.
4. Bei PASS: finalisiere Review-Log.

Output nach $OUTPUT_FILE als Tabellen:
- Spec-Review: Task / Status / Issues
- Quality-Review: File / Status / Issues
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
