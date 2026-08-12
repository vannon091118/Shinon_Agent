#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# worker.sh — Autonomous TID Executor (--all = fully autonomous)
#
# FINALLY executes PENDING TIDs instead of just tracking them.
# --all: Runs chain scripts, detects AUTONOM vs PROMPT output,
#        auto-completes every TID without manual intervention.
#
# Usage:
#   bash worker.sh RUN_ID              # Process next PENDING TID (interactive)
#   bash worker.sh RUN_ID --all [MAX]  # Process ALL PENDING TIDs autonomously
#   bash worker.sh RUN_ID --complete TID  # Mark TID as done
#   bash worker.sh RUN_ID --status     # Show run progress
#   bash worker.sh RUN_ID --dry-run    # Show what WOULD run
#
# Architecture:
#   worker.sh → find next PENDING TID
#            → bash chain-xxx.sh RUN_ID TID
#            → AUTONOM: chain script wrote output → complete.sh (full drift check)
#            → PROMPT:  chain script emitted prompt → complete.sh + gate
#            → GATE:    always uses complete.sh for phase routing
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

# ── Run directory (from seed_tids.py convention: .goal/RUN_ID-slug)
RUN_DIR=$(find .goal -maxdepth 1 -name "${RUN_ID}-*" -type d 2>/dev/null | head -1)
[[ -z "$RUN_DIR" ]] && RUN_DIR=".goal/${RUN_ID}-default"

# ── Colors ────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

# ── Status ─────────────────────────────────────────────────────────
show_status() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  GOAL-CHAIN WORKER — Run: $RUN_ID"
    echo "═══════════════════════════════════════════════════════════"

    local total done inprog failed pending rcd
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

