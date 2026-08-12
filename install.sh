#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# install.sh — Linux/macOS shim for `python install.py`
#
# DEPRECATED in v1.0 — full engine lives in `install.py` (cross-platform).
# This 5-line wrapper just ensures the right Python is invoked.
# Every install.py flag and mode passes through via "$@".
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
    exec python3 "$SCRIPT_DIR/install.py" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "$SCRIPT_DIR/install.py" "$@"
else
    echo "[FAIL] Python 3.11+ nicht gefunden." >&2
    echo "       https://www.python.org/downloads/" >&2
    exit 1
fi
