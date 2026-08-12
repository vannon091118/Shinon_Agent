# R05 — Decision-Journal

**Jede Entscheidung wird dokumentiert.**  
Nicht nur das WAS, sondern auch das WARUM und die verworfenen Alternativen.

## Decision-Eintrag (JSONL)

```json
{
  "what": "perHeadTax hat KEIN hard cap außerhalb UI",
  "why": "EconConfig.perHeadTax ist int ohne @Range. UI clamps [0,500].",
  "evidence": "Fiscal.java:224:setHeadTax → Math.max(0,v) — kein Math.min(cap)",
  "alternatives_rejected": [
    "Hard Cap 500 in EconConfig: wurde nie implementiert"
  ],
  "confidence": "high",
  "source_task_id": "RES-002",
  "timestamp": "2026-07-28T05:36:55Z"
}
```

## Pflichtfelder

- **what** — Die Entscheidung als Satz (nicht: "Kopfsteuer", sondern: "perHeadTax hat kein Hard Cap")
- **why** — Begründung (nicht: "weil anders", sondern: "Math.max(0,v) ohne Math.min(cap)")
- **evidence** — file:line:content (MUSS existieren, kein "siehe Code")
- **alternatives_rejected** — Mindestens 1 Alternative, die NICHT gewählt wurde

## Optionale Felder

- **confidence** — high / medium / low
- **source_task_id** — RES-NNN oder TASK-NNN
- **timestamp** — ISO-8601

## Wann wird eingetragen?

1. **Nach jedem Research-Ingest** — automatisch aus `decisions[]` des JSON
2. **Nach jedem Coder-Task** — wenn der Coder eine neue Entscheidung getroffen hat
3. **Nie retrospektiv** — Entscheidungen werden live getroffen, nicht nachträglich erfunden
