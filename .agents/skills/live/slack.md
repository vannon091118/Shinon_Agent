---
skill: slack
state: idle
last_activation: 2026-08-11T23:01:13Z
activation_count: 2
tags: [catalog]
output_path: ".agents/skills/communication/slack/slack/SKILL.md"
---

# ⏸️  slack · IDLE

> **Token-saving artifact.** Dieser ~20-Zeilen-Snapshot ersetzt das vollständige
> SKILL.md (~200-400 Zeilen) bei Re-Activation. Re-Aktivierungen lesen NUR
> diesen Snapshot, sofern keine erweiterte Funktionalität benötigt wird.

## Aktueller Status
 "[codex:slack] Read Slack context, route to the right Slack workflow, and prepare or perform Slack writes that match the user's intent."

## Pfad zum Output
.agents/skills/communication/slack/slack/SKILL.md

## Re-Aktivierung (schnell)
```bash
bash .agents/skills/live-context.sh slack   # holt diesen Snapshot
# Falls mehr Details nötig:  cat .agents/skills/slack/SKILL.md
```

