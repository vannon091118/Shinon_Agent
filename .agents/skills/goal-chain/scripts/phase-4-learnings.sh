#!/bin/bash
# phase-4-learnings.sh — Self-Improvement
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

## Aufgabe
1. Lade self-improvement Skill.
2. Evaluiere Learnings aus Phase 3.
3. Log errors, learnings, feature-requests.
4. Self-Check: Promotion Rule (Recurrence >= 3 + 2 tasks + 30 d).

Output nach $OUTPUT_FILE:
- # Learnings
- ## Errors
- ## Learnings
- ## Feature Requests
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
