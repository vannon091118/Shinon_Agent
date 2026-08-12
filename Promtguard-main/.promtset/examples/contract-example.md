# Contract-Beispiel (researcher-context/v2)

```json
{
  "schema": "researcher-context/v2",
  "agent": "buffy",
  "task_id": "RES-002",
  "collected_context": {
    "config_definition": [
      {
        "file": "src/EconConfig.java",
        "line": 214,
        "method": "field-declaration",
        "content": "public static int perHeadTax = 0;",
        "context": "Felddeklaration — Default 0 (deaktiviert)"
      }
    ]
  },
  "decisions": [
    {
      "what": "perHeadTax hat kein Hard Cap",
      "why": "...",
      "evidence": "Fiscal.java:224:setHeadTax",
      "confidence": "high"
    }
  ],
  "summary": "perHeadTax wird an 30 Stellen in 11 Dateien referenziert."
}
```

## Schema-Validierung

Beim `ingest` prüft `promptgen.py`:
1. Ist `schema` = "researcher-context/v2"?
2. Sind alle `required`-Felder vorhanden?
3. Passen die Typen?

Bei Fehler: **Ingest wird abgelehnt.**
