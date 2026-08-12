# 🔗 GOAL-CHAIN — `/goal "ZIEL"` Autonome Entwicklungskaskade

> **Prinzip:** Keine erfundenen Regeln. Kein Governance-Layer. Die Chain ist eine
> **KASKADE** aus Skills, deren natürliche Input/Output-Schnittstellen die
> Reihenfolge erzwingen. Jeder Skill validiert SICH SELBST — erst wenn seine
> eigenen internen Completion-Kriterien erfüllt sind, gibt er Output frei.
> Der nächste Skill KANN nicht starten, weil sein Input fehlt.

---

## ⛓️ Die Kaskade: Output→Input→Output

```
/goal "ZIEL:"
    │
    ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PHASE 1: PLANEN                                │
│                                                                    │
│  brainstorming ──→ writing-plans ──→ improve-codebase-architecture │
│       │                  │                        │                │
│       ▼                  ▼                        ▼                │
│  design doc     implementation plan      architecture candidates   │
│  (SKILL.md:     (SKILL.md:              (SKILL.md:                 │
│   Checklist 7)   "all gaps closed")      grilling loop)            │
│                                                                    │
│  JEDER Skill hat seinen eigenen SELF-CHECK, der bestanden          │
│  sein muss, BEVOR der nächste Skill Input bekommt.                 │
└────────────────────────────┬─────────────────────────────────────┘
                             │
               ┌─────────────▼─────────────┐
               │  GATE 1→2: FALSIFIZIERUNG │
               │                           │
               │  verification-before-      │
               │  completion               │
               │                           │
               │  Input:  PLAN + ZIEL      │
               │  Output: PASS / FAIL-LISTE │
               │                           │
               │  SELF-CHECK (SKILL.md):    │
               │  "IRON LAW: no completion │
               │   claim without fresh     │
               │   verification"           │
               └─────────────┬─────────────┘
                             │
              ┌──────────────┼──────────────┐
              │ PASS         │ FAIL         │
              ▼              ▼              │
         Phase 2       ←── Gap-Liste ──────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                 PHASE 2: PLANUNG ABSCHLIESSEN                     │
│                                                                    │
│  writing-plans (re-invoked mit Gap-Liste aus Gate 1→2)            │
│       │                                                            │
│       │  SKILL.md: "Keep refining until all gaps are closed"      │
│       │  SKILL.md: "Gather all necessary context before           │
│       │             completing the plan"                           │
│       ▼                                                            │
│  systematic-debugging (wenn Gap-Ursache unklar)                    │
│       │                                                            │
│       │  SKILL.md: "Document root cause"                          │
│       ▼                                                            │
│  plan V2 — VOLLSTÄNDIG, KEINE Lücken, NICHTS verschoben           │
└────────────────────────────┬─────────────────────────────────────┘
                             │
               ┌─────────────▼─────────────┐
               │  GATE 2→3: FALSIFIZIERUNG │
               │                           │
               │  verification-before-      │
               │  completion               │
               │                           │
               │  Input:  PLAN V2 + ZIEL   │
               │  Output: PASS / FAIL-LISTE │
               │                           │
               │  SAME SKILL, SAME IRON LAW │
               │  Kein zweiter Check =      │
               │  kein Completion-Claim     │
               └─────────────┬─────────────┘
                             │
              ┌──────────────┼──────────────┐
              │ PASS         │ FAIL         │
              ▼              ▼              │
         Phase 3       ←── Gap-Liste ──────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PHASE 3: AUSFÜHREN                              │
│                                                                    │
│  subagent-driven-development (PRIMÄR)                             │
│  ODER executing-plans (wenn keine subagent-Plattform)              │
│       │                                                            │
│       │  PRO TASK (subagent-driven-dev SKILL.md):                  │
│       │                                                             │
│       │  implementer ──→ spec-reviewer ──→ code-quality-reviewer   │
│       │       │               │                    │               │
│       │       │          ❌ FAIL?              ❌ FAIL?             │
│       │       │          → implementer fix    → implementer fix    │
│       │       │          → RE-REVIEW          → RE-REVIEW          │
│       │       │                                                    │
│       │       ▼                                                    │
│       │  ✅ Task complete → next task                              │
│       │                                                             │
│       │  JEDER Subagent validiert SICH SELBST:                     │
│       │  - implementer: self-review vor Commit (SKILL.md)           │
│       │  - spec-reviewer: "code matches spec?" (SKILL.md)          │
│       │  - code-quality-reviewer: patterns, errors (SKILL.md)      │
│       │                                                             │
│       │  Subagent verwendet test-driven-development:               │
│       │  - SKILL.md IRON LAW: "NO PRODUCTION CODE WITHOUT          │
│       │    A FAILING TEST FIRST"                                   │
│       │  - RED → GREEN → REFACTOR per Task                        │
│       │                                                             │
│       │  dispatching-parallel-agents (wenn Tasks unabhängig):      │
│       │  - SKILL.md: "One agent per independent problem domain"    │
│       │  - SKILL.md: "Verify fixes don't conflict"                 │
│       │                                                             │
│       ▼                                                            │
│  final code reviewer (subagent-driven-dev SKILL.md)                │
│       │                                                            │
│       ▼                                                            │
│  finishing-a-development-branch                                    │
│       │                                                            │
│       │  SKILL.md: "Verify tests pass before presenting options"   │
│       │  → merge / cleanup                                        │
│       ▼                                                            │
│  ALLE Tasks DONE + VERIFIED                                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      PHASE 4: DOKU                                │
│                                                                    │
│  documentation-writer ──→ wiki-system ──→ self-improvement         │
│       │                       │                  │                 │
│       ▼                       ▼                  ▼                 │
│  Diátaxis-Docs         wiki/ pages        .learnings/              │
│  (SKILL.md:             (SKILL.md:         (SKILL.md:              │
│   structure approval)    "JEDE Page         Promotion Rule)        │
│                          anlegen/updaten")                         │
│                                                                    │
│  JEDER Skill schreibt NUR, wenn sein eigener SELF-CHECK grün ist. │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔬 Warum das keine Governance braucht

Die Chain-Struktur **selbst** verhindert Drift. Kein externer Checkpoint nötig.

### Regel 1: Kein Skill kann starten ohne Input vom Vorgänger

```
brainstorming produziert design doc (.md)
    → writing-plans BRAUCHT design doc als Input
        → subagent-driven-development BRAUCHT implementation plan als Input
