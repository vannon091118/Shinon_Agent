#!/bin/bash
# chain-autorun.sh — STACK: AUTONOM
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-autorun.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "AUTONOM autorun"
emit_user_input_start "chain-autorun.sh"
cat <<INSTRUCTION

## Goal: $GOAL
## Skill: $SKILL

## Aufgabe
1. Lade autorun Skill via skill-Tool.
2. Analysiere Goal, bestimme optimalen Start-Stack.
3. Welcher Stack zuerst: KREATIV, GOVERNANCE oder LOGISCH?
4. Self-Check: Task-Erkennung vollstaendig.

Output nach $OUTPUT_FILE:
- Goal-Analyse
- Empfohlener Start-Stack + Begruendung
- Dispatch-Anweisung: NEXT_TID=...
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
