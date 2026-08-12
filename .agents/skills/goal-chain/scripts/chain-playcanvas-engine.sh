#!/bin/bash
# chain-playcanvas-engine.sh — STACK: KREATIV
# Auto-generated wrap of games/playcanvas-engine/SKILL.md
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

RUN_ID="${1:?Usage: bash chain-playcanvas-engine.sh RUN_ID TID}"
TID="${2:?}"

ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "KREATIV: playcanvas-engine"
emit_user_input_start "chain-playcanvas-engine.sh"

cat <<INSTRUCTION

## Goal: $GOAL
## Skill: $SKILL
## Source: games/playcanvas-engine/SKILL.md

## Aufgabe
Playcanvas Engine-Integration. Asset-Pipeline + Scene-Graph. Self-Check: Engine-Init + Frame-Budget.

## Domain-Kontext
- Original-Skill liegt unter: `.agents/skills/games/playcanvas-engine/SKILL.md`
- Dieser Wrapper fuehrt den Skill als Chain-Tool aus.
- Drift-Detection: Output wird gegen template_markers verifiziert.

## Output nach $OUTPUT_FILE
- Strukturiert, kein Drift.
- Self-Check gruen, dann: bash $SCRIPT_DIR/complete.sh $TID DONE.

## Agent-Regeln
1. Source-Skills (`.agents/skills/games/playcanvas-engine/SKILL.md`) NICHT veraendern.
2. Output-Format einhalten — sonst Re-Dispatch.
3. NEXT_TID nach Self-Check setzen.
INSTRUCTION

agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"

notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
