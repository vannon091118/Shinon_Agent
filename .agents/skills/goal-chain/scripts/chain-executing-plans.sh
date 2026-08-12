#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-executing-plans.sh — STACK: AUTONOM — Skill: web-dev/superpowers/executing-plans
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-executing-plans.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

## 🎯 AUFGABE
1. Lade den executing-plans Skill via skill-Tool
2. Nimm den aktuellen Plan und führe ihn Task-für-Task aus
3. Dispatche Subagents parallel wo möglich
4. Self-Check: Jeder Task hat clear acceptance criteria

## 📤 OUTPUT → $OUTPUT_FILE
\`\`\`
# Plan Execution Log
## Task 1: [name] → Status: DONE/FAILED
## Task 2: [name] → Status: DONE/FAILED
...
\`\`\`
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh"
echo ""
echo "🤖 AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
