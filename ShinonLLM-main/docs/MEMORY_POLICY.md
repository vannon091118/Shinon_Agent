# Memory Policy (Canonical)

This document is the single source of truth for runtime memory policy.

## Two-Tier Memory Architecture (New in 0.3.0)

ShinonLLM uses a two-tier memory system that separates concrete facts from abstract patterns.

### Tier 1: Personal (Concrete Facts)

Stores specific events, quotes, and observations about the user.

- **Content**: Exact statements with timestamps and context
- **Example**: `"User said on 2026-04-01: 'I am happy with my girlfriend Anna'"`
- **Retention**: Permanent until explicit deletion or user request
- **Access**: Retrieved via pattern anchors from Tier 2
- **Schema**: `personal_facts` table with `id`, `content`, `category`, `created_at`, `session_id`

### Tier 2: Pattern (Abstract Anchors)

Stores generalized patterns with confidence scores, linked to Tier 1 facts.

- **Content**: Pattern types with confidence and example references
- **Example**: `{"anchor": "relationship-inconsistency", "confidence": 0.85, "linked_facts": ["fact_001", "fact_042"]}`
- **Retention**: Updated continuously; confidence scores decay if not reinforced
- **Access**: Primary retrieval mechanism for the runtime
- **Schema**: `patterns` table with `id`, `anchor`, `type`, `confidence`, `examples_json`, `created_at`

### Cross-Tier Linking

Patterns link to facts via the `pattern_links` table:

- `pattern_id`: Reference to Tier 2 pattern
- `fact_id`: Reference to Tier 1 fact
- `relation_type`: `supports`, `contradicts`, `example_of`

## Zone Management (New in 0.3.0)

Memory is organized into three zones based on temporal relevance.

### Hot Zone (Current Session)

- **Scope**: Current active session and conversation
- **Access**: Unfiltered, all entries available
- **Storage**: In-memory + SQLite (immediate persistence)
- **Transition**: On session end → Mid Zone

### Mid Zone (Last 10 Sessions)

- **Scope**: 10 most recent sessions per user
- **Access**: Score-based selection (top 20% by relevance)
- **Storage**: SQLite with indexed retrieval
- **Transition**: Sessions older than 10 → Cold Zone
- **Query**: `SELECT ... ORDER BY score DESC LIMIT 20%`

### Cold Zone (Archive)

- **Scope**: All sessions older than 10
- **Access**: Pattern-extracted summaries only
- **Hardening**: Automated pattern extraction from raw facts
- **Process**:
  1. Extract patterns from accumulated facts
  2. Update Tier 2 anchors with confidence scores
  3. Compress Tier 1 to essential examples only
  4. Remove redundant raw entries

## Runtime knobs

- `SHINON_MEMORY_TTL_SECONDS`: Optional positive integer. If set, appended entries get `expiresAt = createdAt + ttl`.
- `SHINON_MEMORY_KEEP_LATEST_PER_CONVERSATION`: Optional positive integer. Controls decay retention count per `(sessionId, conversationId)`; invalid values fall back to internal default.
- `SHINON_MEMORY_SQLITE_PATH`: Optional explicit SQLite file path override.
- `SHINON_MEMORY_SQLITE=1`: Explicit SQLite enable flag. If set and no explicit path is provided, runtime uses OS app-data defaults.

## SQLite enable and path behavior

SQLite is active when either of these is true:

- `SHINON_MEMORY_SQLITE=1`
- `SHINON_MEMORY_SQLITE_PATH` is non-empty

Default path when `SHINON_MEMORY_SQLITE=1` and no explicit path is provided:

- Windows: `%LOCALAPPDATA%/ShinonLLM/session-memory.sqlite`
- macOS: `~/Library/Application Support/ShinonLLM/session-memory.sqlite`
- Linux: `$XDG_DATA_HOME/ShinonLLM/session-memory.sqlite` or `~/.local/share/ShinonLLM/session-memory.sqlite`

Parent directories are created before opening the database.

## Fail-closed vs best-effort

- Contract parsing / memory input validation: fail-closed (invalid payloads throw `BAD_REQUEST`).
- SQLite schema compatibility: fail-closed (unknown newer schema version aborts initialization).
- `SHINON_MEMORY_SQLITE=1` with init or migration failure: fail-fast startup error (no silent fallback).
- SQLite path-only mode (`SHINON_MEMORY_SQLITE_PATH` without explicit flag): best-effort fallback to in-memory if SQLite runtime init fails.
- **NEW**: Tier boundary violations (accessing Tier 2 as Tier 1) are fail-closed.
- **NEW**: Zone boundary violations (unauthorized Cold Zone access) throw `MEMORY_ACCESS_DENIED`.

## SQLite schema and migrations

- Migration mechanism: `PRAGMA user_version`.
- `user_version=0`: create v1 schema and indexes, then set `user_version=1`.
- `user_version=1`: current supported schema (session_memory_entries only).
- `user_version=2`: **NEW** adds `personal_facts`, `patterns`, `pattern_links`, `attitudes` tables.
- `user_version>2`: blocked fail-closed until explicit migration support is added.

### v1 → v2 Migration (Manual)

When upgrading to 0.3.0:

1. Backup existing database
2. Create new tables (personal_facts, patterns, pattern_links, attitudes)
3. Migrate existing `session_memory_entries` to `personal_facts` (category: 'chat_history')
4. Set `PRAGMA user_version = 2`
5. Verify with `npm run verify:backend`

## Pattern Extraction Policy

### Automatic Extraction (Cold Zone Hardening)

When entries move to Cold Zone:
- Extract pattern types: `preference`, `commitment`, `relationship`, `contradiction`
- Calculate confidence: `0.0 - 1.0` based on frequency and consistency
- Create anchors: Hash-based unique identifiers
- Link examples: Reference supporting Tier 1 facts

### Confidence Decay

Pattern confidence decays if not reinforced:
- `confidence *= 0.95` per week without new examples
- Minimum threshold: `0.3` (patterns below are archived, not deleted)
- Maximum threshold: `0.95` (capped to prevent overconfidence)

## Attitude Storage (New in 0.3.0)

User-specific attitude scores are stored in the `attitudes` table:

- `user_id`: Unique user identifier
- `dimension`: `warmth`, `respect`, `patience`, `trust`
- `score`: `-10` (negative) to `+10` (positive)
- `updated_at`: Last modification timestamp
- `history_json`: Array of `{score, reason, timestamp}` for audit trail

Attitude updates are deterministic and reproducible (required for replay gate).

---

*This policy applies to all memory operations in ShinonLLM 0.3.0+.*

