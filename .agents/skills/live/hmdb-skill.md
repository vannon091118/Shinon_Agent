---
skill: hmdb-skill
state: idle
last_activation: 2026-08-11T23:00:42Z
activation_count: 2
tags: [catalog]
output_path: ".agents/skills/bioscience/life-science-research/hmdb-skill/SKILL.md"
---

# ⏸️  hmdb-skill · IDLE

> **Token-saving artifact.** Dieser ~20-Zeilen-Snapshot ersetzt das vollständige
> SKILL.md (~200-400 Zeilen) bei Re-Activation. Re-Aktivierungen lesen NUR
> diesen Snapshot, sofern keine erweiterte Funktionalität benötigt wird.

## Aktueller Status
 "[codex:life-science-research] Submit compact HMDB search requests for metabolites, proteins, diseases, and pathways. Use when a user wants concise HMDB summaries"

## Pfad zum Output
.agents/skills/bioscience/life-science-research/hmdb-skill/SKILL.md

## Re-Aktivierung (schnell)
```bash
bash .agents/skills/live-context.sh hmdb-skill   # holt diesen Snapshot
# Falls mehr Details nötig:  cat .agents/skills/hmdb-skill/SKILL.md
```

