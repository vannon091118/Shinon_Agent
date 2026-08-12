#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# tid-helpers.sh — Shared TID state management functions (v2)
# Multi-Way Pipeline: alternative_paths, user_decisions, template_markers
# ═══════════════════════════════════════════════════════════════════

# ─── Global paths ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOAL_CHAIN_DIR="$(dirname "$SCRIPT_DIR")"
# Zentral-first: $SHINON_HOME/data/goal-chain/tid-state.db falls vorhanden,
# sonst Legacy-Pfad. Ein Ort fuer TID-State — kein Fragmentieren.
_SHINON_HOME="${SHINON_HOME:-$HOME/.shinon}"
if [[ -n "${SHINON_GOALCHAIN_DB:-}" ]]; then
    DB_PATH="${SHINON_GOALCHAIN_DB}"
elif [[ -f "${_SHINON_HOME}/data/goal-chain/tid-state.db" ]]; then
    DB_PATH="${_SHINON_HOME}/data/goal-chain/tid-state.db"
else
    DB_PATH="${GOAL_CHAIN_DIR}/db/tid-state.db"
fi
PROJECT_ROOT="$(cd "$GOAL_CHAIN_DIR/../../.." && pwd)"
SKILL_BASE=".agents/skills"

# ─── DB Engine Detection ──────────────────────────────────────────
if command -v sqlite3 &>/dev/null; then
    DB_ENGINE="sqlite3"
    db_query() { sqlite3 "$DB_PATH" "$1"; }
    db_exec() { sqlite3 "$DB_PATH" "$1"; }
else
    DB_ENGINE="python3"
    db_query() {
        python3 -c "
import sqlite3, sys
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()
try:
    cur.execute('''$1''')
    rows = cur.fetchall()
    for row in rows:
        print('|'.join(str(x) for x in row))
except:
    pass
conn.close()
" 2>/dev/null
    }
    db_exec() {
        python3 -c "
import sqlite3, sys
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()
try:
    cur.executescript('''$1''')
    conn.commit()
except Exception as e:
    print(f'DB Error: {e}', file=sys.stderr)
conn.close()
" 2>/dev/null
    }
fi

# ─── Get a single value from DB ────────────────────────────────────
task_field() {
    local tid="$1"
    local field="$2"
    db_query "SELECT $field FROM tasks WHERE tid='$tid';" | head -1
}

