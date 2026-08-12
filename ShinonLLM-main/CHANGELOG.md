# Changelog

All notable changes to this project will be documented in this file.

The format follows Keep a Changelog and this project adheres to Semantic Versioning.

## [Unreleased]

### Planned (deferred to next release)

- Memory: Impact-weighted scoring (weight entries by user engagement, not just recency).
- Inference: Persona drift detection mode ("Drift-Schutz").
- Inference: Internal model evaluation pipeline (benchmark small models for quality/speed).
- Ops: CI status badges in README (needs `Vannon0911/ShinonLLM` slug replacement).
- Legal: Final licensing decision (current `LICENSE` is Apache-2.0).

### Added (Recent)

- Frontend: `sessionId` + `conversationId` auto-generation using `node:crypto` in `app/page.tsx`.
- Memory: Stubbed `getConceptFrequencies` for frequency-based pattern tracking.
- Test: Added Smoke Test Plan `SMOKE_TEST_PLAN.md` (now removed/migrated).
- Frontend: UI hardening with 25000 character limit protection.
- Backend: SQLite memory persistence enabled by default with server logs.

## [0.2.3a] - 2026-04-03

### Added

- Runtime stress test verification: 6 test cases (German, English, Japanese/Unicode, nonsense, long-string, empty input) validated through live llama.cpp Qwen 0.5B inference.
- Memory Policy audit: full implementation-vs-documentation verification completed.
- Backend retry mechanism: `inference/src/retry/backendRetry.ts` for reliable service availability.
- Backend SQLite session persistence with schema migrations (`PRAGMA user_version`).
- `AGENTS.md` repo-level agent interaction rules.
- GitHub issue templates (bug report, feature request), PR template, Dependabot config.
- CI workflow (`ci.yml`) and hardened release workflow (`release.yml`).
- `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE` (Apache-2.0).
- Runtime control scripts: `start-local.ps1`, `stop-local.ps1`.
- Ops scripts: `release-smoke.ps1`, `start-llamacpp.ps1`, `cleanup-frontend-next.ps1`.
- Docs: `ARCHITECTURE_OVERVIEW.md`, `MEMORY_POLICY.md`, `OPS_PLAYBOOKS.md`, `gemini.md`.
- Docs: Validation matrix `MATRIX__VALIDATION_GATES.md`.
- Visual assets for GitHub presentation: hero banner, problem/solution comparison, architecture diagram, live chat UI screenshot.

### Changed

- README completely rewritten: product-pitch narrative (WHY Shinon, MVP scope, long-term vision, real statistics, scoring formula), replaces pure tech-doc approach.
- CHANGELOG restructured: unfinished items explicitly deferred to `[Unreleased]` with clear scope notes.
- Scoring engine documented with actual formula: `relevance×0.70 + intentMatch×0.20 + recency×0.05 + structural×0.05 + positionBonus×0.01`.
- Backend router now integrates retry mechanism for reliable inference service availability.
- Frontend chat UX hardened for request timeout and concurrent send protection.
- Package versions at `0.2.3` (root/backend/frontend).

### Verified

- llama.cpp Qwen 0.5B: live inference verified for DE/EN/JP/Unicode input.
- Session memory persistence: InMemory implementation active (SQLite code ready, not activated by default).
- Contract gates, replay gates, baseline integrity gates: all passing.
- 9 test suites across gates/unit/integration/e2e.
- 52 TypeScript source files across 8 modules.

### Known Issues

- llama.cpp KV-cache bleeds context across requests when given nonsense input (model-level, not runtime-level).
- Qwen 0.5B identity hallucination: model sometimes claims to be "ein Wörterbuch" without a system prompt.

## [0.2.3] - 2026-04-02

### Added

- Root local runtime control scripts:
  - `start-local.ps1`
  - `stop-local.ps1`
- Repo hygiene artifacts:
  - `.editorconfig`
  - `.gitattributes`

### Changed

- Runtime policy hardened to live execution with mandatory offline evaluator and replay hash evidence.
- Memory decay handling hardened in write path (no optional runtime skip).
- Frontend chat UX hardened to avoid blocked input/model selection during in-flight requests and to enforce request timeout behavior.
- Package versions promoted from `0.2.1-a` to stable `0.2.3` (root/backend/frontend + lockfiles).

## [0.2.1a] - 2026-04-02

### Added

- MVP target architecture documentation based on `FELIX_SYSTEM_ARCHITECTURE-1.docx`.
- Session memory persistence contract test coverage integrated into backend verification scripts.

### Changed

- Project/package versions moved to semver-compatible prerelease `0.2.1-a`.
- Target system overview rewritten for runtime-first MVP scope alignment.

## [0.2.0] - 2026-04-02

### Added

- Canonical API path support for `/api/chat` and `/api/health`.
- GitHub release playbook with visual assets.
- Local llama.cpp setup guide and Quick-QA script.

### Changed

- Chat route now uses orchestrator execution by default instead of implicit echo fallback.
- Integration tests updated for orchestrator-default behavior.
- Local ops runtime scripts validate presence of llama.cpp model files before startup.

## [0.1.0] - 2026-04-02

### Added

- Initial runtime contracts, gate checks, and architecture baseline.