```

Wenn `writing-plans` keinen Input bekommt, **kann es nicht arbeiten**. Das ist keine
Governance-Regel — es ist die Funktionsweise des Skills.

### Regel 2: Kein Skill gibt Output frei ohne eigenen SELF-CHECK

Jeder Skill hat eingebaute Completion-Kriterien aus seiner SKILL.md:

| Skill | Self-Check (aus SKILL.md) |
|---|---|
| `brainstorming` | Checklist item 7: "Spec self-review — check for placeholders, contradictions, ambiguity, scope" |
| `writing-plans` | "Gather all necessary context before completing", "Keep refining until all gaps are closed" |
| `verification-before-completion` | "IRON LAW: no completion claim without fresh verification" |
| `subagent-driven-development` | Per-Task: spec-review ✅ → code-quality-review ✅. Final: "all requirements met, ready to merge" |
| `test-driven-development` | "IRON LAW: NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST", Verification Checklist |
| `finishing-a-development-branch` | "Verify tests pass before presenting options" |
| `documentation-writer` | "Adhere to all guiding principles", structure approval |
| `wiki-system` | "JEDE referenzierte Entity/Concept-Page anlegen oder updaten" |
| `self-improvement` | Promotion Rule: Recurrence-Count ≥ 3 + 2 tasks + 30-day window |

### Regel 3: Ein Skill, der seinen SELF-CHECK nicht besteht, STALLT

```
writing-plans produziert Plan mit Lücken
    → writing-plans SELF-CHECK: "Keep refining until all gaps are closed"
    → writing-plans STALLT (nicht fertig)
    → verification-before-completion bekommt KEINEN Input
    → verification-before-completion STALLT (kein Input)
    → subagent-driven-development STALLT (kein Plan)
