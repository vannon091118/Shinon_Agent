-- ═══════════════════════════════════════════════════════════════════
-- TID State Database Schema v2 — Multi-Way Pipeline
-- ═══════════════════════════════════════════════════════════════════
-- v2 erweitert die v1 um:
--   - alternative_paths: Multi-Way DAG (mehrere mögliche nächste TIDs)
--   - user_decisions: User-Approval-Checkpoints
--   - template_markers: Drift-Detection (was MUSS in Output sein)
-- ═══════════════════════════════════════════════════════════════════

PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

-- ─── Core Tasks Table ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    tid                TEXT PRIMARY KEY,
    projekt            TEXT NOT NULL,
    run_id             TEXT NOT NULL,
    task               TEXT NOT NULL,
    goal               TEXT NOT NULL,
    phase              TEXT NOT NULL,           -- P1, P2, P3, P4, G1-2, G2-3, STACK, USER
    phase_section      TEXT NOT NULL,
    phase_seq          INTEGER NOT NULL DEFAULT 0,
    status             TEXT NOT NULL DEFAULT 'PENDING',
    skill_name         TEXT,
    script_path        TEXT NOT NULL,
    input_artifacts    TEXT,
    output_artifact    TEXT,
    template_id        TEXT,                    -- ID des Output-Templates (für verify-template)
    requires_approval  INTEGER DEFAULT 0,       -- 1 = User-Checkpoint NACH diesem TID
    context_filter     TEXT,
    created_at         TEXT DEFAULT (datetime('now')),
    updated_at         TEXT DEFAULT (datetime('now')),
    completed_at       TEXT
);

-- ─── Pre-Task Dependencies (mandatory predecessors) ───────────────
CREATE TABLE IF NOT EXISTS pre_tasks (
    tid      TEXT NOT NULL,
    pre_tid  TEXT NOT NULL,
    PRIMARY KEY (tid, pre_tid),
    FOREIGN KEY (tid) REFERENCES tasks(tid),
    FOREIGN KEY (pre_tid) REFERENCES tasks(tid)
);

-- ─── Dispatcher Decisions ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dispatcher_decisions (
    decision_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    tid            TEXT NOT NULL,
    decision_type  TEXT NOT NULL,        -- BRANCH, SKIP, RETRY, SYNTHESIS, GATE_RESULT, PATH_CHOICE
    decision_value TEXT NOT NULL,
    rationale      TEXT,
    next_tid       TEXT,
    alt_tids       TEXT,
    timestamp      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (tid) REFERENCES tasks(tid)
);

-- ─── Follow Skill Tracking ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS follow_skill (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tid          TEXT NOT NULL,
    skill_name   TEXT NOT NULL,
    script_path  TEXT NOT NULL,
    executed_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (tid) REFERENCES tasks(tid)
);

-- ─── Alternative Paths (Multi-Way DAG) ─────────────────────────────
-- Ein TID kann mehrere alternative nächste TIDs haben.
-- Der User wählt via user-checkpoint.sh welchen Pfad.
CREATE TABLE IF NOT EXISTS alternative_paths (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    source_tid        TEXT NOT NULL,         -- TID nach dem die Alternativen existieren
    target_tid        TEXT NOT NULL,         -- möglicher nächster TID
    path_label        TEXT NOT NULL,         -- z.B. "A", "B", "C" — display label
    rationale         TEXT,                  -- Warum diese Option existiert
    tradeoffs         TEXT,                  -- Vor-/Nachteile (für User-Entscheidung)
    ranking           INTEGER DEFAULT 0,     -- 0 = default/primary, höher = alternative
    FOREIGN KEY (source_tid) REFERENCES tasks(tid),
    FOREIGN KEY (target_tid) REFERENCES tasks(tid)
);

-- ─── User Decisions (Approval Checkpoints) ─────────────────────────
-- Jeder requires_approval-Checkpoint erzeugt ein user_decisions-Eintrag.
CREATE TABLE IF NOT EXISTS user_decisions (
    decision_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    after_tid      TEXT NOT NULL,           -- TID nach dem die Entscheidung fiel
    decision       TEXT NOT NULL,           -- CONTINUE, MODIFY, SKIP, REDIRECT_PATH_A, REDIRECT_PATH_B, ABORT
    selected_tid   TEXT,                    -- Welcher TID als nächstes (falls REDIRECT)
    user_rationale TEXT,                    -- User's Begründung (optional)
    timestamp      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (after_tid) REFERENCES tasks(tid)
);

-- ─── Template Markers (Drift-Detection) ─────────────────────────────
-- Definiert was eine Output-Datei MUSS enthalten, um als drift-free zu gelten.
-- Verifiziert von verify-template.sh.
CREATE TABLE IF NOT EXISTS template_markers (
    marker_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id    TEXT NOT NULL,           -- z.B. "design-doc", "implementation-plan"
    marker_type    TEXT NOT NULL,           -- SECTION_HEADER, MARKER_LINE, REQUIRED_FILE, TAG_PATTERN
    pattern        TEXT NOT NULL,           -- regex oder literal
    severity       TEXT DEFAULT 'ERROR',   -- ERROR (fail) | WARNING (warn)
    description    TEXT,
    UNIQUE(template_id, pattern)
);

-- ─── Indexes ──────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_run ON tasks(run_id, phase_seq);
CREATE INDEX IF NOT EXISTS idx_pre_tasks_tid ON pre_tasks(tid);
CREATE INDEX IF NOT EXISTS idx_decisions_tid ON dispatcher_decisions(tid);
CREATE INDEX IF NOT EXISTS idx_follow_tid ON follow_skill(tid);
CREATE INDEX IF NOT EXISTS idx_alt_source ON alternative_paths(source_tid);
CREATE INDEX IF NOT EXISTS idx_user_after ON user_decisions(after_tid);
CREATE INDEX IF NOT EXISTS idx_template ON template_markers(template_id);
