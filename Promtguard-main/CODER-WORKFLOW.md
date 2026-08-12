# CODER-WORKFLOW — So übergibst du Tasks an deinen Coder

> **Promtset v2.0.0** | Ziel: Minimaler Aufwand für den Coder.
> Der Promter-Agent bereitet ALLES vor — der Coder muss nur noch implementieren.

---

## Architektur: Drei-Rollen-Dreieck

```
                      AGENT 
                      
                AGENT LIEST USER INPUT !  
                  
                  /            \
     "Ich will X" /              \ "Hier sind deine Tasks"
                /                \
               v                  v
    ┌──────────────────┐   ┌──────────────────────┐
    │  ROLLE A         │   │  ROLLE B              │
    │  Research-Gen    │   │  Task-Splitter        │
    │  (NUR Promter)   │   │  (NUR Promter)        │
    └────────┬─────────┘   └──────────┬────────────┘
             │                        │
             │ Research-Prompt        │ Coder-Task-Prompts
             v                        v
    ┌──────────────────┐   ┌──────────────────────┐
    │  RESEARCHER       │   │  CODER                │
    │  (hat Mod-Zugriff)│   │  (hat Mod-Zugriff)    │
    │  liest Code,      │   │  implementiert,       │
    │  schreibt NICHT   │   │  testet, committed    │
    └──────────────────┘   └──────────────────────┘
```

**Promter-Agenten (Rolle A/B):** NUR Zugriff auf `.promtset/state/`. Kein Code-Zugriff.
**Researcher/Coder:** VOLLER Zugriff auf Mod-Ordner. Researcher liest nur, Coder schreibt.

---

## Phase 1: Du startest einen Task

**Prompt an Rolle A (Research-Generator):**

```
@Rolle-A

Ich will: [DEIN TASK IN EIGENEN WORTEN, z.B. "die Kopfsteuer soll
einen Freibetrag von 2000 Denari bekommen statt 500"]

Stell mir die Fragen, die der Researcher klären muss, bevor der
Coder anfangen kann. Lies den State, finde die Lücken.
```

Rolle A liest jetzt `.promtset/state/` (Context-Tokens, Entscheidungen,
Task-Index) und erzeugt einen **Research-Prompt** mit Gap-Analyse.

---

## Phase 2: Rolle A liefert den Research-Prompt

Rolle A antwortet mit:

```
## KONTEXT-SCAN-PROTOKOLL
- Gescannt: 3 Context-Token, 4 Entscheidungen, 0 Handoffs
- Übernommen: CTX-c9d2e1 (Projekt-Struktur), CTX-f7a3d5 (Subsysteme)
- Modus: discover

## RESEARCH-PROMPT
### TEIL 1: KONTEXT
[kompakter Projekt-Kontext + dein Original-Prompt wörtlich]

### TEIL 2: CONSTRAINTS
- SCOPE: READ-ONLY. Nur diese 3 Dateien lesen: Taxes.java,
  EconConfig.java, Fiscal.java
- Output-Pflicht: JSON, Schema researcher-context/v1

### TEIL 3: INSTRUCTION
1. In Taxes.java: Wo genau wird perHeadTaxExemptionThreshold
   verwendet? Welche Methode?
2. In EconConfig.java: Wie ist die Konstante definiert? Gibt es
   Abhängigkeiten (andere Konstanten, die darauf referenzieren)?
3. In Fiscal.java: Wie fließt der Freibetrag in die Berechnung ein?
4. Welcher Wert soll auf 2000 geändert werden — NUR die Konstante,
   oder auch Default-Werte in abhängigen Methoden?
```

---

## Phase 3: Du gibst den Research-Prompt an den Researcher

**Prompt an Researcher (hat Mod-Zugriff, NUR LESEN):**

```
Führe diesen Research-Auftrag aus. Antworte NUR mit validem JSON
nach Schema researcher-context/v1. Kein Freitext vor oder nach dem JSON.
Keine Code-Änderungen.

[RESEARCH-PROMPT VON ROLLE A HIER EINFÜGEN]
```

Der Researcher liest die angegebenen Dateien und antwortet mit JSON.
Speichere die Antwort als `.promtset/out/RES-XXX.json`.

---

## Phase 4: Researcher-JSON in State persistieren

```bash
cd /home/vannon/Dokumente/Promter
python3 .promtset/tools/promptgen.py ingest .promtset/out/RES-XXX.json --task-id RES-XXX
```

Das schreibt den Research-Kontext als Context-Token (R01) und neue
Entscheidungen ins Decision-Journal (R05).

---

## Phase 5: Rolle B erzeugt Coder-Tasks

**Prompt an Rolle B (Task-Splitter):**

