---
skill: delivery-tracking
state: idle
last_activation: 2026-08-11T23:00:34Z
activation_count: 2
tags: [catalog]
output_path: ".agents/skills/agents/delivery-tracking/SKILL.md"
---

# ⏸️  delivery-tracking · IDLE

> **Token-saving artifact.** Dieser ~20-Zeilen-Snapshot ersetzt das vollständige
> SKILL.md (~200-400 Zeilen) bei Re-Activation. Re-Aktivierungen lesen NUR
> diesen Snapshot, sofern keine erweiterte Funktionalität benötigt wird.

## Aktueller Status
 "Use when tracking CJ대한통운 or 우체국 parcels by invoice number with official carrier endpoints, or when building a carrier-adapter workflow that can grow to support more couriers late

## Pfad zum Output
.agents/skills/agents/delivery-tracking/SKILL.md

## Re-Aktivierung (schnell)
```bash
bash .agents/skills/live-context.sh delivery-tracking   # holt diesen Snapshot
# Falls mehr Details nötig:  cat .agents/skills/delivery-tracking/SKILL.md
```

