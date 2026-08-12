# content-parser — 1 Skill

> URL-Inhalte extrahieren und als strukturierte Quelle für nachgelagerte Skills bereitstellen.

| Skill | Kurzbeschreibung | 6-Stack | Autonomie |
|---|---|---|---|
| `content-parser` | Extrahiert und normalisiert Inhalte aus HTTP(S)-URLs; liefert Inhalt, Metadaten und Referenzen. | LOGISCH + GOVERNANCE | gated |

## Nutzung im Bündel

`content-parser` ist ein **Vorverarbeitungsschritt** für Research-, Dokument- und Content-Workflows. Er darf nicht als Beleg- oder Wahrheitsprüfung behandelt werden: extrahierter Text muss anschließend über eine kanonische Quelle, Quellen- und Inhaltsprüfung verifiziert werden.

## Gates

- HTTP(S)-URL validieren.
- API-Key nie ausgeben oder loggen.
- Externe Übertragung sensibler Inhalte ausdrücklich berücksichtigen.
- Extraktionsergebnis als `unverified` markieren, bis die Originalquelle geprüft wurde.
- Polling, Rate-Limits und Kosten begrenzen.