```
@Rolle-B

Original-Auftrag: [DEIN TASK VON PHASE 1, WÖRTLICH]

Researcher-Output: [PFAD ZUM JSON, z.B. .promtset/out/RES-001.json]

Zerlege in atomare Coder-Tasks. Der Coder soll Datei für Datei
arbeiten können, mit klarem Scope pro Task.

Regel: JEDER Task darf maximal 3 Dateien ändern und muss in
EINER Sitzung abschließbar sein.

Erzeuge für jeden Task einen fertigen Prompt, den ich 1:1 an
den Coder weitergeben kann.
```

Rolle B:
1. Scannt den State (inkl. neuem Research-JSON)
2. Prüft auf Konsistenz mit bestehenden Entscheidungen
3. Zerlegt in atomare Tasks (R03)
4. Erzeugt pro Task einen R11-konformen Drei-Teile-Prompt

---

## Phase 6: Coder-Tasks an den Coder geben

Rolle B antwortet mit mehreren Task-Prompts:

```
## TASK-PROMPT 1 von 3 — Ziel-Agent: coder

### TEIL 1: KONTEXT
[relevanter Kontext, Bezug auf Original-Auftrag]

### TEIL 2: CONSTRAINTS
- IN SCOPE: EconConfig.java: Zeile 541 — perHeadTaxExemptionThreshold
  von 500 auf 2000 ändern
- NICHT IN SCOPE: Taxes.java, Fiscal.java, Tests
- Output: Context-Token am Ende (R01)

### TEIL 3: INSTRUCTION
Ändere in EconConfig.java die Konstante perHeadTaxExemptionThreshold
von 500 auf 2000. Keine weiteren Änderungen.
```

**Prompt an Coder (hat Mod-Zugriff, DARF SCHREIBEN):**

```
[TASK-PROMPT VON ROLLE B HIER EINFÜGEN]

Implementiere GENAU das. Nichts darüber hinaus.
Nach Abschluss: Context-Token ausgeben.
```

---

## Phase 7: Nach Coder-Abschluss — State updaten

Nachdem der Coder fertig ist, persistiere seine Ergebnisse:

**Prompt an Promter-Agent (State-Update):**

```
Coder hat Task <TASK-ID> abgeschlossen.
Ergebnis: [KURZBESCHREIBUNG, z.B. "EconConfig.java:541 — 500→2000"]

Aktualisiere den State:
- Context-Token für diesen Task-Abschluss
- Task-Index: TASK-XXX → completed
- Falls nötig: Handoff für nächsten Task
```

Oder manuell mit promptgen:

```bash
cd /home/vannon/Dokumente/Promter
python3 .promtset/tools/promptgen.py handoff \
  --from coder --to rolle-B \
  --note "EconConfig.java:541 500→2000, BUILD SUCCESS"
```

---

## Zusammenfassung: Deine Prompts auf einen Blick

| Phase | An wen | Prompt-Template |
|---|---|---|
| **1. Task starten** | Rolle A | `Ich will: [TASK]. Stell mir die Fragen, die der Researcher klären muss.` |
| **3. Research** | Researcher | `Führe diesen Research-Auftrag aus. NUR JSON. Keine Änderungen. [PROMPT]` |
| **5. Tasks bauen** | Rolle B | `Original-Auftrag: [TASK]. Zerlege in atomare Coder-Tasks. Max 3 Dateien/Task.` |
| **6. Coden** | Coder | `[TASK-PROMPT]. Implementiere GENAU das. Context-Token am Ende.` |
| **7. State updaten** | PromptGen | `Coder hat Task X abgeschlossen: [ERGEBNIS]. Aktualisiere State.` |

---

## Quick-Reference: promptgen-Befehle

```bash
# State inspizieren (vor jedem Task)
python3 .promtset/tools/promptgen.py resume -n 5

# Research-JSON einlesen
python3 .promtset/tools/promptgen.py ingest .promtset/out/RES-XXX.json

# Coder-Task-Prompt bauen
python3 .promtset/tools/promptgen.py build RES-XXX

# Handoff zwischen Agenten
python3 .promtset/tools/promptgen.py handoff --from <A> --to <B> --note "<was>"

# Task-Index anzeigen
python3 .promtset/tools/promptgen.py context list-tasks
```

---

## Lessons Learned: Edit-Präzision (2026-07-28)

> Hintergrund: TASK-005 (EngineSeams Rooms-Migration) hat gezeigt, dass Coder
> wiederholt str_replace aus dem Gedächtnis/Read-Cache statt per frischem grep
> angewandt haben. Resultat: verschmolzene Zeilen, fehlende Klammern, mehrfach
> fehlgeschlagene Imports.

### Regel 1: Frischer Grep vor jedem str_replace

