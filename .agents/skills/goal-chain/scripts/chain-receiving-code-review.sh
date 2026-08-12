#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-receiving-code-review.sh — STACK: GOVERNANCE — Skill: agents/receiving-code-review
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-receiving-code-review.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "GOVERNANCE receiving-code-review"
emit_user_input_start "chain-receiving-code-review.sh"
cat <<INSTRUCTION
## 🎯 AUFGABE
1. Lade den receiving-code-review Skill via skill-Tool
2. Review den aktuellen Code-Stand auf Qualität und Konsistenz
3. Prüfe: Error-Handling, Edge-Cases, Performance, Security
4. Self-Check: Jeder Fund hat konkreten Fix-Vorschlag

## 📤 OUTPUT → $OUTPUT_FILE
```
# Code Review Process
## Reviewed Files: ...
## Issues Found: ...
## Approved Patterns: ...
## Action Items: ...
```
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
