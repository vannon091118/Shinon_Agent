# HANDSHAKE CURRENT STATE

Date: 2026-04-05  
Release baseline: 0.3.0-alpha  
Scope: "Real Persona with Two-Tier Memory"

## One-line truth

Shinon ist eine **Real Persona** mit Gedächtnis, Haltungen und der Fähigkeit zum Konfrontieren – gebaut auf lokaler Runtime-Intelligenz, nicht auf Cloud-Prompt-Tricks.

## Current architecture state

- **Runtime entry and request validation** are active in `backend`.
- **Contract-first orchestration** is active in `orchestrator`.
- **Character Runtime Integration** (NEW) - Pattern Engine → Two-Tier Memory → Attitude Tracker → Prompt Generator flow implemented in `orchestrator/src/pipeline/orchestrateTurn.ts`.
- **Inference routing** is active in `inference` with retry mechanism and llama.cpp/Ollama support.
- **Session memory** (v1) exists in `memory` with SQLite persistence via `PRAGMA user_version` (v0 → v1).
- **Determinism and baseline gates** exist in `tests/gates`.
- **Live Inference** tested via llama.cpp (Qwen 0.5B local) for DE, EN, JP.
- **Frontend Memory Binding** is active (sessionId/conversationId passed to ChatShell).

## [DEV] Developer Tools (NEW)

The following DEV-marked panels are now available in the Frontend:

- **[DEV] Model Selector** (`frontend/src/components/dev/ModelSelector.tsx`)
  - Scans `%APPDATA%/ShinonLLM/models` for `.gguf` files
  - Shows required models (Qwen 2.5 0.5B, Llama 3.2 1B)
  - Download links for missing required models
  - Model selection with size/parameters display
  - API: `GET /api/models`

- **[DEV] Debug Panel** (`frontend/src/components/dev/DevDebugPanel.tsx`)
  - Real-time debug logging via `window.shinonDebug(level, component, message, data)`
  - Filter by component or log level (info/warn/error/debug)
  - Collapsible floating panel
  - Shows timestamp, component, and JSON data

- **[DEV] Processing Pipeline Panel** (`frontend/src/components/dev/DevProcessingPanel.tsx`)
  - Visual pipeline: input → pattern-analysis → memory-retrieval → attitude-check → prompt-generation → inference → output-validation
  - Shows WAS verarbeitet wurde (what was processed)
  - Per-message processing tracking
  - Stage status indicators (pending/active/complete/error)

## New architecture components (Scope 0.3.0)

The following components are **IMPLEMENTED** for the new character-based architecture:

- `character/core/identity.ts` - Shinons feste Basis-Personality
- `character/attitudes/tracker.ts` - Dynamische Haltungen pro User (-10 bis +10)
- `character/experience/patterns.ts` - Pattern-Erkennung & Anker-Bildung
- `character/experience/twoTierMemory.ts` - Schicht 1 (Fakten) + Schicht 2 (Patterns)
- `character/state/emotional.ts` - Aktuelle Stimmung pro Session
- `character/prompts/generator.ts` - "Shinons Gedanken"-Prompts für LLM
- `memory/zones/hotZone.ts` - Aktuelle Session (ungefilterter Zugriff)
- `memory/zones/midZone.ts` - Letzte 10 Sessions (selektiver Zugriff)
- `memory/zones/coldZone.ts` - Archiv mit Pattern-Härtung

**Runtime Integration (NEW):**
- `orchestrator/src/pipeline/orchestrateTurn.ts` - Character-aware orchestration flow
  - Step 1 & 2: Hot Zone (Tier 1) + Pattern Check (Tier 2)
  - Step 3: Attitude Check (-10 to +10)
  - Step 5: Prompt Generator with character context
  - Passes patterns, facts, attitudes, and tone directives to LLM

## Security boundaries verified in current state

- Live `/api/chat` traffic is validated before route execution.
- Client-supplied `system` and `assistant` roles are not accepted as trusted orchestration history.
- The orchestrator injects the trusted system prompt server-side for backend calls.
- Backend failure and fallback failure are fail-closed; prompt content is not echoed back as a fake successful assistant reply.

## Determinism and verification policy

Mandatory checks:

1. `npm run test:determinism`
2. `npm run verify:backend`
3. `npm --prefix frontend run build`

Fail-closed principle:

- If contract, replay, or baseline checks fail, release handshake is blocked.
- New character components must maintain determinism in pattern extraction and attitude calculation.

## Latest verification run

Executed on 2026-04-05:

- `npm run test:determinism` → PASS
- `npm run verify:backend` → PASS
- `npm run test:e2e` → PASS
- Documentation restructuring → PASS

## Scope boundaries: Two-Tier Memory Architecture

**MVP Phase (0.3.0-alpha):**
- Local-first, persistent session runtime optimized for 0.5B-7B models.
- Two-Tier Memory: Tier 1 (Personal facts) + Tier 2 (Pattern anchors).
- Hot/Mid/Cold Zones with automated pattern extraction from Cold Zone.
- Character attitudes tracked across sessions (warmth, respect, patience, trust).
- Confrontation mode when pattern confidence > 0.8 and patience < 5.

**Product Phase (0.4.0+):**
- Real Persona behavior through Pattern Analytics scoring (Impact & Frequency).

## Open risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Model Context Bleed** | Medium | llama.cpp KV-cache bleeds previous replies; needs explicit cache isolation between REST calls |
| **Pattern Engine Not Implemented** | High | ✅ **IMPLEMENTED** - Regex-based preference/relationship detection active in runtime |
| **Character Attitudes Not Implemented** | High | ✅ **IMPLEMENTED** - Attitude tracker with SQLite persistence integrated in orchestrateTurn |
| **Two-Tier Schema Migration** | Medium | ✅ **IMPLEMENTED** - SQLite v1 → v2 migration with pattern tables active |
| **Cold Zone Härtung** | Medium | ✅ **IMPLEMENTED** - Pattern extraction from archive active |
| **Runtime Integration** | Medium | ✅ **IMPLEMENTED** - Character-aware flow (Pattern → Memory → Attitude → Prompt) active |
| **Frontend Proxy Auth** | Low | No end-user auth on `/api/chat` yet; tolerable for local dev, security risk for network exposure |
| **Model Management UX** | Low | ✅ **ADDRESSED** - DEV Model Selector provides download links and required model enforcement |

## Next checkpoint

After implementing:
1. SQLite Schema v2 (pattern tables, attitude tracking)
2. Hot/Mid/Cold Zone management
3. Basic pattern extraction (preference, commitment, relationship, contradiction)
4. Attitude tracker with confrontation thresholds
5. Character-aware prompt generator

Bump to 0.3.0-beta and run full determinism verification suite.

## Documentation Reference

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview with AGENTS-style directness |
| `LLM_ENTRY.md` | Mandatory entry gate for developers |
| `ARCHITECTURE_OVERVIEW.md` | Component structure and data flow |
| `MEMORY_POLICY.md` | Two-Tier + Zone Management rules |
| `OPS_PLAYBOOKS.md` | Operational troubleshooting |
| `LOCAL_LLAMACPP_SETUP.md` | Local LLM setup guide |

---

*This is the authoritative current state. For historical versions, check git history.*