```

Die Chain **friert ein**. Kein Agent kann "unbemerkt driften", weil der nächste
Skill in der Kaskade schlicht nichts zu tun hat.

### Regel 4: Jeder Skill validiert den Output des Vorgängers implizit

```
brainstorming → design doc
    → writing-plans LIEST design doc
    → Wenn design doc unbrauchbar: writing-plans kann keinen Plan schreiben
    → writing-plans STALLT
    → Chain zurück zu brainstorming
```

Das ist keine explizite Prüfung — es ist die natürliche Konsequenz der Kaskade.
`writing-plans` scheitert an schlechtem Input, nicht weil eine Governance-Regel es
verbietet, sondern weil der Skill mit unbrauchbarem Input nicht arbeiten KANN.

---

## 🎯 Die 4 Phasen im Detail

### Phase 1: PLANEN

**Skills (in Kaskade):**

```
brainstorming
    │  Input:  GOAL (String)
    │  Output: design doc → docs/superpowers/specs/<date>-<topic>-design.md
    │  SELF-CHECK (SKILL.md): Checklist items 1-7, spec self-review
    ▼
writing-plans
    │  Input:  design doc (von brainstorming)
    │  Output: implementation plan → docs/superpowers/plans/<plan-name>.md
    │  SELF-CHECK (SKILL.md): "Gather all necessary context before completing"
    ▼
improve-codebase-architecture
    │  Input:  codebase (liest CONTEXT.md, ADRs, Module)
    │  Output: architecture candidates → HTML report (tmp)
    │  SELF-CHECK (SKILL.md): Grilling loop, domain model current
    │  NOTE:    Informiert den Plan, modifiziert ihn nicht direkt.
    │           Architektur-Erkenntnisse fließen zurück in writing-plans.
```

**Phase-1-Abbruchkriterium:** `writing-plans` erklärt Plan für VOLLSTÄNDIG.
Keine TBDs, keine TODOs, keine Platzhalter. Wenn nicht vollständig → Skill stallt.

### Gate 1→2: FALSIFIZIERUNG

```
verification-before-completion
    │  Input:  PLAN (.md) + ZIEL (Original-String)
    │  Output: PASS → Phase 2 überspringen, direkt zu Phase 3
    │          FAIL → Gap-Liste → Phase 2
    │  SELF-CHECK (SKILL.md): "IRON LAW: no completion claim without
    │                         fresh verification"
    │
    │  Was wird geprüft:
    │  - Deckt der Plan ALLE Anforderungen des ZIELs ab?
    │  - Gibt es Lücken, Widersprüche, unklare Schritte?
    │  - Sind alle Tasks im Plan ausführbar?
    │  - Fehlt Architektur-Kontext?
```

**Warum das funktioniert:** `verification-before-completion` ist ein Skill, der
genau das tut: "verify that the work satisfies the original ask." Er prüft den
Plan gegen das Ziel. Wenn er Lücken findet → Gap-Liste. Das ist SEINE Funktion,
nicht meine Erfindung.

### Phase 2: PLANUNG ABSCHLIESSEN

**Skills (in Kaskade):**

```
writing-plans (re-invoked)
    │  Input:  Gap-Liste von verification-before-completion
    │  Output: PLAN V2 (Lücken geschlossen)
    │  SELF-CHECK (SKILL.md): "Keep refining until all gaps are closed"
    ▼
