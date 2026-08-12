#!/bin/bash
# phase-3-finishing.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-3-finishing.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")

agent_header "$TID" "Phase 3.3 Finishing Development Branch"
emit_user_input_start "phase-3-finishing.sh"
cat <<INSTRUCTION

## Input Review-Log: $INPUT_ARTIFACT
## Goal: $GOAL
## Skill: $SKILL

## Aufgabe
1. Lade finishing-a-development-branch Skill.
2. Verify: alle Tests gruen.
3. Praesentiere Merge-Optionen.
4. Self-Check: Verify tests pass before presenting options.

Output nach $OUTPUT_FILE:
- # Phase 3 Finish Log
- ## Test-Ergebnisse (alle Tests PASS?)
- ## Merge-Optionen (mindestens 2)
- ## Empfehlung
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
