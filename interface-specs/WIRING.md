# Control Plane — Wiring Documentation

## Pipeline Flow (Corrected)

```
USER
  ↓
SHINON (Position 0: Persönlichkeit, Attitude, Character-Layer)
  │  Input:  user_text + session_id + history
  │  Output: reply + character_context + handoff_to_promtguard
  │  State:  shinon_attitude_state, shinon_memory_hot/mid, shinon_contract_history
  │  Asks:   "Wie klingt das?"
  ↓  Handoff HOFF-0001
PROMTGUARD (Position 1: Prompt-Generierung, Handoffs, Self-Improve)
  │  Input:  prompt_text + character_context (from Shinon) 
  │  Output: handoff + task_prompt + claims + context_token_id
  │  State:  context-log.jsonl, decision-journal.jsonl, claim-log.jsonl, handoffs.jsonl
  │  Asks:   "Was ist der Auftrag?"
  ↓  Handoff HOFF-0002
KARMA (Position 2: CLI, FalsificationGate, Learning, Knowledge Graph)
  │  Input:  handoff (from Promtguard) + claims
  │  Output: falsification_results + experience_records + goalchain_triggers
  │  State:  karma_facts, karma_executions, karma_knowledge_graph, karma_events
  │  Asks:   "Ist das wahr?"
  │
  ├──triggert→ GOAL-CHAIN (Position 2b: Tool Belt, Skill-Chains, TIDs)
  │               Input:  trigger_source=karma + run_id
  │               Output: tid_results + gate_results + evil_twin_results
  │               State:  tasks, dispatcher_decisions, follow_skill, template_markers
  │               Asks:   "Welcher Skill als nächstes?"
  │                    ↓  ALLE API-Calls
  └──────────────── LIMEN (Position 3: Router, Key-Pool, 429-Intelligenz)
                       Input:  OpenAI-compatible ChatCompletion request
                       Output: response + routing_metadata
                       State:  limen_queue, limen_key_state, limen_audit_events
                       Asks:   "Welcher Key ist frei?"
                            ↓
                       [API-Provider]
                            ↓
                 Ergebnis → KARMA (Experience Store, Reward, Pattern)

─────────────────────────────────────────────────────────────
COMMIT-LAYER   ← passiver Observer am git pre-commit Hook
SYXBRIDGE      ← Beweis: läuft in Production (v0.26.x, Steam Workshop)
DOKI C#-PORT   ← existiert (ArcEngine.cs, RngEngine.cs)
SESSION-MGR    ← Dashboard, PTY-Stream, Prozess-Kill
─────────────────────────────────────────────────────────────
```

## Handoff Sequence

| HOFF-ID | From | To | What | Conditional? |
|---------|------|----|------|-------------|
| HOFF-0001 | USER | SHINON | User text (raw input) | Always |
| HOFF-0002 | SHINON | PROMTGUARD | Character-contextualized input | Only if Shinon active |
| HOFF-0003 | PROMTGUARD | KARMA | Task prompt + claims + context token | Always |
| HOFF-0004 | KARMA | GOAL-CHAIN | Skill trigger + TID run request | Only if skills needed |
| HOFF-0004a | GOAL-CHAIN | LIMEN | API request (chain scripts needing LLM) | Only if API call needed |
| HOFF-0004b | LIMEN | GOAL-CHAIN | API response + routing metadata | After HOFF-0004a |
| HOFF-0005 | KARMA | LIMEN | API request (direct LLM calls) | Only if API call needed |
| HOFF-0006 | LIMEN | KARMA | API response + routing metadata | After HOFF-0005 |
| HOFF-0007 | GOAL-CHAIN | KARMA | TID results + gate decisions | After chain completes |
| HOFF-0008 | KARMA | USER | Final response (falsified + validated) | Always |

## Component Boundaries

### What each component OWNS (never shared directly)

| Component | Owns |
|-----------|------|
| Shinon | Attitude state, Hot/Mid memory, Contract Gate decisions |
| Promtguard | Context tokens (CTX-IDs), Decision journal, Research pipeline |
| KARMA | Facts (single source of truth), Experience Store, Falsification results, Reward model |
| goal-chain | TID state, Dispatcher decisions, Skill activation log, Template markers |
| LIMEN | Key state, Queue, Audit events, Rate limit tracking |

### What is SHARED (through the Run Manifest)

