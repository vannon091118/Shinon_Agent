#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# chain-security-scan.sh — STACK: GOVERNANCE — Skill: security/security-scan
#
# v2.0 — Real scanning logic. Checks:
#   1. Hardcoded secrets (API keys, tokens, passwords) in source files
#   2. Unsafe file permissions on config/credential files
#   3. Missing input validation patterns
#   4. SQL injection surfaces (string concatenation in queries)
#   5. OWASP Top 10 category mapping per finding
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"
RUN_ID="${1:?Usage: bash chain-security-scan.sh RUN_ID TID}"
TID="${2:?}"
ensure_db; assert_tid_state "$TID" "PENDING"; tid_start "$TID"
notify_dashboard "TID_STARTED" "$TID" "$(progress_summary "$RUN_ID")"

OUTPUT_FILE=$(task_field "$TID" "output_artifact")
SKILL=$(task_field "$TID" "skill_name")
GOAL=$(task_field "$TID" "goal")
PROJEKT=$(task_field "$TID" "projekt")

# ── Target: scan the project root and all submodules ────────────────
PROJECT_ROOT="${PZ_ROOT:-$(cd "$SCRIPT_DIR/../../../.." && pwd)}"
SCAN_DIRS=(
  "$PROJECT_ROOT/fusion-main"
  "$PROJECT_ROOT/karma-main"
  "$PROJECT_ROOT/limen-main/src"
  "$PROJECT_ROOT/.agents/skills/goal-chain/scripts"
)

# Files to scan (exclude node_modules, .git, __pycache__, .freebuff)
SCAN_EXCLUDE='node_modules|\.git/|__pycache__|\.freebuff|venv|\.db$|\.db-wal$|\.db-shm$'

FINDINGS=()
FINDING_ID=0
CRITICAL=0; HIGH=0; MEDIUM=0; LOW=0

echo "[security-scan] Scanning $(IFS=' '; echo "${SCAN_DIRS[*]}")"

# ── Probe 1: Hardcoded secrets ─────────────────────────────────────
echo "[security-scan] Probe 1: Hardcoded secrets..."
SECRET_PATTERNS=(
  'api_key\s*=\s*"[^"]{8,}"'
  'API_KEY\s*=\s*"[^"]{8,}"'
  'token\s*=\s*"[A-Za-z0-9_\-]{16,}"'
  'password\s*=\s*"[^"]+"'
  'secret\s*=\s*"[^"]{8,}"'
  'sk-[A-Za-z0-9]{20,}'
  'ghp_[A-Za-z0-9]{20,}'
  'Bearer\s+[A-Za-z0-9_\-\.]{20,}'
)

for dir in "${SCAN_DIRS[@]}"; do
  [[ -d "$dir" ]] || continue
  for pattern in "${SECRET_PATTERNS[@]}"; do
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      file=$(echo "$line" | cut -d: -f1)
      lnum=$(echo "$line" | cut -d: -f2)
      content=$(echo "$line" | cut -d: -f3- | sed 's/^[[:space:]]*//' | head -c 120)
      FINDING_ID=$((FINDING_ID + 1))
      FINDINGS+=("SEC-$(printf '%03d' $FINDING_ID)|CRITICAL|Hardcoded secret|$file:$lnum|$content|OWASP A07:2021 - Identification and Authentication Failures")
      CRITICAL=$((CRITICAL + 1))
    done < <(grep -rnE --include='*.py' --include='*.js' --include='*.sh' --include='*.json' --include='*.yaml' --include='*.yml' \
      "$pattern" "$dir" 2>/dev/null | grep -v "$SCAN_EXCLUDE" | grep -v 'EXAMPLE\|example\|fake\|test\|mock\|FCC_QUICKREF\|placeholder' | head -3)
  done
done

