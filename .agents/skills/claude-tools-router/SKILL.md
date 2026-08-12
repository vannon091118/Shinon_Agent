---
name: claude-tools-router
description: "Router für 9 claude-tools-Skills (consolidate-memory, docx, explain-usage, morning, pdf, pp...). Leitet User-Intents automatisch an den richtigen Sub-Skill weiter. Routing-Tabelle im Body."
category: claude-tools
stack: AUTONOM + GOVERNANCE
risk: medium
side_effects: file_changes
requires_approval: true
version: 1.0.0
last_verified: 2026-08-12

---
# 🧭 Claude-Tools Router — 9 Skills

> **Router für `claude-tools/`** — Wählt automatisch den richtigen Sub-Skill basierend auf User-Intent.

## 🗺️ Routing-Tabelle

| User sagt... | → Skill | Pfad |
|---|---|---|
| "[claude] \"Reflective pass over your memory files — merge duplicates, fix stale facts, prune the index.\" | `consolidate-memory` | `claude-tools/consolidate-memory` |
| "[claude] \"Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files) or Word templates ...", "Triggers include: any mention of 'Word doc', 'word document', '.docx', '.dotx', or requests to produce professional documents with ..." | `docx` | `claude-tools/docx` |
| "Explain where this session's tokens went, with one simple chart in plain language", "Use when the user says things like \'explain my usage\', \'where did my tokens go\', or asks for a usage breakdown" | `explain-usage` | `claude-tools/explain-usage` |
| "[claude] \"Render the user's morning brief as a styled HTML artifact, or set it up as a recurring weekday task", "Use only when the user explicitly asks to run, see, or set up their morning brief, or if they invoke /morning by name" | `morning` | `claude-tools/morning` |
| "[claude] Use this skill whenever the user wants to do anything with PDF files", "This includes reading or extracting text/tables from PDFs, combining or merging multiple PDFs into one, splitting PDFs apart, rotating ..." | `pdf` | `claude-tools/pdf` |
| "PPTX creation, editing, and analysis" | `pptx` | `claude-tools/pptx` |
| "Create or update a scheduled task that runs automatically", "Use when the user says things like \'every day\', \'each morning\', \'remind me in an hour\', \'run this at noon\', or wants to reschedule ..." | `schedule` | `claude-tools/schedule` |
| "[claude] \"Guided Cowork setup — install role-matched plugins, connect your tools, try a skill.\" | `setup-cowork` | `claude-tools/setup-cowork` |
| "XLSX creation, editing, and analysis" | `xlsx` | `claude-tools/xlsx` |

## 🔀 Routing-Logik

```
  "Consolidate" → consolidate-memory
  "Docx" → docx
  "Explain" → explain-usage
  "Morning" → morning
  "Pdf" → pdf
  "Pptx" → pptx
  "Schedule" → schedule
  "Setup" → setup-cowork
  "Xlsx" → xlsx
  Unklar? → Nachfrage: Welche Aufgabe, welcher Anbieter?
```

## 📋 Sub-Skill-Register

| # | Skill | Pfad |
|---|---|---|
| 1 | `consolidate-memory` | `claude-tools/consolidate-memory` |
| 2 | `docx` | `claude-tools/docx` |
| 3 | `explain-usage` | `claude-tools/explain-usage` |
| 4 | `morning` | `claude-tools/morning` |
| 5 | `pdf` | `claude-tools/pdf` |
| 6 | `pptx` | `claude-tools/pptx` |
| 7 | `schedule` | `claude-tools/schedule` |
| 8 | `setup-cowork` | `claude-tools/setup-cowork` |
| 9 | `xlsx` | `claude-tools/xlsx` |

_9 Skills · claude-tools · 2026-08-12_
