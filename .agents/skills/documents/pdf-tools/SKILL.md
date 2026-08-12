---
name: pdf-tools
description: "\"Arbeite mit PDF-Dateien: lesen, extrahieren, erstellen, Formulare ausfüllen.\" Nutze pypdf/pdfplumber für Extraktion, reportlab für Generierung, und pdftoppm für Render-Checks."
category: documents
stack: LOGISCH + GOVERNANCE
risk: low
side_effects: file_changes
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
---

# PDF Tools

Erstelle, bearbeite und verifiziere PDF-Dokumente.

## Werkzeug-Wahl

| Werkzeug | Zweck |
|---|---|
| `pypdf` / `pdfplumber` | Text-Extraktion, Formular-Inspektion |
| `reportlab` | Neue PDFs programmatisch erstellen |
| `pdftoppm` (Poppler) | PDF → PNG Rendering für Layout-Checks |
| Native PDF-Read | Schnelle strukturierte Lesevorgänge |

## Workflow

1. **Lesen**: PDF-Inhalt extrahieren (Text, Formularfelder, Metadaten)
2. **Verarbeiten**: Änderungen, Extraktionen, Formularbefüllung
3. **Erstellen**: Neue PDFs mit `reportlab` generieren
4. **Verifizieren**: Render-Check mit `pdftoppm -png input.pdf output_prefix`

## Best Practices

- `tmp/pdfs/` für Intermediate, `output/pdf/` für Finale
- Nach jedem Update: Seiten rendern und Alignment/Spacing prüfen
- Formular-IDs aus `read_pdf`-Output exakt übernehmen
- `reportlab` für pixelgenaue Layouts
- Keine LibreOffice-Abhängigkeit voraussetzen
