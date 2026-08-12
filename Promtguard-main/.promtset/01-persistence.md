# R01 — Persistenz

**Kontext geht nie verloren.** Jeder Agent, der startet, hat den VOLLSTÄNDIGEN Kontext aller Vorgänger.

## State-Dateien (append-only JSONL)

| Datei | Zweck | Format |
|---|---|---|
| `context-log.jsonl` | Context-Token pro abgeschlossenem Task | JSONL, eine Zeile pro Token |
| `decision-journal.jsonl` | Jede Entscheidung mit WAS + WARUM | JSONL, eine Zeile pro Decision |
| `claim-log.jsonl` | Claims (atomare Forschungs-Aussagen) + Verifikations-Trail | JSONL, latest-wins per Claim-ID |
| `handoffs.jsonl` | Jede Übergabe zwischen Agenten | JSONL, eine Zeile pro Handoff |
| `task-index.json` | Task-ID → Status/Pfad-Mapping | JSON, einmalig upgedatet |
| `constraints.json` | Projekt-Constraints (max 3 Dateien/Task etc.) | JSON, einmalig upgedatet |

## Append-only (unverhandelbar)

- Niemals bestehende Einträge löschen oder überschreiben
- Neue Einträge IMMER am Ende anhängen
- `task-index.json` ist die EINZIGE Ausnahme (wird upgedatet, nicht appendinged)

## Context-Token-Struktur

Jeder abgeschlossene Task erzeugt genau EINEN Context-Token:

```json
{
  "id": "CTX-PROJEKT-PHASE-001",
  "timestamp": "2026-07-28T12:00:00Z",
  "source_task_id": "TASK-001",
  "agent": "coder-1",
  "task": "Kurzbeschreibung",
  "status": "completed",
  "summary": "Was gemacht wurde (1-2 Sätze)",
  "code_refs": [{"file": "src/main.java", "line": 42, "method": "calculate"}],
  "diff_stats": "+15 -40"
}
```

## Wiederherstellung nach Agenten-Wechsel

```bash
python3 .promtset/tools/promptgen.py resume -n 10
# → Gibt INIT-Block mit den letzten 10 Context-Token + Decisions + Handoffs aus
```

**Ohne State-Verifizierung = Keine Arbeit.**
