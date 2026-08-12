#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-receiving-code-review.sh — STACK: SELF-IMPROVE — Skill: development/receiving-code-review
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-receiving-code-review.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

## 🎯 AUFGABE
1. Lade den receiving-code-review Skill via skill-Tool
2. Verarbeite Code-Review-Feedback systematisch
3. Kategorisiere: BLOCKER / MAJOR / MINOR / NIT
4. Self-Check: Jedes Feedback hat Action-Item + Owner

## 📤 OUTPUT → $OUTPUT_FILE
\`\`\`
# Code Review Processing
## Blocker: ... (müssen vor Merge gelöst werden)
## Major: ...
## Minor: ...
## Nits: ...
## Action Items: ...
\`\`\`
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh"
echo ""
echo "🤖 AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
