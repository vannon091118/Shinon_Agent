# ShinonLLM - Technical Manual

> **Version:** 0.3.0-alpha  
> **Scope:** Real Persona with Two-Tier Memory  
> **Last Updated:** 2026-04-05

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Scripts & Commands](#scripts--commands)
4. [Module Reference](#module-reference)
5. [Data Sources & Storage](#data-sources--storage)
6. [Environment Variables](#environment-variables)
7. [Testing & Verification](#testing--verification)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites
- Node.js 18+
- PowerShell 5.1+ (Windows)
- SQLite (optional, for persistent memory)
- Local LLM (llama.cpp or Ollama)

### First Run
```powershell
# 1. Install dependencies
npm install

# 2. Start full stack (Backend + Frontend + LLM)
npm run start:local

# 3. Access application
# Frontend: http://127.0.0.1:3000
# Backend API: http://127.0.0.1:3001
```

### Stop Everything
```powershell
npm run stop:local
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                            │
│  Frontend (Next.js) - http://localhost:3000                      │
│  └─ Chat UI, Session Management, Settings                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API LAYER                               │
│  Backend (Express) - http://localhost:3001                     │
│  └─ Routes: /chat, /health                                     │
│  └─ Validation, Routing, Error Handling                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                        │
│  Orchestrator                                                  │
│  ├─ Contract Validation (inputSchema, outputSchema)            │
│  ├─ Pattern Recognition (NEW in 0.3.0)                         │
│  ├─ Attitude Tracking (NEW in 0.3.0)                         │
│  ├─ Prompt Generation (NEW in 0.3.0)                         │
│  └─ Turn Orchestration                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      INFERENCE LAYER                              │
│  Inference Router                                              │
│  ├─ llama.cpp Adapter (local, port 8000)                       │
│  ├─ Ollama Adapter (local, port 11434)                         │
│  └─ Retry Logic, Fallback Handling                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MEMORY LAYER (NEW in 0.3.0)                │
│  Two-Tier Memory System                                        │
│  ├─ Tier 1: Personal Facts (concrete)                          │
│  ├─ Tier 2: Pattern Anchors (abstract)                        │
│  └─ Hot/Mid/Cold Zone Management                              │
└─────────────────────────────────────────────────────────────────┘
```

### Core Principles
1. **Runtime thinks, LLM formulates text** - All logic in TypeScript, LLM only for text generation
2. **Two-Tier Memory** - Concrete facts (Tier 1) + Abstract patterns (Tier 2)
3. **Hot/Mid/Cold Zones** - Temporal memory organization with pattern hardening
4. **Fail-closed** - When uncertain, abort rather than guess
5. **Deterministic** - Same input must produce identical replay hash

---

## Scripts & Commands

### Root-Level Scripts (package.json)

| Script | Description | Usage |
|--------|-------------|-------|
| `start:local` | Start full stack (Backend + Frontend + LLM) | `npm run start:local` |
| `stop:local` | Stop all running services | `npm run stop:local` |
| `verify:full` | Run complete verification suite | `npm run verify:full` |
| `verify:full:node` | Node-based verification (no external deps) | `npm run verify:full:node` |
| `verify:backend` | Backend tests + gates | `npm run verify:backend` |
| `test:backend` | Backend tests only | `npm run test:backend` |
| `test:gates` | Contract + Replay + Baseline gates | `npm run test:gates` |
| `test:determinism` | Replay gate only | `npm run test:determinism` |
| `test:e2e` | End-to-end UI tests | `npm run test:e2e` |
| `test:baseline-integrity` | Baseline hash check | `npm run test:baseline-integrity` |

### PowerShell Scripts

#### `start-local.ps1`
**Purpose:** Launch complete local development stack

**Actions:**
1. Validates npm installation
2. Starts llama.cpp infrastructure (`ops/scripts/start-llamacpp.ps1`)
3. Launches Backend (port 3001) in new PowerShell window
4. Launches Frontend (port 3000) in new PowerShell window
5. Registers cleanup handlers for graceful shutdown

**Parameters:** None (interactive)

**Outputs:**
```
Starte llama.cpp Infrastruktur...
Lokaler Stack gestartet:
- Backend:  http://127.0.0.1:3001
- Frontend: http://127.0.0.1:3000
```

#### `stop-local.ps1`
**Purpose:** Terminate all running services

**Actions:**
1. Finds processes listening on ports 3000, 3001
2. Force-stops those processes
3. Runs frontend cleanup (`ops/scripts/cleanup-frontend-next.ps1`)

**Parameters:** None

#### `verify-full.ps1`
**Purpose:** Execute full verification suite

**Actions:**
1. Resolves npm command path
2. Executes `npm run verify:full:node`
3. Returns exit code from tests

---

## Module Reference

### `/backend/` - API Server
**Technology:** Express.js + TypeScript

**Structure:**
```
backend/
├── src/
│   ├── index.ts           # Entry point, server bootstrap
│   ├── routes/
│   │   ├── chat.ts        # /chat endpoint, main interaction
│   │   ├── health.ts      # /health endpoint, status check
│   │   └── models.ts      # /api/models endpoint (DEV: local model scanner)
│   └── utils/
│       └── validation.ts  # Request/response validation
└── package.json
```

**Key Functions:**
- `createChatRoute()` - Factory for chat route handler
- `chatRouteHandler()` - Processes chat requests
- `scanModels()` - [DEV] Scans `./models/` for .gguf files
- Health monitoring for load balancers

**Routes:**
- `POST /chat` - Main chat endpoint
- `GET /health` - Health check
- `GET /api/models` - [DEV] List local models with download links

**Source Data:**
- Input: HTTP POST /chat with JSON body
- Output: JSON with reply, model info, metadata
- Dependencies: orchestrator, memory, inference

### `/orchestrator/` - Business Logic
**Technology:** TypeScript (pure logic, no framework)

**Structure:**
```
orchestrator/
└── src/
    ├── contracts/
    │   ├── inputSchema.ts   # Input validation contracts
    │   └── outputSchema.ts  # Output validation contracts
    └── pipeline/
        ├── orchestrateTurn.ts  # Main orchestration logic
        └── buildPrompt.ts      # Prompt construction
```

**Key Functions:**
- `orchestrateTurn()` - Main entry for processing user input
- `buildRuntimePlan()` - Intent classification (regex-based, to be replaced)
- `buildPrompt()` - System prompt construction
- `normalizeInput()` - Input sanitization
- `applyGuardrails()` - Output validation

**NEW in 0.3.0 (Placeholder):**
- Pattern recognition integration
- Attitude tracking integration
- Dynamic prompt generation

**Source Data:**
- Input: Validated user text + history + memory context
- Output: Generated prompt bundle + routing decision
- Dependencies: memory, inference, character (NEW)

### `/inference/` - LLM Adapters
**Technology:** TypeScript + HTTP clients

**Structure:**
```
inference/
└── src/
    ├── adapters/
    │   ├── llamacppAdapter.ts   # llama.cpp integration
    │   └── ollamaAdapter.ts     # Ollama integration
    ├── errors/
    │   └── backendErrors.ts     # Error classification
    └── router/
        └── backendRouter.ts     # Routing + retry logic
```

**Key Functions:**
- `routeBackendCall()` - Routes to appropriate backend
- `callLlamaCpp()` - llama.cpp API communication
- `callOllama()` - Ollama API communication
- `evaluateOffline()` - Offline plan inference
- `classifyBackendError()` - Error categorization

**Source Data:**
- Input: Route decision + prompt payload
- Output: Model response + metadata
- External Calls: llama.cpp (localhost:8000), Ollama (localhost:11434)

### `/memory/` - Data Persistence
**Technology:** TypeScript + SQLite (optional)

**Structure:**
```
memory/
└── src/
    ├── longterm/
    │   └── memoryStore.ts       # Long-term storage interface
    ├── retrieval/
    │   ├── retrieveContext.ts   # Context retrieval logic
    │   └── scoreContext.ts      # Relevance scoring
    ├── session/
    │   ├── sessionMemory.ts     # Session memory management
    │   └── sessionPersistence.ts # SQLite persistence
    └── zones/                    # NEW in 0.3.0
        ├── hotZone.ts           # Current session (unfiltered)
        ├── midZone.ts           # Last 10 sessions (selective)
        └── coldZone.ts          # Archive (pattern hardening)
```

**Key Functions:**
- `createInMemorySessionMemoryPersistence()` - In-memory storage
- `createSqliteSessionMemoryPersistence()` - SQLite storage
- `retrieveContext()` - Fetch relevant context
- `scoreContext()` - Calculate relevance scores
- `decay()` - Remove expired entries

**NEW in 0.3.0 (Placeholder):**
- `createHotZone()` - Current session management
- `createMidZone()` - Recent session management
- `createColdZone()` - Archive with pattern extraction
- Two-tier memory queries

**Source Data:**
- SQLite Database: `%LOCALAPPDATA%/ShinonLLM/session-memory.sqlite`
- Schema v1: `session_memory_entries` table
- Schema v2 (NEW): `personal_facts`, `patterns`, `pattern_links`, `attitudes`

### `/character/` - Character System (NEW in 0.3.0)
**Technology:** TypeScript

**Structure:**
```
character/
└── src/
    ├── core/
    │   └── identity.ts          # Shinon's fixed personality
    ├── attitudes/
    │   └── tracker.ts           # Dynamic user attitudes
    ├── experience/
    │   ├── patterns.ts          # Pattern recognition
    │   └── twoTierMemory.ts     # Tier 1 + Tier 2 management
    ├── state/
    │   └── emotional.ts         # Session emotional state
    └── prompts/
        └── generator.ts         # Character-aware prompts
```

**Key Functions:**
- `getCoreIdentity()` - Returns Shinon's base personality
- `createAttitudeState()` - Initialize attitude tracking
- `updateAttitude()` - Modify attitude based on patterns
- `shouldConfront()` - Determine confrontation threshold
- `extractPattern()` - Identify patterns from facts
- `findContradictions()` - Detect inconsistencies
- `generatePrompt()` - Create "Shinon's thoughts" prompts

**Source Data:**
- Attitude dimensions: warmth, respect, patience, trust (-10 to +10)
- Pattern types: preference, commitment, relationship, contradiction
- Emotional states: neutral, amused, annoyed, concerned, curious, confrontational

### `/frontend/` - User Interface
**Technology:** Next.js 14 + React + TypeScript

**Structure:**
```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx           # Main chat page
│   │   └── layout.tsx         # Root layout
│   └── components/
│       ├── chat/
│       │   └── ChatShell.tsx      # Main chat component
│       └── dev/
│           ├── ModelSelector.tsx      # [DEV] Model selection UI
│           ├── DevDebugPanel.tsx      # [DEV] Debug logging panel
│           └── DevProcessingPanel.tsx # [DEV] Processing pipeline vis
├── public/
└── package.json
```

**Key Functions:**
- `ChatShell` - Main chat interface with DEV panels
- `ModelSelector` - [DEV] Select local .gguf models
- `DevDebugPanel` - [DEV] Real-time debug logging
- `DevProcessingPanel` - [DEV] Visual processing pipeline
- `page.tsx` - Route handler with session management
- API client for backend communication

**[DEV] Tools:**
- **Model Selector**: Scans `./models/*.gguf`, shows required models (Qwen 2.5 0.5B, Llama 3.2 1B), download links for missing
- **Debug Panel**: `window.shinonDebug(level, component, message, data)` - filterable real-time logs
- **Processing Panel**: Visual pipeline: input → pattern-analysis → memory-retrieval → attitude-check → prompt-generation → inference → output-validation

**Source Data:**
- Backend API: http://127.0.0.1:3001
- Session storage: localStorage (sessionId, conversationId)
- Model storage: `./models/*.gguf` (local project directory)

### `/shared/` - Utilities
**Technology:** TypeScript

**Structure:**
```
shared/
└── src/
    └── utils/
        ├── hash.ts            # Deterministic hashing
        ├── serialization.ts   # JSON serialization helpers
        └── humanErrors.ts     # NEW: Human-readable errors
```

**Key Functions:**
- `buildReplayHash()` - Deterministic hash for verification
- `serializeDeterministically()` - Stable JSON serialization
- `ErrorCatalog` - Human-readable error messages
- `failClosedWithHumanMessage()` - Fail-closed with context

### `/telemetry/` - Observability
**Technology:** TypeScript

**Structure:**
```
telemetry/
└── src/
    ├── events.ts              # Event logging
    └── replay.ts              # Replay support
```

**Key Functions:**
- `emitEvent()` - Log telemetry events
- `createReplayArtifact()` - Generate replay data
- `validateReplay()` - Verify determinism

### `/tests/` - Test Suite
**Technology:** Node.js Test Runner + TypeScript

**Structure:**
```
tests/
├── e2e/
│   └── chat-ui.spec.ts      # End-to-end UI tests
├── gates/
│   ├── baseline-integrity.spec.ts  # Hash consistency
│   ├── contract-gate.spec.ts       # Schema validation
│   └── replay-gate.spec.ts         # Determinism verification
├── integration/
│   ├── chat-flow.spec.ts     # Full flow tests
│   └── fallback.spec.ts       # Backend failover tests
└── unit/
    ├── orchestrator.spec.ts   # Orchestrator logic
    ├── router.spec.ts         # Backend routing
    └── session-persistence.spec.ts # Memory storage
```

**Test Execution:**
- Unit tests: `node --import tsx ./tests/unit/<name>.spec.ts`
- Integration: `node --import tsx ./tests/integration/<name>.spec.ts`
- Gates: `node --import tsx ./tests/gates/<name>.spec.ts`
- E2E: `node --import tsx ./tests/e2e/<name>.spec.ts`

---

## Data Sources & Storage

### SQLite Database

**Location:**
- Windows: `%LOCALAPPDATA%/ShinonLLM/session-memory.sqlite`
- macOS: `~/Library/Application Support/ShinonLLM/session-memory.sqlite`
- Linux: `~/.local/share/ShinonLLM/session-memory.sqlite`

**Schema v1 (Current):**
```sql
CREATE TABLE session_memory_entries (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT,
  metadata_json TEXT
);
```

**Schema v2 (Planned for 0.3.0):**
```sql
-- Tier 1: Personal Facts
CREATE TABLE personal_facts (
  id TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  category TEXT NOT NULL, -- 'preference', 'event', 'commitment', 'relationship'
  created_at TEXT NOT NULL,
  session_id TEXT NOT NULL
);

-- Tier 2: Pattern Anchors
CREATE TABLE patterns (
  id TEXT PRIMARY KEY,
  anchor TEXT NOT NULL UNIQUE,
  type TEXT NOT NULL, -- 'preference', 'commitment', 'relationship', 'contradiction'
  confidence REAL NOT NULL, -- 0.0 to 1.0
  examples_json TEXT, -- Array of fact references
  created_at TEXT NOT NULL
);

-- Cross-tier linking
CREATE TABLE pattern_links (
  pattern_id TEXT NOT NULL,
  fact_id TEXT NOT NULL,
  relation_type TEXT NOT NULL, -- 'supports', 'contradicts', 'example_of'
  PRIMARY KEY (pattern_id, fact_id)
);

-- User attitudes
CREATE TABLE attitudes (
  user_id TEXT NOT NULL,
  dimension TEXT NOT NULL, -- 'warmth', 'respect', 'patience', 'trust'
  score INTEGER NOT NULL, -- -10 to +10
  updated_at TEXT NOT NULL,
  history_json TEXT,
  PRIMARY KEY (user_id, dimension)
);
```

**Migration:**
- Mechanism: `PRAGMA user_version`
- v0 → v1: Create initial schema
- v1 → v2: Create new tables, migrate data

### Environment-Based Configuration

**File:** None (environment variables only)

**Purpose:** Runtime knobs for memory behavior

---

## Environment Variables

### Memory Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SHINON_MEMORY_TTL_SECONDS` | integer | undefined | Entry expiration time |
| `SHINON_MEMORY_KEEP_LATEST_PER_CONVERSATION` | integer | 32 | Retention count per conversation |
| `SHINON_MEMORY_SQLITE` | flag | undefined | Enable SQLite (set to `1`) |
| `SHINON_MEMORY_SQLITE_PATH` | string | OS-dependent | Override default SQLite path |

**Examples:**
```powershell
# Windows PowerShell
$env:SHINON_MEMORY_SQLITE=1
$env:SHINON_MEMORY_SQLITE_PATH="C:\Shinon\memory.sqlite"

# Linux/macOS
export SHINON_MEMORY_SQLITE=1
export SHINON_MEMORY_SQLITE_PATH="/var/shinon/memory.sqlite"
```

### LLM Backend Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LLAMA_CPP_BASE_URL` | string | `http://127.0.0.1:8000` | llama.cpp server URL |
| `OLLAMA_BASE_URL` | string | `http://127.0.0.1:11434` | Ollama server URL |

**Note:** These are used by adapters in `/inference/src/adapters/`

---

## Testing & Verification

### Verification Levels

#### Level 1: Backend Tests
**Command:** `npm run test:backend`

**Coverage:**
- Unit: orchestrator, router, session-persistence
- Integration: fallback, chat-flow

**Duration:** ~10-30 seconds

#### Level 2: Gates
**Command:** `npm run test:gates`

**Coverage:**
- Contract Gate: Schema validation
- Replay Gate: Determinism verification
- Baseline Integrity: Hash consistency

**Duration:** ~5-15 seconds

#### Level 3: Full Verification
**Command:** `npm run verify:backend`

**Coverage:** Backend Tests + Gates

**Duration:** ~15-45 seconds

#### Level 4: Complete Verification
**Command:** `npm run verify:full`

**Coverage:** Full verification + Frontend build + E2E tests

**Duration:** ~1-2 minutes

**Requirements:** Running backend + frontend servers

### Determinism Requirements

**Replay Hash:** Must be identical for identical inputs

**Factors affecting determinism:**
- Timestamps (use normalized/rounded)
- Random values (avoid or seed)
- Sorting (stable algorithms)
- Floating point (consistent precision)

**Verification:**
```typescript
// In test files
const hash1 = buildReplayHash(input1);
const hash2 = buildReplayHash(input2);
assert.strictEqual(hash1, hash2); // Must pass
```

---

## Troubleshooting

### Common Issues

#### Issue: `npm run start-local` fails with "Backend-Verzeichnis fehlt"
**Cause:** Running from wrong directory
**Fix:** Run from repository root
```powershell
cd C:\Users\Vannon\OneDrive\Desktop\LLmrab\ShinonLLM
npm run start-local
```

#### Issue: Ports 3000/3001 already in use
**Cause:** Previous session not properly stopped
**Fix:**
```powershell
npm run stop-local
# Or manually:
Get-NetTCPConnection -LocalPort 3000,3001 | Stop-Process -Force
```

#### Issue: llama.cpp not reachable
**Cause:** Model not downloaded or wrong port
**Fix:**
```powershell
# Check if llama.cpp is running
curl http://127.0.0.1:8000/health

# Start llama.cpp manually
.\ops\scripts\start-llamacpp.ps1 -ModelFile 'qwen2.5-0.5b-instruct-q4_k_m.gguf'
```

#### Issue: SQLite schema version mismatch
**Cause:** Database from newer version
**Fix:**
```powershell
# Backup and reset
$env:SHINON_MEMORY_SQLITE_PATH="C:\Shinon\fresh.sqlite"
# Or manually delete old database
Remove-Item "$env:LOCALAPPDATA\ShinonLLM\session-memory.sqlite"
```

#### Issue: TypeScript compilation errors in new modules
**Cause:** Placeholder modules have incomplete types
**Fix:**
```powershell
# Check for errors
npx tsc --noEmit

# Fix in files:
# - character/src/attitudes/tracker.ts
# - character/src/experience/patterns.ts
```

### Debug Mode

**Enable verbose logging:**
```powershell
$env:DEBUG="shinon:*"
npm run start-local
```

**Check system status:**
```powershell
# Backend health
curl http://127.0.0.1:3001/health

# LLM backend health
curl http://127.0.0.1:8000/health

# Check ports
Get-NetTCPConnection -LocalPort 3000,3001,8000
```

---

## Development Workflow

### Adding New Features

1. **Update Contracts** (`/orchestrator/src/contracts/`)
   - Define input/output schemas
   - Add validation logic

2. **Implement Logic** (appropriate module)
   - Add functions with JSDoc
   - Maintain determinism

3. **Add Tests** (`/tests/`)
   - Unit tests for logic
   - Integration tests for flows
   - Update gates if needed

4. **Update Documentation**
   - This manual
   - HANDSHAKE_CURRENT_STATE.md
   - README.md (if user-facing)

5. **Verify**
   ```powershell
   npm run verify:backend
   npm run verify:full
   ```

### Release Checklist

- [ ] All gates pass
- [ ] Determinism verified
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in package.json
- [ ] Git tag created

---

## Reference: File Index

### Configuration Files
- `package.json` - Root npm configuration
- `backend/package.json` - Backend dependencies
- `frontend/package.json` - Frontend dependencies
- `tsconfig.json` - TypeScript configuration
- `.editorconfig` - Editor settings

### Entry Points
- `backend/src/index.ts` - Backend server
- `frontend/src/app/page.tsx` - Frontend UI
- `orchestrator/src/pipeline/orchestrateTurn.ts` - Main logic

### Documentation
- `README.md` - Project overview
- `LLM_ENTRY.md` - Developer onboarding
- `AGENTS.md` - AI assistant instructions
- `docs/HANDSHAKE_CURRENT_STATE.md` - Current status
- `docs/ARCHITECTURE_OVERVIEW.md` - Architecture
- `docs/MEMORY_POLICY.md` - Memory rules
- `docs/TODO.md` - Task list
- `docs/OPS_PLAYBOOKS.md` - Operations
- `docs/LOCAL_LLAMACPP_SETUP.md` - LLM setup

---

*End of Manual*

For updates, check `docs/HANDSHAKE_CURRENT_STATE.md` for current release status.
