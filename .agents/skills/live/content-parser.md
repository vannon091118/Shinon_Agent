---
skill: content-parser
state: idle
last_activation: 2026-08-11T23:01:14Z
activation_count: 2
tags: [catalog]
output_path: ".agents/skills/content-parser/SKILL.md"
---

# ⏸️  content-parser · IDLE

> **Token-saving artifact.** Dieser ~20-Zeilen-Snapshot ersetzt das vollständige
> SKILL.md (~200-400 Zeilen) bei Re-Activation. Re-Aktivierungen lesen NUR
> diesen Snapshot, sofern keine erweiterte Funktionalität benötigt wird.

## Aktueller Status
"\"Extract and parse content from URLs. Triggers on: user provides a URL to extract\" content from, another skill needs to parse source material, \"parse this URL\", \"extract cont

## Pfad zum Output
.agents/skills/content-parser/SKILL.md

## Re-Aktivierung (schnell)
```bash
bash .agents/skills/live-context.sh content-parser   # holt diesen Snapshot
# Falls mehr Details nötig:  cat .agents/skills/content-parser/SKILL.md
```

