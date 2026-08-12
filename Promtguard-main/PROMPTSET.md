# 🎯 Promtset — Sprachagnostisches Prompt-Regelsystem

> **Promter ist eine eigenständige Repo.** Funktioniert mit Python, JavaScript, Rust,
> Java, Node.js, Shell-Skripten — egal welche Sprache, egal welches Framework.
>
> Version: 2.0.0 | Letzte Änderung: 2026-07-28

---

## Kurzfassung (für schnelle Agenten)

Dieses Projekt verwendet ein **Promtset** — ein Regelwerk, das sicherstellt, dass:
- JEDER Agent den VOLLSTÄNDIGEN Kontext aller Vorgänger hat
- KEIN Agent eine Entscheidung rückgängig macht, die bereits getroffen wurde
- ALLE Aufgaben atomar, klar abgegrenzt und widerspruchsfrei sind
- FEHLER transparent gemeldet und nie verschwiegen werden
- DAS SYSTEM mit JEDER Sprache und JEDEM Framework funktioniert

**Ohne dieses Promtset zu laden = Keine Arbeit.**

---

## Die 12 Regeln

| Regel | Name | Kernaussage |
|-------|------|-------------|
| **R01** | [Persistenz](.promtset/01-persistence.md) | Kontext geht nie verloren — jeder Agent lädt das Promtset + Context-Token |
| **R02** | [Kontext-Vererbung](.promtset/02-context-inherit.md) | Sub-Agenten erhalten den VOLLSTÄNDIGEN Kontext-Pfad |
| **R03** | [Aufgaben-Atomizität](.promtset/03-atomicity.md) | Jede Aufgabe = genau EINE Sache |
| **R04** | [Handoff-Protokoll](.promtset/04-handoff.md) | Übergaben zwischen Agenten folgen dem definierten Schema |
| **R05** | [Entscheidungs-Journal](.promtset/05-decision-journal.md) | Jede Entscheidung wird mit WAS + WARUM + Alternativen dokumentiert |
| **R06** | [Validierungs-Gate](.promtset/06-validation-gate.md) | Konsistenz-Check vor Task-Build + Abschluss-Check vor "completed" |
| **R07** | [Selbstverbesserung v2.0](.promtset/07-self-improve.md) | Evidence-Check, code_refs+commit-sha Pflicht, Quiet-Mode |
| **R08** | [Output-Vertrag](.promtset/08-output-contract.md) | Agent-zu-Agent-Kommunikation folgt definierten Schemata |
| **R09** | [Scope-Bounding](.promtset/09-scope.md) | Jede Aufgabe definiert: WAS drin ist, WAS draußen ist |
| **R10** | [Fehler-Transparenz](.promtset/10-failure.md) | Kein stilles Sterben — jeder Fehler wird gemeldet |
| **R11** | [Prompt-Template](.promtset/11-prompt-template.md) | Deklarativ > Imperativ, Drei-Teile-Struktur (KONTEXT/CONSTRAINTS/INSTRUCTION) |
| **R12** | [Task-Reihenfolge](.promtset/12-task-sequence.md) | Tasks werden sequenziert, parallelisiert und gelockt |
| **R13** | [Claims](.promtset/13-claims.md) | Jede Research-Aussage = Claim bis verifiziert. Eigenes Schema, eigener Log, latest-wins per ID |

---

## Agenten-Initialisierung (Pflicht)

→ **[`agents.md`](agents.md)** ← Zentrale Agenten-Regelung mit INIT-Protokoll, Anti-Duplicate-Regeln und `/promtset-state-update` Skill.

JEDER Agent MUSS zu Beginn seines Tasks die 5 Schritte aus `agents.md` befolgen:

```markdown
## INIT: State-First Protocol (siehe agents.md)

1. ✅ PROMPTSET.md geladen (Version 2.0.0)
2. ✅ State laden: task-index.json, context-log.jsonl, decision-journal.jsonl, handoffs.jsonl
3. ✅ Anti-Duplicate Check: Prüfe task-index.json ob Task-ID bereits "completed"
4. ✅ Projekt identifiziert: "In welchem Projekt arbeiten wir?"
5. ✅ Erst dann: Arbeit beginnen
```

