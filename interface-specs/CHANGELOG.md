# Contracts — Changelog

## 2026-08-12 — Initial Release (v1.0.0)

### Added
- `run-manifest.schema.json` — JSON Schema for cross-component session document
- `shinon.contract.json` — ShinonLLM character layer contract
- `promtguard.contract.json` — Promtguard prompt layer contract
- `karma.contract.json` — KARMA cognition layer contract
- `goal-chain.contract.json` — goal-chain orchestration layer contract
- `limen.contract.json` — LIMEN infrastructure layer contract
- `WIRING.md` — Full pipeline wiring with handoff sequence and claim status mapping
- `session.example.json` — Example pipeline run

### goal-chain P0 Bugfixes (2026-08-12)

| Bug | Description | Files Changed |
|-----|-------------|---------------|
| P0-1 | `verify-template.sh` now runs BEFORE `tid_done()` — prevents pipeline stall when drift detected after DONE | `complete.sh` |
| P0-2 | Gate file (PASS/FAIL) is now evaluated: PASS → skip next phase (TIDs marked SKIPPED), FAIL → continue | `complete.sh`, `tid-helpers.sh` |
| P0-2b | Gate logic runs BEFORE user-checkpoint (which exits with `exit 0`, blocking gate routing) | `complete.sh` |
| P0-3 | MARKER_LINE regex now uses `grep -E` instead of `grep -F` + `sed` escaping. Field delimiter changed from `\|` to ASCII Unit Separator (`\x1f`) to avoid collision with regex alternation | `verify-template.sh` |

### Design Decisions
- **Claim status mapping**: Promtguard `verified` → KARMA `supported`, Promtguard `refuted` → KARMA `refuted`. KARMA-native `confirmed` and `conflicted` are FalsificationGate-only.
- **Handoff direction**: LIMEN→GOAL-CHAIN return path (HOFF-0004b) added for API responses to chain scripts.
- **goal-chain position**: Integer `2` (KARMA's tool belt), not a separate sequential step.
- **Persistence**: Current state = 3 separate stores (JSONL + 2× SQLite). Planned = central SQLite with namespaces.
