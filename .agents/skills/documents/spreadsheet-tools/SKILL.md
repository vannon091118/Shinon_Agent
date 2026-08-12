---
name: spreadsheet-tools
description: "Arbeite mit Excel-Dateien (.xlsx, .xls, .csv, .tsv). Erstelle, bearbeite, auditiere und analysiere Spreadsheets. Nutze openpyxl für reichhaltige Workbooks, pandas für Datenanalyse, und native Lese/Schreib-Tools für schnelle Edits."
category: documents
stack: LOGISCH + GOVERNANCE
risk: low
side_effects: file_changes
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
---

# Spreadsheet Tools

Erstelle, bearbeite und auditiere Excel-Workbooks mit professioneller Qualität.

## Werkzeuge & Pfade

| Pfad | Wann |
|---|---|
| `openpyxl` | Mehrere Sheets, Formeln, Charts, Formatierung, Templates |
| `pandas` | Datenanalyse, Reshaping, Extraktion |
| Native reads | Schnelle Zell-Lesevorgänge, Style-Inspektion |
| Native writes | Einfache Tabellen-Schreibvorgänge |

## Workbook-Erstellung

Gute Standard-Struktur: **Executive Summary → Inputs/Assumptions → Calculation → Output**

1. Vorher Struktur durchdenken (Sheets, Formeln, Layout)
2. Builder-Script mit `openpyxl` schreiben
3. Formeln statt Hardcoding wo sinnvoll
4. Validierung: Formeln prüfen, Recalculation, Export-Check

## Audit-Modus

Bei Workbook-Audit diese Checks:

- Formelfehler (`#REF!`, `#VALUE!`, `#DIV/0!`)
- Hardcodes in Formeln
- Inkonsistente Formeln in Reihen/Spalten
- Off-by-one Ranges
- Zirkuläre Referenzen
- Kaputte Cross-Sheet-Links
- Unit/Skalen-Mismatches
- Versteckte Zeilen/Tabs

## Best Practices

- `openpyxl` für finale Workbook-Erstellung, nicht `pandas.to_excel`
- Nach externen Edits: Recalculation triggern
- Bei Finance/Payroll-Modellen: Quellen-Audit-Trail in Assumptions-Sheet
- Versteckte Helper-Sheets vor Delivery entfernen
