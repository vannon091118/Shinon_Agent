# 🧠 Skill Chains v2 — Task/Stack-Generalisiert

> **Prinzip:** Nicht "welcher Skill folgt auf welchen", sondern:
> **Welcher STACK wird für welchen TASK-TYP aktiviert?**
>
> Strikte Trennung: 🎨 Kreativ ≠ 🔬 Logisch — **nie im selben Durchlauf.**

---

## 📐 Die 6 Core-Stacks

Jeder Stack bündelt Skills nach ihrem **Prinzip**, nicht nach ihrer Kategorie.

### 🧠 MEMORY — Wissen behalten & lernen
```
LERNZYKLUS: task-abschluss → self-improvement → wiki-system → consolidate-memory
```
**Skills:** `self-improvement`, `wiki-system`, `claude-tools/consolidate-memory`, `persona-researcher`, `web-dev/superpowers/writing-skills`

**Wann:** Nach JEDEM Task-Durchlauf. Memory ist der letzte Schritt jeder Kette.

---

### 📈 SELF-IMPROVE — Kontinuierlich besser werden
```
VERBESSERUNGSZYKLUS: receiving-code-review → improve-codebase-architecture → self-improvement → writing-skills
```
**Skills:** `self-improvement`, `improve-codebase-architecture`, `receiving-code-review`, `claude-tools/consolidate-memory`

**Wann:** Bei Fehlern, nach Reviews, bei erkannten Mustern. Läuft ASYNCHRON zum Haupt-Task.

---

### ⚖️ GOVERNANCE — Deterministische Regeln & Gates
```
GATE-CHECK: threat-model → security-scan → verification-before-completion → track-findings
```
**Skills:** `multi-agent-orchestrator`, `security/codex-security/*`, `web-dev/superpowers/verification-before-completion`, `security/codex-security/track-findings`

**Wann:** VOR jedem Schreibzugriff, NACH jedem Kreativ-Pass, VOR jedem Merge. GOVERNANCE ist die Brücke zwischen KREATIV und LOGISCH — sie prüft, ob der Kreativ-Output den Regeln entspricht, bevor LOGISCH startet.

---

### 🤖 AUTONOM — Selbständiges Arbeiten ohne Mensch
```
AUTO-ZYKLUS: autorun → guide-architekt → brainstorming → dispatching-parallel-agents → executing-plans → finishing-a-development-branch
```
**Skills:** `agents/autorun`, `agents/guide-architekt`, `web-dev/superpowers/brainstorming`, `web-dev/superpowers/dispatching-parallel-agents`, `web-dev/superpowers/executing-plans`, `web-dev/superpowers/subagent-driven-development`, `web-dev/superpowers/finishing-a-development-branch`, `web-dev/superpowers/using-superpowers`

**Wann:** Wenn der Agent selbst entscheiden muss, was als nächstes zu tun ist. AUTONOM steuert den Gesamtablauf, delegiert an KREATIV/LOGISCH, aber mischt sich nicht in deren Arbeit ein.

---

### 🎨 KREATIV — Generieren, Designen, Ideen entwickeln
```
⚠️ STRIKT GETRENNT VON LOGISCH — NIE GEMISCHT
```
```
KREATIV-PASS: brainstorming → frontend-design → canvas-design → media-generation → writing-skills
```
**Skills:** `web-dev/superpowers/brainstorming`, `design/frontend-design`, `design/canvas-design`, `design/canvas`, `media/media-generation`, `design-tools/figma/*`, `design-tools/canva/*`, `games/playcanvas-engine`

**Regel:** KREATIV-Pass endet mit GOVERNANCE-Check. Erst wenn GOVERNANCE grün gibt, darf LOGISCH starten.

---

### 🔬 LOGISCH — Analysieren, Prüfen, Debuggen
```
⚠️ STRIKT GETRENNT VON KREATIV — NIE GEMISCHT
```
```
LOGISCH-PASS: systematic-debugging → python-testing-patterns → playwright-expert → validation → python-performance-optimization
```
**Skills:** `development/systematic-debugging`, `development/python-testing-patterns`, `testing/playwright-expert`, `development/python-performance-optimization`, `development/typescript-expert`, `security/codex-security/validation`, `security/codex-security/security-scan`

**Regel:** LOGISCH arbeitet NUR mit dem Output, den GOVERNANCE nach dem KREATIV-Pass freigegeben hat. LOGISCH validiert, testet, optimiert — aber generiert NICHTS Neues.

---

## 🔀 Task/Stack-Matrix

Jeder Task-Typ aktiviert eine spezifische Stack-Kombination:

