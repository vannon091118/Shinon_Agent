#!/bin/bash
# phase-4-wiki.sh — Wiki Update
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-4-wiki.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")

agent_header "$TID" "Phase 4.2 Wiki System"
emit_user_input_start "phase-4-wiki.sh"
cat <<INSTRUCTION

## Input Finish-Log: $INPUT_ARTIFACT
## Goal: $GOAL
## Skill: $SKILL

## Aufgabe
1. Lade wiki-system Skill.
2. Ingest neue Erkenntnisse ins Wiki.
3. Self-Check: JEDE referenzierte Entity/Concept-Page anlegen/updaten.

Output nach $OUTPUT_FILE.
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
