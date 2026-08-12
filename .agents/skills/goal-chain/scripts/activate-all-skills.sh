#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# activate-all-skills.sh — Bootstraps ALL listed skills ins Live-Dashboard
#
# Feuert für jeden der 6 Skills einen Snapshot-Update. Nützlich bei:
#   • Demo / Initial-State des Dashboards
#   • Re-Init nach Server-Restart (Skills aus registry.jsonl wiederhergestellt)
#   • Smoke-Tests
#
# Reihenfolge folgt der User-Activations-Reihenfolge:
#   goal-chain → skill-chains → dbs-goal → routers → patterns
#
# Usage:
#   bash activate-all-skills.sh              # smoke-test
#   bash activate-all-skills.sh --reset      # clear registry first
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
cd "$ROOT"

UPD="$SCRIPT_DIR/skills-updaters"

if [[ "${1:-}" == "--reset" ]]; then
    rm -f .agents/skills/live/*.md .agents/skills/live/registry.jsonl
    echo "🔄 Registry reset."
fi

echo "═══════════════════════════════════════════════════════════════"
echo "  ⚡ BOOTSTRAP: 6 Skills als UPDATER + Context-Artefakt"
echo "═══════════════════════════════════════════════════════════════"

bash "$UPD/updater-goal-chain.sh"                  active "TID-Kaskade P1→P4 vorbereitet" "" P1 planning
bash "$UPD/updater-skill-chains.sh"               active "Stack-Matrix geladen — AUTONOM/GOVERNANCE/EVIL_TWIN" "" AUTONOM GOVERNANCE EVIL_TWIN
bash "$UPD/updater-dbs-goal.sh"                   done   "Zielkarte erstellt & freigegeben" "" GOAL AUDIT
bash "$UPD/updater-cloud-platforms-router.sh"     planning "Vercel/Next.js Sub-Skill ermittelt" "" ROUTING Vercel Nextjs
bash "$UPD/updater-nodejs-backend-patterns.sh"    idle   "Express+TS Middleware-Patterns geladen" "" Node Express MIDDLEWARE
bash "$UPD/updater-ai-ml-router.sh"               idle   "HF/NVIDIA/OpenAI Routing-Decision pending" "" ROUTING HF OpenAI

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ BOOTSTRAP abgeschlossen. Dashboard konsultiert via:"
echo "     bash .agents/skills/live-context.sh --list"
echo "     curl http://127.0.0.1:4200/api/skills    (SSE-Server)"
echo "═══════════════════════════════════════════════════════════════"