# ─── Evil-Twin Synthesis (v4.0: structured result.json statt Prosa) ──
# Die Synthese-Schritte (writing-plans, writing-plans-v2) konsumieren NICHT
# die Prosa (WIDERSPRUCH .md), sondern die STRUKTUR aus <output>.result.json:
# verdict + objections[]. Der Evil Twin kritisiert das GLEICHE Artefakt, das
# der Synthese-Schritt als input_artifacts liest — daher Auflösung über den
# input_artifacts-Match (deterministisch, kein Prosa-Parsing).
#
# Usage: evil_twin_result_json TID → echo Pfad (leer wenn keiner gefunden)
evil_twin_result_json() {
    local tid="$1"
    local inp; inp=$(task_field "$tid" "input_artifacts")
    [[ -z "$inp" ]] && { echo ""; return 0; }
    local out
    out=$(db_query "SELECT t.output_artifact FROM tasks t
        WHERE t.run_id=(SELECT run_id FROM tasks WHERE tid='$tid')
          AND t.phase_section LIKE 'evil-twin%'
          AND t.input_artifacts='$inp'
        ORDER BY t.phase_seq DESC LIMIT 1;" 2>/dev/null | head -1 || true)
    [[ -z "$out" ]] && { echo ""; return 0; }
    if [[ "$out" == *.md ]]; then
        echo "${out%.md}.result.json"
    else
        echo "${out}.result.json"
    fi
    return 0
}

# Read verdict + objections from an Evil-Twin result.json (structure, NOT prose).
# Sets globals: ET_VERDICT (FUNDAMENTAL|OBERFLÄCHLICH|""), ET_OBJECTIONS (text).
# Never fails the caller: missing file / bad JSON → both globals stay empty.
# Usage: read_evil_twin_result RESULT_JSON
read_evil_twin_result() {
    local f="$1"
    ET_VERDICT=""
    ET_OBJECTIONS=""
    [[ -z "$f" ]] && return 0
    # CWD-robust: erst relativ (Ziel-Chain-Konvention), dann via PROJECT_ROOT.
    if [[ ! -f "$f" && "$f" != /* ]]; then f="${PROJECT_ROOT}/${f}"; fi
    [[ -f "$f" ]] || return 0
    if ! command -v python3 &>/dev/null; then
        return 0
    fi
    local parsed
    parsed=$(python3 - "$f" <<'PY' 2>/dev/null || true
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
v = (d.get("verdict") or "").strip().upper()
# Unbekannter/leerer Verdict → explizit NONE statt stiller Einwand-Drop:
# sonst würden objections als "kein Result" verworfen, ohne dass es sichtbar ist.
if v not in ("FUNDAMENTAL", "OBERFLÄCHLICH"):
    print("VERDICT|NONE")
    sys.exit(0)
print("VERDICT|" + v)
for o in (d.get("objections") or []):
    kind = (o.get("kind") or "").strip()
    target = (o.get("target") or "").strip()
    claim = (o.get("claim") or "").strip()
    argument = (o.get("argument") or "").strip()
    evidence = (o.get("required_evidence") or "").strip()
    if not claim and not argument:
        continue
    line = f"- [{kind}] {target}: '{claim}'"
    if argument:
        line += f" | Gegenargument: {argument}"
    if evidence:
        line += f" | Geforderter Beleg: {evidence}"
    print("POINT|" + line)
PY
)
    ET_VERDICT=$(printf '%s\n' "$parsed" | sed -n 's/^VERDICT|//p' | head -1)
    ET_OBJECTIONS=$(printf '%s\n' "$parsed" | sed -n 's/^POINT|//p')
    return 0
}

# ─── State Transitions ─────────────────────────────────────────────
tid_start() {
    local tid="$1"
    local skill_name; skill_name=$(task_field "$tid" "skill_name")
    local script_path; script_path=$(task_field "$tid" "script_path")
    local phase_section; phase_section=$(task_field "$tid" "phase_section")
    local output_artifact; output_artifact=$(task_field "$tid" "output_artifact")
    db_exec "UPDATE tasks SET status='IN_PROGRESS', updated_at=datetime('now') WHERE tid='$tid';"
    db_exec "INSERT INTO follow_skill (tid, skill_name, script_path) VALUES ('$tid', '$skill_name', '$script_path');"
    echo "[tid:$tid] STATUS: PENDING → IN_PROGRESS"

    # LIVE-SKILL UPDATER (Dual-Rolle Auto-Hook): goal-chain ist der Orchestrator
    # ALLER sub-skills; bumpt Live-Snapshot bei jedem TID-Start.
    if [[ -x "$PROJECT_ROOT/.agents/skills/live-snapshot.sh" ]]; then
        bash "$PROJECT_ROOT/.agents/skills/live-snapshot.sh" "goal-chain" active \
            "TID ${tid} aktiv · ${phase_section:-subphase}" "${output_artifact:-}" \
            "${phase_section:-subphase},TID" 2>/dev/null || true
    fi
}

# A TID may only become DONE after complete.sh has supplied a valid,
# structured FalsificationGate decision. Direct tid_done calls are deliberately
# rejected: this is the runtime enforcement for "no valid gate decision →
# execution impossible", not merely a prompt convention.
_validate_gate_decision_for_tid() {
    local tid="$1"
    local gate_log="${2:-}"
    [[ -n "$gate_log" && -f "$gate_log" ]] || {
        echo "ERROR: TID $tid has no valid FalsificationGate decision (log missing)" >&2
        return 1
    }
    python3 - "$gate_log" "$tid" "$(task_field "$tid" "projekt")" <<'PY'
import json
import sys
from pathlib import Path

path, tid, project = sys.argv[1:]
try:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: invalid FalsificationGate decision: {exc}", file=sys.stderr)
    raise SystemExit(1)

required = ("gate", "passed", "execution_exit_code", "results", "tid", "project", "output_file", "artifact_sha256")
missing = [key for key in required if key not in payload]
if missing:
    print(f"ERROR: invalid FalsificationGate decision: missing {', '.join(missing)}", file=sys.stderr)
    raise SystemExit(1)
if payload.get("gate") != "FalsificationGate":
    print("ERROR: invalid FalsificationGate decision: wrong gate", file=sys.stderr)
    raise SystemExit(1)
if payload.get("tid") != tid or payload.get("project") != project:
    print("ERROR: invalid FalsificationGate decision: TID/project mismatch", file=sys.stderr)
    raise SystemExit(1)
if payload.get("passed") is not True or payload.get("execution_exit_code") != 0:
    print("ERROR: FalsificationGate did not pass", file=sys.stderr)
    raise SystemExit(1)
if not isinstance(payload.get("results"), list):
    print("ERROR: invalid FalsificationGate decision: results is not a list", file=sys.stderr)
    raise SystemExit(1)

output = Path(str(payload.get("output_file") or ""))
if not output.is_absolute():
    output = Path.cwd() / output
if not output.is_file():
    print("ERROR: invalid FalsificationGate decision: artifact is missing", file=sys.stderr)
    raise SystemExit(1)
import hashlib
actual_hash = hashlib.sha256(output.read_bytes()).hexdigest()
if payload.get("artifact_sha256") != actual_hash:
    print("ERROR: invalid FalsificationGate decision: artifact hash mismatch", file=sys.stderr)
    raise SystemExit(1)
PY
}

tid_done() {
    local tid="$1"
    local gate_log="${2:-}"
    _validate_gate_decision_for_tid "$tid" "$gate_log" || return 1
    local phase_section; phase_section=$(task_field "$tid" "phase_section")
    db_exec "UPDATE tasks SET status='DONE', completed_at=datetime('now'), updated_at=datetime('now') WHERE tid='$tid';"
    echo "[tid:$tid] STATUS: IN_PROGRESS → DONE (FalsificationGate verified)"

    # LIVE-SKILL UPDATER hook
    if [[ -x "$PROJECT_ROOT/.agents/skills/live-snapshot.sh" ]]; then
        bash "$PROJECT_ROOT/.agents/skills/live-snapshot.sh" "goal-chain" planning \
            "TID ${tid} fertig · ${phase_section:-subphase} → DONE" "" \
            "${phase_section:-subphase},TID-DONE" 2>/dev/null || true
    fi
}

tid_fail() {
    local tid="$1"
    local reason="${2:-No reason given}"
    local phase_section; phase_section=$(task_field "$tid" "phase_section")
    db_exec "UPDATE tasks SET status='FAILED', updated_at=datetime('now') WHERE tid='$tid';"
    echo "[tid:$tid] STATUS: FAILED — $reason"

    # LIVE-SKILL UPDATER hook
    if [[ -x "$PROJECT_ROOT/.agents/skills/live-snapshot.sh" ]]; then
        bash "$PROJECT_ROOT/.agents/skills/live-snapshot.sh" "goal-chain" error \
            "TID ${tid} fehlgeschlagen: ${reason}" "" "FAIL,${phase_section:-subphase}" 2>/dev/null || true
    fi
}

# ROOT_CAUSE_DONE — replaces SKIPPED. The system NEVER skips without analysis.
# Every "skip" MUST document WHY the TID was unnecessary (root cause).
# Usage: tid_root_cause_done TID "G1-2 PASS: planning output already covers gap analysis"
tid_root_cause_done() {
    local tid="$1"
    local root_cause="${2:?ROOT CAUSE REQUIRED — skipping without analysis is forbidden}"
    echo "ERROR: ROOT_CAUSE_DONE cannot be granted directly. A valid FalsificationGate decision is required; no gate → execution impossible." >&2
    return 1
    # Internal gate routing updates ROOT_CAUSE_DONE only after complete.sh has
    # already validated the KARMA gate. This public helper is not an escape hatch.
    db_exec "UPDATE tasks SET status='ROOT_CAUSE_DONE', updated_at=datetime('now'), completed_at=datetime('now') WHERE tid='$tid';"
    record_decision "$tid" "ROOT_CAUSE" "$root_cause" "Gate-verified: no gap to fill" "" ""
    echo "[tid:$tid] STATUS: ROOT_CAUSE_DONE — $root_cause"
}

# Legacy compat — routes to tid_root_cause_done with mandatory root cause
tid_skip() {
    local tid="$1"
    local reason="${2:-No reason given}"
    echo "[tid:$tid] ⚠️  WARNING: tid_skip is deprecated — use tid_root_cause_done with explicit root cause" >&2
    tid_root_cause_done "$tid" "DEPRECATED tid_skip: $reason"
}

# ─── Dependency Checks ─────────────────────────────────────────────
pre_tasks_done() {
    local tid="$1"
    local pending
    pending=$(db_query "SELECT COUNT(*) FROM pre_tasks pt JOIN tasks t ON pt.pre_tid = t.tid WHERE pt.tid='$tid' AND t.status != 'DONE' AND t.status != 'SKIPPED' AND t.status != 'ROOT_CAUSE_DONE';")
    [[ "$pending" -eq 0 ]] && return 0 || return 1
}

# Next linear pending TID (for default flow)
next_pending_tid() {
    local run_id="$1"
    db_query "SELECT t.tid FROM tasks t
              WHERE t.run_id='$run_id' AND t.status='PENDING'
              AND NOT EXISTS (
                  SELECT 1 FROM pre_tasks pt
                  JOIN tasks pt2 ON pt.pre_tid = pt2.tid
                  WHERE pt.tid = t.tid AND pt2.status NOT IN ('DONE','SKIPPED','ROOT_CAUSE_DONE')
              )
              ORDER BY t.phase_seq ASC LIMIT 1;" | head -1
}

# ─── Gate Gap Extraction ──────────────────────────────────────────
# Liest das Gate-Output-File und extrahiert konkrete Gaps.
# Erwartet: Zeilen die mit "# Gap:" oder "# Missing:" beginnen.
# Fallback: alle #-Kommentarzeilen ab Zeile 2.
# Usage: _extract_gate_gaps OUTPUT_FILE → setzt GATE_GAPS global
_extract_gate_gaps() {
    local output_file="$1"
    GATE_GAPS=""
    if [[ -z "$output_file" || ! -f "$output_file" ]]; then
        return
    fi
    # Extrahiere explizite Gap-Zeilen
    local gaps
    gaps=$(grep -iE '^# (Gap|Missing|Incomplete|Failed|Issue|Lücke|Fehlt|Unvollständig):' "$output_file" 2>/dev/null || true)
    if [[ -z "$gaps" ]]; then
        # Fallback: nimm alle #-Kommentarzeilen ausser Zeile 1 (PASS/FAIL)
        gaps=$(tail -n +2 "$output_file" 2>/dev/null | grep '^#' | head -5 || true)
    fi
    # Bereinigen: "# " prefix entfernen, auf 120 Zeichen kürzen
    while IFS= read -r line; do
        line="${line#\# }"
        line="${line:0:120}"
        GATE_GAPS="${GATE_GAPS}${line}; "
    done <<< "$gaps"
    GATE_GAPS="${GATE_GAPS%; }"  # trailing "; " entfernen
}

# ─── Root-Cause-Aware Gate Routing (SKIPPED ersetzt durch ROOT_CAUSE_DONE) ──
# Jeder PASS erzeugt ROOT_CAUSE_DONE mit Analyse WARUM die Phase nicht nötig war.
# Jeder FAIL identifiziert die Gap und routet zurück zur Behebung.
# Usage: next_pending_tid_after_gate RUN_ID GATE_PHASE GATE_RESULT [GATE_OUTPUT_FILE]
next_pending_tid_after_gate() {
    local run_id="$1"
    local gate_phase="$2"
    local gate_result="$3"
    local gate_output_file="${4:-}"
    local gate_log="${5:-}"
    local source_tid="${6:-}"

    # Root-cause routing is itself a state transition. It must carry the same
    # validated gate authorization as DONE; a caller cannot manufacture PASS
    # and directly mark another phase ROOT_CAUSE_DONE.
    if [[ -z "$gate_log" || -z "$source_tid" ]] || ! _validate_gate_decision_for_tid "$source_tid" "$gate_log"; then
        echo "ERROR: gate routing denied — no valid gate decision → execution impossible" >&2
        return 1
    fi

    if [[ "$gate_result" == "PASS" ]]; then
        local skip_phase=""
        case "$gate_phase" in
            "G1-2") skip_phase="P2" ;;
            "G2-3") ;;  # No skip — Gate 2→3 confirms plan readiness; Phase 3 starts naturally
            *) ;;
        esac
        if [[ -n "$skip_phase" ]]; then
            echo "  🎯 Gate PASS → Root-Cause-Analyse für Phase $skip_phase" >&2
            # Per-TID root cause analysis statt blindem Massen-SKIP
            # Jede P2-TID bekommt eine individuelle Root-Cause-Begründung
            local tids_to_analyze
            tids_to_analyze=$(db_query "SELECT tid, phase_section FROM tasks WHERE run_id='$run_id' AND phase='$skip_phase' AND status='PENDING';")
            if [[ -n "$tids_to_analyze" ]]; then
                while IFS='|' read -r tid section; do
                    [[ -z "$tid" ]] && continue
                    local rc_reason="$gate_phase PASS: '$section' — Planungs-Output deckt diesen Bereich bereits ab. Keine Lücke identifiziert."
                    db_exec "UPDATE tasks SET status='ROOT_CAUSE_DONE', updated_at=datetime('now'), completed_at=datetime('now') WHERE tid='$tid';"
                    echo "  🎯 $tid → ROOT_CAUSE_DONE: $rc_reason" >&2
                    record_decision "$tid" "ROOT_CAUSE" "$rc_reason" "Gate $gate_phase PASS — no gap to fill" "" ""
                done <<< "$tids_to_analyze"
            fi
            db_query "SELECT t.tid FROM tasks t
                      WHERE t.run_id='$run_id' AND t.status='PENDING'
                      AND NOT EXISTS (
                          SELECT 1 FROM pre_tasks pt
                          JOIN tasks pt2 ON pt.pre_tid = pt2.tid
                          WHERE pt.tid = t.tid AND pt2.status NOT IN ('DONE','SKIPPED','ROOT_CAUSE_DONE')
                      )
                      ORDER BY t.phase_seq ASC LIMIT 1;" | head -1
            return
        fi
    fi
    # FAIL → Root-Cause-Identifikation: WAS hat das Gate abgelehnt?
    if [[ "$gate_result" == "FAIL" ]]; then
        echo "  🔁 Gate FAIL → Root-Cause: Gap identifiziert, routen zur Behebung" >&2
        case "$gate_phase" in
            "G1-2")
                # Extrahiere KONKRETE Gaps aus dem Gate-Output
                _extract_gate_gaps "$gate_output_file"
                local gap_summary="${GATE_GAPS:-Planungs-Lücken identifiziert (keine spezifischen Gaps im Gate-Output)}"
                # P2 ist noch PENDING — keine Aktion nötig, next_pending_tid findet sie
                echo "  🎯 G1-2 FAIL: $gap_summary → P2 muss diese schließen" >&2
                ;;
            "G2-3")
                # Extrahiere KONKRETE Gaps aus dem Gate-Output-File
                _extract_gate_gaps "$gate_output_file"
                local gap_summary="${GATE_GAPS:-P2-Output unzureichend (keine spezifischen Gaps im Gate-Output)}"

                # P2 TIDs sind DONE — zuruecksetzen auf PENDING fuer Rework
                # MIT Root-Cause: KONKRETE Gaps aus G2-3-Gate-Output extrahiert
                db_exec "UPDATE tasks SET status='PENDING', completed_at=NULL, updated_at=datetime('now')
                         WHERE run_id='$run_id' AND phase='P2' AND status='DONE';"
                echo "  🎯 G2-3 FAIL: $gap_summary → P2 TIDs zurückgesetzt" >&2
                local reset_tids
                reset_tids=$(db_query "SELECT tid, phase_section FROM tasks WHERE run_id='$run_id' AND phase='P2' AND status='PENDING';")
                if [[ -n "$reset_tids" ]]; then
                    while IFS='|' read -r tid section; do
                        [[ -z "$tid" ]] && continue
                        record_decision "$tid" "ROOT_CAUSE_RESET" \
                            "G2-3 FAIL: '$section' — $gap_summary" \
                            "Gate G2-3 identifizierte: $gap_summary" "" ""
                    done <<< "$reset_tids"
                fi
                ;;
            *) ;;
        esac
    fi
    next_pending_tid "$run_id"
}

# ─── Multi-Way DAG Queries ─────────────────────────────────────────

# Get all alternative next-TIDs for a given source TID
next_tids_multiway() {
    local source_tid="$1"
    python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()
rows = cur.execute('''
    SELECT ap.path_label, ap.target_tid, t.phase, t.phase_section, ap.rationale, ap.tradeoffs, ap.ranking
    FROM alternative_paths ap
    JOIN tasks t ON ap.target_tid = t.tid
    WHERE ap.source_tid = ?
    ORDER BY ap.ranking, ap.path_label
''', ('$source_tid',)).fetchall()
for label, target, phase, section, rat, tof, ranking in rows:
    print(f'{label}|{target}|{phase}|{section}|{rat}|{tof}|{ranking}')
conn.close()
" 2>/dev/null
}

# Check if TID requires user approval
tid_requires_approval() {
    local tid="$1"
    local req; req=$(task_field "$tid" "requires_approval")
    [[ "$req" == "1" ]] && return 0 || return 1
}

# Get latest user decision for after_tid
latest_user_decision() {
    local after_tid="$1"
    db_query "SELECT decision, selected_tid, user_rationale FROM user_decisions WHERE after_tid='$after_tid' ORDER BY decision_id DESC LIMIT 1;"
}

# ─── SQL Escaping ───────────────────────────────────────────────
# Doubles single quotes for safe SQLite string literals.
# Usage: val=$(sql_escape "$raw_value")
sql_escape() {
    local val="$1"
    echo "${val//\'/''}"
}

# ─── Decision Recording ────────────────────────────────────────────
record_decision() {
    local tid="$1"
    local decision_type="$2"
    local decision_value="$3"
    local rationale="${4:-}"
    local next_tid="${5:-}"
    local alt_tids="${6:-}"

    # Escape ALL string values for SQLite (single quotes → doubled)
    local tid_e; tid_e=$(sql_escape "$tid")
    local type_e; type_e=$(sql_escape "$decision_type")
    local val_e; val_e=$(sql_escape "$decision_value")
    local rat_e; rat_e=$(sql_escape "$rationale")
    local next_e; next_e=$(sql_escape "$next_tid")
    local alt_e; alt_e=$(sql_escape "$alt_tids")

    # Use Python for INSERT with proper parameterization when available.
    # Falls back to sqlite3 CLI with escaped values.
    if command -v python3 &>/dev/null; then
        python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('$DB_PATH')
    conn.execute(
        '''INSERT INTO dispatcher_decisions (tid, decision_type, decision_value, rationale, next_tid, alt_tids)
           VALUES (?, ?, ?, ?, ?, ?)''',
        ('$tid_e', '$type_e', '$val_e', '$rat_e', '$next_e', '$alt_e')
    )
    conn.commit()
    conn.close()
except Exception as e:
    import sys
    print(f'DB Error in record_decision: {e}', file=sys.stderr)
" 2>/dev/null
    else
        db_exec "INSERT INTO dispatcher_decisions (tid, decision_type, decision_value, rationale, next_tid, alt_tids)
                 VALUES ('$tid_e', '$type_e', '$val_e', '$rat_e', '$next_e', '$alt_e');"
    fi
}

record_user_decision() {
    local after_tid="$1"
    local decision="$2"
    local selected_tid="${3:-}"
    local rationale="${4:-}"
    db_exec "INSERT INTO user_decisions (after_tid, decision, selected_tid, user_rationale)
             VALUES ('$after_tid', '$decision', '$selected_tid', '$rationale');"
}

# ─── Alternative Paths Registration ─────────────────────────────────
register_alternative_path() {
    local source_tid="$1"
    local target_tid="$2"
    local label="$3"
    local rationale="$4"
    local tradeoffs="$5"
    local ranking="${6:-0}"
    db_exec "INSERT OR REPLACE INTO alternative_paths (source_tid, target_tid, path_label, rationale, tradeoffs, ranking)
             VALUES ('$source_tid', '$target_tid', '$label', '$rationale', '$tradeoffs', $ranking);"
}

# ─── Template Markers Registration ──────────────────────────────────
register_template_marker() {
    local template_id="$1"
    local marker_type="$2"
    local pattern="$3"
    local severity="${4:-ERROR}"
    local description="$5"
    db_exec "INSERT OR REPLACE INTO template_markers (template_id, marker_type, pattern, severity, description)
             VALUES ('$template_id', '$marker_type', '$pattern', '$severity', '$description');"
}

# ─── Context Filtering ─────────────────────────────────────────────

# ─── USER INPUT EMULATION ────────────────────────────────────────
# Wrappt Script-Output als User-Nachricht (mit > markers).
# Das Model/der Agent EMPFÄNGT das Output als wäre es eine User-Nachricht.
# Usage:
#   emit_user_input "section text" [--prompt="Was nun?"]
#
# Aufgerufen mit `start` und `end` Markern:
#   emit_user_input_start
#   ... content via echo/cat ...
#   emit_user_input_end "phase-1-brainstorming.sh"
emit_user_input_start() {
    local source_script="${1:-unknown-script}"
    local timestamp=$(date +%H:%M:%S)
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════"
    echo "│ > USER INPUT EMULATION · SouRCe: ${source_script} · ${timestamp}"
    echo "═══════════════════════════════════════════════════════════════════════"
    echo "│"
    echo "│  (Du empfängst dies wie eine direkt eingetippte User-Nachricht.)"
    echo "│"
}

emit_user_input_end() {
    local destination_path="${1:-continue with the next command from above}"
    echo "│"
    echo "└───────────────────────────────────────────────────────────────────────"
    echo "  ✅ END USER INPUT · Destination: $destination_path"
    echo ""
}

# Convenience wrapper for full emulated user message
emulate_user_message() {
    local title="$1"
    local body="$2"
    local destination="${3:-next command}"
    local timestamp=$(date +%H:%M:%S)
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════"
    echo "│ > USER [goal-chain] · ${timestamp}"
    echo "───────────────────────────────────────────────────────────────────────"
    echo "│  $title"
    echo "│"
    while IFS= read -r line; do
        echo "│  $line"
    done <<< "$body"
    echo "│"
    echo "└───────────────────────────────────────────────────────────────────────"
    echo "  ▶ Destination: $destination"
    echo ""
}

# ─── Dashboard notification (logs to dashboard file) ────────────────
notify_dashboard() {
    local event="$1"
    local tid="$2"
    local detail="${3:-}"
    local dash_log="/tmp/goal-chain-dashboard.log"
    echo "[$(date +%H:%M:%S)] $event | $tid | $detail" >> "$dash_log" 2>/dev/null || true

    # Auto-refresh HTML snapshot so register_preview shows latest state
    if [[ -n "${RUN_ID:-}" && -x "$SCRIPT_DIR/update-snapshot.sh" ]]; then
        local snap
        snap=$(find ".goal" -name 'snapshot.html' 2>/dev/null | head -1)
        if [[ -n "$snap" ]]; then
            bash "$SCRIPT_DIR/update-snapshot.sh" "$RUN_ID" "$event · $detail" > "$snap" 2>/dev/null || true
        fi
    fi
}

# ─── LIVE-SKILL UPDATER (Dual-Rolle: Updater + Token-Spar-Artifact) ──
# Schreibt kompakten Snapshot (≤2KB) statt voller SKILL.md.
# JEDES Script/Agent ruft dies bei Skill-Activation auf.
# Usage:
#   register_skill_live <skill> <state> <summary> [output_path] [tags...]
register_skill_live() {
    local skill="${1:?Missing skill name}"
    local state="${2:-active}"
    local summary="${3:-activation}"
    local output="${4:-}"
    shift 4 2>/dev/null || shift $#
    local tags="${*:-}"

    local snap_tool="$PROJECT_ROOT/.agents/skills/live-snapshot.sh"
    if [[ -x "$snap_tool" ]]; then
        bash "$snap_tool" "$skill" "$state" "$summary" "$output" $tags 2>/dev/null || true
    fi
}

# Live progress computation
progress_summary() {
    local run_id="$1"
    python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()
total = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=?', ('$run_id',)).fetchone()[0]
done = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status=\"DONE\"', ('$run_id',)).fetchone()[0]
inprog = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status=\"IN_PROGRESS\"', ('$run_id',)).fetchone()[0]
failed = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status=\"FAILED\"', ('$run_id',)).fetchone()[0]
percent = (done * 100 // total) if total > 0 else 0
print(f'{done}/{total} done ({percent}%) · {inprog} active · {failed} failed')
conn.close()
"
}

# FOLLOW/PRE_TASK counts for a given TID (for live display)
follow_pre_counts() {
    local tid="$1"
    python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()
pre = cur.execute('SELECT COUNT(*) FROM pre_tasks WHERE tid=?', ('$tid',)).fetchone()[0]
follows = cur.execute('SELECT COUNT(*) FROM follow_skill WHERE tid=?', ('$tid',)).fetchone()[0]
alt_alts = cur.execute('SELECT COUNT(*) FROM alternative_paths WHERE source_tid=?', ('$tid',)).fetchone()[0]
print(f'pre={pre} follow={follows} alt_paths={alt_alts}')
conn.close()
"
}

agent_header() {
    local tid="$1"
    local title="$2"
    local skill_name; skill_name=$(task_field "$tid" "skill_name")
    local goal; goal=$(task_field "$tid" "goal")
    local output_artifact; output_artifact=$(task_field "$tid" "output_artifact")
    local template_id; template_id=$(task_field "$tid" "template_id")

    cat <<HEADER

╔══════════════════════════════════════════════════════════════╗
║  TID: $tid
║  SKILL: $skill_name
║  TITLE: $title
║  GOAL: $goal
║  OUTPUT: $output_artifact
║  TEMPLATE: $template_id
╚══════════════════════════════════════════════════════════════╝

HEADER
}

agent_footer() {
    local tid="$1"
    local next_script="${2:-}"
    local next_tid="${3:-}"
    local output_artifact; output_artifact=$(task_field "$tid" "output_artifact")
    local template_id; template_id=$(task_field "$tid" "template_id")

    cat <<FOOTER

────────────────────────────────────────────────────────────────
🔒 AGENT REGELN (NICHT VERLETZEN):
  1. Dieses Script NICHT verändern.
  2. Output nach: $output_artifact schreiben.
  3. Output MUSS Template '$template_id' EXAKT entsprechen.
  4. NUR bereitgestellten Kontext verwenden.
  5. Placeholder {{...}} MÜSSEN gefüllt sein vor complete.sh.
FOOTER

    if [[ -n "$next_script" ]]; then
        echo "  6. NACH Abschluss + verify-template.sh: bash $next_script \\$TID"
    fi
    echo "────────────────────────────────────────────────────────────────"
}

# ─── Script Discovery ──────────────────────────────────────────────
script_for_tid() {
    local tid="$1"
    db_query "SELECT script_path FROM tasks WHERE tid='$tid';" | head -1
}

tids_for_run() {
    local run_id="$1"
    db_query "SELECT tid, phase, phase_section, status FROM tasks WHERE run_id='$run_id' ORDER BY phase_seq ASC;"
}

# ─── Validation ────────────────────────────────────────────────────
assert_tid_state() {
    local tid="$1"
    local expected_state="$2"
    local actual; actual=$(task_field "$tid" "status")
    if [[ "$actual" != "$expected_state" ]]; then
        echo "ERROR: TID $tid expected $expected_state but is $actual" >&2
        return 1
    fi
    return 0
}

ensure_db() {
    if [[ ! -f "$DB_PATH" ]]; then
        echo "ERROR: TID database not found at $DB_PATH" >&2
        echo "Run: bash $SCRIPT_DIR/db-init.sh" >&2
        return 1
    fi
    return 0
}
