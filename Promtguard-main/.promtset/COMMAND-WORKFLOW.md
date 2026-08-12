# COMMAND-WORKFLOW — Einfacher Workflow

> Promter hat KEINEN Code-Zugriff. Commands → JSON → Nächster Prompt.

```
Agent (hat Code-Zugriff)          Promter (KEIN Code-Zugriff)
  → Führt Commands aus               → Liest JSON + State
  → Liefert JSON mit file:line REFs  → Entscheidet: RES vs TASK
  → NICHTS mit Promter zu tun        → Generiert nächsten Prompt
```

## Workflow

1. **User** gibt Wunsch
2. **Promter** generiert Research-Prompt (`promptgen.py research`)
3. **Researcher** liest Code → JSON mit `file:line:method`-Referenzen
4. **Promter** ingested JSON → prüft Konsistenz (RULE 1) → baut Task-Prompt
5. **Coder** implementiert → Context-Token zurück
6. **Promter** updated State → nächster Zyklus

## JSON-Schema

Jeder Fund MUSS `file:line:method` als REF-ID enthalten (Schema: `command-result-v1.json`).
