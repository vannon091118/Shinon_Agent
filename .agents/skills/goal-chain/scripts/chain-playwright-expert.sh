#!/bin/bash
# chain-playwright-expert.sh — STACK: LOGISCH
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-playwright-expert.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "LOGISCH playwright-expert"
emit_user_input_start "chain-playwright-expert.sh"
cat <<INSTRUCTION

## Goal: $GOAL
## Skill: $SKILL

## Aufgabe
1. Lade playwright-expert Skill via skill-Tool.
2. Schreibe browser-basierte E2E-Tests: Navigation, Formulare, Errors, Responsive.
3. Self-Check: Jeder User-Flow hat einen Test.

Output nach $OUTPUT_FILE in einer Tabelle:
- ID: PW-001 etc.
- Flow: Name
- Status: PASS/FAIL
- File: test_xyz.py
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
