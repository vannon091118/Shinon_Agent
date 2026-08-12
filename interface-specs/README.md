# Control Plane — Interface Specifications

## Overview

This directory defines the **Cross-Component Interface Specifications** for the LLM Control Plane pipeline. Every component declares its input, output, state, and implementation status. Pipeline state lives in **SQLite** (`pipeline-state.db`), the immutable audit trail in **JSONL** (`audit-trail.jsonl`).

## Architecture Decision: State vs. Audit (Evil Twin Synthesis)

| Concern | Store | Type | Why |
|---------|-------|------|-----|
| **Pipeline State** | `pipeline-state.db` | SQLite (mutable) | Queryable, concurrent-safe, goal-chain-kompatibel |
| **Audit Trail** | `audit-trail.jsonl` | JSONL (append-only) | Immutable, replay-fähig, Promtguard-kompatibel |

Originally designed as a single `session.json`. Evil Twin correctly identified this as an anti-pattern: mixing mutable state with immutable audit in one document. The existing components already implement this separation (Promtguard JSONL, goal-chain SQLite) — the interface specs now correctly reflect this architectural truth.

## Files

| File | Purpose |
|------|---------|
| `pipeline-state.schema.sql` | SQLite schema for pipeline run state |
| `audit-trail.schema.json` | JSONL event schema for immutable audit trail |
| `run-manifest.schema.json` | LEGACY — superseded by `pipeline-state.schema.sql` + `audit-trail.schema.json`. Kept for reference. |
| `session.example.json` | LEGACY — example of the old combined format. Kept for migration reference. |
| `shinon.contract.json` | ShinonLLM: character layer specification + implementation status |
| `promtguard.contract.json` | Promtguard: prompt layer specification + implementation status |
| `karma.contract.json` | KARMA: cognition layer specification + implementation status |
| `goal-chain.contract.json` | goal-chain: orchestration layer specification + implementation status |
| `limen.contract.json` | LIMEN: infrastructure layer specification + implementation status |
| `WIRING.md` | Pipeline wiring: handoff sequence, claim mapping, persistence architecture |
| `CHANGELOG.md` | Version history and P0 bugfix documentation |

## Design Principles

1. **Specifications describe intent, `implementation_status` describes reality.** Every spec has a `known_gaps` section.
2. **Components are loosely coupled.** Communication goes through well-defined artifacts and handoffs recorded in the audit trail.
3. **The audit trail is append-only.** Immutable. Replay-fähig. Never modified.
4. **Pipeline state is queryable.** SQLite with WAL mode. Components read/write their own status.
5. **Every component fails closed.** Invalid input → rejection with error code. Invalid output → blocked at handoff.
