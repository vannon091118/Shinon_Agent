---
skill: morning
state: idle
last_activation: 2026-08-11T23:00:47Z
activation_count: 2
tags: [catalog]
output_path: ".agents/skills/claude-tools/morning/SKILL.md"
---

# ⏸️  morning · IDLE

> **Token-saving artifact.** Dieser ~20-Zeilen-Snapshot ersetzt das vollständige
> SKILL.md (~200-400 Zeilen) bei Re-Activation. Re-Aktivierungen lesen NUR
> diesen Snapshot, sofern keine erweiterte Funktionalität benötigt wird.

## Aktueller Status
"[claude] \"Render the user's morning brief as a styled HTML artifact, or set it up as a recurring weekday task. Use only when the user explicitly asks to run, see, or set up their

## Pfad zum Output
.agents/skills/claude-tools/morning/SKILL.md

## Re-Aktivierung (schnell)
```bash
bash .agents/skills/live-context.sh morning   # holt diesen Snapshot
# Falls mehr Details nötig:  cat .agents/skills/morning/SKILL.md
```

