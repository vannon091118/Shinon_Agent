#!/bin/bash
# phase-4-docs.sh — Documentation (Diataxis)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-4-docs.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")

agent_header "$TID" "Phase 4.1 Documentation Writer"
emit_user_input_start "phase-4-docs.sh"
cat <<INSTRUCTION

## Input Finish-Log: $INPUT_ARTIFACT
## Goal: $GOAL
## Skill: $SKILL

## Aufgabe
1. Lade documentation-writer Skill.
2. Erstelle Diataxis-Dokumentation:
   - Tutorial (Schritt-fuer-Schritt)
   - How-to (Anleitungen)
   - Reference (technische Referenz)
   - Explanation (Hintergrund/Konzepte)
3. Self-Check: Diataxis principles.

Output nach $OUTPUT_FILE.
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
