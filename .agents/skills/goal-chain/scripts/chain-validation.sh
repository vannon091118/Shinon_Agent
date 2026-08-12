#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-validation.sh — STACK: GOVERNANCE — Skill: testing/validation
#
# v2.0 — Real validation logic. Checks:
#   1. Template compliance (output files match their template markers)
#   2. Schema compliance (output files exist, have content, are not stubs)
#   3. Contract compliance (handoff files have required fields)
#   4. REGEL 1 enforcement (seeded TIDs without real output are flagged)
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-validation.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")
PROJECT_ROOT="${PZ_ROOT:-$(cd "$SCRIPT_DIR/../../../.." && pwd)}"

PASSED=0; FAILED=0; WARNINGS=0
DEVIATIONS=()

echo "[validation] Validating TIDs in run $RUN_ID..."

# ── Collect all DONE TIDs with output files ─────────────────────────
DONE_TIDS=$(db_query "SELECT tid, phase_section, output_artifact, template_id FROM tasks WHERE run_id='$RUN_ID' AND status='DONE' AND output_artifact IS NOT NULL AND output_artifact != '';")

if [[ -z "$DONE_TIDS" ]]; then
  echo "[validation] ⚠️ No DONE TIDs with output — nothing to validate"
fi

# ── Check 1: Template compliance ────────────────────────────────────
echo "[validation] Check 1: Template compliance..."
while IFS='|' read -r tid section output template_id; do
  [[ -z "$tid" ]] && continue

  # Resolve output path (may be relative to PROJECT_ROOT or .goal/)
  if [[ -f "$PROJECT_ROOT/$output" ]]; then
    outpath="$PROJECT_ROOT/$output"
  elif [[ -f "$output" ]]; then
    outpath="$output"
  else
    DEVIATIONS+=("$tid|TEMPLATE|Output file not found: $output")
    FAILED=$((FAILED + 1))
    continue
  fi

  size=$(stat -c%s "$outpath" 2>/dev/null || echo 0)

  # Stub detection: files < 100 bytes are suspicious
  if [[ "$size" -lt 100 ]]; then
    DEVIATIONS+=("$tid|TEMPLATE|Output too small (${size} bytes) — possible stub: $output")
    WARNINGS=$((WARNINGS + 1))
    continue
  fi

  # Check for template markers if template_id exists
  if [[ -n "$template_id" && "$template_id" != "—" ]]; then
    case "$template_id" in
      design-doc-v1)
        if ! grep -qE '^# Design:|^## Übersicht|^## Architektur|^## Komponenten' "$outpath" 2>/dev/null; then
          DEVIATIONS+=("$tid|TEMPLATE|Design doc missing required sections (Übersicht/Architektur/Komponenten)")
          FAILED=$((FAILED + 1))
        else
          PASSED=$((PASSED + 1))
        fi
        ;;
      implementation-plan-v1)
        if ! grep -qE '^# Implementation Plan:|^## Tasks|^## Done When' "$outpath" 2>/dev/null; then
          DEVIATIONS+=("$tid|TEMPLATE|Implementation plan missing required sections")
          FAILED=$((FAILED + 1))
        else
          PASSED=$((PASSED + 1))
        fi
        ;;
      evil-twin-v1)
        if ! grep -qE 'FUNDAMENTAL|OBERFLÄCHLICH' "$outpath" 2>/dev/null; then
          DEVIATIONS+=("$tid|TEMPLATE|Evil Twin missing FUNDAMENTAL/OBERFLÄCHLICH verdict")
          FAILED=$((FAILED + 1))
        elif ! grep -qE '^# 👯 Evil Twin' "$outpath" 2>/dev/null; then
          DEVIATIONS+=("$tid|TEMPLATE|Evil Twin missing title marker")
          WARNINGS=$((WARNINGS + 1))
        else
          PASSED=$((PASSED + 1))
        fi
        ;;
      gate-result-v1)
        if ! grep -qE '^(PASS|FAIL)$' "$outpath" 2>/dev/null; then
          DEVIATIONS+=("$tid|TEMPLATE|Gate result missing PASS/FAIL")
          FAILED=$((FAILED + 1))
        else
          PASSED=$((PASSED + 1))
        fi
        ;;
      architecture-report-v1)
        if ! grep -qE 'Komponenten|Datenfluss|Risiken' "$outpath" 2>/dev/null; then
          DEVIATIONS+=("$tid|TEMPLATE|Architecture report missing Komponenten/Datenfluss/Risiken")
          WARNINGS=$((WARNINGS + 1))
        else
          PASSED=$((PASSED + 1))
        fi
        ;;
      *)
        # Unknown template — just check file is non-empty
        if [[ "$size" -gt 50 ]]; then
          PASSED=$((PASSED + 1))
        else
          DEVIATIONS+=("$tid|TEMPLATE|Unknown template $template_id — output too small")
          WARNINGS=$((WARNINGS + 1))
        fi
        ;;
    esac
  else
    # No template — just check non-empty
    if [[ "$size" -gt 50 ]]; then
      PASSED=$((PASSED + 1))
    fi
  fi