# ── Complete TID (interactive/manual mode) ──────────────────────────
complete_tid() {
    local tid="$1"
    echo ""
    echo "── Abschluss: $tid ───────────────────────────────────────"

    local output; output=$(task_field "$tid" "output_artifact")
    if [[ -n "$output" && -f "$output" ]]; then
        local size; size=$(stat -c%s "$output" 2>/dev/null || stat -f%z "$output" 2>/dev/null || echo 0)
        if [[ "$size" -gt 50 ]]; then
            echo "  ✅ Output: $output (${size} bytes)"
        else
            echo "  ⚠️  Output zu klein (${size} bytes) — Inhalt prüfen"
        fi
    else
        echo "  ⚠️  Kein Output-File: ${output:-NONE}"
    fi

    bash "$SCRIPT_DIR/complete.sh" "$tid" "DONE" "--auto"
    echo "  ✅ $tid → DONE"

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

# ── Execute Next TID (interactive mode — shows Buffy instructions) ──
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

    if [[ ! -f "$script" ]]; then
        echo ""
        echo "❌ SCRIPT NICHT GEFUNDEN: $script"
        echo "   TID $tid wird als FAILED markiert"
        bash "$SCRIPT_DIR/complete.sh" "$tid" "FAIL" "--auto"
        return 2
    fi

    if [[ -n "$output" ]]; then
        mkdir -p "$(dirname "$output")"
    fi

    echo ""
    echo "── Chain-Script wird ausgeführt ──────────────────────────"
    echo ""

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
        # ROOT CAUSE: Extract error details from chain script output
        local fail_reason="Chain-Script exit=$exit_code"
        local err_tail; err_tail=$(tail -8 "$output.tmp" 2>/dev/null | paste -sd '|' - | head -c 400)
        [[ -n "$err_tail" ]] && fail_reason="Chain-Script exit=$exit_code | $err_tail"
        echo "❌ $fail_reason"
        echo "   TID $tid wird als FAILED markiert"
        record_decision "$tid" "CHAIN_SCRIPT_FAILED" "$fail_reason" "Chain script exited non-zero; output captured for root cause" "" "" || true
        bash "$SCRIPT_DIR/complete.sh" "$tid" "FAIL" "--auto" "$fail_reason"
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

# ── Execute ALL Pending TIDs (AUTONOMOUS) ────────────────────────────
execute_all() {
    local max="${TID_ARG:-100}"
    local count=0
    local done_count=0
    local fail_count=0
    local auto_count=0
    local prompt_count=0

    # Trap: reset IN_PROGRESS TIDs back to PENDING on unexpected exit
    cleanup_in_progress() {
        local stuck; stuck=$(db_query "SELECT tid FROM tasks WHERE run_id='$RUN_ID' AND status='IN_PROGRESS' LIMIT 1;" | head -1)
        if [[ -n "$stuck" ]]; then
            db_exec "UPDATE tasks SET status='PENDING', updated_at=datetime('now') WHERE tid='$stuck';"
            echo "  🧹 Cleanup: $stuck → PENDING (interrupted)" >&2
        fi
    }
    trap cleanup_in_progress EXIT INT TERM

    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  🤖 WORKER --all: AUTONOMER DURCHLAUF                  ║"
    echo "║  Run: $RUN_ID  |  Max: $max TIDs                       ║"
    echo "╚══════════════════════════════════════════════════════════╝"

    while [[ $count -lt $max ]]; do
        local tid; tid=$(next_pending_tid "$RUN_ID")
        if [[ -z "$tid" ]]; then
            break
        fi

        count=$((count + 1))

        # Get TID details
        local script; script=$(script_for_tid "$tid")
        local skill; skill=$(task_field "$tid" "skill_name")
        local output; output=$(task_field "$tid" "output_artifact")
        local phase; phase=$(task_field "$tid" "phase")
        local section; section=$(task_field "$tid" "phase_section")
        local goal; goal=$(task_field "$tid" "goal")

        # Normalize output (DB may store Python None as "None")
        [[ "$output" == "None" ]] && output=""

        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  WORKER #$count: ${CYAN}${tid}${NC}"
        echo "  Phase: $phase · $section | Skill: $skill"
        echo "  Goal:  ${goal:0:70}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # Check if script exists
        if [[ ! -f "$script" ]]; then
            echo "  ❌ SCRIPT NICHT GEFUNDEN: $script → FAILED"
            record_decision "$tid" "SCRIPT_NOT_FOUND" "$script" "Chain script file does not exist" "" "" || true
            bash "$SCRIPT_DIR/complete.sh" "$tid" "FAIL" "--auto" "Script not found: $script" > /dev/null 2>&1 || true
            fail_count=$((fail_count + 1))
            continue
        fi

        # Resolve output path (may not exist yet)
        local resolved_output=""
        local output_existed_before=false
        if [[ -n "$output" ]]; then
            if [[ -f "$PROJECT_ROOT/$output" ]]; then
                resolved_output="$PROJECT_ROOT/$output"
                output_existed_before=true
            elif [[ -f "$output" ]]; then
                resolved_output="$output"
                output_existed_before=true
            else
                resolved_output="$PROJECT_ROOT/$output"
            fi
            mkdir -p "$(dirname "$resolved_output")" 2>/dev/null || true
        fi

        # Record mtime BEFORE running script
        local output_mtime_before=0
        if $output_existed_before; then
            output_mtime_before=$(stat -c%Y "$resolved_output" 2>/dev/null || echo 0)
        fi

        # Run chain script, capture output (ALWAYS capture for root cause analysis)
        local tmp_output="/tmp/worker-${tid}-$$.tmp"
        local exit_code=0
        bash "$script" "$RUN_ID" "$tid" > "$tmp_output" 2>&1 || exit_code=$?

        # Check if chain script CREATED/MODIFIED the output file
        local output_size=0
        local output_is_new=false
        if [[ -n "$resolved_output" && -f "$resolved_output" ]]; then
            output_size=$(stat -c%s "$resolved_output" 2>/dev/null || echo 0)
            if $output_existed_before; then
                local mtime; mtime=$(stat -c%Y "$resolved_output" 2>/dev/null || echo 0)
                [[ "$mtime" -gt "$output_mtime_before" ]] && output_is_new=true
            else
                output_is_new=true
            fi
        fi

        # Gate TIDs (G1-2, G2-3) ALWAYS need complete.sh for routing
        local is_gate=false
        [[ "$phase" == G* ]] && is_gate=true

        # ── Classify and complete ──
        if [[ $exit_code -ne 0 ]]; then
            # ROOT CAUSE: Extract error details from chain script output
            local fail_reason="Chain-Script exit=$exit_code"
            if [[ -f "$tmp_output" && -s "$tmp_output" ]]; then
                local err_tail; err_tail=$(tail -8 "$tmp_output" 2>/dev/null | paste -sd '|' - | head -c 400)
                [[ -n "$err_tail" ]] && fail_reason="Chain-Script exit=$exit_code | $err_tail"
            fi
            echo "  ❌ $fail_reason → FAILED"
            record_decision "$tid" "CHAIN_SCRIPT_FAILED" "$fail_reason" "Chain script exited non-zero; output captured for root cause" "" "" || true
            bash "$SCRIPT_DIR/complete.sh" "$tid" "FAIL" "--auto" "$fail_reason" > /dev/null 2>&1 || true
            fail_count=$((fail_count + 1))

        elif $output_is_new && { [[ "$output_size" -gt 50 ]] || $is_gate; }; then
            # AUTONOM: chain script wrote output file.
            # Gate TIDs always pass (output may be small: "PASS\n# comments\n").
            # Non-gate TIDs require > 50 bytes.
            if $is_gate; then
                echo "  ✅ GATE AUTONOM: $resolved_output (${output_size} bytes) → DONE"
            else
                echo "  ✅ AUTONOM: $resolved_output (${output_size} bytes) → DONE"
                record_decision "$tid" "AUTONOM_OUTPUT" "$resolved_output (${output_size} bytes)" "Chain script wrote output file autonomously" "" "" || true
            fi
            if bash "$SCRIPT_DIR/complete.sh" "$tid" "DONE" "--auto" > /dev/null 2>&1; then
                done_count=$((done_count + 1))
                auto_count=$((auto_count + 1))
            else
                echo "  ❌ AUTONOM completion blocked by FalsificationGate"
                fail_count=$((fail_count + 1))
            fi

        elif [[ -f "$tmp_output" && -s "$tmp_output" ]] && grep -q '[^[:space:]]' "$tmp_output" 2>/dev/null; then
            # PROMPT script: captured output becomes the artifact (must have non-whitespace content)
            local target
            if [[ -n "$output" ]]; then
                target="$resolved_output"
            else
                target="$RUN_DIR/${tid}-output.md"
                mkdir -p "$RUN_DIR" 2>/dev/null || true
            fi
            mv "$tmp_output" "$target"
            output_size=$(stat -c%s "$target" 2>/dev/null || echo 0)

            if $is_gate; then
                # Gate TIDs: use complete.sh for proper phase routing
                echo "  🔀 GATE PROMPT: $target (${output_size} bytes)"
                if bash "$SCRIPT_DIR/complete.sh" "$tid" "DONE" "--auto" > /dev/null 2>&1; then
                    echo "  ✅ → DONE (gate routing applied)"
                    done_count=$((done_count + 1))
                else
                    echo "  ❌ GATE PROMPT completion blocked by FalsificationGate"
                    fail_count=$((fail_count + 1))
                fi
            else
                # Regular PROMPT: it is still an executable completion path.
                # Route through complete.sh so the same FalsificationGate is
                # mandatory; direct tid_done is intentionally not an escape hatch.
                if [[ "$output_size" -gt 50 ]]; then
                    echo "  📋 PROMPT: $target (${output_size} bytes) → gate"
                else
                    echo "  ⚠️  PROMPT: Minimal output (${output_size} bytes) → gate"
                fi
                if bash "$SCRIPT_DIR/complete.sh" "$tid" "DONE" "--auto"; then
                    notify_dashboard "TID_DONE" "$tid" "$(progress_summary "$RUN_ID")" || true
                    record_decision "$tid" "PROMPT_CAPTURED" "DONE" "Worker captured chain script output ($output_size bytes) after gate" "" "" || true
                else
                    echo "  ❌ PROMPT completion blocked by FalsificationGate"
                    fail_count=$((fail_count + 1))
                fi
            fi
            prompt_count=$((prompt_count + 1))

        else
            # REGEL 1: Kein Output = NICHTS zu zeigen → FAIL, nicht DONE
            local empty_reason="EMPTY_OUTPUT: chain script produced no output (not stdout, not file)"
            echo "  ❌ $empty_reason → FAILED"
            record_decision "$tid" "EMPTY_OUTPUT" "$empty_reason" "Chain script ran (exit=0) but produced zero output — needs investigation" "" "" || true
            bash "$SCRIPT_DIR/complete.sh" "$tid" "FAIL" "--auto" "$empty_reason" > /dev/null 2>&1 || true
            fail_count=$((fail_count + 1))
        fi

        # Clean up tmp
        rm -f "$tmp_output"
    done

    # ── Summary ──
    local total_done total_all pct
    total_done=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$RUN_ID' AND status='DONE';" | head -1)
    total_all=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$RUN_ID';" | head -1)
    pct=0
    [[ "$total_all" -gt 0 ]] && pct=$(( total_done * 100 / total_all ))

    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  🎉 WORKER --all ABGESCHLOSSEN                         ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    echo "║  In diesem Lauf:                                       ║"
    echo "║    ✅ DONE:     $done_count  (autonom: $auto_count, prompt: $prompt_count)"
    echo "║    ❌ FAILED:   $fail_count"
    echo "║                                                        ║"
    echo "║  Gesamt: $total_done/$total_all TIDs (${pct}%)"
    echo "╚══════════════════════════════════════════════════════════╝"

    if [[ "$count" -ge "$max" ]]; then
        echo "  ⚠️  Max $max TIDs erreicht — Rest manuell:"
        echo "      bash worker.sh $RUN_ID --all"
    fi

    [[ "$done_count" -gt 0 ]] && return 0 || return 1
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
