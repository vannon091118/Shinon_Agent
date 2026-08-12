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

## 🎯 AUFGABE
1. Lade den frontend-design Skill via skill-Tool
2. Entwerfe UI-Design: Layout, Komponenten, Interaktionen
3. Berücksichtige: Responsive, Accessibility, Animation
4. Self-Check: Design-System konsistent, keine toten States

## 📤 OUTPUT → $OUTPUT_FILE
\`\`\`
# Frontend Design
## Layout: ...
## Komponenten-Baum: ...
## Interaktions-Flows: ...
## Style Guide: ...
\`\`\`
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh"
echo ""
echo "🤖 AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