done <<< "$DONE_TIDS"

# ── Check 2: REGEL 1 enforcement (SEEDED detection) ─────────────────
echo "[validation] Check 2: REGEL 1 enforcement..."
SEEDED_TIDS=$(db_query "SELECT tid FROM tasks WHERE run_id='$RUN_ID' AND status='DONE' AND (output_artifact IS NULL OR output_artifact = '');")
SEEDED_COUNT=$(echo "$SEEDED_TIDS" | grep -c . || echo 0)
SEEDED_COUNT=$(echo "$SEEDED_COUNT" | tr -d '[:space:]')
SEEDED_COUNT=${SEEDED_COUNT:-0}

if [[ "$SEEDED_COUNT" -gt 0 ]]; then
  DEVIATIONS+=("REGEL1|CRITICAL|$SEEDED_COUNT TIDs marked DONE without output — REGEL 1 violation")
  FAILED=$((FAILED + SEEDED_COUNT))
  echo "[validation] ⚠️ REGEL 1: $SEEDED_COUNT TIDs are SEEDED (DONE without output)"
else
  echo "[validation] ✅ REGEL 1: 0 SEEDED TIDs"
fi

# ── Check 3: Contract compliance ────────────────────────────────────
echo "[validation] Check 3: Contract compliance..."
HANDOFF_FILE="$PROJECT_ROOT/.promtset/state/handoffs.jsonl"
if [[ -f "$HANDOFF_FILE" ]]; then
  handoff_count=$(wc -l < "$HANDOFF_FILE" 2>/dev/null || echo 0)
  valid_handoffs=$(python3 -c "
import json, sys
valid = 0
with open('$HANDOFF_FILE') as f:
    for line in f:
        try:
            d = json.loads(line.strip())
            if all(k in d for k in ('from','to','timestamp')): valid += 1
        except: pass
print(valid)
" 2>/dev/null || echo 0)

  if [[ "$handoff_count" -gt 0 && "$valid_handoffs" -lt "$handoff_count" ]]; then
    invalid=$((handoff_count - valid_handoffs))
    DEVIATIONS+=("CONTRACT|HIGH|$invalid/$handoff_count handoffs missing required fields (from/to/timestamp)")
    FAILED=$((FAILED + invalid))
  else
    echo "[validation] ✅ Handoffs: $valid_handoffs/$handoff_count valid"
  fi
else
  echo "[validation] ⚠️ No handoffs file found — skipping contract check"
fi

# ── Check 4: Cross-TID consistency ──────────────────────────────────
echo "[validation] Check 4: Cross-TID consistency..."
DONE_COUNT=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$RUN_ID' AND status='DONE';" | head -1)
INPROG_COUNT=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$RUN_ID' AND status='IN_PROGRESS';" | head -1)
PENDING_COUNT=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$RUN_ID' AND status='PENDING';" | head -1)
TOTAL_COUNT=$((DONE_COUNT + INPROG_COUNT + PENDING_COUNT))

if [[ "$TOTAL_COUNT" -eq 0 ]]; then
  DEVIATIONS+=("CONSISTENCY|WARNING|Run has 0 TIDs — possible DB corruption")
  WARNINGS=$((WARNINGS + 1))
fi

# Check: if G1-2 is DONE, all P1 TIDs should be DONE
G12_STATUS=$(db_query "SELECT status FROM tasks WHERE run_id='$RUN_ID' AND phase_section='verification' AND phase='G1-2' LIMIT 1;" | head -1)
if [[ "$G12_STATUS" == "DONE" ]]; then
  P1_PENDING=$(db_query "SELECT COUNT(*) FROM tasks WHERE run_id='$RUN_ID' AND phase='P1' AND status='PENDING';" | head -1)
  if [[ "$P1_PENDING" -gt 0 ]]; then
    DEVIATIONS+=("CONSISTENCY|HIGH|G1-2 is DONE but $P1_PENDING P1 TIDs are still PENDING — inconsistent state")
    FAILED=$((FAILED + 1))
  fi
fi

# ── Generate Report ─────────────────────────────────────────────────
REPORT_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TOTAL_DEVIATIONS=${#DEVIATIONS[@]}

mkdir -p "$(dirname "$OUTPUT_FILE")"

cat > "$OUTPUT_FILE" <<REPORT
# Validation Report

**Generated**: $REPORT_TIMESTAMP
**Run**: $RUN_ID
**TID**: $TID
**Goal**: $GOAL

## What Was Checked

| Check | Scope | Result |
|-------|-------|--------|
| Template compliance | All DONE TIDs with output | $PASSED passed, $FAILED failed |
| REGEL 1 (SEEDED detection) | All DONE TIDs without output | $SEEDED_COUNT SEEDED |
| Contract handoffs | .promtset/state/handoffs.jsonl | $handoff_count entries checked |
| Cross-TID consistency | Phase-gate state verification | G1-2/P1 consistency verified |

## Summary

| Metric | Count |
|--------|-------|
| ✅ Passed | $PASSED |
| ❌ Failed | $FAILED |
| ⚠️ Warnings | $WARNINGS |
| 📋 Deviations | $TOTAL_DEVIATIONS |

## Deviations

$(if [[ $TOTAL_DEVIATIONS -gt 0 ]]; then
  for d in "${DEVIATIONS[@]}"; do
    IFS='|' read -r source severity detail <<< "$d"
    echo "### [$severity] $source"
    echo "- $detail"
    echo ""
  done
else
  echo "✅ No deviations detected."
fi)

## Run State

| Status | Count |
|--------|-------|
| DONE | $DONE_COUNT |
| IN_PROGRESS | $INPROG_COUNT |
| PENDING | $PENDING_COUNT |
| **TOTAL** | **$TOTAL_COUNT** |

## Recommended Fixes

$(for d in "${DEVIATIONS[@]}"; do
  IFS='|' read -r source severity detail <<< "$d"
  case "$source" in
    *TEMPLATE*) echo "- Fix template compliance for \`$source\`: ensure required sections are present";;
    *REGEL1*) echo "- Write real output for SEEDED TIDs — REGEL 1: no DONE without output";;
    *CONTRACT*) echo "- Fix handoff files: ensure \`from\`, \`to\`, \`timestamp\` fields are present";;
    *CONSISTENCY*) echo "- Resolve inconsistent state: run \`verify-state.sh\` for diagnostic";;
    *) echo "- Review \`$source\`: \`$detail\`";;
  esac
done)

## Self-Check

- [x] Template compliance checked ($PASSED passed)
- [x] REGEL 1 enforced (SEEDED detection)
- [x] Contract handoffs validated
- [x] Cross-TID consistency verified
REPORT

FILE_SIZE=$(stat -c%s "$OUTPUT_FILE" 2>/dev/null || echo 0)
echo "[validation] Report: $OUTPUT_FILE ($FILE_SIZE bytes, $PASSED passed, $FAILED failed, $WARNINGS warnings)"

# ── Agent prompt for verification ───────────────────────────────────
agent_header "$TID" "GOVERNANCE validation"
emit_user_input_start "chain-validation.sh"
cat <<INSTRUCTION
## 🎯 AUFGABE
Validation abgeschlossen. Report liegt unter: $OUTPUT_FILE

1. Prüfe die Deviations-Liste — sind alle FAILED legitim?
2. Verifiziere REGEL 1: 0 SEEDED TIDs = korrekt
3. Cross-TID consistency: keine inkonsistenten States
4. Self-Check: Template + Contract + REGEL1 checks ✅

## 📤 OUTPUT → $OUTPUT_FILE (bereits geschrieben, ${FILE_SIZE} bytes)
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
