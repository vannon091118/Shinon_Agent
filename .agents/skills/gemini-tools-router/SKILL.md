---
name: gemini-tools-router
description: "Router für 2 gemini-tools-Skills (agy-customizations, antigravity_guide). Leitet User-Intents automatisch an den richtigen Sub-Skill weiter. Routing-Tabelle im Body."
category: gemini-tools
stack: AUTONOM + GOVERNANCE
risk: medium
side_effects: file_changes
requires_approval: true
version: 1.0.0
last_verified: 2026-08-12

---
# 🧭 Gemini-Tools Router — 2 Skills

> **Router für `gemini-tools/`** — Wählt automatisch den richtigen Sub-Skill basierend auf User-Intent.

## 🗺️ Routing-Tabelle

| User sagt... | → Skill | Pfad |
|---|---|---|
| "[gemini] The Antigravity Customization System allows you to tailor the agent's behavior, teach it new workflows, enforce guidelines, and ...", "By customizing the agent, you can transition it from a general-purpose assistant to an expert pair programmer specialized in your project's ..." | `agy-customizations` | `gemini-tools/agy-customizations` |
| "[gemini] Provides a comprehensive guide, quick reference, and sitemap for Google Antigravity (AGY), including the Antigravity CLI (agy), ...", "Activate this skill when the user asks questions about how to use, configure, or customize Antigravity, AGY, the agy CLI, the Antigravity ..." | `antigravity-guide` | `gemini-tools/antigravity_guide` |

## 🔀 Routing-Logik

```
  "Agy" → agy-customizations
  "Antigravity" → antigravity-guide
  Unklar? → Nachfrage: Welche Aufgabe, welcher Anbieter?
```

## 📋 Sub-Skill-Register

| # | Skill | Pfad |
|---|---|---|
| 1 | `agy-customizations` | `gemini-tools/agy-customizations` |
| 2 | `antigravity-guide` | `gemini-tools/antigravity_guide` |

_2 Skills · gemini-tools · 2026-08-12_