**Ohne State-Verifizierung = Keine Arbeit.**

---

## Struktur

```
.promtset/                  ← Das gesamte Regelsystem (12 Regeln + Templates)
  ├── 00-meta.md
  ├── 01-persistence.md     ...  12-task-sequence.md
  ├── agent-templates/      ← Agenten-spezifische Prompt-Templates (R13)
  │   ├── promptgen-agent-rolle-A-research.md
  │   ├── promptgen-agent-rolle-B-tasksplit.md
  │   ├── code-researcher-prompt.md
  │   ├── context-researcher-prompt.md
  │   └── promter-rolle-instruktion.md
  ├── examples/
  │   ├── handoff-example.md
  │   ├── decision-example.md
  │   └── contract-example.md
  ├── schemas/              ← Output-Contract-Schemata (R08)
  │   ├── researcher-context-v1.json  ← legacy (v1)
  │   ├── researcher-context-v2.json  ← aktuell (bevorzugt)
  │   └── live-test-findings-v1.json
  ├── state/                ← Persistenter Zustand (append-only JSONL)
  │   ├── context-log.jsonl      ← Context-Token (R01)
  │   ├── decision-journal.jsonl ← Entscheidungen (R05)
  │   ├── handoffs.jsonl         ← Handoffs (R04)
  │   └── task-index.json        ← Task-ID → Status/Datei
  ├── out/                  ← Generierte Research-/Task-Prompts
  ├── tools/                ← Automatisierungswerkzeuge
  │   ├── promptgen.py           ← Promtset-Automatisierung (Python 3)
  │   └── README.md              ← Nutzungsdokumentation
  └── issues/               ← Promtset-Verbesserungsvorschläge
  
PROMPTSET.md                ← Diese Datei (Einstiegspunkt)
promptgen                   ← Convenience-Wrapper (./promptgen ...)
```

---

## Context-Token (deterministische IDs)

# Globale ID-Systeme

| ID | Format | Wo erzeugt | Zweck |
|---|---|---|---|
| `RES-NNN` | `RES-001` | `research`-Subcommand | Forschungs-Auftrag (vom Promter vergeben) |
| `TASK-NNN` | `TASK-001` | `build`-Subcommand | Coder-Auftrag (vom Promter vergeben) |
| `CTX-{PREFIX}-{PHASE}-{SEQ}` | `CTX-SYX-RES-001` | `ingest` + `task-done` | Context-Token (deterministisch) |
| `CLAIM-{PREFIX}-{SEQ}` | `CLAIM-SYX-001` | `ingest` aus `decisions[]` + `claim`-Subcommands | Verifikations-Atom (jede Research-Aussage) |

```json
{"id":"CTX-TPP-TASK-001","timestamp":"<ISO-8601>","source_task_id":"TASK-001","agent":"coder-1","task":"...","status":"completed","summary":"...","promtset_version":"2.0.0","code_refs":[{"file":"src/app.py","line":42,"method":"create_user"}],"diff_stats":"+15 -40"}
```

**Pflichtfelder:** id, timestamp, source_task_id, agent, task, status, summary, promtset_version
**🔴 HIGH:** code_refs ({file, line, method}), diff_stats ("+N -M")
**🟡 MEDIUM:** commit_sha, remaining_tasks

---

## Für User: So nutzt du Promter mit JEDEM Projekt

```bash
# 1. Projekt registrieren (einmalig)
./promptgen project init --name "MeinProjekt" --language python --build pip --test pytest

# 2. Research-Prompt generieren
./promptgen research "Ich will eine REST API bauen"
# → Prompt an Researcher geben → JSON zurückbekommen

# 3. JSON ingestieren → Task bauen
./promptgen ingest .promtset/out/RES-001.json
./promptgen build RES-001

# 4. Task abschließen
./promptgen task-done TASK-001 --agent coder-1 --status completed --summary "..."
```

**Sprachenunabhängig.** Funktioniert mit Python, JS, Rust, Java, Go, Shell — egal.

