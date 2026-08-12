#!/bin/bash
# chain-canvas-design.sh — STACK: KREATIV
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-canvas-design.sh RUN_ID TID}"
TID="${2:?}"
ensure_db
assert_tid_state "$TID" "PENDING"
tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "KREATIV canvas-design"
emit_user_input_start "chain-canvas-design.sh"
cat <<INSTRUCTION

## Goal: $GOAL
## Skill: $SKILL

## Aufgabe
1. Lade canvas-design Skill via skill-Tool.
2. Erstelle visuelles Design: Color Palette, Typography, Icons.
3. Dark/Light Mode konsistent.
4. Self-Check: Brand-Identity.

Output nach $OUTPUT_FILE:
- Color Palette: Hex-Codes
- Typography: Schriftarten + Sizes
- Icon Set: Namen/Pfade
- Assets: SVG/CSS
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
