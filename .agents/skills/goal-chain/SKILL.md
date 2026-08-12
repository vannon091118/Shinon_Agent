---
name: goal-chain
description: "4-Phasen autonome Entwicklungskaskade mit Evil-Twin-Protocol + TID-State-Management. 20 TIDs in globaler SQLite-DB. Script-Pflicht: Agent MUSS Scripts ausführen, NICHT verändern. Phasen: Planen (brainstorming→👯→writing-plans→👯→architecture→👯), Gate 1→2, Planung abschließen (👯), Gate 2→3, Ausführen (subagent-dev→👯→TDD→finishing), Doku (👯). Relative Pfade, DISPATCHER_DECISIONS, PRE_TASKS. Use when user types /goal."
category: agents
stack: AUTONOM
risk: high
side_effects: code_changes, db_writes
requires_approval: false
version: "3.0.0"
last_verified: "2026-08-11"

---
# 🔗 GOAL-CHAIN v3.0 — `/goal "ZIEL"` TID-basierte Autonome Entwicklungskaskade

> **Prinzip:** Jeder Skill liefert ein ausführbares Script mit RELATIVEN PFADEN.
> Der Agent MUSS die Scripts ausführen — NICHT verändern.
> State wird in einer globalen SQLite-DB via TID (Task ID) gemanaged.
> Scripts geben Pfade vor und begründen Follow-ups logisch.
> Der Agent bekommt NUR den Context den er braucht.

---

## ⛓️ Die Kaskade: Output→Input→Output

```
/goal "ZIEL:"
    │
    ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PHASE 1: PLANEN                                │
│                                                                    │
│  brainstorming ──→ 👯 Evil Twin ──→ Synthese                     │
│       │                  │                                         │
│  writing-plans ───→ 👯 Evil Twin ──→ Synthese                    │
│       │                  │                                         │
│  improve-codebase-architecture ──→ 👯 Evil Twin ──→ Synthese      │
│       │                  │                        │                │
│       ▼                  ▼                        ▼                │
│  design doc     implementation plan      architecture candidates   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
               ┌─────────────▼─────────────┐
               │  GATE 1→2: FALSIFIZIERUNG │
               │  verification-before-      │
               │  completion               │
               └─────────────┬─────────────┘
                             │
              ┌──────────────┼──────────────┐
              │ PASS         │ FAIL         │
              ▼              ▼              │
         Phase 3       ←── Gap-Liste ──────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                 PHASE 2: PLANUNG ABSCHLIESSEN                     │
│  writing-plans (re-invoke) ──→ 👯 Evil Twin ──→ Synthese         │
│  systematic-debugging ───────→ 👯 Evil Twin ──→ Synthese          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
               ┌─────────────▼─────────────┐
               │  GATE 2→3: FALSIFIZIERUNG │
               │  verification-before-      │
               │  completion               │
               └─────────────┬─────────────┘
                             │
┌──────────────────────────────────────────────────────────────────┐
│                    PHASE 3: AUSFÜHREN                              │
│  subagent-driven-development → TDD → dispatching → finishing      │
│       │                                                           │
│       └── PRO TASK: implementer ──→ 👯 Evil Twin ──→ Synthese    │
│                         │                                         │
│                    spec-reviewer → code-quality-reviewer           │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌──────────────────────────────────────────────────────────────────┐
│                      PHASE 4: DOKU                                │
│  documentation-writer ──→ 👯 Evil Twin ──→ Synthese              │
│  wiki-system ‖ self-improvement                                   │
│       │                                                           │
│       └── 👯 Evil Twin: "Was fehlt? Was ist falsch?"             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 👯 Evil Twin Protocol — FESTER BESTANDTEIL JEDES THINKER-SCHRITTS

> **"Jede Wahrheit braucht ihren Widerspruch, um sich zu beweisen."**

Nach JEDEM Thinker-Durchlauf wird ein Spiegel-Thinker mit identischer Datenlage gespawnt. Seine Aufgabe: **Fundamental widersprechen.** Nicht an Kleinigkeiten aufhalten, sondern die komplett umgekehrte Richtung denken.

```
Thinker-Agent (Original) → produziert Output
    │
    ▼