---

---

## COMMAND-WORKFLOW (NEU — Vereinfacht)

Für das einfachste mögliche Workflow gibt es jetzt [`COMMAND-WORKFLOW.md`](.promtset/COMMAND-WORKFLOW.md):

```
Agent (hat Code-Zugriff)          Promter (KEIN Code-Zugriff)
  → Führt Commands aus               → Liest JSON + State
  → Liefert JSON mit file:line REFs  → Entscheidet: RES vs TASK
  → NICHTS mit Promter zu tun        → Generiert nächsten Prompt
```

**JSON-Schema:** `.promtset/schemas/command-result-v1.json`
**Kernregel:** Jeder Fund MUSS `file:line:method` als REF-ID enthalten.

---

## Coder-Dreieck: Der komplette Workflow (7 Phasen)

Für das Zusammenspiel **User → Promter-Agent → Coder** gibt es einen
dokumentierten 7-Phasen-Workflow mit konkreten Prompt-Rezepten:

→ **[`CODER-WORKFLOW.md`](CODER-WORKFLOW.md)** ←

**Rollen im Dreieck:**
| Rolle | Zugriff | Aufgabe |
|---|---|---|
| **Rolle A** (Research-Generator) | NUR `.promtset/state/` | Scannt State, analysiert Lücken, erzeugt Research-Prompt |
| **Researcher** | Mod-Ordner (read-only) | Liest Code, beantwortet Fragen aus Research-Prompt → JSON |
| **Rolle B** (Task-Splitter) | NUR `.promtset/state/` | Prüft Konsistenz, zerlegt in atomare Coder-Tasks (R03) |
| **Coder** | Mod-Ordner (read+write) | Implementiert GENAU einen Task, gibt Context-Token aus |

**Quickstart (deine Prompts auf einen Blick):**

```
Phase 1 → Rolle A:    "Ich will: [TASK]. Stell mir die Fragen, die der
                       Researcher klären muss."

Phase 3 → Researcher:  "Führe diesen Research-Auftrag aus. NUR JSON.
                       Keine Änderungen. [PROMPT VON ROLLE A]"

Phase 5 → Rolle B:    "Original-Auftrag: [TASK]. Zerlege in atomare
                       Coder-Tasks. Max 3 Dateien/Task."

Phase 6 → Coder:      "[TASK-PROMPT VON ROLLE B]. Implementiere GENAU
                       das. Context-Token am Ende."
```

---

## Automatisierung: `promptgen`

Das Projekt enthält **promptgen.py** — eine Pipeline, die das gesamte Regelsystem
als CLI-Werkzeug abbildet. Keine externen Dependencies, nur Python 3.

**Pipeline (ein kompletter Durchlauf):**

```bash
# 1) Rohe Aussage -> read-only Research-Prompt erzeugen
./promptgen research "baue Feature X ein"
#    -> .promtset/out/RES-001-research-prompt.md

# 2) Diesen Prompt einem Research-Agenten geben (nur Lesen!)
#    Agent antwortet mit researcher-context/v1 JSON

# 3) Research-JSON einlesen, validieren, persistieren (R01/R05)
./promptgen ingest .promtset/out/RES-001.json --task-id RES-001

# 4) Finalen atomaren Task-Prompt bauen (R03/R08/R09/R11)
./promptgen build RES-001
#    -> .promtset/out/TASK-001-task-prompt.md -> an implementer-Agent
```

**Nach Agenten-/Provider-Wechsel:**
```bash
./promptgen resume -n 5
# Gibt fertigen INIT-Block (R00/R01) mit den letzten N Einträgen aus
```

**Manueller Handoff (R04):**
```bash
./promptgen handoff --from implementer-1 --to tester-1 --note "validate() fertig"
```

**Inspektion:**
```bash
./promptgen context show -n 10
./promptgen context list-tasks
```

Siehe [`promptgen.py`](.promtset/tools/promptgen.py) (Docstring) oder `./promptgen --help` für die vollständige Nutzungsdokumentation.

---

**Promtset geladen. Version 2.0.0. Bereit für Aufgaben.**
