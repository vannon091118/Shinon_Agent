#!/bin/bash
# updater-cloud-platforms-router.sh — cloud-platforms-router als UPDATER
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
cd "$ROOT"

DEFAULT_STATE="${1:-planning}"
DEFAULT_SUMMARY="${2:-Wählt Vercel/Render/Netlify/Cloudflare Sub-Skill}"
DEFAULT_OUTPUT="${3:-}"
shift 3 2>/dev/null || shift $#

bash .agents/skills/live-snapshot.sh \
    "cloud-platforms-router" "$DEFAULT_STATE" "$DEFAULT_SUMMARY" "$DEFAULT_OUTPUT" \
    $(echo "$@" | tr ' ' ',')
