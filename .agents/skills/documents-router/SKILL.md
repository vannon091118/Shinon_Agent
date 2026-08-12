---
name: documents-router
description: "Router für 4 documents-Skills (document-tools, pdf-tools, presentation-tools, spreadshee...). Leitet User-Intents automatisch an den richtigen Sub-Skill weiter. Routing-Tabelle im Body."
category: documents
stack: AUTONOM + GOVERNANCE
risk: medium
side_effects: file_changes
requires_approval: true
version: 1.0.0
last_verified: 2026-08-12

---
# 🧭 Documents Router — 4 Skills

> **Router für `documents/`** — Wählt automatisch den richtigen Sub-Skill basierend auf User-Intent.

## 🗺️ Routing-Tabelle

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Arbeite mit Word-Dokumenten (.docx", "Erstelle, bearbeite, review und verifiziere professionelle Dokumente" | `document-tools` | `documents/document-tools` |
| "Arbeite mit PDF-Dateien: lesen, extrahieren, erstellen, Formulare ausfüllen.\" Nutze pypdf/pdfplumber für Extraktion, reportlab für ..." | `pdf-tools` | `documents/pdf-tools` |
| "Erstelle und bearbeite PowerPoint-Präsentationen (.pptx", "Baue visuell anspruchsvolle Slide-Decks mit python-pptx oder Artifact-Tool" | `presentation-tools` | `documents/presentation-tools` |
| "Arbeite mit Excel-Dateien (.xlsx, .xls, .csv, .tsv", "Erstelle, bearbeite, auditiere und analysiere Spreadsheets" | `spreadsheet-tools` | `documents/spreadsheet-tools` |

## 🔀 Routing-Logik

```
  "Document" → document-tools
  "Pdf" → pdf-tools
  "Presentation" → presentation-tools
  "Spreadsheet" → spreadsheet-tools
  Unklar? → Nachfrage: Welche Aufgabe, welcher Anbieter?
```

## 📋 Sub-Skill-Register

| # | Skill | Pfad |
|---|---|---|
| 1 | `document-tools` | `documents/document-tools` |
| 2 | `pdf-tools` | `documents/pdf-tools` |
| 3 | `presentation-tools` | `documents/presentation-tools` |
| 4 | `spreadsheet-tools` | `documents/spreadsheet-tools` |

_4 Skills · documents · 2026-08-12_
