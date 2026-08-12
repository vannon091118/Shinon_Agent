#!/bin/bash
# updater-nodejs-backend-patterns.sh — nodejs-backend-patterns als UPDATER
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
cd "$ROOT"

DEFAULT_STATE="${1:-idle}"
DEFAULT_SUMMARY="${2:-Express/Fastify+TS Patterns geladen}"
DEFAULT_OUTPUT="${3:-}"
shift 3 2>/dev/null || shift $#

bash .agents/skills/live-snapshot.sh \
    "nodejs-backend-patterns" "$DEFAULT_STATE" "$DEFAULT_SUMMARY" "$DEFAULT_OUTPUT" \
    $(echo "$@" | tr ' ' ',')
