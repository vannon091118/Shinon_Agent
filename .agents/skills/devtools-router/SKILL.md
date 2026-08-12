---
name: devtools-router
description: "Router für 20 devtools-Skills (base44, circleci, github, plugin-eval, replayio, sentry, ...). Leitet User-Intents automatisch an den richtigen Sub-Skill weiter. Routing-Tabelle im Body."
category: devtools
stack: AUTONOM + GOVERNANCE
risk: medium
side_effects: file_changes
requires_approval: true
version: 1.0.0
last_verified: 2026-08-12

---
# 🧭 Devtools Router — 20 Skills

> **Router für `devtools/`** — Wählt automatisch den richtigen Sub-Skill basierend auf User-Intent.

## 🗺️ Routing-Tabelle

| User sagt... | → Skill | Pfad |
|---|---|---|
| "The base44 CLI is used for EVERYTHING related to base44 projects: resource configuration (entities, backend functions, ai agents), ...", "This skill is the place for learning about how to configure resources" | `base44` | `devtools/base44/base44-cli` |
| "The base44 SDK is the library to communicate with base44 services", "In projects, you use it to communicate with remote resources (entities, backend functions, ai agents) and to write backend functions" | `base44-sdk` | `devtools/base44/base44-sdk` |
| "Troubleshoot production issues using backend function logs", "Use when investigating app errors, debugging function calls, or diagnosing production problems in Base44 apps" | `base44-troubleshooter` | `devtools/base44/base44-troubleshooter` |
| "Diagnose and fix failing CircleCI builds quickly and safely", "Use when users ask to investigate failed CircleCI jobs, triage flaky pipelines, identify root causes from logs, and implement minimal fixes ..." | `circleci-builds` | `devtools/circleci/builds` |
| "Use CircleCI Chunk for AI-assisted CI/CD work through either the Chunk web UI or the chunk-cli", "Trigger this skill when users ask to set up Chunk, troubleshoot or fix failing builds with Chunk, configure Chunk environments, ..." | `chunk` | `devtools/circleci/chunk` |
| "Operate and troubleshoot CircleCI using the CircleCI CLI", "Use when users ask to authenticate CLI access, inspect pipeline/workflow/job status, validate configuration locally, rerun pipelines/jobs, ..." | `circleci-cli` | `devtools/circleci/cli` |
| "Optimize CircleCI configuration for speed, reliability, and maintainability", "Use when users ask to improve `.circleci/config.yml`, reduce CI runtime, tune caching/workspaces/parallelism, remove pipeline waste, or fix ..." | `circleci-config` | `devtools/circleci/config` |
| "Address actionable GitHub pull request review feedback", "Use when the user wants to inspect unresolved review threads, requested changes, or inline review comments on a PR, then implement selected ..." | `gh-address-comments` | `devtools/github/gh-address-comments` |
| "a user asks to debug or fix failing GitHub PR checks that run in GitHub Actions" | `gh-fix-ci` | `devtools/github/gh-fix-ci` |
| "Triage and orient GitHub repository, pull request, and issue work through the connected GitHub app", "Use when the user asks for general GitHub help, wants PR or issue summaries, or needs repository context before choosing a more specific ..." | `github` | `devtools/github/github` |
| "Publish local changes to GitHub by confirming scope, committing intentionally, pushing the branch, and opening a draft PR through the ..." | `yeet` | `devtools/github/yeet` |
| "Evaluate a local Codex plugin in engineer-friendly language", "Use when the user says \"evaluate this plugin\", \"audit this plugin\", \"why did this score that way\", \"what should I fix first\", ..." | `evaluate-plugin` | `devtools/plugin-eval/evaluate-plugin` |
| "Evaluate a local Codex skill in engineer-friendly terms", "Use when the user says \"evaluate this skill\", \"give me an analysis of the game dev skill\", \"audit this skill\", \"why did this score ..." | `evaluate-skill` | `devtools/plugin-eval/evaluate-skill` |
| "Turn plugin-eval findings into a concrete rewrite brief for a Codex skill", "Use when the user already evaluated a skill and now wants Codex to improve it, especially after asking what to fix first" | `improve-skill` | `devtools/plugin-eval/improve-skill` |
| "Design custom metric packs for plugin-eval so teams can add local evaluation rubrics that emit schema-compatible checks and metrics", "Use when the user wants their own evaluation criteria or visualizations" | `metric-pack-designer` | `devtools/plugin-eval/metric-pack-designer` |
| "Help engineers evaluate a local skill or plugin, explain why it scored that way, show what to fix first, measure real token usage, ...", "Use when the user says things like \"evaluate this skill\", \"give me an analysis of the game dev skill\", \"why did this score that way\", ..." | `plugin-eval` | `devtools/plugin-eval/plugin-eval` |
| "calling Replay QA's REST API directly from Codex. Covers bearer-token setup", "Replay recording prerequisites", "project creation from Replay recordings or target URLs", "polling" | `replay-qa-api` | `devtools/replayio/replay-qa-api` |
| "you need to record or inspect an agent browser run in Replay", "test a local app with the host agent browser using Replay Chromium", "or use the Replay MCP server for deeper debugging of an uploaded recording.\" | `replayio` | `devtools/replayio/replayio` |
| "the user asks to inspect Sentry issues or events", "summarize recent production errors", "or pull basic Sentry health data via the Sentry API; perform read-only queries with the bundled script and require `SENTRY_AUTH_TOKEN`.\" | `sentry` | `devtools/sentry/sentry` |
| "Develop, debug, and manage Temporal applications across Python, TypeScript, Go, and Java", "Use when the user is building workflows, activities, or workers with a Temporal SDK, debugging issues like non-determinism errors, stuck ..." | `temporal-developer` | `devtools/temporal/temporal-developer` |

