<div align="center">

![Shinon Control Plane](assets/banner.svg)

**LLM Control Plane — A Deterministic Operating System Layer Between Model and Application**

[![Architecture](https://img.shields.io/badge/architecture-event--driven-purple?style=flat-square)](#architecture)
[![Determinism](https://img.shields.io/badge/determinism-seed--replay-blue?style=flat-square)](#karma)
[![Falsification](https://img.shields.io/badge/falsification-6--probe--gate-red?style=flat-square)](#karma)
[![Pipeline](https://img.shields.io/badge/pipeline-e2e--verified-green?style=flat-square)](#pipeline)
[![Skills](https://img.shields.io/badge/skills-657-orange?style=flat-square)](#goal-chain)

</div>

---

## Was das ist

Nicht ein Framework. Nicht ein Wrapper. Eine **LLM Control Plane** — ein deterministisches Betriebssystem-Layer das zwischen Modell und Anwendung sitzt und das Modell auf einen Read-Only-Oracle reduziert.

```
State Container
→ explizit validierte Aktionen
→ externes Modell (read-only)
→ append-only Persistenz
→ messbares Feedback
```

Jedes einzelne Projekt hat dieselbe architektonische DNA — 5 Sprachen, 5 Domänen, ein Prinzip.

---

## Die 9 Projekte

### 🔵 Shinon — Die Persönlichkeitsschicht
> **Position 0 · Character Engine**

**Herkunft:** Benannt nach der Hauptfigur. Kein Chat-Wrapper — eine Persona mit Gedächtnis, Haltungen und der Fähigkeit, dich zur Rede zu stellen wenn du dich widersprichst.

| Metadatum | Wert |
|-----------|------|
| Sprache | TypeScript → Python (portiert) |
| Konzept | Two-Tier Memory, Pattern Engine, Attitude Tracker |
| Status | ✅ Portiert (Pattern Engine + Memory v2 + Attitudes v2) |

**Kernprinzip:** *Runtime denkt, LLM formuliert.* Das TypeScript/Python-System macht die Analyse, das lokale LLM nur die Text-Ausgabe.

---

### 🟣 Promtguard — Der Prompt-Wächter
> **Position 1 · Prompt Layer**

**Herkunft:** "Prompt" + "Guard". Transformiert rohen Intent in strukturierte, atomare Task-Prompts. Extrahiert Claims, managed Handoffs, persistiert alles append-only.

| Metadatum | Wert |
|-----------|------|
| Sprache | Python |
| Konzept | Claim-Extraktion, HOFF-Handoffs, JSONL-Audit-Trail |
| Status | ✅ Implementiert (36 Claims, 27 in pipeline-state.db) |

**Kernfrage:** *"What is the task?"*

---

### 🟡 KARMA — Knowledge-Aware Runtime Memory Architecture
> **Position 2 · Cognition / Falsification**

**Herkunft:** Akronym. Jeder erste Buchstabe jeder Regel ergibt den Namen:

- **K**eep every execution immutable
- **A**ssume nothing, falsify everything
- **R**ewards are interpretations, not facts
- **M**emory without lineage is organized gossip
- **A**gents that cannot explain their own decisions are not intelligent

| Metadatum | Wert |
|-----------|------|
| Sprache | Python |
| Konzept | DispatchGate, FalsificationGate (6 Probes), ReplayEngine, Knowledge Graph |
| Status | ✅ Portiert (v5 Persistence, 18/18 Gate-Tests) |

**Kernprinzip:** *"The Gate decides, not the Agent."* Kein Output betritt die Learning Pipeline ohne Falsification.

---

### 🟢 goal-chain — Die Sicherheitsnetz-Orchestrierung
> **Position 3 · Orchestration / Tool Belt**

**Herkunft:** 4-Phasen autonome Entwicklungskaskade mit Evil-Twin-Protocol + TID-State-Management. 20 TIDs + 43 STACK-Tools in SQLite.

| Metadatum | Wert |
|-----------|------|
| Sprache | Bash + Python |
| Konzept | TID-State-Machine, Gate-Routing, Skill-Chain-Dispatch |
| Status | ✅ 63 TIDs, 18/18 Gate-Tests, Dashboard :4200 |

**Kernprinzip:** *Script-Pflicht: Agent MUSS Scripts ausführen — NICHT verändern.* State wird in globaler SQLite-DB via TID gemanaged.

---

### 🔴 LIMEN — Die Schwelle
> **Position 4 · API Dispatch / Router**

**Herkunft:** Lateinisch *limen* — "Schwelle, Eingang". Die unsichtbare Grenze zwischen CLI-AI-Tools und mehreren Provider-Deployments.

| Metadatum | Wert |
|-----------|------|
| Sprache | Python 3.11+ |
| Konzept | Key-Pool, 429-Intelligence (5 Typen), Multi-Provider-Routing |
| Status | ✅ Phase 0-5 implementiert, 207 Tests |

**Kernprinzip:** *Kein künstliches Funktionslimit.* Sichtbare Grenzen sind Sicherheit, Datenintegrität und überprüfbare Semantik — nicht die Menge der UI-Funktionen.

---

### 🌉 SyxBridge — Der erste Beweis
> **Position — Vorläufer · CLI-Launcher-Pattern**

**Herkunft:** Bridge für *Songs of Syx* (Indie-City-Builder). Der erste Beweis dass die Control-Plane-Architektur funktioniert. 8 Provider, Steam Workshop live, r/songsofsyx Community.

| Metadatum | Wert |
|-----------|------|
| Sprache | C# (CommitLayer) + Tauri + Vue3 (GUI) |
| Konzept | Mod-Übersetzungs-Pipeline, Provider-Routing, CLI-Launcher |
| Status | ✅ v0.26.x live, Launcher-Pattern nach PZ portiert |

---

### 🧬 LifeGameLab — Der deterministische Ursprung
> **Position — Ursprung der DNA**

**Herkunft:** SHA-256 deterministischer Kernel, patch-only State-Mutation, multi-agent adversarielle Verification. Das erste *FalsificationGate* bevor der Begriff existierte.

| Metadatum | Wert |
|-----------|------|
| Sprache | JavaScript |
| Konzept | store.js (State-Envelope), stableStringify, xorshift32 RNG, assertPatchesAllowed |
| Status | ✅ Konzepte portiert (DispatchGate, ReplayEngine, sanitizeBySchema) |

---

### 💬 ChatKI — Die State-Machine-Spezifikation
> **Position — Blaupause**

**Herkunft:** Chat + KI. Die erste formale State-Machine-Spezifikation die später in KARMA landete. RPG Framework v4.0 mit VALIDATE_DEFINITIONS-Gate und UUID-Entity-IDs.

| Metadatum | Wert |
|-----------|------|
| Sprache | Spezifikation |
| Konzept | State-Machine, VALIDATE_DEFINITIONS, UUID-Entities |
| Status | ✅ DNA in KARMA DispatchGate übernommen |

---

### 📦 LLM_Middleware_Context_Framework
> **Position — Direkter KARMA-Vorläufer**

**Herkunft:** Juli 2026. Die Evolutionslinie: `LLM_Middleware.7z → karma`. Der fehlende Link zwischen LifeGameLab und der Control Plane.

| Metadatum | Wert |
|-----------|------|
| Format | 7z-Archiv |
| Konzept | Context-Framework, Middleware-Patterns |
| Status | 📦 Hochgeladen, nie ausgepackt |

---

## Architektur

### Zweistufige Event-Architektur

```
┌─────────────────────────────────────────────────────────────┐
│  STUFE 1 — Chat-Flow (sync, <3s)                           │
│                                                             │
│  User → CLI (ctl) → Shinon (Character)                     │
│       → Promtguard (Claims) → KARMA (Falsification)        │
│       → LIMEN (Key-Pool, Provider-Routing, 429-Intel)      │
│       → Response                                            │
└───────────────────────────┬─────────────────────────────────┘
                            │ LIMEN-Log persistiert
┌───────────────────────────▼─────────────────────────────────┐
│  STUFE 2 — Cognition-Flow (async)                           │
│                                                             │
│  LIMEN-Log → KARMA Experience Store                        │
│       → FalsificationGate (6 Probes)                        │
│       → RewardModel (Needs Engine)                          │
│       → Shinon Memory-Update                                │
│       → Promtguard Claims-Extraktion                        │
│       → GoalChain Trigger (Skill-Chains)                    │
└─────────────────────────────────────────────────────────────┘
```

### EventBus — 10 Topics, 12 Subscribers

```
EventBus (in-process, asyncio-based)
  ├── runtime.input         → Shinon
  ├── shinon.output         → Promtguard
  ├── promtguard.claims     → KARMA
  ├── karma.falsified       → GoalChain
  ├── limen.rate_limited    → GoalChain (NEU)
  ├── limen.key_cooldown    → GoalChain (Monitoring)
  ├── limen.key_exhausted   → GoalChain (CRITICAL REWORK)
  ├── limen.budget_warning  → GoalChain
  ├── runtime.error         → Error Handler
  └── runtime.completed     → Teardown
```

### 5 Gold-Muster — Auf Komponenten verteilt

| Muster | Komponente | Implementierung |
|--------|-----------|----------------|
| QUEUE_JOB_CONTRACT | LIMEN | Claim/Lease/Heartbeat/Dead-Letter, baseRev-CAS |
| COMPACT_OUTPUT_FORMAT | goal-chain | 6-Blöcke, Step-Log-Tags, verify-template.sh |
| tate.md-Statusmodell | Promtguard | unverified/verified/refuted/refined/unknown + Evidence-Enum |
| Done-Manifest | goal-chain | Gate-Output, stateHash, gateSummary, ROOT_CAUSE_DONE |
| Deterministischer Kernel | KARMA | stableStringify, xorshift32, assertPatchesAllowed |

---

## Komponenten-Metadaten

| Komponente | Position | Sprache | Herkunft | Status |
|-----------|---------|---------|----------|--------|
| Shinon | 0 | TS→Python | Charakter-Name | ✅ Portiert |
| Promtguard | 1 | Python | "Prompt Guard" | ✅ |
| KARMA | 2 | Python | Akronym (s.o.) | ✅ |
| goal-chain | 3 | Bash+Python | /goal-Kommando | ✅ |
| LIMEN | 4 | Python | Lat. "Schwelle" | ✅ |
| SyxBridge | Pre | C#+Tauri | Songs of Syx Brücke | ✅ v0.26 |
| LifeGameLab | Pre | JavaScript | Deterministischer Kernel | ✅ Portiert |
| ChatKI | Pre | Spec | Chat + KI | ✅ DNA übernommen |
| LLM_Middleware | Pre | Archiv | Context Framework | 📦 Archiviert |

---

## Skill-Library — 657 Skills

```
.agents/skills/
├── bioscience/      76  (Life-Science APIs + NGS-Workflows)
├── claude-tools/    43  (docx, pdf, pptx, xlsx, morning, schedule)
├── cloud-platforms/ 89  (Vercel, Cloudflare, Netlify, Render, DigitalOcean)
├── communication-apis/ 108 (Twilio 55 + Zoom 53)
├── design-tools/    40  (DataViz, Figma, Canva, Hyperframes, Remotion)
├── mobile-dev/      35  (Expo, macOS, iOS, Android)
├── ai-ml/           28  (HuggingFace, NVIDIA, OpenAI)
├── finance/         44  (Daloopa, Moody's, Datasite, Morningstar)
├── ecommerce/       26  (Shopify, Stripe, Wix)
├── security/        14  (CodeRabbit, Codex Security)
├── agents/           5  (goal-chain, evil-twin, skill-chains)
└── osint/            1  (OSINT Self-Audit)
```

Router: **goal-chain → skill-chains → 8 Router → 657 Sub-Skills** (4-Layer-Architektur, 376 verifiziert).

---

## Pipeline End-to-End (verifiziert)

```
Shinon (Pattern Engine + Two-Tier Memory)
  → Promtguard (1 Claim extrahiert, JSONL + SQLite Dual-Write)
  → KARMA FalsificationGate (6 Probes: assumptions, test_coverage,
    contradictions, regressions, idempotency, determinism)
  → GoalChain Trigger (Skill-Chain-Mapping)
  → Needs Engine (RewardModel Score: 0.92)
  → 27 Claims in pipeline-state.db
```

**Ergebnis:** 7 EventBus-Events, 0 Errors, 18/18 Gate-Routing-Assertions, ReplayEngine deterministisch.

---

## Quickstart

```bash
# Dashboard (live auf :4200)
node .agents/skills/goal-chain/scripts/live-dashboard-server.mjs 4200 &

# Pipeline E2E Test
PYTHONPATH=fusion-main:karma-main python3 -c "
import asyncio
from fusion import ControlPlaneRuntime
rt = ControlPlaneRuntime()
result = asyncio.run(rt.process('Verifiziere: SQLite ist die einzige State-Quelle'))
print(f'Claims: {len(result.claims)}, Falsified: {len(result.falsification_results)}')
"

# JSONL → SQLite Migration
python3 tools/migrate-claims-to-sqlite.py

# Goal-Chain Gate Self-Test
bash .agents/skills/goal-chain/scripts/test-gates.sh
```

---

## Dokumentation

| Dokument | Inhalt |
|----------|--------|
| [Interface Specs](interface-specs/) | Component Contracts (shinon, promtguard, karma, goal-chain, limen) |
| [Pipeline State Schema](interface-specs/pipeline-state.schema.sql) | `pipeline-state.db` DDL |
| [WIRING.md](interface-specs/WIRING.md) | EventBus-Verdrahtung und Persistenzgrenzen |
| [Component Contracts](interface-specs/) | Schnittstellenspezifikationen für die fünf Runtime-Komponenten |
| [Goal-Chain Self-Test](.agents/skills/goal-chain/scripts/test-gates.sh) | Reproduzierbarer Gate-Routing-Test |
| [LIMEN Tests](limen-main/tests/) | Provider-Routing-, Queue- und Resilience-Tests |

> Laufzeitdaten wie `.goal/`, `pipeline-state.db` und die Goal-Chain-SQLite werden absichtlich nicht versioniert. Sie werden lokal durch die Setup-/Self-Test-Skripte erzeugt; veröffentlichte Reports müssen aus einem reproduzierbaren Lauf stammen.

---

<div align="center">

**"Der Prototyp ist tot. Das ist ein ernstzunehmender Runtime-Kern."**

*Shinon Control Plane MVP · 2026 · Deterministic · Falsification-Gated · Append-Only*

</div>
