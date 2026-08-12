#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# live-snapshot.sh — Generic skill-updater + token-saving artifact writer
#
# JEDER Skill ruft dieses Script beim Activation-Event auf. Output ist
# ein ~20-Zeilen Markdown-Snapshot (.agents/skills/live/<skill>.md) statt
# des vollen SKILL.md (~200-400 Zeilen). DUAL-ROLLE:
#   1. UPDATER    — schreibt Live-State ins Dashboard
#   2. ARTIFACT   — bei Re-Activation liest der Orchestrator nur diesen
#                   Snapshot (~95% Tokenersparnis ggü. voller SKILL.md)
#
# Usage:
#   bash live-snapshot.sh <skill_name> <state> <summary> [output_path] [tags...]
#
# States: active | idle | done | error | planning
#
# Examples:
#   bash live-snapshot.sh goal-chain active "Phase 1 läuft" \
#       .goal/R20260811-x/P1-design.md "P1,brainstorming"
#   bash live-snapshot.sh dbs-goal done "Zielkarte bestätigt" "" "GOAL"
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

SKILL="${1:?Usage: live-snapshot.sh <skill> <state> <summary> [out] [tags...]}"
STATE="${2:?Missing state}"
SUMMARY="${3:?Missing summary}"
OUTPUT="${4:-}"
# Tags: comma-joined remaining args (5..N). Empty if none passed.
TAGS=""
if [[ $# -ge 5 ]]; then
    TAGS=$(printf '%s,' "${@:5}")
    TAGS="${TAGS%,}"  # strip trailing comma
fi

LIVE_DIR=".agents/skills/live"
SNAPSHOT="$LIVE_DIR/${SKILL}.md"
REGISTRY="$LIVE_DIR/registry.jsonl"

mkdir -p "$LIVE_DIR"

# ─── Helpers ───────────────────────────────────────────────────────
iso()  { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
ts()   { date +"%H:%M:%S"; }
slug() { echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/-/g' | head -c40; }

# ─── State icon mapping ────────────────────────────────────────────
case "$STATE" in
    active)    ICON="🔄" ; COLOR="var(--accent)"  ;;
    idle)      ICON="⏸️ " ; COLOR="var(--muted)"   ;;
    done)      ICON="✅" ; COLOR="var(--success)" ;;
    error)     ICON="❌" ; COLOR="var(--danger)"  ;;
    planning)  ICON="🧠" ; COLOR="var(--warn)"    ;;
    *)         ICON="⏳" ; COLOR="var(--muted)"   ;;
esac

# ─── Read previous run count (if any) ─────────────────────────────
PREV_COUNT=0
if [[ -f "$SNAPSHOT" ]]; then
    PREV_COUNT=$(grep -oP 'activation_count:\s*\K\d+' "$SNAPSHOT" | head -1 || echo 0)
    PREV_COUNT="${PREV_COUNT:-0}"
fi
NEW_COUNT=$((PREV_COUNT + 1))

# ─── Truncate summary to 200 chars ─────────────────────────────────
SHORT_SUMMARY="${SUMMARY:0:200}"

# ─── Write snapshot (compact, token-sparend) ──────────────────────
cat > "$SNAPSHOT" <<EOF
---
skill: ${SKILL}
state: ${STATE}
last_activation: $(iso)
activation_count: ${NEW_COUNT}
tags: [${TAGS}]
output_path: "${OUTPUT}"
---

# ${ICON} ${SKILL} · ${STATE^^}

> **Token-saving artifact.** Dieser ~20-Zeilen-Snapshot ersetzt das vollständige
> SKILL.md (~200-400 Zeilen) bei Re-Activation. Re-Aktivierungen lesen NUR
> diesen Snapshot, sofern keine erweiterte Funktionalität benötigt wird.

## Aktueller Status
${SHORT_SUMMARY}

## Pfad zum Output
${OUTPUT:-_kein Output-File_}

## Re-Aktivierung (schnell)
\`\`\`bash
bash .agents/skills/live-context.sh ${SKILL}   # holt diesen Snapshot
# Falls mehr Details nötig:  cat .agents/skills/${SKILL}/SKILL.md
\`\`\`

EOF

# ─── Append to audit registry (proper JSON) ──────────────────────
TAG_JSON=$(python3 -c "
import json, sys
raw = '${TAGS}'.strip()
tags = [t.strip() for t in raw.split(',') if t.strip()] if raw else []
print(json.dumps(tags))
")
printf '{"ts":"%s","skill":"%s","state":"%s","tags":%s,"count":%d}\n' \
    "$(iso)" "$SKILL" "$STATE" "$TAG_JSON" "$NEW_COUNT" >> "$REGISTRY"

echo "[$(ts)] live-snapshot: ${SKILL} → ${STATE} (count=${NEW_COUNT}) → ${SNAPSHOT}"
