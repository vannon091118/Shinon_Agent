---
name: debug-zoom
description:  "[codex:zoom] Use when debugging issues."
category: communication-apis
stack: GOVERNANCE + AUTONOM
risk: medium
side_effects: network_calls
requires_approval: true
version: 1.0.0
last_verified: 2026-08-11

---
# /debug-zoom

> For local plugin installation and app mapping details, see [README.md](../../README.md).

Debug Zoom auth, API, webhook, or SDK issues without wandering through the entire docs set.

## Usage

```text
/debug-zoom $ARGUMENTS
```

## Workflow

1. Identify the failing layer: auth, API request, webhook, SDK init, or media/session behavior.
2. Ask for the minimum missing evidence: exact error, platform, request/response, event payload, or code path.
3. Produce 2-4 plausible causes ranked by likelihood.
4. Route to the most relevant deep references in `skills/`.
5. Give a short verification plan so the user can confirm the fix.

## Output

- Most likely failure layer
- Ranked hypotheses
- Targeted fix steps
- Verification checklist
- Relevant skill links

## Related Skills

- [debug-zoom-integration](../debug-zoom-integration/SKILL.md)
- [setup-zoom-oauth](../setup-zoom-oauth/SKILL.md)
