#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-consolidate-memory.sh — STACK: MEMORY — Skill: claude-tools/consolidate-memory
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-consolidate-memory.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

## 🎯 AUFGABE
1. Lade den consolidate-memory Skill via skill-Tool
2. Konsolidiere ALLE Learnings aus diesem Run
3. Update Wiki, Knowledge-Base, Patterns
4. Self-Check: Kein Learning geht verloren

## 📤 OUTPUT → $OUTPUT_FILE
\`\`\`
# Memory Consolidation
## Learnings: ...
## Updated Pages: ...
## New Patterns: ...
\`\`\`
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh"
echo ""
echo "🤖 AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
