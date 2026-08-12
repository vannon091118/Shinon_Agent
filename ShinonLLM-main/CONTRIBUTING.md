# Contributing

Danke fuer deinen Beitrag zu ShinonLLM.

## Leitprinzipien

- Runtime-first bleibt unverhandelbar: zentrale Entscheidungen gehoeren in Code, nicht in Prompt-Improvisation.
- Aenderungen muessen reproduzierbar pruefbar sein.
- Kleine, klar abgegrenzte Pull Requests sind Standard.

## Setup und Pflichtchecks

1. Abhaengigkeiten installieren:
   - `npm ci`
   - `npm --prefix frontend ci`
2. Verifikation ausfuehren:
   - `npm run verify:backend`
   - `npm --prefix frontend run build`
3. Bei Verhaltensaenderungen `CHANGELOG.md` unter `[Unreleased]` aktualisieren.

## Pull Request Anforderungen

- Klarer Scope und Nutzerwirkung.
- Hinweise auf Contract-/Runtime-Auswirkung.
- Doku-Updates bei geaendertem Verhalten.
- Release-Einordnung (Patch/Minor/Major).

## Source-of-Truth Hinweis

`README.md` dient der Produktpraesentation.
Autoritative technische Regeln liegen in `LLM_ENTRY.md`, `docs/LLM_ENTRY_CONFORMITY.md` und `docs/HANDSHAKE_CURRENT_STATE.md`.

