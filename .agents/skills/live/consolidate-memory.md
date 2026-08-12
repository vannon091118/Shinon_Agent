---
skill: consolidate-memory
state: idle
last_activation: 2026-08-11T23:00:46Z
activation_count: 2
tags: [catalog]
output_path: ".agents/skills/claude-tools/consolidate-memory/SKILL.md"
---

# ⏸️  consolidate-memory · IDLE

> **Token-saving artifact.** Dieser ~20-Zeilen-Snapshot ersetzt das vollständige
> SKILL.md (~200-400 Zeilen) bei Re-Activation. Re-Aktivierungen lesen NUR
> diesen Snapshot, sofern keine erweiterte Funktionalität benötigt wird.

## Aktueller Status
"[claude] \"Reflective pass over your memory files — merge duplicates, fix stale facts, prune the index.\""

## Pfad zum Output
.agents/skills/claude-tools/consolidate-memory/SKILL.md

## Re-Aktivierung (schnell)
```bash
bash .agents/skills/live-context.sh consolidate-memory   # holt diesen Snapshot
# Falls mehr Details nötig:  cat .agents/skills/consolidate-memory/SKILL.md
```

