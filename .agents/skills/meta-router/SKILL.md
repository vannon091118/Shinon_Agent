---
name: meta-router
description: "Router für 3 meta-Skills (find-skills, self-improvement, skill-creator). Leitet User-Intents automatisch an den richtigen Sub-Skill weiter. Routing-Tabelle im Body."
category: meta
stack: AUTONOM + GOVERNANCE
risk: medium
side_effects: file_changes
requires_approval: true
version: 1.0.0
last_verified: 2026-08-12

---
# 🧭 Meta Router — 3 Skills

> **Router für `meta/`** — Wählt automatisch den richtigen Sub-Skill basierend auf User-Intent.

## 🗺️ Routing-Tabelle

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Helps users discover and install agent skills when they ask questions like \"how do I do X\", \"find a skill for X\", \"is there a skill ...", "This skill should be used when the user is looking for functionality that might exist as an installable skill" | `find-skills` | `meta/find-skills` |
| "Captures learnings, errors, corrections, and feature requests to enable continuous improvement", "Use when: (1) User corrects Claude ('No, that's wrong...', 'Actually...'), (2) User requests a capability that doesn't exist, (3) Claude ..." | `self-improvement` | `meta/self-improvement` |
| "Create new skills, modify and improve existing skills, and measure skill performance", "Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill ..." | `skill-creator` | `meta/skill-creator` |

## 🔀 Routing-Logik

```
  "Find" → find-skills
  "Self" → self-improvement
  "Skill" → skill-creator
  Unklar? → Nachfrage: Welche Aufgabe, welcher Anbieter?
```

## 📋 Sub-Skill-Register

| # | Skill | Pfad |
|---|---|---|
| 1 | `find-skills` | `meta/find-skills` |
| 2 | `self-improvement` | `meta/self-improvement` |
| 3 | `skill-creator` | `meta/skill-creator` |

_3 Skills · meta · 2026-08-12_
