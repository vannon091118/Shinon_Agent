#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# ctl — Linux/macOS shim for `python ctl.py`
#
# DEPRECATED in v1.0 — cross-platform lifecycle manager lives in
# `ctl.py` (uses Python sockets for port detection, not lsof).
# This 5-line wrapper preserves the `./ctl start|stop|status|...` UX.
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
    exec python3 "$SCRIPT_DIR/ctl.py" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "$SCRIPT_DIR/ctl.py" "$@"
else
    echo "[FAIL] Python 3.11+ nicht gefunden." >&2
    exit 1
fi
