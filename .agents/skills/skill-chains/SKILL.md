---
name: skill-chains
description: "Task/Stack-generalisierte Skill-Chain-Architektur. 6 Core-Stacks (MEMORY, SELF-IMPROVE, GOVERNANCE, AUTONOM, KREATIV, LOGISCH) mit strikter Kreativ/Logisch-Trennung. Task/Stack-Matrix für Feature-Bau, Bug-Fixes, Refactoring, Research, Design, Security. Use zusammen mit goal-chain für autonome Entwicklung."
category: agents
stack: AUTONOM
risk: low
side_effects: none
requires_approval: false
version: "2.0.0"
last_verified: "2026-08-11"

---
# 🧠 Skill Chains — Task/Stack-Generalisiert

> **Prinzip:** Welcher STACK wird für welchen TASK-TYP aktiviert?
> Strikte Trennung: 🎨 Kreativ ≠ 🔬 Logisch — **nie im selben Durchlauf.**

---

## 📐 Die 7 Core-Stacks (6 + Evil Twin)

### 🧠 MEMORY — Wissen behalten & lernen
```
LERNZYKLUS: task-abschluss → self-improvement → wiki-system → consolidate-memory
```
**Skills:** `self-improvement`, `wiki-system`, `consolidate-memory`

### 📈 SELF-IMPROVE — Kontinuierlich besser werden
```
VERBESSERUNGSZYKLUS: receiving-code-review → improve-codebase-architecture → self-improvement
```
**Skills:** `self-improvement`, `improve-codebase-architecture`, `receiving-code-review`

### ⚖️ GOVERNANCE — Deterministische Regeln & Gates
```
GATE-CHECK: threat-model → security-scan → verification-before-completion → track-findings
ADVERSARIAL-CHECK: thinker-output → 👯 evil-twin-protocol → synthese
```
**Skills:** `multi-agent-orchestrator`, `security-scan`, `verification-before-completion`, `track-findings`, `evil-twin-protocol`

### 🤖 AUTONOM — Selbständiges Arbeiten ohne Mensch
```
AUTO-ZYKLUS: autorun → guide-architekt → brainstorming → dispatching-parallel-agents → executing-plans → finishing-a-development-branch
```
**Skills:** `autorun`, `guide-architekt`, `brainstorming`, `dispatching-parallel-agents`, `executing-plans`, `subagent-driven-development`, `finishing-a-development-branch`

### 🎨 KREATIV — Generieren, Designen, Ideen entwickeln
```
⚠️ STRIKT GETRENNT VON LOGISCH — NIE GEMISCHT
KREATIV-PASS: brainstorming → frontend-design → canvas-design → media-generation
```
**Skills:** `brainstorming`, `frontend-design`, `canvas-design`, `media-generation`

### 👯 EVIL TWIN — Adversariale Validierung (GOVERNANCE + LOGISCH)
```
⚠️ NACH JEDEM THINKER-SCHRITT — FESTER BESTANDTEIL
EVIL-TWIN-PASS: thinker-output → 👯 evil-twin-protocol → WIDERSPRUCH.md → SYNTHESE
```
**Skills:** `evil-twin-protocol`
**Regeln:** Gleiche Datenlage wie Original-Thinker, adversarial Prompt, NUR fundamentale Widersprüche, keine Kleinkariertheit

### 🔬 LOGISCH — Analysieren, Prüfen, Debuggen
```
⚠️ STRIKT GETRENNT VON KREATIV — NIE GEMISCHT
LOGISCH-PASS: systematic-debugging → python-testing-patterns → playwright-expert → validation
```
**Skills:** `systematic-debugging`, `python-testing-patterns`, `playwright-expert`, `validation`

---

## 🔀 Task/Stack-Matrix

