#!/bin/bash
# chain-presentation-tools.sh — STACK: MEMORY
# Auto-generated wrap of documents/presentation-tools/SKILL.md
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

RUN_ID="${1:?Usage: bash chain-presentation-tools.sh RUN_ID TID}"
TID="${2:?}"

ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "MEMORY: presentation-tools"
emit_user_input_start "chain-presentation-tools.sh"

cat <<INSTRUCTION

## Goal: $GOAL
## Skill: $SKILL
## Source: documents/presentation-tools/SKILL.md

## Aufgabe
Presentation-Tool. Beamer/Keynote/PPT-Logic. Self-Check: Folien-Anzahl + Speaker-Notes.

## Domain-Kontext
- Original-Skill liegt unter: `.agents/skills/documents/presentation-tools/SKILL.md`
- Dieser Wrapper fuehrt den Skill als Chain-Tool aus.
- Drift-Detection: Output wird gegen template_markers verifiziert.

## Output nach $OUTPUT_FILE
- Strukturiert, kein Drift.
- Self-Check gruen, dann: bash $SCRIPT_DIR/complete.sh $TID DONE.

## Agent-Regeln
1. Source-Skills (`.agents/skills/documents/presentation-tools/SKILL.md`) NICHT veraendern.
2. Output-Format einhalten — sonst Re-Dispatch.
3. NEXT_TID nach Self-Check setzen.
INSTRUCTION

agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"

notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
