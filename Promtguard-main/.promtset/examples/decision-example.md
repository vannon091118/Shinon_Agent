# Decision-Journal-Beispiel

```json
{
  "what": "perHeadTax hat KEIN hard cap außerhalb UI + TreasuryCrisis",
  "why": "EconConfig.perHeadTax ist int ohne @Range-Annotation. UI-Slider clamps [0,500]. TreasuryCrisis setzt auf 500. Aber setHeadTax() clamps nur auf ≥0 — kein Sentinel gegen Overflow.",
  "evidence": "Fiscal.java:224:setHeadTax → `EconConfig.perHeadTax = Math.max(0, v);` — kein `Math.min(cap)`",
  "alternatives_rejected": [
    "Hard Cap 500 in EconConfig: Feld ist raw public static int"
  ],
  "confidence": "high",
  "source_task_id": "RES-002",
  "timestamp": "2026-07-28T05:36:55Z"
}
```

## Felder

| Feld | Pflicht | Beispiel |
|---|---|---|
| what | ja | "perHeadTax hat kein Hard Cap" |
| why | ja | "Math.max(0,v) ohne Math.min(cap)" |
| evidence | ja | "Fiscal.java:224:setHeadTax..." |
| alternatives_rejected | ja | [...] |
| confidence | nein | "high" |
| source_task_id | nein | "RES-002" |
| timestamp | ja | ISO-8601 |
