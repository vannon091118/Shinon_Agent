#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-community-deep-research.sh — STACK: LOGISCH — Skill: research/community-deep-research
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-community-deep-research.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

## 🎯 AUFGABE
1. Lade den community-deep-research Skill via skill-Tool
2. Recherchiere tiefgehend: Docs, Foren, Issues, Papers
3. Sammle Erkenntnisse, Patterns, Best Practices
4. Self-Check: Quellen zitiert, keine Halluzination

## 📤 OUTPUT → $OUTPUT_FILE
\`\`\`
# Deep Research
## Quellen: ...
## Erkenntnisse: ...
## Patterns: ...
## Empfehlungen: ...
\`\`\`
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh"
echo ""
echo "🤖 AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
