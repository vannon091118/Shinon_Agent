#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# worker.sh — Autonomous TID Executor
#
# FINALLY executes PENDING TIDs instead of just tracking them.
# Runs chain scripts, feeds LLM prompts to Buffy, marks complete.
#
# Usage:
#   bash worker.sh RUN_ID              # Process next PENDING TID
#   bash worker.sh RUN_ID --all        # Process ALL PENDING TIDs
#   bash worker.sh RUN_ID --complete TID  # Mark TID as done
#   bash worker.sh RUN_ID --status     # Show run progress
#   bash worker.sh RUN_ID --dry-run    # Show what WOULD run
#
# Architecture:
#   worker.sh → find next PENDING TID
#            → bash chain-xxx.sh RUN_ID TID  (executes prompt generator)
#            → Buffy reads prompt, does work, writes output_artifact
#            → bash worker.sh RUN_ID --complete TID
#            → repeat until all TIDs DONE
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

RUN_ID="${1:?Usage: bash worker.sh RUN_ID [--all|--complete TID|--status|--dry-run]}"
shift || true
MODE="${1:-next}"
TID_ARG="${2:-}"

ensure_db

# ── Colors ────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

# ── Status ─────────────────────────────────────────────────────────
show_status() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  GOAL-CHAIN WORKER — Run: $RUN_ID"
    echo "═══════════════════════════════════════════════════════════"

    local total done inprog failed pending skipped rcd
    total=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$RUN_ID';" | head -1)
    done=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$RUN_ID' AND status='DONE';" | head -1)
    inprog=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$RUN_ID' AND status='IN_PROGRESS';" | head -1)
    failed=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$RUN_ID' AND status='FAILED';" | head -1)
    pending=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$RUN_ID' AND status='PENDING';" | head -1)
    rcd=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$RUN_ID' AND status='ROOT_CAUSE_DONE';" | head -1)
    local pct=0
    [[ "$total" -gt 0 ]] && pct=$(( (done + rcd) * 100 / total ))

    echo "  ${GREEN}DONE:${NC} $done  ${YELLOW}IN_PROGRESS:${NC} $inprog  ${RED}FAILED:${NC} $failed"
    echo "  PENDING: $pending  ROOT_CAUSE_DONE: $rcd"
    echo "  Progress: $((done + rcd))/$total (${pct}%)"
    echo ""

    # Show next TID
    local next; next=$(next_pending_tid "$RUN_ID")
    if [[ -n "$next" ]]; then
        local phase; phase=$(task_field "$next" "phase")
        local section; section=$(task_field "$next" "phase_section")
        local skill; skill=$(task_field "$next" "skill_name")
        local goal; goal=$(task_field "$next" "goal")
        echo "  ▶ NÄCHSTER TID: ${CYAN}${next}${NC}"
        echo "    Phase: $phase · Section: $section"
        echo "    Skill: $skill"
        echo "    Goal:  ${goal:0:120}"
        echo ""
    else
        echo "  🎉 KEINE PENDING TIDs — Run komplett!"
        echo ""
    fi
}

# ── Dry Run ────────────────────────────────────────────────────────
dry_run() {
    show_status
    local next; next=$(next_pending_tid "$RUN_ID")
    if [[ -z "$next" ]]; then
        echo "  Nichts zu tun."
        return
    fi
    local script; script=$(script_for_tid "$next")
    echo "  WÜRDE ausführen:"
    echo "    TID:     $next"
    echo "    Script:  $script"
    echo "    Command: bash $script $RUN_ID $next"
}

# ── Complete TID ───────────────────────────────────────────────────
complete_tid() {
    local tid="$1"
    echo ""
    echo "── Abschluss: $tid ───────────────────────────────────────"

    # Verify output exists and has content
    local output; output=$(task_field "$tid" "output_artifact")
    local has_real_output=false

    if [[ -n "$output" && -f "$output" ]]; then
        local size; size=$(stat -c%s "$output" 2>/dev/null || stat -f%z "$output" 2>/dev/null || echo 0)
        if [[ "$size" -gt 50 ]]; then
            has_real_output=true
            echo "  ✅ Output: $output (${size} bytes)"
        else
            echo "  ⚠️  Output zu klein (${size} bytes) — Inhalt prüfen"
        fi
    else
        echo "  ⚠️  Kein Output-File: ${output:-NONE}"
    fi

    # Mark complete via complete.sh
    bash "$SCRIPT_DIR/complete.sh" "$tid" "DONE" "--auto"
    echo "  ✅ $tid → DONE"

    # Return next TID for chaining
    local next; next=$(next_pending_tid "$RUN_ID")
    if [[ -n "$next" ]]; then
        echo ""
        echo "────────────────────────────────────────────────────────"
        echo "  ▶ NÄCHSTER: $next"
        echo "────────────────────────────────────────────────────────"
        return 0
    else
        echo ""
        echo "╔══════════════════════════════════════════════════════════╗"
        echo "║  🎉 ALLE TIDs ABGESCHLOSSEN!                           ║"
        echo "║  Run $RUN_ID ist komplett.                              ║"
        echo "╚══════════════════════════════════════════════════════════╝"
        return 1
    fi
}

