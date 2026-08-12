#!/bin/bash
# chain-track-findings.sh — STACK: GOVERNANCE
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-track-findings.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "GOVERNANCE track-findings"
emit_user_input_start "chain-track-findings.sh"
cat <<INSTRUCTION

## Goal: $GOAL
## Skill: $SKILL

## Aufgabe
1. Lade track-findings Skill via skill-Tool.
2. Sammle Findings aus Security-Scans, Reviews, Gates.
3. Status: OFFEN / IN_BEARBEITUNG / GESCHLOSSEN / FALSE_POSITIVE.
4. Self-Check: Kein Finding ohne Owner + Deadline.

Output nach $OUTPUT_FILE als Tabelle:
- ID: F-001 ...
- Typ: SECURITY / REVIEW / GATE ...
- Severity: HIGH / MEDIUM / LOW
- Status: OFFEN / IN_BEARBEITUNG / GESCHLOSSEN
- Owner: Person
- Deadline: Datum
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
