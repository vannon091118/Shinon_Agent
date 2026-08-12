# R09 — Scope-Bounding

**Jede Aufgabe definiert: WAS drin ist, WAS draußen ist.**  
Ein Task ohne Scope-Endung ist ein Task, der nie fertig wird.

## Pflichtfelder in jedem Task-Prompt

### IN SCOPE (was geändert wird)

- Exakte Datei + Zeile + Änderung
- "EconConfig.java:214 — perHeadTax von 500 auf 2000"
- Nicht: "Kopfsteuer anpassen"

### NICHT IN SCOPE (was NICHT geändert wird)

- Explizite Negativ-Liste
- "Keine Änderungen an: Fiscal.java, Taxes.java, Tests"
- Nicht: "alles andere bleibt"

## Beispiele

| Task | IN SCOPE | NICHT IN SCOPE |
|---|---|---|
| perHeadTax anpassen | EconConfig.java:214 | Fiscal.java, Taxes.java, Tests, UI |
| EngineSeams löschen | EconomySim.java:361 + EconomyAuditEngine.java:188 | Andere Fallbacks, Adapter, Tests |
| FirmLedger-Test | FirmLedgerEdgeCaseTest.java | FirmLedger.java selbst, FlowMeter, Docs |

## Warum?

- Ohne Scope-Endung weiß der Coder nicht, wann er fertig ist
- Ohne Negativ-Liste ändert der Coder Dinge, die er nicht ändern sollte
- Scope-Bounding ist die günstigste Form von Qualitätssicherung