| Shared Concept | Source of Truth | Read Access |
|---------------|-----------------|-------------|
| Claims | Promtguard claim-log.jsonl | KARMA (falsifies), Shinon (reads via KARMA facts) |
| Cold Memory / Long-term Facts | KARMA karma_facts | Shinon (READ_ONLY), Promtguard (context enrichment) |
| Pipeline Run Identity | Run Manifest | ALL components |
| Handoff Events | Run Manifest (append-only) | ALL components |
| Errors | Run Manifest (append-only) | ALL components |

## Persistence Architecture (Evil Twin Synthesis)

Trennung von State und Audit — reflektiert das existierende Pattern (Promtguard JSONL, goal-chain SQLite):

```
┌──────────────────────────────────────────────────────────┐
│  PIPELINE STATE (mutable, queryable)                      │
│  pipeline-state.db — SQLite WAL                           │
│                                                          │
│  run_state       — Ein Eintrag pro Pipeline-Run          │
│  component_state — Status pro Komponente pro Run         │
│  artifacts       — Alle produzierten Artefakte            │
│  claims          — Cross-Referenzierte Claims             │
│  metrics         — Aggregierte Metriken                   │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  AUDIT TRAIL (immutable, append-only, replay-fähig)      │
│  audit-trail.jsonl — JSONL (Promtguard-kompatibel)       │
│                                                          │
│  Jedes Event: EVT-{SEQ}, pipeline_run_id, timestamp,     │
│  event_type, component, from/to, artifacts, claims,      │
│  note, error_code, severity, duration_ms                  │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  ZENTRALE SQLITE (vision)                                │
│                                                          │
│  shinon.*     — Attitude, Hot/Mid Memory, Gates          │
│  promtguard.* — Context Tokens, Decisions, Claims        │
│  karma.*      — Facts, Executions, Knowledge Graph       │
│  goalchain.*  — TIDs, Decisions, Skills, Templates       │
│  limen.*      — Queue, Key State, Audit, Leases           │
│  pipeline.*   — Run State, Component State, Metrics      │
│                                                          │
│  Shinon COLD → karma_facts (READ_ONLY view)              │
│  Alle Claims → karma_facts.claim_status (Falsification)  │
│  Audit Trail → audit-trail.jsonl (immutable, extern)     │
└──────────────────────────────────────────────────────────┘
```

### Current State (3 separate stores)

| Store | Type | Location |
|-------|------|----------|
| Promtguard | JSONL (append-only) | `.promtset/state/` |
| KARMA | SQLite (schema-versioned) | `karma-main/` |
| goal-chain | SQLite (WAL mode) | `.agents/skills/goal-chain/db/tid-state.db` |
| LIMEN | SQLite (WAL mode) | `limen-main/` |
| Pipeline State | SQLite | `pipeline-state.db` (neu) |
| Audit Trail | JSONL | `audit-trail.jsonl` (neu) |

## Claim Status Mapping (Promtguard ↔ KARMA)

Promtguard and KARMA use different status vocabularies. The Run Manifest uses KARMA-native status as the unified truth.

| Promtguard Status | KARMA Status | Meaning |
|------------------|--------------|---------|
| `unverified` | `unverified` | Claim exists, no evidence evaluated |
| `verified` | `supported` | Evidence supports the claim (not yet conclusive) |
| — | `confirmed` | Multiple independent evidence sources confirm (KARMA-only) |
| `refuted` | `refuted` | Evidence contradicts the claim |
| `refined` | `supported` (with note) | Claim was adjusted based on evidence, now supported |
| — | `conflicted` | Evidence both supports and contradicts (KARMA-only) |

**Handoff rule:** When Promtguard hands off to KARMA:
- Promtguard's `verified` → KARMA's `supported`
- Promtguard's `refuted` → KARMA's `refuted`
- Promtguard's `refined` → KARMA's `edited` (claim was wrong, now corrected)
- Promtguard's `unknown` → KARMA's `unverified`
The `confirmed` and `conflicted` statuses are KARMA-native and can only be set by the FalsificationGate.

---

## Contract Version Policy

- **MAJOR** bump: breaking change to input/output schema
- **MINOR** bump: new optional fields, backward-compatible
- **PATCH** bump: documentation, metadata updates

Current versions:
- `run-manifest.schema.json` → `1.0.0`
- `shinon.contract.json` → `1.0.0`
- `promtguard.contract.json` → `1.0.0`
- `karma.contract.json` → `1.0.0`
- `goal-chain.contract.json` → `1.0.0`
- `limen.contract.json` → `1.0.0`
