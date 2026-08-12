#!/bin/bash
# phase-1-architecture.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash phase-1-architecture.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
INPUT_ARTIFACT=$(task_field "$TID" "input_artifacts")
GOAL=$(task_field "$TID" "goal")
SKILL=$(task_field "$TID" "skill_name")

agent_header "$TID" "Phase 1.3 Architecture Review"
emit_user_input_start "phase-1-architecture.sh"
cat <<INSTRUCTION

## Input Plan: $INPUT_ARTIFACT
## Goal: $GOAL
## Skill: $SKILL

## Aufgabe
1. Lade improve-codebase-architecture Skill.
2. Analysiere Codebase-Architektur im Kontext des Goals.
3. Finde passende Architektur-Kandidaten.
4. Self-Check: grilling loop, domain model current.

Output als HTML nach $OUTPUT_FILE:
- Architektur-Uebersicht
- Betroffene Komponenten
- Aenderungs-Vorschlaege
- Risiko-Bewertung
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