# ── Execute Next TID ───────────────────────────────────────────────
execute_next() {
    local tid; tid=$(next_pending_tid "$RUN_ID")
    if [[ -z "$tid" ]]; then
        echo ""
        echo "╔══════════════════════════════════════════════════════════╗"
        echo "║  🎉 KEINE PENDING TIDs — Run $RUN_ID komplett!         ║"
        echo "╚══════════════════════════════════════════════════════════╝"
        return 1
    fi

    local script; script=$(script_for_tid "$tid")
    local phase; phase=$(task_field "$tid" "phase")
    local section; section=$(task_field "$tid" "phase_section")
    local skill; skill=$(task_field "$tid" "skill_name")
    local goal; goal=$(task_field "$tid" "goal")
    local output; output=$(task_field "$tid" "output_artifact")
    local template; template=$(task_field "$tid" "template_id")

    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  🤖 WORKER: TID $tid ausführen                     ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    echo "║  Phase:   $phase · $section"
    echo "║  Skill:   $skill"
    echo "║  Goal:    ${goal:0:55}"
    echo "║  Output:  $output"
    echo "║  Script:  $script"
    echo "╚══════════════════════════════════════════════════════════╝"

    # Check if script exists
    if [[ ! -f "$script" ]]; then
        echo ""
        echo "❌ SCRIPT NICHT GEFUNDEN: $script"
        echo "   TID $tid wird als FAILED markiert"
        bash "$SCRIPT_DIR/complete.sh" "$tid" "FAIL" "--auto"
        return 2
    fi

    # Create output directory
    if [[ -n "$output" ]]; then
        mkdir -p "$(dirname "$output")"
    fi

    echo ""
    echo "── Chain-Script wird ausgeführt ──────────────────────────"
    echo ""

    # Execute the chain script and capture its output (the LLM prompt)
    if [[ -n "$output" ]]; then
        bash "$script" "$RUN_ID" "$tid" 2>&1 | tee "$output.tmp"
    else
        bash "$script" "$RUN_ID" "$tid" 2>&1
    fi

    local exit_code=$?

    echo ""
    echo "── Chain-Script beendet (exit=$exit_code) ────────────────"
    echo ""

    if [[ $exit_code -ne 0 ]]; then
        echo "❌ Chain-Script fehlgeschlagen (exit=$exit_code)"
        echo "   TID $tid wird als FAILED markiert"
        bash "$SCRIPT_DIR/complete.sh" "$tid" "FAIL" "--auto"
        return 2
    fi

    echo ""
    echo "────────────────────────────────────────────────────────"
    echo "  📋 JETZT: Buffy führt die Arbeit aus"
    echo ""
    echo "  1. Lies das Chain-Script-Output oben (den LLM-Prompt)"
    echo "  2. Führe die Instruktionen aus"
    echo "  3. Schreibe Output nach: $output"
    echo "  4. Rufe auf: bash worker.sh $RUN_ID --complete $tid"
    echo "────────────────────────────────────────────────────────"
    echo ""

    return 0
}

# ── Execute ALL Pending TIDs ───────────────────────────────────────
execute_all() {
    local max="${TID_ARG:-100}"
    local count=0

    while [[ $count -lt $max ]]; do
        local tid; tid=$(next_pending_tid "$RUN_ID")
        if [[ -z "$tid" ]]; then
            echo ""
            echo "✅ ALLE TIDs abgearbeitet ($count in diesem Lauf)"
            return 0
        fi

        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  WORKER LOOP #$((count + 1)): TID $tid"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        execute_next || {
            local rc=$?
            if [[ $rc -eq 1 ]]; then
                # No more TIDs — success
                return 0
            else
                echo "⚠️  TID $tid fehlgeschlagen, fahre mit nächstem fort..."
            fi
        }

        count=$((count + 1))
    done

    echo "⚠️  Max $max TIDs erreicht — Rest manuell fortsetzen"
}

# ── Main Dispatch ──────────────────────────────────────────────────

case "$MODE" in
    --status|status)
        show_status
        ;;
    --dry-run|dry-run)
        dry_run
        ;;
    --complete|complete)
        complete_tid "${TID_ARG:?TID required for --complete}"
        ;;
    --all|all)
        execute_all
        ;;
    next|--next)
        execute_next
        ;;
    *)
        echo "Usage: bash worker.sh RUN_ID [--all|--complete TID|--status|--dry-run]"
        echo ""
        echo "  RUN_ID              Process next PENDING TID (default)"
        echo "  RUN_ID --all [MAX]  Process all PENDING TIDs (max MAX)"
        echo "  RUN_ID --complete TID  Mark TID as done"
        echo "  RUN_ID --status     Show run progress"
        echo "  RUN_ID --dry-run    Show what WOULD run"
        exit 1
        ;;
esac
