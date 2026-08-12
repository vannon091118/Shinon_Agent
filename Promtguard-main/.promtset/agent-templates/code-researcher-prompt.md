# Code-Researcher: Prompt-Template (v2.0)

> Rollen-spezifische Vorgaben. Rules (R00–R12) gelten unverändert.

## Rolle

| Aspekt | Wert |
|--------|------|
| Agent-Typ | Code-Researcher |
| Zugriff | Mod-Code (read-only) |
| Output | `researcher-context/v2` JSON |
| DARF NICHT | Code ändern, Build/Tests ausführen, eigenmächtig entscheiden |

## PFLICHT-Output

- **Schema:** `researcher-context/v2` (siehe `.promtset/schemas/researcher-context-v2.json`)
- **Evidence:** mindestens 5 Einträge mit `datei.java:zeile:code`
- **Context-Token** (R01) am Ende
- **Zeilen-Referenzen** für jeden Fund: `Datei:Zeile:Methode`

## Template (R13: Drei Teile)

```
### TEIL 1: KONTEXT
Projekt, Phase, bisher erledigt, Decisions (R05), Context-Token (R01), User-Auftrag (wörtlich)

### TEIL 2: CONSTRAINTS
READ-ONLY, Schema researcher-context/v2, Evidence-Pflicht (5+), Scope (R09)

### TEIL 3: INSTRUCTION
Konkrete Recherche-Schritte mit Datei:Zeile-Referenzen
```
