# R00 — Meta: Fundament

**Wer das liest, ist im Promtset.**  
Dieses Regelwerk definiert, wie Prompt-orchestrierte Agenten-Arbeit funktioniert.

## Was ist ein Promtset?

Ein Promtset ist ein **deterministischer, auditierbarer Handoff-Layer** zwischen KI-Agenten.  
Es löst drei Probleme:

1. **Kontext-Verlust** — Agent A arbeitet, Agent B startet ohne Wissen von A → Promtset persistiert State
2. **Widersprüchliche Entscheidungen** — Agent B macht rückgängig, was Agent A entschied → Decision-Journal
3. **Undurchsichtige Ergebnisse** — "es funktioniert" ohne Beleg → Contract-Schemas mit file:line-Pflicht

## Für wen?

- **Promter** — generiert Prompts, managed State, hat KEINEN Code-Zugriff
- **Researcher** — liest Code, beantwortet Fragen, ändert NICHTS
- **Coder** — implementiert genau einen Task, gibt Context-Token aus
- **User** — formuliert Wünsche, kriegt Ergebnisse

## Kernprinzipien

1. **Append-only State** — Nichts wird gelöscht, nichts überschrieben (R01)
2. **Keine Annahmen** — Jede Behauptung wird gegen Code verifiziert (RULE 1 agents.md)
3. **Sprachagnostisch** — Funktioniert mit Python, Java, Rust, JS, Go, egal
4. **Narbengewebe** — Jede Regel ist die Antwort auf einen konkreten Vorfall
