#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-web-design-guidelines.sh — STACK: KREATIV — Skill: design/web-design-guidelines
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-web-design-guidelines.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "KREATIV web-design-guidelines"
emit_user_input_start "chain-web-design-guidelines.sh"
cat <<INSTRUCTION
## 🎯 AUFGABE
1. Lade den web-design-guidelines Skill via skill-Tool
2. Definiere/Prüfe Design-Guidelines für das Projekt
3. Berücksichtige: Accessibility (WCAG), Responsive Design, Performance
4. Self-Check: Guidelines messbar, durch Beispiele belegt

## 📤 OUTPUT → $OUTPUT_FILE
```
# Web Design Guidelines Checklist
## Accessibility: ...
## Responsive Breakpoints: ...
## Typography: ...
## Spacing System: ...
## Component Patterns: ...
```
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
