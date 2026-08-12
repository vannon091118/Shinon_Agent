#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# live-context.sh — Token-saving context artifact CONSUMER
#
# Statt das volle SKILL.md zu laden (~200-400 Zeilen), liest dieses
# Script nur den kompakten Live-Snapshot (~25 Zeilen). ~85% Tokenersparnis
# pro Re-Aktivierung.
#
# Usage:
#   bash live-context.sh <skill>               # gibt Snapshot aus
#   bash live-context.sh <skill> --full        # zusätzlich volle SKILL.md
#   bash live-context.sh <skill> --json        # maschinenlesbar
#   bash live-context.sh --list                # alle aktiven Skills
#
# Examples:
#   bash live-context.sh goal-chain
#   bash live-context.sh dbs-goal --json
#   bash live-context.sh --list
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

LIVE_DIR=".agents/skills/live"

usage() {
    cat <<USAGE
Usage:
  bash live-context.sh <skill>      [Options]
  bash live-context.sh --list

Options:
  --full      Include full SKILL.md after compact snapshot
  --json      Machine-readable JSON summary
  --count     Just the activation count
  --tags      Just the tags
USAGE
}

# ─── List Mode ─────────────────────────────────────────────────────
if [[ "${1:-}" == "--list" ]]; then
    if [[ ! -d "$LIVE_DIR" ]]; then
        echo "No live directory at $LIVE_DIR"
        exit 0
    fi
    echo "═══════════════════════════════════════════════════════════════"
    echo "  ACTIVE SKILL REGISTRY — Live Snapshots @ $(date +%H:%M:%S)"
    echo "═══════════════════════════════════════════════════════════════"
    for f in "$LIVE_DIR"/*.md; do
        [[ -f "$f" ]] || continue
        skill=$(basename "$f" .md)
        state=$(grep -oP 'state:\s*\K\S+' "$f" | head -1)
        count=$(grep -oP 'activation_count:\s*\K\d+' "$f" | head -1)
        last=$(grep -oP 'last_activation:\s*\K\S+' "$f" | head -1)
        case "$state" in
            active)       icon="🔄" ;;
            done)         icon="✅" ;;
            error)        icon="❌" ;;
            idle)         icon="⏸️ " ;;
            planning)     icon="🧠" ;;
            *)            icon="⏳" ;;
        esac
        printf "  %s  %-25s %-10s count=%-3d last=%s\n" \
               "$icon" "$skill" "$state" "${count:-0}" "${last:11:8}"
    done
    echo "═══════════════════════════════════════════════════════════════"
    exit 0
fi

SKILL="${1:-}"
[[ -z "$SKILL" ]] && { usage; exit 1; }

SNAPSHOT="$LIVE_DIR/${SKILL}.md"
SKILL_FULL=".agents/skills/${SKILL}/SKILL.md"

if [[ ! -f "$SNAPSHOT" ]]; then
    echo "❌ No live snapshot for skill '$SKILL'" >&2
    echo "   Expected: $SNAPSHOT" >&2
    echo "" >&2
    echo "   Run: bash .agents/skills/live-snapshot.sh $SKILL active '<summary>'" >&2
    exit 1
fi

# ─── Output Modes ─────────────────────────────────────────────────
shift || true
MODE="${1:-}"

case "$MODE" in
    --full)
        echo "════ COMPACT SNAPSHOT (~25 lines · token-saving) ════"
        cat "$SNAPSHOT"
        echo ""
        echo "════ FULL SKILL.md (only if needed) ════"
        if [[ -f "$SKILL_FULL" ]]; then
            cat "$SKILL_FULL"
        else
            echo "(no SKILL.md found for $SKILL)"
        fi
        ;;
    --json)
        python3 -c "
import re, json, sys
text = open('$SNAPSHOT').read()
fm = re.search(r'---\n(.+?)\n---', text, re.DOTALL)
data = {}
if fm:
    for line in fm.group(1).split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            k, v = k.strip(), v.strip().strip('\"')
            if k == 'tags':
                v = [t.strip() for t in v.lstrip('[').rstrip(']').split(',') if t.strip()]
            data[k] = v
print(json.dumps(data, ensure_ascii=False, indent=2))
"
        ;;
    --count)
        grep -oP 'activation_count:\s*\K\d+' "$SNAPSHOT" | head -1
        ;;
    --tags)
        grep -oP 'tags:\s*\K\[.*?\]' "$SNAPSHOT" | head -1
        ;;
    *)
        cat "$SNAPSHOT"
        ;;
esac
