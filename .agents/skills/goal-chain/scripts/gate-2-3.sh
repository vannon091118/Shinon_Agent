#!/bin/bash
# gate-2-3.sh — TID: G2-3-verify
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash gate-2-3.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")

PLAN_V2="$INPUT_ARTIFACT"
if [[ ! -f "$PLAN_V2" ]]; then
  PLAN_V2="${INPUT_ARTIFACT/_v2/}"
fi

agent_header "$TID" "Gate 2-3 FALSIFIZIERUNG 2. Durchlauf"
emit_user_input_start "gate-2-3.sh"
cat <<INSTRUCTION

## Input Plan V2: $PLAN_V2
## Goal: $GOAL
## Skill: $SKILL, IRON LAW: no completion claim without fresh verification

## Aufgabe
1. Lade verification-before-completion Skill.
2. Lies Plan V2.
3. Pruefe: IST DER PLAN JETZT VOLLSTAENDIG?

## Output nach $OUTPUT_FILE, ERSTE ZEILE MUSS SEIN:
PASS
oder:
FAIL
mit Gap-Liste ab Zeile 2

## Entscheidung
- PASS: bash complete.sh $TID DONE
- FAIL: bash complete.sh $TID FAIL
INSTRUCTION
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
