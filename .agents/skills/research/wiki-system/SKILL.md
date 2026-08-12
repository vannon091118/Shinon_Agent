---
name: wiki-system
description: "Baue und pflege ein persistentes, verlinktes Markdown-Wiki (Second Brain, Research Notebook, persönliche Wissensdatenbank). Ingest neue Quellen, beantworte Fragen aus dem Wiki, führe Health-Checks durch. \"Kompatibel mit Obsidian Vaults. Trigger: \"add to wiki\", \"what does my wiki say\",\" \"health-check wiki\", \"find orphan pages\"."
category: research
stack: LOGISCH + MEMORY
risk: low
side_effects: network_calls
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
---

# Wiki System

Behandle den Workspace als persistente, wachsende Wissensdatenbank.

## Architektur

```
raw/          ← unveränderliche Quelldateien (Read-Only)
wiki/         ← deine Output-Ebene: Summaries, Entities, Concepts, Syntheses
index.md      ← Navigation
log.md        ← Chronik
```

## Page-Typen (in `wiki/`)

Jede Seite ist Markdown mit YAML-Frontmatter:

```yaml
---
title: Seiten-Titel
type: source | entity | concept | synthesis | comparison | overview
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [raw/path.md]
tags: [tag1, tag2]
---
```

- **source** — eine aufgenommene Quelle mit Zitat, Takeaways, Zitaten, Wikilinks
- **entity** — Person, Organisation, Ort, Produkt, Event
- **concept** — Idee, Mechanismus, Theorie, Methode
- **synthesis** — Multi-Source-Analyse mit Quellenangaben
- **comparison** — Side-by-Side-Vergleich
- **overview** — Topic-Übersichtsseite

## Operations

### Ingest (Neue Quelle einpflegen)
1. Quelle vollständig lesen
2. Key Takeaways (3-8 Bullets) mit User besprechen
3. Source-Page in `wiki/sources/<slug>.md` erstellen
4. JEDE referenzierte Entity/Concept-Page anlegen oder updaten
5. `index.md` updaten
6. `log.md` mit Standard-Präfix erweitern

### Query (Wiki befragen)
1. Relevante Notes via Graph/Navigation finden
2. Antwort mit `[[Wikilinks]]`-Zitaten belegen
3. Optional Antwort zurück ins Wiki schreiben

### Lint (Health-Check)
- Orphan-Notes finden
- Dangling Links identifizieren
- Fehlende Pages auflisten
- Graph-Lücken und Widersprüche markieren

### Bootstrap (Neues Wiki initialisieren)
- `raw/` und `wiki/` Ordner anlegen
- `index.md` mit Sektionen erstellen
- `log.md` initialisieren

## Wichtige Regeln

- **Alles verlinken**: `[[Page Name]]` Wikilinks (Obsidian-kompatibel)
- Widersprüche mit `> [!warning] Contradiction` Callout markieren
- Bestehende Ordnerstruktur des Users respektieren
