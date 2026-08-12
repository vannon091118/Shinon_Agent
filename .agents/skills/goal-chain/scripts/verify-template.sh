#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# verify-template.sh — DRIFT DETECTION (v2: + Live-Snapshot-Scan)
# Verifiziert Output-Dateien gegen Template-Marker in der DB.
# Verhindert dass das Model "driftet" — Struktur muss exakt sein.
#
# Usage:
#   bash verify-template.sh TID OUTPUT_FILE              # Einzel-Check
#   bash verify-template.sh TID OUTPUT_FILE --explain    # mit Details
#   bash verify-template.sh --scan-live                  # alle 658 Snapshots
#   bash verify-template.sh --scan-live --explain        # mit Details
#   bash verify-template.sh --scan-live --json           # maschinenlesbar
#   bash verify-template.sh --scan-live --summary        # nur Summary
#
# Exit codes:
#   0 = PASS (kein Drift)
#   1 = FAIL mit Details (Drift entdeckt)
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

MODE="${1:-}"

# ─── Global-Scan Mode — alle Live-Snapshots prüfen ────────────────
if [[ "$MODE" == "--scan-live" ]]; then
    EXPLAIN=false
    JSON_OUT=false
    SUMMARY_ONLY=false
    for arg in "${@:2}"; do
        case "$arg" in
            --explain) EXPLAIN=true ;;
            --json)    JSON_OUT=true ;;
            --summary) SUMMARY_ONLY=true ;;
        esac
    done

    LIVE_DIR=".agents/skills/live"
    [[ ! -d "$LIVE_DIR" ]] && { echo "❌ $LIVE_DIR not found"; exit 1; }

    TOTAL=0
    CLEAN=0
    DIRTY=0
    DIRTY_FILES=()
    DIRTY_PLACEHOLDERS=()

    if $JSON_OUT; then
        python3 << 'PYEOF'
import os, re, json
live_dir = ".agents/skills/live"
total = 0
clean = 0
dirty = 0
results = []
for fname in sorted(os.listdir(live_dir)):
    if not fname.endswith(".md"): continue
    total += 1
    with open(os.path.join(live_dir, fname)) as f:
        text = f.read()
    # Exclude CSS blocks (they contain {{ ... }} legitimately)
    # Only look for {{UPPER}} patterns that aren't in CSS
    body = re.sub(r'\{\{[^{}]*\}\}', '', text)  # Remove ALL triple-brace patterns
    # Re-scan in original text
    found = re.findall(r'\{\{[A-Z_][A-Z_ ]+\}\}', text)
    # Filter out CSS variables: {{ var(--xxx) }}
    real_placeholders = [p for p in found if 'var(--' not in p and not p.startswith('{{ 0%')]
    if real_placeholders:
        dirty += 1
        skill = fname.replace('.md', '')
        results.append({"skill": skill, "placeholders": list(set(real_placeholders)), "file": f"{live_dir}/{fname}"})
    else:
        clean += 1
output = {
    "scan_type": "live-snapshot-placeholder-scan",
    "directory": live_dir,
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "summary": {"total": total, "clean": clean, "dirty": dirty, "dirty_pct": round(dirty/total*100,1) if total else 0},
    "dirty_skills": results
}
print(json.dumps(output, indent=2, ensure_ascii=False))
PYEOF
        exit 0
    fi

    if $SUMMARY_ONLY; then
        # Lightweight: just count
        python3 << PYEOF
import os, re
live_dir = ".agents/skills/live"
total = 0
clean = 0
dirty = 0
dirty_names = []
for fname in sorted(os.listdir(live_dir)):
    if not fname.endswith(".md"): continue
    total += 1
    with open(os.path.join(live_dir, fname)) as f:
        text = f.read()
    found = re.findall(r'\{\{[A-Z_][A-Z_ ]+\}\}', text)
    real = [p for p in found if 'var(--' not in p]
    if real:
        dirty += 1
        dirty_names.append(fname.replace('.md', ''))
    else:
        clean += 1
print(f"Total: {total}  Clean: {clean}  Dirty: {dirty}  ({round(dirty/total*100,1) if total else 0}%)")
if dirty:
    print(f"Dirty: {', '.join(dirty_names[:10])}{'...' if len(dirty_names)>10 else ''}")
PYEOF
        exit 0
    fi

    # Full scan with optional --explain
    echo "═══════════════════════════════════════════════════════════════"
    echo "  🔍 GLOBAL PLACEHOLDER SCAN — $LIVE_DIR"
    echo "═══════════════════════════════════════════════════════════════"

    # Run Python scan, capture summary line to determine dirty count
    SCAN_OUTPUT=$(python3 << PYEOF
import os, re
live_dir = ".agents/skills/live"
total = 0; clean = 0; dirty = 0
for fname in sorted(os.listdir(live_dir)):
    if not fname.endswith(".md"): continue
    total += 1
    with open(os.path.join(live_dir, fname)) as f:
        text = f.read()
    found = re.findall(r'\{\{[A-Z_][A-Z_ ]+\}\}', text)
    real = [p for p in found if 'var(--' not in p and not p.startswith('{{ 0%')]
    if real:
        dirty += 1
        unique = list(set(real))
        print(f"  ❌ {fname.replace('.md','')}: {', '.join(unique)}")
        if "$EXPLAIN" == "true":
            for p in unique:
                print(f"      → {p}")
    else:
        clean += 1
print(f"")
print(f"  📊 Total: {total}  ✅ Clean: {clean}  ❌ Dirty: {dirty}  ({round(dirty/total*100,1) if total else 0}%)")
# Also emit the dirty count as last line for bash capture
exit(dirty)
PYEOF
)
    DIRTY_EXIT=$?
    echo "$SCAN_OUTPUT"
    if [[ $DIRTY_EXIT -gt 0 ]]; then exit 1; else exit 0; fi
