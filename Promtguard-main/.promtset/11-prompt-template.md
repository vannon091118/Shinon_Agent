# R11 — Prompt-Template (deklarativ)

**Jeder Agent strukturiert seine Prompts nach dem Drei-Teile-Template. WAS vorgeben, WIE dem Agenten überlassen.**

## Kernprinzip: Deklarativ > Imperativ

```
✅ "EconConfig.java:214 — perHeadTax von 0 auf 500"
❌ "Öffne EconConfig.java, suche Zeile 214, ändere 'public static int perHeadTax = 0;' in ..."
```

- Deklarative Vorgaben sind sprachagnostisch (funktionieren in Java, Python, Rust)
- Der Agent kennt sein Toolset besser als der Promter
- Imperative Anweisungen altern schnell (ändert sich die Zeile, ist die Anweisung falsch)

## Drei-Teile-Struktur

JEDER Prompt besteht aus genau 3 Teilen:

```
### TEIL 1: KONTEXT
- Projekt: [...]
- Letzter Context: CTX-...
- Task-ID: TASK-NNN

### TEIL 2: CONSTRAINTS
- IN SCOPE: [...]
- NICHT IN SCOPE: [...]
- Output: Context-Token (R01) oder JSON (R08)
- Max 3 Dateien (R03)

### TEIL 3: INSTRUCTION
1. Erster Schritt
2. Zweiter Schritt
3. Akzeptanzkriterium
```

## Varianten

| Agent | TEIL 1 | TEIL 2 | TEIL 3 |
|---|---|---|---|
| **Researcher** | Kontext + Forschungsfrage | READ-ONLY, JSON-Output | Dateien + Methoden zum Anschauen |
| **Coder** | Kontext + exakter Task | Scope, Edit-Regeln | Datei:Zeile + Änderung |
| **Rolle A** | User-Wunsch | NUR State-Zugriff | State scannen, Lücken finden |
| **Rolle B** | Original-Auftrag + Research-JSON | Task-Split-Regeln | Atomare Tasks bauen |

## Ausnahme

Bei kritischen Stellen (private Engine-Seams, reflection-basierte Adapter) DARF der Promter imperativ werden — aber NUR mit Begründung.
