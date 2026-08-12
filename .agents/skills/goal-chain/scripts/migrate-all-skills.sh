#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# migrate-all-skills.sh — Bulk-Migration ALLER SKILL.md → Live-Snapshots
#
# Scannt rekursiv `.agents/skills/**/SKILL.md` und registriert JEDEN Skill
# als live-snapshot. State default: 'idle' (verfügbar, noch nicht aktiv).
# Existierende Snapshots werden NICHT überschrieben wenn --force fehlt —
# stattdessen wird das Frontmatter aktualisiert (neue Skill-Discovery).
#
# Usage:
#   bash migrate-all-skills.sh                       # nur neue
#   bash migrate-all-skills.sh --force               # alle neu schreiben
#   bash migrate-all-skills.sh --root=PATH          # anderes Wurzelverzeichnis
#   bash migrate-all-skills.sh --tag=ROUTING        # zusätzliche Tags
#
# Output:
#   - .agents/skills/live/<skill>.md (compact snapshot)
#   - .agents/skills/live/registry.jsonl (append audit)
#   - stdout: Anzahl + Liste der migrierten Skills
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
cd "$ROOT"

FORCE=false
SCAN_ROOT=".agents/skills"
EXTRA_TAGS=""
EXCLUDE_REGEX='/(node_modules|__pycache__|\.git)/'

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force)     FORCE=true ; shift ;;
        --root=*)    SCAN_ROOT="${1#--root=}" ; shift ;;
        --tag=*)     EXTRA_TAGS="${1#--tag=}" ; shift ;;
        --exclude=*) EXCLUDE_REGEX="${1#--exclude=}" ; shift ;;
        *) echo "Unknown arg: $1" >&2 ; exit 1 ;;
    esac
done

SNAP_TOOL="$ROOT/.agents/skills/live-snapshot.sh"
[[ ! -x "$SNAP_TOOL" ]] && { echo "❌ Missing $SNAP_TOOL" >&2; exit 1; }

# ─── Discover ALL SKILL.md files ─────────────────────────────────
mapfile -t SKILL_FILES < <(
    find "$SCAN_ROOT" -type f -name SKILL.md \
        -not -path "*/node_modules/*" \
        -not -path "*/__pycache__/*" \
        -not -path "*/.git/*" \
        2>/dev/null | sort
)

TOTAL=${#SKILL_FILES[@]}
[[ $TOTAL -eq 0 ]] && { echo "⚠️  No SKILL.md files found under $SCAN_ROOT" >&2; exit 0; }

echo "═══════════════════════════════════════════════════════════════"
echo "  🔍 Found $TOTAL SKILL.md files under $SCAN_ROOT"
echo "═══════════════════════════════════════════════════════════════"

MIGRATED=0
SKIPPED=0
FAILED=0
DIR_LIST=()

for sf in "${SKILL_FILES[@]}"; do
    # Skill-Name = letzte Verzeichniskomponente VOR SKILL.md
    skill_dir="$(dirname "$sf")"
    skill="$(basename "$skill_dir")"
    # Wenn Parent-Dir == "skills" oder Router-Name, prefer die letzte Komponente;
    # sonst nimm den vollen Relativpfad (für Doppelnamen wie communication/google-calendar/google-calendar)
    parent="$(basename "$(dirname "$skill_dir")")"
    if [[ "$parent" == "skills" || "$parent" == "$skill" ]]; then
        # Default-Naming
        skill_id="$skill"
    else
        # Sub-Skill (z.B. teams-messages unter communication/teams)
        skill_id="$skill"
        # Falls Name-Duplikat, ergänze Parent
        if [[ -f ".agents/skills/live/${skill_id}.md" ]]; then
            # Check ob schon migriert aus anderem Pfad
            existing_path="$(grep -oP 'output_path: "\K[^"]+' ".agents/skills/live/${skill_id}.md" 2>/dev/null || echo "")"
            if [[ -n "$existing_path" && "$existing_path" != "$sf" ]]; then
                skill_id="${parent}-${skill}"
            fi
        fi
    fi

    snap=".agents/skills/live/${skill_id}.md"

    # Frontmatter aus SKILL.md extrahieren (YAML zwischen --- ... ---)
    summary=""
    description=""
    version=""
    stack=""
    category=""
    in_fm=false
    fm_done=false
    while IFS= read -r line; do
        if [[ "$fm_done" == false ]]; then
            if [[ "$line" == "---" && "$in_fm" == true ]]; then
                fm_done=true
                continue
            fi
            if [[ "$line" == "---" ]]; then
                in_fm=true
                continue
            fi
            [[ "$in_fm" == true ]] && {
                key="${line%%:*}"
                val="${line#*:}"
                val="${val# }" ; val="${val% }"
                case "$key" in
                    name)        name_val="$val"        ;;
                    description) description="$val"     ;;
                    version)     version="$val"         ;;
                    stack)       stack="$val"           ;;
                    category)    category="$val"        ;;
                esac
            }
        elif [[ "$summary" == "" && -n "$line" && ! "$line" =~ ^# ]]; then
            summary="$line"
        fi
    done < "$sf"

    # Summary = description || summary || erstes Body-Statement
    short_summary="${description:-$summary}"
    short_summary="${short_summary:0:180}"

    TAGS="catalog,$EXTRA_TAGS"
    [[ -n "$stack" ]]   && TAGS="$TAGS,${stack// /_}"
    [[ -n "$category" ]] && TAGS="$TAGS,${category// /_}"
    [[ -n "$version" ]]  && TAGS="$TAGS,v${version}"

    # Skip wenn schon vorhanden + --force nicht gegeben
    if [[ -f "$snap" && "$FORCE" != true ]]; then
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # Direkt update output_path durch Aufruf von live-snapshot.sh
    if bash "$SNAP_TOOL" "$skill_id" idle "$short_summary" "$sf" \
        $EXTRA_TAGS catalog 2>/dev/null; then
        MIGRATED=$((MIGRATED + 1))
    else
        FAILED=$((FAILED + 1))
        echo "   ⚠️  failed: $sf"
    fi
done

# ─── Summary ─────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ Migration complete"
echo "═══════════════════════════════════════════════════════════════"
echo "   Total found:     $TOTAL"
echo "   Newly migrated:  $MIGRATED"
echo "   Skipped:         $SKIPPED"
echo "   Failed:          $FAILED"
echo "   Snapshot dir:    .agents/skills/live/"
echo ""
echo "   List all:        bash .agents/skills/live-context.sh --list"
echo "   Reset all:       bash .agents/skills/goal-chain/scripts/activate-all-skills.sh --reset"
echo "═══════════════════════════════════════════════════════════════"