fi

# ─── Normal Mode — single TID verification ───────────────────────────
TID="${1:?Usage: bash verify-template.sh TID OUTPUT_FILE}"
OUTPUT_FILE="${2:?}"
EXPLAIN=false
[[ "${3:-}" == "--explain" ]] && EXPLAIN=true

ensure_db

# Load template_id for TID
TEMPLATE_ID=$(task_field "$TID" "template_id")

# If no template defined, skip (free-form output)
if [[ -z "$TEMPLATE_ID" || "$TEMPLATE_ID" == "None" || "$TEMPLATE_ID" == "null" ]]; then
    echo "  ℹ️  TID '$TID' hat kein Template-Spec → minimaler Check nur"
    if [[ -f "$OUTPUT_FILE" ]]; then
        echo "  ✅ Datei existiert: $OUTPUT_FILE"
        exit 0
    else
        echo "  ❌ Datei fehlt: $OUTPUT_FILE"
        exit 1
    fi
fi

# Check file exists
if [[ ! -f "$OUTPUT_FILE" ]]; then
    echo "❌ DRIFT DETECTED"
    echo "  Datei fehlt: $OUTPUT_FILE"
    exit 1
fi

# Load markers via Python (since we use complex query)
# NOTE: Uses ASCII Unit Separator (\x1f) as field delimiter to avoid
# conflicts with regex patterns containing | characters (e.g. ^(PASS|FAIL)$).
MARKERS=$(python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()
rows = cur.execute(
    'SELECT marker_type, pattern, severity, description FROM template_markers WHERE template_id=?',
    ('$TEMPLATE_ID',)
).fetchall()
for mtype, pattern, severity, desc in rows:
    print(f'{mtype}\x1f{pattern}\x1f{severity}\x1f{desc}')
conn.close()
" 2>/dev/null)

if [[ -z "$MARKERS" ]]; then
    echo "  ⚠️  Template '$TEMPLATE_ID' hat keine Marker in DB. Template-Datei fehlt?"
    echo "  Datei existiert: $OUTPUT_FILE — PRÜFE INHALT MANUELL"
    exit 0
fi

ERRORS=0
WARNINGS=0
DETAILS=""

while IFS=$'\x1f' read -r mtype pattern severity desc; do
    [[ -z "$pattern" ]] && continue

    case "$mtype" in
        SECTION_HEADER)
            # Pattern should match start of a line: ^# Section
            if grep -qE "$pattern" "$OUTPUT_FILE"; then
                echo "  ✅ $desc"
            else
                [[ "$severity" == "WARNING" ]] && WARNINGS=$((WARNINGS+1)) || ERRORS=$((ERRORS+1))
                DETAILS="${DETAILS}❌ MISSING: $desc (pattern: $pattern)"$'\n'
            fi
            ;;
        MARKER_LINE)
            # Bugfix (P0-3): grep -E statt grep -F + sed-escaping.
            # Pattern in DB sind Regex (z.B. ^(PASS|FAIL)$).
            # grep -F + sed-escaping suchte nach literalem Escape-Text → nie Match.
            if grep -qE "$pattern" "$OUTPUT_FILE"; then
                echo "  ✅ $desc"
            else
                [[ "$severity" == "WARNING" ]] && WARNINGS=$((WARNINGS+1)) || ERRORS=$((ERRORS+1))
                DETAILS="${DETAILS}❌ MISSING MARKER: $pattern"$'\n'
            fi
            ;;
        REQUIRED_FILE)
            # Pattern is filepath that must exist relative to output dir
            DIR=$(dirname "$OUTPUT_FILE")
            if [[ -f "$DIR/$pattern" ]]; then
                echo "  ✅ Required file: $pattern"
            else
                ERRORS=$((ERRORS+1))
                DETAILS="${DETAILS}❌ MISSING FILE: $pattern (sollte in $(basename "$DIR")/)"$'\n'
            fi
            ;;
        TAG_PATTERN)
            # {{...}} placeholder must not remain (anti-drift)
            if grep -qE '\{\{[^}]+\}\}' "$OUTPUT_FILE"; then
                ERRORS=$((ERRORS+1))
                PLACEHOLDERS=$(grep -oE '\{\{[^}]+\}\}' "$OUTPUT_FILE" | sort -u | tr '\n' ' ')
                DETAILS="${DETAILS}❌ UNFILLED PLACEHOLDERS: $PLACEHOLDERS"$'\n'
            else
                echo "  ✅ Alle {{PLACEHOLDER}} ersetzt"
            fi
            ;;
    esac
done <<< "$MARKERS"

echo ""
if [[ $ERRORS -gt 0 ]]; then
    echo "❌ DRIFT DETECTED ($ERRORS errors, $WARNINGS warnings)"
    echo "   Template: $TEMPLATE_ID"
    echo "   Output:   $OUTPUT_FILE"
    if $EXPLAIN; then
        echo ""
        echo "─────────────────────────────────── DRIFT DETAILS ───────────────────────────────────"
        echo "$DETAILS"
        echo "──────────────────────────────────────────────────────────────────────────────────────"
    fi
    exit 1
fi

if [[ $WARNINGS -gt 0 ]]; then
    echo "⚠️  PASS with $WARNINGS warnings"
    exit 0
fi

echo "✅ DRIFT-FREE — TID $TID output conforms to template '$TEMPLATE_ID'"
exit 0
