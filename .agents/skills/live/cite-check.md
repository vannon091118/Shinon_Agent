---
skill: cite-check
state: idle
last_activation: 2026-08-11T23:01:41Z
activation_count: 2
tags: [catalog]
output_path: ".agents/skills/productivity/midpage/cite-check/SKILL.md"
---

# ⏸️  cite-check · IDLE

> **Token-saving artifact.** Dieser ~20-Zeilen-Snapshot ersetzt das vollständige
> SKILL.md (~200-400 Zeilen) bei Re-Activation. Re-Aktivierungen lesen NUR
> diesen Snapshot, sofern keine erweiterte Funktionalität benötigt wird.

## Aktueller Status
"[codex:midpage] \"Cite-checks a brief, motion, or memo (PDF/Word): verifies each cited case is real, supports the proposition, is good law, and quoted accurately. Returns one mark

## Pfad zum Output
.agents/skills/productivity/midpage/cite-check/SKILL.md

## Re-Aktivierung (schnell)
```bash
bash .agents/skills/live-context.sh cite-check   # holt diesen Snapshot
# Falls mehr Details nötig:  cat .agents/skills/cite-check/SKILL.md
```

