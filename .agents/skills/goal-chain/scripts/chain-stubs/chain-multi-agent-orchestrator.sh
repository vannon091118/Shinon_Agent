#!/bin/bash
# chain-multi-agent-orchestrator.sh — STACK: GOVERNANCE
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-multi-agent-orchestrator.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "GOVERNANCE multi-agent-orchestrator"
emit_user_input_start "chain-multi-agent-orchestrator.sh"
cat <<INSTRUCTION

## Goal: $GOAL
## Skill: $SKILL

## Aufgabe
1. Lade multi-agent-orchestrator Skill via skill-Tool.
2. Bestaetige welche Subagents noetig sind und in welcher Reihenfolge.
3. Definiere Agent-Vertraege: Input/Output pro Subagent.
4. Self-Check: Keine Ueberlappung.

Output nach $OUTPUT_FILE in einer Tabelle:
- Agent | Skill | Input | Output | Parallel moeglich ja/nein
- Execution Order: ...
- Gate Checks: ...
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
