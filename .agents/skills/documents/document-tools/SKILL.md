---
name: document-tools
description: >-
category: documents
stack: LOGISCH + GOVERNANCE
risk: low
side_effects: file_changes
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
  Arbeite mit Word-Dokumenten (.docx). Erstelle, bearbeite, review und 
  verifiziere professionelle Dokumente. Nutze python-docx für Struktur-Edits
  und native Read/Replace-Tools für schnelle Text-Änderungen.
---

# Document Tools (Word .docx)

Erstelle und bearbeite Word-Dokumente mit Fokus auf Struktur, Formatierung und visuelle Qualität.

## Werkzeug-Priorität

1. **Native Replace/Read** — für exakte Text-Ersetzungen, Tabellen-Updates, Kommentare
2. **`python-docx`** — für Struktur-Edits, Styles, neue Dokumente, komplexe Rewrites
3. **Render-Check** — DOCX → PDF konvertieren zur Layout-Prüfung

## Workflow

1. Dokument lesen und Struktur erfassen
2. Änderungen durchführen (native oder python-docx)
3. Nach jeder signifikanten Änderung: Render-Check via PDF-Export
4. Finale Version speichern

## Source-backed Documents

- Quellen-Dokumente sind Content-Autorität — nicht stillschweigend umbenennen
- Bei Research-Dokumenten: Quellen-Ledger führen (Source, URL, Fakt)
- `web_search` ist nur Lead-Finding, nicht Beweis — echte Seiten fetchen!

## Best Practices

- `tmp/docs/` für Intermediate-Files, `output/doc/` für Finale
- Nach Edit: File-Refresh im Viewer triggern
- Überschreibungen mit `_v2.docx` versionieren
- Layout-Risiko explizit nennen wenn kein Render-Check möglich
