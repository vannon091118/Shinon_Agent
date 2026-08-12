# Handoff-Beispiel

```json
{
  "handoff_version": "1.0",
  "from": "promter",
  "to": "implementer-1",
  "timestamp": "2026-07-28T12:00:00Z",
  "note": "RES-001 bis RES-009 abgeschlossen. 26 Decisions in journal. Ready für Implementierung.",
  "promtset_version": "2.0.0"
}
```

## Erzeugung

```bash
python3 .promtset/tools/promptgen.py handoff \
  --from promter --to coder-1 \
  --note "TASK-003: FirmLedger profit-Formel fixen"
```

## Felder

| Feld | Pflicht | Beispiel |
|---|---|---|
| handoff_version | ja | "1.0" |
| from | ja | "promter" |
| to | ja | "implementer-1" |
| timestamp | ja | "2026-07-28T12:00:00Z" |
| note | ja | "Was wurde übergeben" |
| promtset_version | ja | "2.0.0" |