systematic-debugging (nur wenn Gap-Ursache unklar)
    │  Input:  spezifische Gap, die writing-plans nicht lösen kann
    │  Output: Root-Cause-Analyse → zurück zu writing-plans
    │  SELF-CHECK (SKILL.md): "Document root cause"
```

**Phase-2-Abbruchkriterium:** `writing-plans` V2 hat KEINE Lücken mehr.
Kein Gap aus der Gap-Liste bleibt offen. NICHTS wird auf Phase 3 verschoben.

### Gate 2→3: FALSIFIZIERUNG

```
verification-before-completion
    │  Input:  PLAN V2 (.md) + ZIEL (Original-String)
    │  Output: PASS → Phase 3
    │          FAIL → Gap-Liste → ZURÜCK zu Phase 2
    │  SELF-CHECK: DERSELBE Skill, DERSELBE Iron Law.
    │              Kein zweiter Check = kein Completion-Claim.
```

### Phase 3: AUSFÜHREN

**Skills (in Kaskade):**

```
subagent-driven-development (PRIMÄR, wenn Subagent-Plattform verfügbar)
    │  Input:  PLAN V2 (.md)
    │  Process: Read plan → Extract all tasks → Per Task:
    │
    │    implementer (subagent)
    │      │  verwendet: test-driven-development (IRON LAW)
    │      │  SELF-CHECK: "self-review before commit"
    │      │  Output: implementierter Code + Tests + Commit
    │      ▼
    │    spec-reviewer (subagent)
    │      │  SELF-CHECK: "code matches spec?"
    │      │  ❌ → implementer fix → RE-REVIEW
    │      │  ✅ → weiter
    │      ▼
    │    code-quality-reviewer (subagent)
    │      │  SELF-CHECK: patterns, errors, quality
    │      │  ❌ → implementer fix → RE-REVIEW
    │      │  ✅ → Task complete
    │
    │  dispatching-parallel-agents (wenn Tasks unabhängig)
    │      │  SELF-CHECK: "Verify fixes don't conflict"
    │      │  "Run full suite"
    │
    │  SELF-CHECK (SKILL.md): Final code reviewer über gesamte
    │                         Implementierung
    ▼
finishing-a-development-branch
    │  Input:  completed work (alle Tasks DONE)
    │  SELF-CHECK (SKILL.md): "Verify tests pass before presenting options"
    │  Output: Merge / Cleanup
```

**Phase-3-Abbruchkriterium:** ALLE Tasks haben:
- ✅ spec-review PASS
- ✅ code-quality-review PASS
- ✅ tests GREEN
- ✅ final code reviewer PASS

### Phase 4: DOKU

**Skills (parallel, da unabhängig):**

```
documentation-writer       wiki-system              self-improvement
    │                          │                          │
    │  Input: codebase         │  Input: neue             │  Input: errors,
    │  SELF-CHECK:             │  Erkenntnisse            │  learnings,
    │  structure approval,     │  SELF-CHECK:             │  corrections
    │  Diátaxis principles     │  "JEDE Page             │  SELF-CHECK:
    │                          │  anlegen/updaten"        │  Promotion Rule
    ▼                          ▼                          ▼
