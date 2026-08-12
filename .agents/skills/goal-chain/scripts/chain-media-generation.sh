#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-media-generation.sh — STACK: KREATIV — Skill: media/media-generation
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-media-generation.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

## 🎯 AUFGABE
1. Lade den media-generation Skill via skill-Tool
2. Generiere Medien: Bilder, Videos, Audio, 3D
3. Optimiere für Web-Performance
4. Self-Check: Alle Assets haben Alt-Text/Fallback

## 📤 OUTPUT → $OUTPUT_FILE
\`\`\`
# Media Generation
## Generated Assets: ...
## Formats: ...
## Optimizations: ...
\`\`\`
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh"
echo ""
echo "🤖 AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
