# R12 — Task-Reihenfolge

**Tasks werden sequenziert, parallelisiert und gelockt.**  
Niemand arbeitet an einem Task, der von einem laufenden Task abhängt.

## Sequentialisierung

Tasks mit Abhängigkeiten MÜSSEN sequenziell ausgeführt werden:

```
TASK-001 (perHeadTax ändern) → TASK-002 (Tests für perHeadTax)
  ↑ geht nicht parallel, weil TASK-002 den geänderten Code braucht
```

## Parallelisierung

Tasks OHNE Abhängigkeiten DÜRFEN parallel laufen:

```
TASK-003 (FirmLedger-Test)  → parallel mit TASK-004 (Wallets-Test) möglich
TASK-005 (UI-Tab)           → parallel mit beiden möglich
```

## Locking (Task-Index)

```json
{
  "TASK-003": {
    "type": "task",
    "status": "in_progress",
    "locked_by": "coder-1",
    "locked_at": "2026-07-28T12:00:00Z"
  }
}
```

- `locked_by` — Welcher Agent arbeitet gerade dran?
- `locked_at` — Seit wann?
- Ein Task kann NUR von EINEM Agenten gleichzeitig gelockt werden

## Status-Diagramm

```
prompt_generated → in_progress → completed
                        ↓
                     failed → prompt_generated (retry)
                        ↓
                     blocked (wartet auf anderen Task)
```

## Maximale Parallelität

- Maximal 2 Tasks parallel (Konfiguration in `constraints.json`)
- Research und Coder können parallel laufen (verschiedene Zugriffsrechte)
- Promter und Coder können parallel laufen (verschiedene Verzeichnisse)