DECISIONS.md              wiki/ pages              .learnings/
Tutorials                 index.md                 LEARNINGS.md
How-to Guides             log.md                   ERRORS.md
Reference                                          FEATURE_REQUESTS.md
Explanation
```

---

## 🧬 Die Kaskaden-Regel (emergiert aus Skills, nicht erfunden)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Skill[n] PRODUCES Output[n]                               │
│       │                                                     │
│       │  Skill[n]'s eigener SELF-CHECK muss GRÜN sein       │
│       │  (aus Skill[n]'s SKILL.md, nicht von mir erfunden)  │
│       │                                                     │
│       ▼                                                     │
│   Skill[n+1] CONSUMES Output[n] as Input                    │
│       │                                                     │
│       │  Wenn Output[n] unbrauchbar → Skill[n+1] STALLT    │
│       │  (nicht wegen Regel — wegen Input-Mangel)           │
│       │                                                     │
│       ▼                                                     │
│   Skill[n+1] PRODUCES Output[n+1]                           │
│       │                                                     │
│       │  Skill[n+1]'s eigener SELF-CHECK muss GRÜN sein    │
│       │                                                     │
│       ▼                                                     │
│   Skill[n+2] ...                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Skill-Mapping: Phase → Stack → Skill

| Phase | Stack | Skills (aus SKILL.md) | Self-Check-Quelle |
|---|---|---|---|
| **1: Planen** | KREATIV + AUTONOM | `brainstorming`, `writing-plans`, `improve-codebase-architecture` | Checklist 7, "all gaps closed", grilling loop |
| **Gate 1→2** | LOGISCH | `verification-before-completion` | IRON LAW |
| **2: Abschließen** | KREATIV + LOGISCH | `writing-plans` (re-invoke), `systematic-debugging` | "Keep refining", "document root cause" |
| **Gate 2→3** | LOGISCH | `verification-before-completion` | IRON LAW |
| **3: Ausführen** | AUTONOM + LOGISCH | `subagent-driven-development`, `test-driven-development`, `dispatching-parallel-agents`, `finishing-a-development-branch` | Two-stage review, IRON LAW, "verify fixes don't conflict" |
| **4: Doku** | MEMORY + SELF-IMPROVE | `documentation-writer`, `wiki-system`, `self-improvement` | Diátaxis principles, "JEDE Page", Promotion Rule |

---

## 🚫 Was hier NICHT existiert (bewusst)

| Nicht existent | Warum |
|---|---|
| **Governance-Layer** | Kein Skill heißt "governance". `verification-before-completion` ist ein LOGISCHER Skill — er VERIFIZIERT, er GOVERNT nicht. |
| **Externer Gate-Checker** | Die Gates sind `verification-before-completion` selbst. Der Skill prüft, weil das seine Funktion ist. |
| **Stack-Flag-Enforcement** | Skills arbeiten in ihrem natürlichen Modus (KREATIV, LOGISCH). Die Trennung ergibt sich daraus, dass KREATIVE Skills Designs produzieren und LOGISCHE Skills verifizieren — sie KÖNNEN nicht gleichzeitig im selben Durchlauf arbeiten, weil LOGISCH den Output von KREATIV als Input braucht. |
| **"Phase must complete before next"** | Das ist kein Enforcement — es ist Kausalität. Phase 3 KANN nicht starten ohne Plan. Phase 4 KANN nicht starten ohne Code. |
| **"Kein Platzhalter"** | Das sagt `writing-plans` SELBST: "Keep refining until all gaps are closed." Nicht meine Regel. |

---

## 🔄 Vollständiger Durchlauf (Pseudocode)

```bash
/goal "Baue eine User-Authentifizierung mit OAuth2"

# ═══════════ PHASE 1: PLANEN ═══════════

# Skill 1: brainstorming
# → liest Projekt-Kontext
# → stellt Fragen (autonom: prüft gegen Codebase statt User)
# → produziert design doc: docs/superpowers/specs/2026-08-11-oauth2-auth-design.md
# → SELF-CHECK: Checklist item 7 (Spec self-review) → PASS

# Skill 2: writing-plans
# → Input: docs/superpowers/specs/2026-08-11-oauth2-auth-design.md
# → produziert implementation plan: docs/superpowers/plans/oauth2-auth.md
# → SELF-CHECK: "all gaps closed" → PASS

# Skill 3: improve-codebase-architecture
# → Input: codebase (liest CONTEXT.md, sucht auth-relevante Module)
# → produziert HTML report mit Architektur-Kandidaten
# → SELF-CHECK: grilling loop → PASS
# → Erkenntnisse fließen zurück zu writing-plans
# → writing-plans updatet Plan mit Architektur-Kontext