👯 Evil Twin (Spiegel-Thinker)
    │  Gleiche Datenlage, adversarial Prompt
    │  Aufgabe: "Finde die tiefsten Annahmen und kehre sie um"
    ▼
┌─────────────────────────────────┐
│ FUNDAMENTALER Widerspruch?      │
│  JA → SYNTHESE nötig            │
│  NEIN (nur Oberflächlich) →     │
│  Original bestätigt, weiter     │
└─────────────────────────────────┘
```

- **Skill:** `evil-twin-protocol`
- **Token-Overhead:** ~30-50% pro Thinker-Schritt
- **FUNDAMENTAL-Rate:** 15-30% der Durchläufe

---

## 🎯 Die 4 Phasen im Detail

### Phase 1: PLANEN

**Skills:** `brainstorming` → `👯 evil-twin-protocol` → `writing-plans` → `👯 evil-twin-protocol` → `improve-codebase-architecture` → `👯 evil-twin-protocol`

1. **brainstorming**: Erstellt Design-Dokument aus dem GOAL
   - Self-Check: Checklist item 7 — spec self-review (placeholders, contradictions, ambiguity, scope)
   - **👯 Evil Twin**: "Welche Grundannahmen im Design sind falsch? Was wenn das Gegenteil wahr ist?"
2. **writing-plans**: Übersetzt Design in vollständigen Implementierungsplan
   - Self-Check: "Gather all necessary context before completing", "Keep refining until all gaps are closed"
   - **👯 Evil Twin**: "Warum scheitert dieser Plan? Welche Alternative wurde NICHT bedacht?"
3. **improve-codebase-architecture**: Analysiert Codebase-Architektur im Kontext des Ziels
   - Self-Check: Grilling loop, domain model current
   - **👯 Evil Twin**: "Ist die Architektur-Richtung fundamental falsch? Welche blinden Flecken?"

**Abbruchkriterium:** Plan ist VOLLSTÄNDIG — keine TBDs, TODOs, Platzhalter. Jeder Evil Twin wurde gehört und Widersprüche wurden synthetisiert.

### Gate 1→2: FALSIFIZIERUNG

**Skill:** `verification-before-completion`
- Prüft Plan gegen Original-Ziel
- Output: PASS → überspringe Phase 2, direkt zu Phase 3
- Output: FAIL → Gap-Liste → Phase 2
- Self-Check: "IRON LAW: no completion claim without fresh verification"

### Phase 2: PLANUNG ABSCHLIESSEN

**Skills:** `writing-plans` (re-invoke mit Gap-Liste) → `👯 evil-twin-protocol` → `systematic-debugging` (bei unklaren Gaps) → `👯 evil-twin-protocol`

- Alle Lücken aus Gate 1→2 schließen
- NICHTS auf Phase 3 verschieben
- **👯 Evil Twin**: "Wurden die Gaps wirklich geschlossen oder nur umformuliert? Was wurde übersehen?"

### Gate 2→3: FALSIFIZIERUNG

**Skill:** `verification-before-completion` (zweiter Durchlauf)
- Gleicher Skill, gleicher Iron Law
- PASS → Phase 3, FAIL → zurück zu Phase 2

### Phase 3: AUSFÜHREN

**Skills:** `subagent-driven-development` → `test-driven-development` → `dispatching-parallel-agents` → `finishing-a-development-branch`

Pro Task:
```
implementer (TDD IRON LAW)
    │
    ▼
👯 Evil Twin: "Implementiert der Code das FALSCHE? Was wenn die Anforderung falsch verstanden wurde?"
    │
    ▼
spec-reviewer → code-quality-reviewer
    │                    │
❌ FAIL?              ❌ FAIL?
→ fix → RE-REVIEW    → fix → RE-REVIEW
    ▼
✅ Task complete → next task
```

- **👯 Evil Twin prüft FUNDAMENTALE Richtigkeit** (nicht Spec-Konformität — das macht der spec-reviewer)
- Evil Twin fragt: "Löst dieser Code das RICHTIGE Problem?"

### Phase 4: DOKU

**Skills (parallel):** `documentation-writer` ‖ `wiki-system` ‖ `self-improvement`

- **👯 Evil Twin** (nach documentation-writer): "Was fehlt in der Doku? Welcher Use-Case wurde vergessen? Welcher Leser wird scheitern?"

---

## 🧬 Die Kaskaden-Regel

```
Skill[n] PRODUCES Output[n]
    │  Self-Check muss GRÜN sein
    ▼
