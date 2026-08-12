#!/bin/bash
# updater-ai-ml-router.sh — ai-ml-router als UPDATER
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"
cd "$ROOT"

DEFAULT_STATE="${1:-idle}"
DEFAULT_SUMMARY="${2:-HF/NVIDIA/OpenAI Routing geladen}"
DEFAULT_OUTPUT="${3:-}"
shift 3 2>/dev/null || shift $#

bash .agents/skills/live-snapshot.sh \
    "ai-ml-router" "$DEFAULT_STATE" "$DEFAULT_SUMMARY" "$DEFAULT_OUTPUT" \
    $(echo "$@" | tr ' ' ',')
