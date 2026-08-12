---
skill: goal-chain
state: error
last_activation: 2026-08-12T12:16:12Z
activation_count: 190
tags: [FAIL,test]
output_path: ""
---

# ❌ goal-chain · ERROR

> **Token-saving artifact.** Dieser ~20-Zeilen-Snapshot ersetzt das vollständige
> SKILL.md (~200-400 Zeilen) bei Re-Activation. Re-Aktivierungen lesen NUR
> diesen Snapshot, sofern keine erweiterte Funktionalität benötigt wird.

## Aktueller Status
TID X5 fehlgeschlagen: Script not found: /home/vannon/Schreibtisch/projects/PZ/.agents/skills/goal-chain/scripts/MISSING.sh

## Pfad zum Output
_kein Output-File_

## Re-Aktivierung (schnell)
```bash
bash .agents/skills/live-context.sh goal-chain   # holt diesen Snapshot
# Falls mehr Details nötig:  cat .agents/skills/goal-chain/SKILL.md
```