## 🔀 Routing-Logik

```
  "Base44" → base44
  "Base44" → base44-sdk
  "Base44" → base44-troubleshooter
  "Circleci" → circleci-builds
  "Chunk" → chunk
  "Circleci" → circleci-cli
  "Circleci" → circleci-config
  "Gh" → gh-address-comments
  "Gh" → gh-fix-ci
  "Github" → github
  "Yeet" → yeet
  "Evaluate" → evaluate-plugin
  "Evaluate" → evaluate-skill
  "Improve" → improve-skill
  "Metric" → metric-pack-designer
  "Plugin" → plugin-eval
  "Replay" → replay-qa-api
  "Replayio" → replayio
  "Sentry" → sentry
  "Temporal" → temporal-developer
  Unklar? → Nachfrage: Welche Aufgabe, welcher Anbieter?
```

## 📋 Sub-Skill-Register

| # | Skill | Pfad |
|---|---|---|
| 1 | `base44` | `devtools/base44/base44-cli` |
| 2 | `base44-sdk` | `devtools/base44/base44-sdk` |
| 3 | `base44-troubleshooter` | `devtools/base44/base44-troubleshooter` |
| 4 | `circleci-builds` | `devtools/circleci/builds` |
| 5 | `chunk` | `devtools/circleci/chunk` |
| 6 | `circleci-cli` | `devtools/circleci/cli` |
| 7 | `circleci-config` | `devtools/circleci/config` |
| 8 | `gh-address-comments` | `devtools/github/gh-address-comments` |
| 9 | `gh-fix-ci` | `devtools/github/gh-fix-ci` |
| 10 | `github` | `devtools/github/github` |
| 11 | `yeet` | `devtools/github/yeet` |
| 12 | `evaluate-plugin` | `devtools/plugin-eval/evaluate-plugin` |
| 13 | `evaluate-skill` | `devtools/plugin-eval/evaluate-skill` |
| 14 | `improve-skill` | `devtools/plugin-eval/improve-skill` |
| 15 | `metric-pack-designer` | `devtools/plugin-eval/metric-pack-designer` |
| 16 | `plugin-eval` | `devtools/plugin-eval/plugin-eval` |
| 17 | `replay-qa-api` | `devtools/replayio/replay-qa-api` |
| 18 | `replayio` | `devtools/replayio/replayio` |
| 19 | `sentry` | `devtools/sentry/sentry` |
| 20 | `temporal-developer` | `devtools/temporal/temporal-developer` |

_20 Skills · devtools · 2026-08-12_