| Task-Typ | AUTONOM | KREATIV | GOVERNANCE | EVIL TWIN | LOGISCH | MEMORY | SELF-IMPROVE |
|---|---|---|---|---|---|---|---|
| **Feature bauen** | ✅ | ✅ (Design) | ✅ (Pre-Merge) | ✅ (Jeder Thinker) | ✅ (Tests) | ✅ | bei Fehlern |
| **Bug fixen** | — | — | ✅ | ✅ (Debug-Analyse) | ✅ (Debug) | ✅ | ✅ |
| **Refactoring** | — | — | ✅ (Arch-Check) | ✅ (Plan-Review) | ✅ (Verify) | ✅ | ✅ |
| **Forschen** | ✅ | ✅ (Ideate) | — | ✅ (Hypothesen) | ✅ (Validate) | ✅ | — |
| **Design-System** | — | ✅ | ✅ (Guidelines) | ✅ (Design-Review) | — | — | bei Review |
| **Security-Audit** | — | — | ✅ (Scan) | ✅ (Threat-Model) | ✅ (Validate) | ✅ | ✅ (Harden) |
| **Code-Review** | — | — | ✅ (Gates) | ✅ (Arch-Review) | ✅ (Analyze) | — | ✅ |
| **Brainstorming** | ✅ | ✅ | — | ✅ (Gegenideen) | — | ✅ | — |
| **Deployment** | ✅ | — | ✅ (Verify) | ✅ (Rollback-Plan) | ✅ (Test) | ✅ | bei Rollback |

---

## 🔄 Generalisierte Zwei-Phasen-Architektur (mit Evil Twin)

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
    │ 👯 EVIL TWIN │◄────┘
    │ adversarial │
    │ fundamental │
    │ widersprechen│
    └──────┬──────┘
           │ SYNTHESE
           ▼
    ┌─────────────┐
    │ ⚖️ GOVERNANCE│
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
| 👯 EVIL TWIN **nach jedem** Thinker-Schritt | Kein ungeprüfter Thinker-Output existiert ohne Widerspruch |
| ⚖️ GOVERNANCE **immer** zwischen EVIL TWIN und LOGISCH | Kein ungeprüfter Kreativ-Output erreicht LOGISCH |
| 🧠 MEMORY **nach jedem** Task-Durchlauf | Jeder Zyklus erzeugt Learnings |
| 🤖 AUTONOM delegiert, **arbeitet nicht selbst** | AUTONOM ist der Dirigent, nicht der Musiker |
| 📈 SELF-IMPROVE läuft **asynchron** | Verbesserung soll den Haupt-Task nicht blockieren |
| 👯 EVIL TWIN ≠ GOVERNANCE | Evil Twin ist ADVERSARIAL (denkt umgekehrt), GOVERNANCE ist DETERMINISTISCH (prüft Regeln) |

---

## 🎯 Minimale ausführbare Ketten

### MINI: Frage beantworten (LOGISCH + MEMORY)
```
community-deep-research → wiki-system → consolidate-memory
```

### MINI: UI-Entwurf (KREATIV + GOVERNANCE)
```
brainstorming → frontend-design → web-design-guidelines
```

### MINI: Bug fixen (GOVERNANCE + LOGISCH + MEMORY + SELF-IMPROVE)
```
systematic-debugging → receiving-code-review → self-improvement
```

### VOLL: Feature von 0 bis Merge
```
AUTONOM: autorun → guide-architekt
KREATIV: brainstorming → 👯 evil-twin → writing-plans → 👯 evil-twin → frontend-design → 👯 evil-twin
GOVERNANCE: verification-before-completion
LOGISCH: test-driven-development → 👯 evil-twin (pro implementer) → playwright-expert
MEMORY: self-improvement → wiki-system
```

### /goal: Autonome 4-Phasen-Entwicklungskaskade
→ Siehe `goal-chain` Skill für die vollständige Chain.

---

_7 Stacks (inkl. Evil Twin) · 36 Chain-Scripts · Strikte Kreativ/Logisch-Trennung · Task/Stack Matrix · August 2026_
