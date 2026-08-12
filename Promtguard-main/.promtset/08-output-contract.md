# R08 — Output-Contract

**Agent-zu-Agent-Kommunikation folgt definierten Schemata.**  
Kein Agent rät, was der andere von ihm will.

## Aktive Schemata

| Schema | Datei | Zweck |
|---|---|---|
| `researcher-context/v2` | `.promtset/schemas/researcher-context-v2.json` | Research-Ergebnisse (bevorzugt) |
| `researcher-context/v1` | `.promtset/schemas/researcher-context-v1.json` | Research-Ergebnisse (legacy) |
| `live-test-findings/v1` | `.promtset/schemas/live-test-findings-v1.json` | Live-Test-Ergebnisse |
| `command-result/v1` | `.promtset/schemas/command-result-v1.json` | Command-Ausführungs-Ergebnisse |
| `claim/v1` | `.promtset/schemas/claim-v1.json` | Claim-Eintrag (claim-log.jsonl) |

## Schema-Anforderungen

Jedes Schema definiert:
- **required** — Pflichtfelder (bei Fehlen → Ingest fehlgeschlagen)
- **properties** — Feld-Typen + Beschreibungen
- **$id** — Eindeutige ID für Schema-Referenzen

## Validierung

Beim `ingest`-Befehl prüft `promptgen.py`:
1. Ist das `schema`-Feld gültig?
2. Sind alle `required`-Felder vorhanden?
3. Entsprechen die Typen der Definition?

Bei Schema-Verstoß: **Ingest fehlgeschlagen, JSON wird NICHT persistiert.**