**Vor jedem `str_replace`-Aufruf** die exakte Zielzeile(n) per `grep -n` frisch
aus dem Dateisystem ermitteln. NIEMALS aus vorherigem Read-Cache oder Gedächtnis
rekonstruieren — der Read-Cache kann veraltet sein (andere Agenten, andere Edits
im selben Batch).

```bash
# VOR dem Edit:
grep -n 'exakter String' src/vannon/syx/economy/datei.java
# ERST dann str_replace mit dem exakten Ergebnis
```

### Regel 2: sed/Python bei 3+ identischen Edits

Ab **3 strukturell identischen, aber whitespace-unterschiedlichen Ersetzungen**
(=z.B. EngineSeams.→EngineMirror.api().rooms(). mit variierenden Einrückungen):
sed- oder Python-Skript über Basher verwenden statt einzelner str_replace-Aufrufe.

```bash
# Beispiel: EngineSeams-Calls in FirmLedger.java migrieren
sed -i 's/EngineSeams\.settRoomsHome()/EngineMirror.api().rooms().settRoomsHome()/g' \
  src/vannon/syx/economy/core/FirmLedger.java
```

### Regel 3: Syntax-Check nach jedem Edit-Batch

Nach **jedem einzelnen Edit-Batch** sofort einen Syntax-Check durchführen —
nicht erst am Ende der gesamten Task-Kette. Das Projekt nutzt Maven, also
immer `mvn compile` verwenden (kein javac direkt):

```bash
cd SyxEconomyMod_Workspace && mvn compile -q 2>&1 | head -20
```

Fehler so früh wie möglich erkennen und sofort beheben — nicht
akkumulieren.

---

## Coder-Regeln (was du dem Coder mitgibst)

Jeder Coder-Task-Prompt MUSS enthalten:

1. ✅ **Scope (R09):** WAS genau wird geändert (Datei, Zeile, vorher/nachher)
2. ✅ **Nicht-Scope:** WAS wird NICHT geändert (andere Dateien, Tests, Docs)
3. ✅ **Akzeptanzkriterium:** Woran erkennt der Coder, dass er fertig ist?
4. ✅ **Constraints:** Welche Regeln/Entscheidungen aus dem State sind relevant?
5. ✅ **Context-Token-Pflicht:** Der Coder MUSS am Ende einen Context-Token
   ausgeben (sonst ist der Task für den State unsichtbar)
6. ✅ **Edit-Präzision:** Vor jedem str_replace frisch grep'n, bei 3+
   identischen Edits sed/Python nutzen, nach jedem Batch kompilieren
7. ✅ **Syntax-Verifizierung:** Kein merged Statement, keine fehlende Klammer —
   verifiziert per Grep-Diff + Compile-Check vor Abschluss

---

## Anti-Patterns (was NICHT tun)

| ❌ Falsch | ✅ Richtig |
|---|---|
| "Bau die Kopfsteuer um" | "EconConfig.java:541 — 500→2000. NUR diese Zeile." |
| Coder sucht selbst, WAS zu tun ist | Rolle B hat ALLES vorrecherchiert |
| Coder macht 5 Dinge in einem Task | Max 3 Dateien, 1 Thema pro Task |
| Kein Context-Token nach Abschluss | Coder MUSS CTX ausgeben |
| User rät, wo der Code liegt | Researcher hat die exakten Dateien/Zeilen gefunden |
| str_replace aus Gedächtnis/Cache | Immer frisch per `grep -n` ermitteln |
| 3+ identische Edits einzeln | sed/Python-Skript über Basher |
| Erst am Ende kompilieren | Nach jedem Edit-Batch Syntax-Check |

---

## Projekt-Setup (einmalig)

Falls der Coder das erste Mal arbeitet, gib ihm diesen Kontext mit:

```
Projekt: SyxEconomyMod (Songs of Syx V71.44)
Version: 2.0.0
Build: mvn verify install -DskipTests
Tests: mvn test (402 Tests)
Package-Struktur: src/vannon/syx/economy/{core,adapter,ui}/
Promter-State: /home/vannon/Dokumente/Promter/.promtset/state/

Agent-Regeln: README.md, ARCHITECTURE.md, agents.md, CODER-WORKFLOW.md

## SELF-OPTIMIZATION-LOOP

Nach JEDEM Coder-Output (JSON) prüft der Promter:
1. Hat das JSON alle erwarteten Felder?
2. Sind `collected_context`-Einträge vollständig (Zeilen-Referenzen)?
3. Hat `atomic_task_prompt` Acceptance Criteria?
4. Sind `decisions` konsistent mit dem State?

Falls Lücken → Prompt optimieren für nächsten Durchlauf.
```