# ═══════════ GATE 1→2 ═══════════

# Skill: verification-before-completion
# → Input: PLAN (oauth2-auth.md) + ZIEL ("Baue eine User-Authentifizierung...")
# → Prüft: Deckt der Plan OAuth2-Flow, Token-Refresh, Session-Management ab?
# → Findet Gap: "Kein Rate-Limiting für Login-Endpunkte"
# → Output: FAIL mit Gap-Liste

# ═══════════ PHASE 2: PLANUNG ABSCHLIESSEN ═══════════

# Skill: writing-plans (re-invoked mit Gap-Liste)
# → Input: Gap "Rate-Limiting für Login-Endpunkte"
# → Ergänzt Plan um Rate-Limiting-Task
# → SELF-CHECK: "Keep refining" → PASS

# ═══════════ GATE 2→3 ═══════════

# Skill: verification-before-completion (zweiter Durchlauf)
# → Input: PLAN V2 + ZIEL
# → Prüft: Alle Gaps geschlossen?
# → Output: PASS

# ═══════════ PHASE 3: AUSFÜHREN ═══════════

# Skill: subagent-driven-development
# → Input: PLAN V2 (oauth2-auth.md)
# → Extrahiert 4 Tasks:
#    1. OAuth2 Provider Integration
#    2. Token Management
#    3. Session Handling
#    4. Rate Limiting
#
# Task 1: OAuth2 Provider Integration
#   → implementer (subagent) dispatched
#     → verwendet test-driven-development
#     → RED: schreibt Test für OAuth2-Flow
#     → GREEN: implementiert Provider-Integration
#     → REFACTOR: extracted OAuth2Client helper
#     → SELF-CHECK: "self-review before commit" → PASS
#   → spec-reviewer (subagent): "code matches spec?" → ✅
#   → code-quality-reviewer (subagent): patterns, errors → ✅
#   → Task 1 DONE
#
# Task 2-4 ebenso...
#
# → Final code reviewer: "all requirements met" → PASS
#
# Skill: finishing-a-development-branch
# → Input: completed work (4/4 tasks)
# → SELF-CHECK: "Verify tests pass" → all green
# → Merge

# ═══════════ PHASE 4: DOKU ═══════════

# Skill: documentation-writer
# → Input: Codebase + OAuth2-Feature
# → Proposes: Tutorial (How to add OAuth2), Reference (API docs), Explanation
# → SELF-CHECK: "structure approval", "Diátaxis principles" → PASS
# → Output: docs/oauth2-*.md

# Skill: wiki-system
# → Input: OAuth2-Erkenntnisse, Architektur-Entscheidungen
# → Erstellt: wiki/concepts/oauth2-flow.md, wiki/entities/oauth2-provider.md
# → SELF-CHECK: "JEDE Page anlegen/updaten" → PASS

# Skill: self-improvement
# → Input: Errors (Token-Refresh-Timeout beim ersten Implementierungsversuch)
# → Loggt: .learnings/ERRORS.md → ERR-20260811-001
# → SELF-CHECK: logged → PASS

# ═══════════ /goal COMPLETE ═══════════
```

---

## 📈 Metriken

| Metrik | Wert |
|---|---|
| Skills in Chain | 12 (brainstorming, writing-plans, improve-codebase-architecture, verification-before-completion, systematic-debugging, subagent-driven-development, test-driven-development, dispatching-parallel-agents, finishing-a-development-branch, documentation-writer, wiki-system, self-improvement) |
| Phasen | 4 |
| Falsifizierungs-Gates | 2 (1→2, 2→3) |
| Governance-Layer | 0 |
| Selbst-erfundene Regeln | 0 |
| Self-Checks (aus SKILL.md) | 12 (einer pro Skill) |

---

_/goal Chain · 12 Skills · 4 Phasen · 0 Governance · August 2026_