Skill[n+1] CONSUMES Output[n] as Input
    │  Wenn Output[n] unbrauchbar → Skill[n+1] STALLT
    ▼
Skill[n+1] PRODUCES Output[n+1]
```

---

## 📊 Skill-Mapping

| Phase | Skills | Self-Check-Quelle | Evil Twin |
|---|---|---|---|
| **1: Planen** | brainstorming, writing-plans, improve-codebase-architecture | Checklist 7, "all gaps closed", grilling loop | ✅ Nach jedem Skill |
| **Gate 1→2** | verification-before-completion | IRON LAW | — (Gate selbst ist adversial) |
| **2: Abschließen** | writing-plans (re-invoke), systematic-debugging | "Keep refining", "document root cause" | ✅ Nach jedem Skill |
| **Gate 2→3** | verification-before-completion | IRON LAW | — (Gate selbst ist adversial) |
| **3: Ausführen** | subagent-driven-dev, TDD, dispatching-parallel-agents, finishing-a-dev-branch | Two-stage review, IRON LAW | ✅ Pro Task nach implementer |
| **4: Doku** | documentation-writer, wiki-system, self-improvement | Diátaxis, "JEDE Page", Promotion Rule | ✅ Nach documentation-writer |

---

## 🚫 Was NICHT existiert

| Nicht existent | Warum |
|---|---|
| **Governance-Layer** | Kein Skill heißt "governance". verification-before-completion VERIFIZIERT, governt nicht. |
| **Externer Gate-Checker** | Die Gates SIND verification-before-completion. |
| **Stack-Flag-Enforcement** | Trennung ergibt sich natürlich: KREATIVE Skills produzieren, LOGISCHE verifizieren. |
| **"Phase must complete"** | Kein Enforcement — es ist Kausalität. Phase 3 KANN nicht ohne Plan starten. |

---

## 📈 Metriken

| Metrik | Wert |
|---|---|
| Skills in Chain | 13 (inkl. evil-twin-protocol) |
| Phasen | 4 |
| Falsifizierungs-Gates | 2 (1→2, 2→3) |
| Governance-Layer | 0 (Evil Twin ist ADVERSARIAL, nicht Governance) |
| Self-Checks (aus SKILL.md) | 13 |

---

## Verwendung

```bash
/goal "Baue eine User-Authentifizierung mit OAuth2"
/goal "Refactore den Authentication-Service"
/goal "Erstelle ein interaktives Dashboard mit React und D3"
```

Die Chain startet automatisch Phase 1 (Planen), führt durch beide Falsifizierungs-Gates, implementiert in Phase 3, und dokumentiert in Phase 4.

---

## 🗄️ TID State Management System

> **Jeder Skill liefert ein ausführbares Script. Der Agent MUSS es ausführen — NICHT verändern.**

### Globale Datenbank

**Pfad:** `.agents/skills/goal-chain/db/tid-state.db`
**Schema:** `.agents/skills/goal-chain/db/schema.sql`
**Engine:** SQLite3 (WAL-Mode, Busy-Timeout 5000ms)

### TID-Format

```
{PROJEKT}-{RUN_ID}-{PHASE}-{SECTION}

Beispiele:
  PZ-R20260811-143022-P1-brainstorming
  PZ-R20260811-143022-P1-evil-twin-1
  PZ-R20260811-143022-G1-2-verify
  PZ-R20260811-143022-P3-implementer
