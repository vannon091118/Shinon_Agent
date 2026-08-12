---
name: autorun
description: "Use when the agent needs to decide what an Auto tab does next — driving work forward until genuinely finished and merged, then continuing as far as the selected scope allows."
category: agents
stack: AUTONOM + GOVERNANCE
risk: high
side_effects: code_changes
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
metadata:
  freebuff-builtin: "autorun"

---
# Auto Run

Drive the user's request forward until it is genuinely finished and merged, then keep going as far as the selected scope allows.

## Workflow

Create and merge whatever follow-up pull requests that scope admits. Get each coherent unit reviewed, verified and merged on its own rather than stacking everything onto one branch. Work the scope does not admit is something to name when you hand the tab back, not something to start.