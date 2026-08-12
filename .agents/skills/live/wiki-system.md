---
skill: wiki-system
state: idle
last_activation: 2026-08-11T23:01:44Z
activation_count: 2
tags: [catalog]
output_path: ".agents/skills/research/wiki-system/SKILL.md"
---

# ⏸️  wiki-system · IDLE

> **Token-saving artifact.** Dieser ~20-Zeilen-Snapshot ersetzt das vollständige
> SKILL.md (~200-400 Zeilen) bei Re-Activation. Re-Aktivierungen lesen NUR
> diesen Snapshot, sofern keine erweiterte Funktionalität benötigt wird.

## Aktueller Status
"Baue und pflege ein persistentes, verlinktes Markdown-Wiki (Second Brain, Research Notebook, persönliche Wissensdatenbank). Ingest neue Quellen, beantworte Fragen aus dem Wiki, fü

## Pfad zum Output
.agents/skills/research/wiki-system/SKILL.md

## Re-Aktivierung (schnell)
```bash
bash .agents/skills/live-context.sh wiki-system   # holt diesen Snapshot
# Falls mehr Details nötig:  cat .agents/skills/wiki-system/SKILL.md
```

