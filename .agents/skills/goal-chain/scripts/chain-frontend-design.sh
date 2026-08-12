#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-frontend-design.sh — STACK: KREATIV — Skill: design/frontend-design
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-frontend-design.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "KREATIV frontend-design"
emit_user_input_start "chain-frontend-design.sh"
cat <<INSTRUCTION
## 🎯 AUFGABE
1. Lade den frontend-design Skill via skill-Tool
2. Entwerfe UI-Konzept für die aktuelle Komponente
3. Beachte: Responsive Design, Accessibility, Dark/Light-Mode
4. Self-Check: Design-System konsistent, Abstände/Grid eingehalten

## 📤 OUTPUT → $OUTPUT_FILE
```
# Frontend Design Decision Log
## Layout: ...
## Component Tree: ...
## Color Palette: ...
## Accessibility Notes: ...
```
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
