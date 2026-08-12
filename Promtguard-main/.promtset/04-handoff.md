# R04 — Handoff-Protokoll

**Übergaben zwischen Agenten folgen dem definierten Schema.**  
Jeder Handoff wird geloggt, kein Agent startet ohne zu wissen, wer vor ihm war.

## Handoff-Eintrag (JSONL)

```json
{
  "handoff_version": "1.0",
  "from": "promter",
  "to": "implementer-1",
  "timestamp": "2026-07-28T12:00:00Z",
  "note": "RES-001 bis RES-009 abgeschlossen. 26 Decisions in journal.",
  "promtset_version": "2.0.0"
}
```

## Erzeugung

```bash
python3 .promtset/tools/promptgen.py handoff \
  --from promter --to coder-1 \
  --note "TASK-003: FirmLedger.java:278 profit-Formel fixen"
```

## Wann?

1. **Nach Research → vor Task-Build:** Researcher hat JSON geliefert, Promter muss an Coder übergeben
2. **Nach Coder → vor nächstem Research:** Coder hat Task abgeschlossen, nächster Research kann starten
3. **Bei Fehler:** Coder abgestürzt → Handoff mit Status "failed" + Fehlerbeschreibung

## Pflichtfelder

- `from` — Wer übergibt? (promter, researcher, coder, rolle-A, rolle-B)
- `to` — Wer kriegt? (gleiche Liste)
- `timestamp` — ISO-8601
- `note` — WAS wurde übergeben? (nicht: "hier ist der Task", sondern: "EconConfig.java:214 500→2000, ready für Test")
