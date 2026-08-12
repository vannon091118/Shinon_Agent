# DECISIONS.md – Vorlage und Beispiel

## So startet die Datei

Erste Zeile der `DECISIONS.md` im Projektordner:

```markdown
# Entscheidungen

Jede getroffene Entscheidung wird hier eingetragen – Datum, Entscheidung, Grund, wer sie getroffen hat. Aufsteigend: neue Einträge nach unten.
```

## Eintrag-Vorlage

```markdown
## [YYYY-MM-DD] – [Kurzer Titel]
- Entscheidung: [was genau entschieden wurde]
- Grund: [warum diese Entscheidung]
- Getroffen von: Architekt (Guide nur bei ausdrücklicher Übergabe)
- Alternativen: [was hätte es noch gegeben]
- Konsequenz: [was bedeutet das für das Projekt]
```

## Ausgefülltes Beispiel

```markdown
# Entscheidungen

Jede getroffene Entscheidung wird hier eingetragen – Datum, Entscheidung, Grund, wer sie getroffen hat.

## 2026-08-01 – Sprache der To-do-App: Java
- Entscheidung: Die To-do-App wird in Java gebaut.
- Grund: Java läuft überall und wir haben den Projektaufbau schon.
- Getroffen von: Architekt
- Alternativen: Python (einfacher, aber anderes Setup), JavaScript (Web statt Konsole)
- Konsequenz: Alle weiteren Schritte setzen Java voraus.
```

## Wichtige Hinweise

- **Nur im Projektkontext:** Die Datei wird nur angelegt und befüllt, wenn wir in einem Projekt mit Dateien arbeiten. Bei einer reinen Wissensfrage ohne Projekt bleibt die Datei weg.
- **Jede Entscheidung dokumentieren** – auch kleine. Was nicht dokumentiert ist, wird später wieder neu diskutiert (Kreis!).
- **Keine Annahmen eintragen.** Steht etwas in der Datei, muss es wirklich abgesprochen worden sein.
- **Nicht löschen.** Ein Eintrag, der sich später als falsch erweist, wird mit einem neuen Eintrag korrigiert – nicht überschrieben. So sieht man die Geschichte des Projekts.
