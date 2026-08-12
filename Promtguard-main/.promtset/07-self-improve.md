# R07 — Selbstverbesserung (v2.0)

**Fehler → Promtset-Lücke → Verbesserung. Das System lernt aus seinen Fehlern.**

## Der Zyklus

```
1. Fehler passiert (Agent halluziniert, Diskrepanz übersehen, Task falsch gebaut)
2. Promter erkennt: "Das ist kein Einzelfall — das ist eine Systemlücke"
3. Verbesserung in agents.md oder Regel-Datei
4. Nächster Agent profitiert von der Verbesserung
```

## Automatische Erkennung

`promptgen.py self-improve` analysiert:
- **Erfolgreiche Patterns:** Tasks mit code_refs, vollständigen Context-Token, bestandenen Checks
- **Fehlermuster:** Tasks ohne code_refs, abgebrochene Tasks, Diskrepanzen die ignoriert wurden

## SELF-IMPROVE v2.0: Evidence-Check vor Abschluss

Bevor ein Research als abgeschlossen gemeldet wird:
- [ ] Enthält das JSON mindestens 5 evidence-Einträge mit `datei.java:zeile:code`?
- [ ] Sind alle Decisions mit `confidence` markiert?
- [ ] Gibt es bei Widerlegungen neue Decisions?

Fehlt Evidence → zurück an Researcher mit "evidence unvollständig".

## SELF-IMPROVE v2.0: code_refs + commit-sha PFLICHT

Jeder Research-Output MUSS `evidence` enthalten: mindestens 5 Einträge im Format `datei.java:42:relevanter code`.

Bei Task-Abschluss IMMER `--commit-sha` in `task-done` angeben:
```bash
python3 promptgen.py task-done TASK-NNN --agent implementer-1 \
  --status completed \
  --summary "Kurze Beschreibung" \
  --code-refs '[{"file":"src/...","line":42,"method":"foo"}]' \
  --diff-stats "+15 -40" \
  --commit-sha "$(git rev-parse HEAD)"
```

## SELF-IMPROVE v2.0: Alte Dokumente bereinigen

Nach Abschluss eines Research-Zyklus:
- Alte `RES-*-research-prompt.md` löschen (bereits ingested als JSON)
- Veraltete `AUSWERTUNG-*.json` löschen (durch neue ersetzt)

## SELF-IMPROVE v2.0: Quiet-Mode

Bei großen Research-Prompts `--quiet` Flag verwenden:
```bash
python3 promptgen.py research "<prompt>" --agent code-researcher --quiet
```