# ── Probe 2: Unsafe file permissions (.env, credentials) ────────────
echo "[security-scan] Probe 2: Unsafe file permissions..."
for dir in "${SCAN_DIRS[@]}"; do
  [[ -d "$dir" ]] || continue
  while IFS= read -r file; do
    [[ -z "$file" ]] && continue
    perms=$(stat -c '%a' "$file" 2>/dev/null || echo '???')
    if [[ "$perms" != "600" && "$perms" != "400" ]]; then
      FINDING_ID=$((FINDING_ID + 1))
      FINDINGS+=("SEC-$(printf '%03d' $FINDING_ID)|HIGH|Unsafe file permissions ($perms)|$file|Should be 600 or 400|OWASP A05:2021 - Security Misconfiguration")
      HIGH=$((HIGH + 1))
    fi
  done < <(find "$dir" -type f \( -name '.env' -o -name '*.pem' -o -name 'credentials*' -o -name '*secret*' \) 2>/dev/null | grep -v "$SCAN_EXCLUDE" | head -5)
done

# ── Probe 3: SQL injection surfaces ─────────────────────────────────
echo "[security-scan] Probe 3: SQL injection surfaces..."
SQLI_PATTERNS=(
  'execute\s*\(\s*["\x27].*%s.*["\x27]'
  'execute\s*\(\s*["\x27].*format\s*\(.*\)'
  'execute\s*\(\s*f["\x27]'
)

for dir in "${SCAN_DIRS[@]}"; do
  [[ -d "$dir" ]] || continue
  for pattern in "${SQLI_PATTERNS[@]}"; do
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      file=$(echo "$line" | cut -d: -f1)
      lnum=$(echo "$line" | cut -d: -f2)
      # Skip if it uses parameterized queries (? placeholder)
      if echo "$line" | grep -q '?'; then continue; fi
      FINDING_ID=$((FINDING_ID + 1))
      FINDINGS+=("SEC-$(printf '%03d' $FINDING_ID)|MEDIUM|Potential SQL injection|$file:$lnum|String formatting in SQL query|OWASP A03:2021 - Injection")
      MEDIUM=$((MEDIUM + 1))
    done < <(grep -rnE --include='*.py' "$pattern" "$dir" 2>/dev/null | grep -v "$SCAN_EXCLUDE" | head -3)
  done
done

# ── Probe 4: Missing input validation ───────────────────────────────
echo "[security-scan] Probe 4: Missing input validation..."
for dir in "${SCAN_DIRS[@]}"; do
  [[ -d "$dir" ]] || continue
  # Find Python functions that take user input without validation
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    file=$(echo "$line" | cut -d: -f1)
    lnum=$(echo "$line" | cut -d: -f2)
    # Check if the NEXT 3 lines contain validation
    next_lnum=$((lnum + 1))
    has_validation=$(sed -n "${next_lnum},$((lnum + 5))p" "$file" 2>/dev/null | grep -ciE 'validate|sanitize|isinstance|assert|if.*not|raise.*Error' || echo 0)
    has_validation=$(echo "$has_validation" | tr -d '[:space:]')
    has_validation=${has_validation:-0}
    if [[ "$has_validation" -eq 0 ]]; then
      FINDING_ID=$((FINDING_ID + 1))
      FINDINGS+=("SEC-$(printf '%03d' $FINDING_ID)|LOW|Missing input validation|$file:$lnum|Function accepts input without validation|OWASP A03:2021 - Injection")
      LOW=$((LOW + 1))
    fi
  done < <(grep -rnE --include='*.py' 'def (process|handle|extract|parse|create|update).*\(.*(input|data|payload|request|text)' "$dir" 2>/dev/null | grep -v "$SCAN_EXCLUDE" | grep -v 'test_' | head -5)
done

