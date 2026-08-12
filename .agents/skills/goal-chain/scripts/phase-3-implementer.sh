#!/bin/bash
# phase-3-implementer.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-3-implementer.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")

agent_header "$TID" "Phase 3.1 Subagent-Driven Development"
emit_user_input_start "phase-3-implementer.sh"
cat <<INSTRUCTION

## Input Plan: $INPUT_ARTIFACT
## Goal: $GOAL
## Skill: $SKILL

## Aufgabe
1. Lade subagent-driven-development Skill.
2. Lies Plan, extrahiere alle Tasks.
3. Pro Task:
   a. implementer via spawn_agents (TDD IRON LAW: RED-GREEN-REFACTOR)
   b. Evil Twin prompt (siehe chain-3-Evil-Twin Skill)
   c. spec-reviewer
   d. code-quality-reviewer
4. dispatching-parallel-agents fuer unabhaengige Tasks.
5. FINAL: code-reviewer-deepseek.

Output nach $OUTPUT_FILE:
- # Phase 3 Implementation Log
- ## Task 1: Status, Files, Reviewer-Ergebnis
- ## Task 2 ...
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
