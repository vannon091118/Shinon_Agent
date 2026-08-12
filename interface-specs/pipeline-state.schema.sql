-- ═══════════════════════════════════════════════════════════════════
-- pipeline-state.db — Run State Table
-- Cross-Component Pipeline State (mutable, queryable, SQLite)
--
-- Trennung vom Audit-Trail:
--   pipeline-state.db  → aktueller Stand (mutable, SQLite)
--   audit-trail.jsonl  → immutable Beweiskette (append-only, JSONL)
--
-- Diese Trennung reflektiert das existierende Pattern:
--   goal-chain  → SQLite für TID-State
--   Promtguard  → JSONL für Audit-Trail
-- ═══════════════════════════════════════════════════════════════════

PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

-- ─── Run State (ein Eintrag pro Pipeline-Run) ──────────────────
CREATE TABLE IF NOT EXISTS run_state (
    pipeline_run_id  TEXT PRIMARY KEY,                          -- RUN-{PREFIX}-{YYYYMMDD}-{HHMMSS}
    goal             TEXT NOT NULL,                             -- User's original goal
    project          TEXT NOT NULL,                             -- Project prefix (3-5 chars)
    status           TEXT NOT NULL DEFAULT 'INIT',              -- INIT|IN_PROGRESS|COMPLETED|FAILED|ABORTED
    current_phase    TEXT,                                      -- Current pipeline phase
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at     TEXT
);

-- ─── Component Status (ein Eintrag pro Komponente pro Run) ────
CREATE TABLE IF NOT EXISTS component_state (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_run_id  TEXT NOT NULL REFERENCES run_state(pipeline_run_id),
    component        TEXT NOT NULL CHECK(component IN ('shinon','promtguard','karma','goalchain','limen')),
    status           TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','ACTIVE','COMPLETED','FAILED','SKIPPED')),
    version          TEXT NOT NULL,
    started_at       TEXT,
    completed_at     TEXT,
    error_count      INTEGER DEFAULT 0,
    retry_count      INTEGER DEFAULT 0,
    input_artifact   TEXT,                                      -- artifact_id consumed
    output_artifact  TEXT,                                      -- artifact_id produced
    metadata_json    TEXT,                                      -- Component-specific metadata as JSON
    UNIQUE(pipeline_run_id, component)
);

-- ─── Artifact Registry ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id      TEXT PRIMARY KEY,                          -- ART-{PREFIX}-{SEQ}
    pipeline_run_id  TEXT NOT NULL REFERENCES run_state(pipeline_run_id),
    component        TEXT NOT NULL,
    type             TEXT NOT NULL,
    path             TEXT NOT NULL,
    sha256           TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    size_bytes       INTEGER
);

-- ─── Claims (Cross-Referenced from Promtguard → KARMA) ─────────
CREATE TABLE IF NOT EXISTS claims (
    claim_id         TEXT PRIMARY KEY,                          -- CLAIM-{PREFIX}-{SEQ}
    pipeline_run_id  TEXT NOT NULL REFERENCES run_state(pipeline_run_id),
    source_component TEXT NOT NULL CHECK(source_component IN ('promtguard','karma')),
    status           TEXT NOT NULL DEFAULT 'unverified' CHECK(status IN ('unverified','supported','confirmed','refuted','conflicted')),
    verified_by      TEXT CHECK(verified_by IN ('karma','promtguard')),
    verified_at      TEXT,
    UNIQUE(claim_id, pipeline_run_id)
);

-- ─── Metrics (aggregiert nach Run-Ende) ────────────────────────
CREATE TABLE IF NOT EXISTS metrics (
    pipeline_run_id       TEXT PRIMARY KEY REFERENCES run_state(pipeline_run_id),
    total_tokens          INTEGER DEFAULT 0,
    total_cost_usd        REAL DEFAULT 0.0,
    total_duration_ms     INTEGER DEFAULT 0,
    api_calls             INTEGER DEFAULT 0,
    retries               INTEGER DEFAULT 0,
    claims_verified       INTEGER DEFAULT 0,
    claims_refuted        INTEGER DEFAULT 0,
    gates_passed          INTEGER DEFAULT 0,
    gates_failed          INTEGER DEFAULT 0
);

-- ─── Indexes ────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_component_run ON component_state(pipeline_run_id, component);
CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifacts(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_claims_run ON claims(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