| Task-Typ | AUTONOM | KREATIV | GOVERNANCE | LOGISCH | MEMORY | SELF-IMPROVE |
|---|---|---|---|---|---|---|
| **Feature bauen** | ✅ | ✅ (Design) | ✅ (Pre-Merge) | ✅ (Tests) | ✅ | bei Fehlern |
| **Bug fixen** | — | — | ✅ | ✅ (Debug) | ✅ | ✅ |
| **Refactoring** | — | — | ✅ (Arch-Check) | ✅ (Verify) | ✅ | ✅ |
| **Forschen** | ✅ | ✅ (Ideate) | — | ✅ (Validate) | ✅ | — |
| **Design-System** | — | ✅ | ✅ (Guidelines) | — | — | bei Review |
| **Security-Audit** | — | — | ✅ (Scan) | ✅ (Validate) | ✅ | ✅ (Harden) |
| **Code-Review** | — | — | ✅ (Gates) | ✅ (Analyze) | — | ✅ |
| **Brainstorming** | ✅ | ✅ | — | — | ✅ | — |
| **Deployment** | ✅ | — | ✅ (Verify) | ✅ (Test) | ✅ | bei Rollback |

---

## 🔄 Generalisierte Zwei-Phasen-Architektur

JEDER Task durchläuft maximal diese Struktur:

```
┌─────────────────────────────────────────────────┐
│               🤖 AUTONOM (Steuerung)             │
│  autorun → guide-architekt → Task-Erkennung     │
└──────────────────┬──────────────────────────────┘
                   │
         ┌─────────▼─────────┐
         │  Task braucht     │
         │  KREATIV-Output?  │
         └────┬─────────┬────┘
              │ JA      │ NEIN
              ▼         │
    ┌─────────────┐     │
    │ 🎨 KREATIV   │     │
    │ brainstorming│     │
    │ design       │     │
    │ generieren   │     │
    └──────┬──────┘     │
           │            │
           ▼            │
    ┌─────────────┐     │
    │ ⚖️ GOVERNANCE│◄────┘
    │ gate-check   │
    │ verify       │
    │ threat-model │
    └──────┬──────┘
           │ GRÜN
           ▼
    ┌─────────────┐
    │ 🔬 LOGISCH   │
    │ testen       │
    │ debuggen     │
    │ validieren   │
    │ optimieren   │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ 🧠 MEMORY    │
    │ lernen       │
    │ speichern    │
    │ konsolidieren│
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ 📈 SELF-     │
    │ IMPROVE      │
    │ (asynchron)  │
    └─────────────┘
```

---

## 🚫 Harte Trennregeln

| Regel | Begründung |
|---|---|
| 🎨 KREATIV und 🔬 LOGISCH **nie im selben Durchlauf** | Kreative Generierung verfälscht logische Validierung |
| ⚖️ GOVERNANCE **immer** zwischen KREATIV und LOGISCH | Kein ungeprüfter Kreativ-Output erreicht LOGISCH |
| 🧠 MEMORY **nach jedem** Task-Durchlauf | Jeder Zyklus erzeugt Learnings |
| 🤖 AUTONOM delegiert, **arbeitet nicht selbst** | AUTONOM ist der Dirigent, nicht der Musiker |
| 📈 SELF-IMPROVE läuft **asynchron** | Verbesserung soll den Haupt-Task nicht blockieren |

---

## 🎯 Minimale ausführbare Ketten

### MINI: Frage beantworten (nur LOGISCH + MEMORY)
```
community-deep-research → wiki-system → consolidate-memory
```

### MINI: UI-Entwurf (nur KREATIV + GOVERNANCE)
```
brainstorming → frontend-design → web-design-guidelines
```

### MINI: Bug fixen (nur GOVERNANCE + LOGISCH + MEMORY + SELF-IMPROVE)
```
systematic-debugging → receiving-code-review → self-improvement
```

### VOLL: Feature von 0 bis Merge
```
AUTONOM: autorun → guide-architekt
KREATIV: brainstorming → writing-plans → frontend-design
GOVERNANCE: verification-before-completion
LOGISCH: test-driven-development → playwright-expert
MEMORY: self-improvement → wiki-system
```

### /goal: Autonome 4-Phasen-Entwicklungskaskade
```
PHASE 1 (Planen):               brainstorming → writing-plans → improve-codebase-architecture
GATE 1→2 (Falsifizierung):      verification-before-completion
PHASE 2 (Planung abschließen):   writing-plans (re-invoke) → systematic-debugging
GATE 2→3 (Falsifizierung):      verification-before-completion
PHASE 3 (Ausführen):             subagent-driven-development → test-driven-development → dispatching-parallel-agents → finishing-a-development-branch
PHASE 4 (Doku):                  documentation-writer → wiki-system → self-improvement
```
→ Vollständige Architektur: [`GOAL-CHAIN.md`](GOAL-CHAIN.md)

---

_6 Stacks · Strikte Kreativ/Logisch-Trennung · Task/Stack Matrix · /goal Chain · August 2026_
