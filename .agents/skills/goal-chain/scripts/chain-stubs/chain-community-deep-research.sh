#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-community-deep-research.sh — STACK: AUTONOM — Skill: agents/community-deep-research
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-community-deep-research.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")

agent_header "$TID" "AUTONOM community-deep-research"
emit_user_input_start "chain-community-deep-research.sh"
cat <<INSTRUCTION
## 🎯 AUFGABE
1. Lade den community-research Skill via skill-Tool
2. Recherchiere aktuelle Best Practices zum Goal-Thema
3. Sammle: Community-Meinungen, GitHub-Diskussionen, Stack-Overflow-Insights
4. Self-Check: Quellen verlinkt, Bias-Analyse durchgeführt

## 📤 OUTPUT → $OUTPUT_FILE
```
# Community Research Report
## Key Findings: ...
## Sources: ...
## Recommendations: ...
```
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
