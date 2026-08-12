# R02 — Kontext-Vererbung

**Sub-Agenten erhalten den VOLLSTÄNDIGEN Kontext-Pfad.**  
Kein Agent startet ohne Wissen der Vorgänger.

## Vererbungskette

```
User → Promter → Researcher → Promter → Coder → Promter
  ↑         ↑          ↑          ↑        ↑        ↑
  |    lädt State  |   kriegt    |   lädt |   gibt  |
  |    + generiert |   JSON +    |   State|   CTX   |
  |    Research    |   Research- |   + baut|   + upd.|
  |                |   Prompt    |   Task  |   State |
```

## Was wird vererbt?

1. **Alle Context-Token** aus `context-log.jsonl` (nicht nur die letzten 5)
2. **Alle Decisions** aus `decision-journal.jsonl`
3. **Task-Status** aus `task-index.json` (was ist schon erledigt?)
4. **Letzter Handoff** aus `handoffs.jsonl` (wer hat was übergeben?)

## Was passiert NICHT?

- Sub-Agenten bekommen KEINEN Zugriff auf `.promtset/out/` (Research-Rohdaten bleiben beim Promter)
- Sub-Agenten bekommen KEINEN Zugriff auf Mod-Code, den sie nicht brauchen (Researcher ≠ Coder)

## Implementierung

Der Promter übergibt den Kontext via INIT-Block am Anfang jedes Prompts:

```markdown
## INIT: State-First Protocol
- Letzter Context: CTX-SYX-TASK-003 (completed, +15 -40)
- Letzte Decision: perHeadTax hard cap existiert nicht
- Offene Tasks: TASK-004 (wartet auf Coder)
- Projekt: SyxEconomyMod (Java/Maven)
```
