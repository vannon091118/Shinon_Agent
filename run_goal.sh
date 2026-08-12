#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# run_goal.sh — /goal "ZIEL" Entry-Point
# WRAPPER für das TID-basierte Dispatch-System.
#
# Alle Phasen-Scripts liegen in:
#   .agents/skills/goal-chain/scripts/
#
# Der Agent MUSS die Scripts ausführen, NICHT verändern.
# Jedes Script managed State via TID in der globalen SQLite-DB.
#
# Usage:
#   ./run_goal.sh "Baue eine User-Authentifizierung mit OAuth2"
#   ./run_goal.sh --status [RUN_ID]
#   ./run_goal.sh --list
#   ./run_goal.sh --verify RUN_ID
#
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

DISPATCH_SCRIPT=".agents/skills/goal-chain/scripts/dispatch.sh"
VERIFY_SCRIPT=".agents/skills/goal-chain/scripts/verify-state.sh"

if [[ "${1:-}" == "--status" ]]; then
    bash "$DISPATCH_SCRIPT" --status "${2:-}"
    exit $?
fi

if [[ "${1:-}" == "--list" ]]; then
    bash "$DISPATCH_SCRIPT" --list
    exit $?
fi

if [[ "${1:-}" == "--verify" ]]; then
    bash "$VERIFY_SCRIPT" "${2:?Missing RUN_ID}"
    exit $?
fi

if [[ "${1:-}" == "--init-db" ]]; then
    bash .agents/skills/goal-chain/scripts/db-init.sh
    exit $?
fi

GOAL="${1:-}"
if [[ -z "${GOAL// }" ]]; then
    cat <<'USAGEEOF'
╔══════════════════════════════════════════════════════════╗
║  /goal — TID-basierte Autonome Entwicklungskaskade     ║
║  👯 Evil Twin Protocol · Script-Pflicht · TID-State-DB  ║
║                                                        ║
║  Usage:                                                ║
║    ./run_goal.sh 'ZIEL'                                ║
║    ./run_goal.sh --status [RUN_ID]                     ║
║    ./run_goal.sh --list                                ║
║    ./run_goal.sh --verify RUN_ID                       ║
║    ./run_goal.sh --init-db                             ║
║                                                        ║
║  TID-System:                                           ║
║    20 TIDs · 4 Phasen · 2 Gates · 7 Evil Twins         ║
║    DB: .agents/skills/goal-chain/db/tid-state.db       ║
║    Scripts: .agents/skills/goal-chain/scripts/         ║
╚══════════════════════════════════════════════════════════╝
USAGEEOF
    exit 0
fi

PROJEKT="${2:-PZ}"

# Ensure DB exists
if [[ ! -f ".agents/skills/goal-chain/db/tid-state.db" ]]; then
    echo "⚠️  TID-Datenbank nicht initialisiert."
    echo "   Führe aus: ./run_goal.sh --init-db"
    echo ""
    read -r -p "Jetzt initialisieren? [J/n] " confirm
    if [[ ! "$confirm" =~ ^[nN] ]]; then
        bash .agents/skills/goal-chain/scripts/db-init.sh
    else
        exit 1
    fi
fi

# Delegate to dispatch system
bash "$DISPATCH_SCRIPT" "$GOAL" "$PROJEKT"