```

### Datenbank-Tabellen

| Tabelle | Felder | Zweck |
|---|---|---|
| **tasks** | tid, projekt, run_id, task, goal, phase, phase_section, phase_seq, status, skill_name, script_path, input_artifacts, output_artifact | Kern-Tabelle: alle 20 TIDs pro Run |
| **pre_tasks** | tid, pre_tid | DAG-Abhängigkeiten: TID X benötigt TID Y |
| **dispatcher_decisions** | decision_id, tid, decision_type, decision_value, rationale, next_tid, alt_tids | Branching: PASS/FAIL, PATH_CHOICE, SYNTHESIS |
| **follow_skill** | id, tid, skill_name, script_path, executed_at | Audit-Trail: welcher Skill wurde wann ausgeführt |

### Script-Struktur

```
.agents/skills/goal-chain/scripts/
├── tid-helpers.sh              # DB-Funktionen (shared)
├── db-init.sh                  # DB-Initialisierung
├── dispatch.sh                 # Entry-Point: seed 20 TIDs
├── complete.sh                 # TID-DONE + Next-Step
├── verify-state.sh             # Recovery: Zombies & Status
├── phase-1-brainstorming.sh    # TID: P1-brainstorming
├── phase-1-evil-twin.sh       # TID: evil-twin-* (parametrisiert)
├── phase-1-writing-plans.sh    # TID: P1-writing-plans
├── phase-1-architecture.sh     # TID: P1-architecture
├── gate-1-2.sh                 # TID: G1-2-verify
├── phase-2-writing-plans-v2.sh # TID: P2-writing-plans-v2
├── phase-2-debugging.sh        # TID: P2-debugging
├── gate-2-3.sh                 # TID: G2-3-verify
├── phase-3-implementer.sh      # TID: P3-implementer
├── phase-3-evil-twin.sh       # TID: P3-evil-twin-6
├── phase-3-reviewer.sh         # TID: P3-reviewer
├── phase-3-finishing.sh        # TID: P3-finishing
├── phase-4-docs.sh             # TID: P4-docs
├── phase-4-wiki.sh             # TID: P4-wiki
└── phase-4-learnings.sh        # TID: P4-learnings
```

### 🔒 AGENT-REGELN (SCRIPT-PFLICHT)

| # | Regel | Konsequenz bei Verstoß |
|---|---|---|
| 1 | **Scripts NICHT verändern** — sie sind read-only | TID-Status wird invalid |
| 2 | **NUR den bereitgestellten Kontext verwenden** | Context-Overflow, Halluzination |
| 3 | **Output im spezifizierten Format schreiben** | Nachfolgender TID kann Input nicht parsen |
| 4 | **Nach Abschluss: complete.sh $TID DONE ausführen** | Chain stallt, Zombie-TID |
| 5 | **Bei Verlust: verify-state.sh $RUN_ID ausführen** | Recovery-Pfad |
| 6 | **Nur den NEXT-Befehl aus dem Script ausführen** | Falsche TID-Reihenfolge |

### 🔀 Branching & Entscheidungspfade

Scripts schlagen verschiedene Wege vor und begründen sie logisch:

```
Gate 1→2 Script:
  → Agent prüft Plan
  → Schreibt "PASS" oder "FAIL" in Output
  → Bei PASS: DISPATCHER_DECISIONS → next_tid = G2-3-verify
  → Bei FAIL: DISPATCHER_DECISIONS → next_tid = P2-writing-plans-v2

Evil Twin Script:
  → Agent bewertet Widerspruch
  → FUNDAMENTAL → SYNTHESIS → DISPATCHER_DECISIONS vermerkt
  → OBERFLÄCHLICH → weiter ohne Synthese
```

### Quickstart

```bash
# 1. DB initialisieren (einmalig)
./run_goal.sh --init-db

# 2. Goal starten
./run_goal.sh "Baue eine REST-API mit FastAPI"
# → Output: "AGENT: bash .agents/skills/goal-chain/scripts/phase-1-brainstorming.sh ..."

# 3. Agent führt Scripts der Reihe nach aus
#    Jedes Script sagt exakt, was als nächstes zu tun ist.

# 4. Status prüfen
./run_goal.sh --status

# 5. Recovery bei Verlust
./run_goal.sh --verify R20260811-143022
```

---

## 📈 TID-Metriken

| Metrik | Wert |
|---|---|
| TIDs pro Run | 20 |
| Phasen | 4 (P1, P2, P3, P4) |
| Gates | 2 (G1-2, G2-3) |
| Evil Twins | 7 (1 nach jedem Thinker + Phase 3 + Phase 4) |
| Scripts | 19 (.sh Dateien in scripts/) |
| DB-Tabellen | 4 (tasks, pre_tasks, dispatcher_decisions, follow_skill) |

_13 Skills · 4 Phasen · 20 TIDs · 19 Scripts · 0 Governance · Evil Twin Protocol · TID-State-DB · August 2026_
