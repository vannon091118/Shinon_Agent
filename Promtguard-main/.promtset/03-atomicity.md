# R03 — Aufgaben-Atomizität

**Jede Aufgabe = genau EINE Sache.**  
Ein Task ändert genau eine Konstante, migriert genau eine Methode, schreibt genau einen Test.

## Warum?

- Ein Task, der 5 Dinge macht, kann nicht atomar abgeschlossen werden
- Wenn Task "perHeadTax-Cap" auch "UI-Slider" und "Test" macht, ist nach 2/3 kein klarer Status möglich
- Code-Review bei 5 Änderungen in 5 Dateien ist unmöglich

## Grenzen

- Maximal **3 Dateien pro Task** (Konfiguration: `constraints.json`)
- Maximal **1 logische Änderung pro Task** ("perHeadTax-Cap" ≠ "FirmLedger-Refactoring")
- Tasks, die "und" im Namen haben, sind NICHT atomar → teilen

## Beispiele

| ❌ Zu groß | ✅ Atomar |
|---|---|
| "Bau die Kopfsteuer um" | "EconConfig.java:214 — 500→2000" |
| "Migriere EngineSeams zu Mirror" | "FirmLedger.java:178 — EngineSeams→EngineMirror.api().rooms()" |
| "Schreib Tests für 10 Klassen" | "BrokeFoodPlan: Edge-Case-Test für starvation()" |

## Abgrenzung (R09)

Jeder Task-Prompt MUSS enthalten:
- **IN SCOPE:** Exakte Datei + Zeile + Änderung
- **NICHT IN SCOPE:** Was NICHT geändert wird (andere Dateien, Tests, Docs)
