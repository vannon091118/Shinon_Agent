#!/bin/bash
# phase-1-writing-plans.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-1-writing-plans.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")

agent_header "$TID" "Phase 1.2 Writing Plans"
emit_user_input_start "phase-1-writing-plans.sh"
cat <<INSTRUCTION

## Input Design: $INPUT_ARTIFACT
## Goal: $GOAL
## Skill: $SKILL

## Aufgabe
1. Lade writing-plans Skill.
2. Lies Design aus $INPUT_ARTIFACT.
3. Erstelle VOLLSTAENDIGEN Implementierungsplan.
4. KEINE TBDs, TODOs, Platzhalter.
5. Self-Check: alle Luecken geschlossen.

Output nach $OUTPUT_FILE:
- # Implementierungsplan
- ## Phase 1 Tasks (Checkboxen)
- ## Phase 2 Tasks
- ## Phase 3 Tasks
- ## Schaetzung pro Task
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
