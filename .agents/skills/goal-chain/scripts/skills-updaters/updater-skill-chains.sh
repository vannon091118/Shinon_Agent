#!/bin/bash
# updater-skill-chains.sh — skill-chains als UPDATER + Context-Artifact
# State: aktiv wenn Stack-Matrix geladen/entschieden wird
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
cd "$ROOT"

DEFAULT_STATE="${1:-active}"
DEFAULT_SUMMARY="${2:-Stack-Matrix geladen: 6 Stacks}"
DEFAULT_OUTPUT="${3:-}"
shift 3 2>/dev/null || shift $#

bash .agents/skills/live-snapshot.sh \
    "skill-chains" "$DEFAULT_STATE" "$DEFAULT_SUMMARY" "$DEFAULT_OUTPUT" \
    $(echo "$@" | tr ' ' ',')
