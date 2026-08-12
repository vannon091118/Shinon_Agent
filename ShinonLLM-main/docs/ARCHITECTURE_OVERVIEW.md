# Architecture Overview

This document is an orientation layer.
For the verified current state, treat [HANDSHAKE_CURRENT_STATE.md](./HANDSHAKE_CURRENT_STATE.md) as authoritative.

## The Two Rules

1. **The runtime thinks. The LLM formulates text.**
2. **Shinon is a character with memory, not a configuration.**

In practice, this means:

- Runtime code owns contracts, routing, scoring, pattern recognition, and attitude tracking.
- Shinon develops opinions about the user based on observed patterns (not prompt instructions).
- Any state mutation is explicit, typed, and validated by gates (fail-closed).
- The model receives "Shinon's thoughts" as prompts, not raw chat logs.

## Components (Updated for 0.3.0)

### Core Runtime

- `backend/`: HTTP boundary, request validation, fail-closed routing.
- `orchestrator/`: Turn orchestration with character-aware prompt generation.
- `inference/`: Model execution adapters (llama.cpp, Ollama) and routing.
- `telemetry/`: Replay support and determinism artifacts.

### Memory & Character (New in 0.3.0)

- `character/`: Character system with identity, attitudes, and pattern engine.
  - `core/identity.ts`: Shinons fixed base personality
  - `attitudes/tracker.ts`: Dynamic user-specific attitudes (-10 to +10)
  - `experience/patterns.ts`: Pattern recognition and anchor formation
  - `experience/twoTierMemory.ts`: Tier 1 (facts) + Tier 2 (patterns)
  - `state/emotional.ts`: Current mood per session
  - `prompts/generator.ts`: "Shinon's thoughts" prompts for LLM
- `memory/zones/`: Hot/Mid/Cold zone management.
  - `hotZone.ts`: Current session (unfiltered access)
  - `midZone.ts`: Last 10 sessions (selective access)
  - `coldZone.ts`: Archive with pattern hardening
- `memory/tiers/`: Two-tier storage (Personal + Pattern anchors).

### Supporting

- `frontend/`: Delivery surface (UI), no policy ownership.
- `tests/`: Unit/integration/e2e and gate checks (contract/replay/baseline).
- `shared/`: Utils (hashing, serialization) used across modules.

## Memory Architecture

### Two-Tier System

```text
┌─────────────────────────────────────────────────────────────┐
│                    TIER 1: PERSONAL                          │
│  Concrete facts, quotes, events                             │
│  Example: "User said on 1.4: 'Happy with Anna'"            │
│  Storage: SQLite, permanent until explicit deletion         │
└─────────────────────────────────────────────────────────────┘
                              ↕
                    Pattern Extraction
                    (Cold Zone Hardening)
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                    TIER 2: PATTERN                           │
│  Abstract anchors with confidence scores                    │
│  Example: "relationship-inconsistency: 0.85"                 │
│  Links: Array of Tier-1 fact IDs                            │
└─────────────────────────────────────────────────────────────┘
```

### Zone Management

```text
User Input
    ↓
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  HOT ZONE   │ →  │  MID ZONE   │ →  │  COLD ZONE  │
│  (Current   │    │  (Last 10   │    │  (Archive +│
│   Session)  │    │   Sessions) │    │   Harden)  │
│             │    │             │    │             │
│ Unfiltered  │    │ Score-based │    │ Pattern     │
│ access      │    │ selection   │    │ extraction  │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Data Flow (New)

```text
┌──────────┐     ┌─────────────┐     ┌──────────────┐
│  USER    │────→│   INPUT     │────→│    HOT       │
│  INPUT   │     │ VALIDATION  │     │    ZONE      │
└──────────┘     └─────────────┘     │   (Tier 1)   │
                                     └──────┬───────┘
                                            ↓
                                     ┌──────────────┐
                                     │   PATTERN    │
                                     │   CHECK      │
                                     │  (Tier 2)    │
                                     └──────┬───────┘
                                            ↓
                                     ┌──────────────┐
                                     │   ATTITUDE   │
                                     │   CHECK      │
                                     │(-10 to +10)  │
                                     └──────┬───────┘
                                            ↓
                                     ┌──────────────┐
                                     │   PROMPT     │
                                     │   GENERATOR  │
                                     │              │
                                     │ "I (Shinon)  │
                                     │  have seen   │
                                     │  pattern X,  │
                                     │  my patience │
                                     │  is 3/10..." │
                                     └──────┬───────┘
                                            ↓
                                     ┌──────────────┐
                                     │     LLM      │
                                     │  (0.5B-7B)   │
                                     │              │
                                     │  Text output │
                                     │  only - no   │
                                     │  state writes│
                                     └──────┬───────┘
                                            ↓
                                     ┌──────────────┐
                                     │   RESPONSE   │
                                     │   OUTPUT     │
                                     └──────────────┘
```

## Hot Path Details

1. **Input Validation**: Contract-first validation (fail-closed)
2. **Hot Zone Retrieval**: Unfiltered access to current session facts (Tier 1)
3. **Pattern Recognition**: Check Tier 2 anchors for relevant patterns
4. **Attitude Calculation**: Current warmth/respect/patience/trust scores
5. **Prompt Generation**: Runtime creates "Shinon's thoughts" prompt
6. **LLM Inference**: Local model (llama.cpp/Ollama) generates response
7. **Response Output**: Validated, character-consistent output

## Quality Gates (Release Handshake)

ShinonLLM treats determinism and contract integrity as release conditions:

- **Contract gate** ensures input/output schemas match the declared contracts.
- **Replay gate** ensures identical inputs reproduce identical replay hashes and action sequences.
- **Baseline integrity** ensures the expected deterministic baseline is stable across runs.

New for 0.3.0:

- **Pattern gate** (planned): Validates pattern extraction determinism.
- **Attitude gate** (planned): Ensures attitude calculations are reproducible.

## Memory policy reference

Detailed runtime memory behavior (Two-Tier, Zones, TTL, decay retention, SQLite opt-in, and fail-closed rules) is maintained in:

- [MEMORY_POLICY.md](./MEMORY_POLICY.md)

## Migration Notes (v0.2.3a → 0.3.0)

The architecture shifts from:
- **Chat-History storage** → **Two-Tier Memory** (facts + patterns)
- **Static prompts** → **Character-aware prompt generation**
- **FIFO decay** → **Zone-based hardening with pattern extraction**

See [HANDSHAKE_CURRENT_STATE.md](./HANDSHAKE_CURRENT_STATE.md) for implementation status.
