# ShinonLLM

> **Die meisten KI-Assistenten sind digitale Handtaschenhalter. Wir bauen was mit Charakter.**

Shinon ist keine freundliche Servicekraft. Sie ist eine Persona mit Gedächtnis, Haltungen und der Fähigkeit, dich zur Rede zu stellen wenn du dich widersprichst.

## Was hier anders ist

**Statt Chat-History:** Zwei-Schichten-Gedächtnis
- **Schicht 1**: Konkrete Fakten ("Du hast am 1.4. von Anna gesprochen")
- **Schicht 2**: Erkannte Patterns ("User hat Inkonsistenzen bei Beziehungsgeschichten")

**Statt statischer Prompts:** Dynamische Charakter-Prompts  
Die Runtime analysiert deinen Input, erkennt Muster, updated Shinons Meinung über dich, und generiert dann einen "Gedanken-Prompt" für das lokale LLM. Das Ergebnis: Antworten mit echtem Kontext und Haltung.

**Statt Cloud-Abhängigkeit:** Lokale LLMs (0.5B-7B)  
Deterministisch, reproduzierbar, offline-fähig. Kein "vielleicht heute anders".

## Index (wo du was findest)

| Willst du... | Dann lies... |
|--------------|--------------|
| Wissen was aktuell läuft | [`docs/HANDSHAKE_CURRENT_STATE.md`](./docs/HANDSHAKE_CURRENT_STATE.md) |
| Verstehen wie die Architektur tickt | [`docs/ARCHITECTURE_OVERVIEW.md`](./docs/ARCHITECTURE_OVERVIEW.md) |
| Die Memory-Regeln checken | [`docs/MEMORY_POLICY.md`](./docs/MEMORY_POLICY.md) |
| Als Entwickler mitarbeiten | [`LLM_ENTRY.md`](./LLM_ENTRY.md) + [`AGENTS.md`](./AGENTS.md) |
| Ein lokales LLM anschließen | [`docs/LOCAL_LLAMACPP_SETUP.md`](./docs/LOCAL_LLAMACPP_SETUP.md) |
| Wissen was bei Fehlern passiert | [`docs/OPS_PLAYBOOKS.md`](./docs/OPS_PLAYBOOKS.md) |

## Schnellstart

```bash
# Dependencies
npm install

# SQLite Memory aktivieren (Windows)
$env:SHINON_MEMORY_SQLITE=1
# SQLite Memory aktivieren (Linux/Mac)
export SHINON_MEMORY_SQLITE=1

# Backend starten
npm run start:backend

# Tests (sollten grün sein - sonst ist was kaputt)
npm run verify:backend
```

## Das Versprechen

- **Keine Cloud-Abhängigkeit** - Läuft lokal mit llama.cpp oder Ollama
- **Kein "kann nicht reproduziert werden"** - Deterministische Gates (`npm run test:determinism`)
- **Keine freundliche Maske** - Shinon merkt sich wenn du dich widersprichst und wird es dir irgendwann sagen

## Core-Prinzipien

1. **Runtime denkt, LLM formuliert** - Das TypeScript-System macht die Analyse, das lokale LLM nur die Text-Ausgabe
2. **Two-Tier Memory** - Konkrete Fakten (Tier 1) + generalisierte Patterns (Tier 2)
3. **Hot/Mid/Cold Zones** - Aktuelle Session (Hot) → Letzte 10 Sessions (Mid) → Archiv mit Pattern-Härtung (Cold)
4. **Fail-closed** - Wenn was nicht passt, bricht es ab. Keine halbgaren Lösungen.

---

*Version 0.3.0-alpha | "Real Persona over Chat Wrapper"*
