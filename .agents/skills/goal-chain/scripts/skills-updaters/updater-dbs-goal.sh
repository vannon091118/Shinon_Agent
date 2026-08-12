#!/bin/bash
# updater-dbs-goal.sh — dbs-goal als UPDATER + Context-Artifact
# State: done nach Zielkarte; planning während Audit
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
cd "$ROOT"

DEFAULT_STATE="${1:-done}"
DEFAULT_SUMMARY="${2:-Zielkarte erstellt & freigegeben}"
DEFAULT_OUTPUT="${3:-}"
shift 3 2>/dev/null || shift $#

bash .agents/skills/live-snapshot.sh \
    "dbs-goal" "$DEFAULT_STATE" "$DEFAULT_SUMMARY" "$DEFAULT_OUTPUT" \
    $(echo "$@" | tr ' ' ',')
