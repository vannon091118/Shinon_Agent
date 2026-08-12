---
skill: autorun
state: idle
last_activation: 2026-08-11T23:00:34Z
activation_count: 2
tags: [catalog]
output_path: ".agents/skills/agents/autorun/SKILL.md"
---

# ⏸️  autorun · IDLE

> **Token-saving artifact.** Dieser ~20-Zeilen-Snapshot ersetzt das vollständige
> SKILL.md (~200-400 Zeilen) bei Re-Activation. Re-Aktivierungen lesen NUR
> diesen Snapshot, sofern keine erweiterte Funktionalität benötigt wird.

## Aktueller Status
"Use when the agent needs to decide what an Auto tab does next — driving work forward until genuinely finished and merged, then continuing as far as the selected scope allows."

## Pfad zum Output
.agents/skills/agents/autorun/SKILL.md

## Re-Aktivierung (schnell)
```bash
bash .agents/skills/live-context.sh autorun   # holt diesen Snapshot
# Falls mehr Details nötig:  cat .agents/skills/autorun/SKILL.md
```

