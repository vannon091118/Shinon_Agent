---
skill: render-debug
state: idle
last_activation: 2026-08-11T23:00:50Z
activation_count: 2
tags: [catalog]
output_path: ".agents/skills/cloud-platforms/render/render-debug/SKILL.md"
---

# ⏸️  render-debug · IDLE

> **Token-saving artifact.** Dieser ~20-Zeilen-Snapshot ersetzt das vollständige
> SKILL.md (~200-400 Zeilen) bei Re-Activation. Re-Aktivierungen lesen NUR
> diesen Snapshot, sofern keine erweiterte Funktionalität benötigt wird.

## Aktueller Status
 "Debug failed Render deployments by analyzing logs, metrics, and database state. Identifies errors (missing env vars, port binding, OOM, etc.) and suggests fixes. Use when deploym

## Pfad zum Output
.agents/skills/cloud-platforms/render/render-debug/SKILL.md

## Re-Aktivierung (schnell)
```bash
bash .agents/skills/live-context.sh render-debug   # holt diesen Snapshot
# Falls mehr Details nötig:  cat .agents/skills/render-debug/SKILL.md
```