# ── Probe 5: Node.js dependency audit ───────────────────────────────
echo "[security-scan] Probe 5: Node.js dependency audit..."
for dir in "${SCAN_DIRS[@]}"; do
  [[ -d "$dir" ]] || continue
  pkg_json=$(find "$dir" -name 'package.json' -maxdepth 3 2>/dev/null | grep -v node_modules | head -1)
  if [[ -n "$pkg_json" && -f "$pkg_json" ]]; then
    dep_count=$(python3 -c "import json; d=json.load(open('$pkg_json')); print(len(d.get('dependencies',{}))+len(d.get('devDependencies',{})))" 2>/dev/null || echo 0)
    if [[ "$dep_count" -gt 0 ]]; then
      FINDING_ID=$((FINDING_ID + 1))
      FINDINGS+=("SEC-$(printf '%03d' $FINDING_ID)|LOW|Dependencies need audit|$pkg_json|$dep_count total dependencies — run npm audit|OWASP A06:2021 - Vulnerable Components")
      LOW=$((LOW + 1))
    fi
  fi
done

# ── Generate Report ─────────────────────────────────────────────────
REPORT_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TOTAL=$((CRITICAL + HIGH + MEDIUM + LOW))

mkdir -p "$(dirname "$OUTPUT_FILE")"

cat > "$OUTPUT_FILE" <<REPORT
# Security Scan Report

**Generated**: $REPORT_TIMESTAMP
**Run**: $RUN_ID
**TID**: $TID
**Goal**: $GOAL
**Scanned**: $(IFS=', '; echo "${SCAN_DIRS[*]}")

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | $CRITICAL |
| HIGH     | $HIGH |
| MEDIUM   | $MEDIUM |
| LOW      | $LOW |
| **TOTAL** | **$TOTAL** |

## Findings

$(for f in "${FINDINGS[@]}"; do
  IFS='|' read -r id severity category location detail owasp <<< "$f"
  echo "### [$id] $severity: $category"
  echo "- **Location**: $location"
  echo "- **Detail**: $detail"
  echo "- **OWASP**: $owasp"
  echo ""
done)

$(if [[ $TOTAL -eq 0 ]]; then
  echo "## ✅ No findings"
  echo "No security issues detected in the scanned scope."
fi || true)

## Recommendations

1. **CRITICAL findings**: Remediate immediately — hardcoded secrets must be moved to environment variables or a secrets manager.
2. **HIGH findings**: Restrict file permissions on credential files to 600 (owner read/write only).
3. **MEDIUM findings**: Review SQL queries — ensure all user-supplied values use parameterized queries (? placeholder).
4. **LOW findings**: Add input validation to all public-facing functions. Run \`npm audit\` on Node.js projects.

## Self-Check

- [x] All findings have OWASP category references
- [x] Scan covered $(IFS=' '; echo "${#SCAN_DIRS[@]}") directories
- [x] Report generated with structured format
REPORT

FILE_SIZE=$(stat -c%s "$OUTPUT_FILE" 2>/dev/null || echo 0)
echo "[security-scan] Report: $OUTPUT_FILE ($FILE_SIZE bytes, $TOTAL findings)"

# ── Agent prompt for verification ───────────────────────────────────
agent_header "$TID" "GOVERNANCE security-scan"
emit_user_input_start "chain-security-scan.sh"
cat <<INSTRUCTION
## 🎯 AUFGABE
Security-Scan abgeschlossen. Report liegt unter: $OUTPUT_FILE

1. Prüfe den Report auf Plausibilität ($TOTAL Findings, $CRITICAL CRITICAL)
2. Verifiziere die OWASP-Kategorien pro Finding
3. Falls Findings: priorisiere CRITICAL > HIGH > MEDIUM > LOW
4. Self-Check: Jeder Fund hat CVE-Referenz oder OWASP-Kategorie ✅

## 📤 OUTPUT → $OUTPUT_FILE (bereits geschrieben, ${FILE_SIZE} bytes)
INSTRUCTION
agent_footer "$TID" "$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh $TID DONE"
notify_dashboard "AWAITING_OUTPUT" "$TID" "$OUTPUT_FILE"
echo ""
echo "AGENT: bash $SCRIPT_DIR/complete.sh $TID DONE"
