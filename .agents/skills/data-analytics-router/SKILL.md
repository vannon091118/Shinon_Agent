---
name: data-analytics-router
description: "Router für 14 data-analytics-Skills (airtable, deepnote, hex, mixpanel-headless, posthog). Leitet User-Intents automatisch an den richtigen Sub-Skill weiter. Routing-Tabelle im Body."
category: data-analytics
stack: AUTONOM + GOVERNANCE
risk: medium
side_effects: file_changes
requires_approval: true
version: 1.0.0
last_verified: 2026-08-12

---
# 🧭 Data-Analytics Router — 14 Skills

> **Router für `data-analytics/`** — Wählt automatisch den richtigen Sub-Skill basierend auf User-Intent.

## 🗺️ Routing-Tabelle

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Tools are fetched from the MCP server at runtime, so the CLI never has a hardcoded command list", "Discover what's available" | `airtable-cli` | `data-analytics/airtable/airtable-cli` |
| "Use this skill when the user wants to find, filter, or narrow down Airtable records by field values, even when they don't explicitly say ..." | `airtable-filters` | `data-analytics/airtable/airtable-filters` |
| "Explains what Airtable is and how data is structured — bases, tables, fields, records, views, automations, and interfaces", "Use when you need context about the Airtable data model" | `airtable-overview` | `data-analytics/airtable/airtable-overview` |
| "a task mentions Deepnote", "the connected Deepnote app", "Deepnote OAuth connection", "Deepnote docs" | `deepnote` | `data-analytics/deepnote/deepnote` |
| "running Deepnote notebooks", "inspecting notebook inputs", "reviewing integration references and cached table structure", "listing run history" | `deepnote-data-execution` | `data-analytics/deepnote/deepnote-data-execution` |
| "a task asks for Deepnote URLs", "links", "project links", "notebook links" | `deepnote-links` | `data-analytics/deepnote/deepnote-links` |
| "creating Deepnote projects or notebooks", "adding or updating blocks or cells", "moving existing blocks", "scaffolding notebook content" | `deepnote-notebook-editing` | `data-analytics/deepnote/deepnote-notebook-editing` |
| "reading", "reviewing", "inspecting", "or reasoning about hosted Deepnote notebooks" | `deepnote-notebooks` | `data-analytics/deepnote/deepnote-notebooks` |
| "Search Hex projects and ask Hex Threads questions", "Use when the user explicitly references Hex, Hex projects, Hex dashboards, Hex data apps, Hex Threads, or asks to search an existing Hex ..." | `hex` | `data-analytics/hex/hex` |
| "Analyze, build, modify, and explain Mixpanel dashboards", "Four modes — pick the one matching the user's intent" | `dashboard-expert` | `data-analytics/mixpanel-headless/dashboard-expert` |
| "Manage Mixpanel Headless authentication: check session state, list/add/use accounts, run OAuth login, switch projects/workspaces, manage ..." | `mixpanel-auth` | `data-analytics/mixpanel-headless/mixpanel-auth` |
| "This skill should be used when the user asks about Mixpanel product analytics, event data, funnel analysis, retention curves, cohort ...", "Also use when the user asks to read, write, or manage Mixpanel \"business context\" — the markdown documentation that grounds AI assistants ..." | `mixpanelyst` | `data-analytics/mixpanel-headless/mixpanelyst` |
| "This skill installs mixpanel_headless, pandas, numpy, matplotlib, seaborn, networkx, anytree, scipy (and pyarrow on Python 3.11+), then ...", "It should be invoked when setting up a new environment for Mixpanel data analysis, when dependencies are missing, or when configuring ..." | `mixpanel-headless-setup` | `data-analytics/mixpanel-headless/setup` |
| "Analyze product data and manage product tooling in PostHog", "Use when the user wants product analytics or insights, HogQL/SQL queries, feature flags, experiments and A/B tests, error tracking, session ..." | `posthog` | `data-analytics/posthog/posthog` |

## 🔀 Routing-Logik

```
  "Airtable" → airtable-cli
  "Airtable" → airtable-filters
  "Airtable" → airtable-overview
  "Deepnote" → deepnote
  "Deepnote" → deepnote-data-execution
  "Deepnote" → deepnote-links
  "Deepnote" → deepnote-notebook-editing
  "Deepnote" → deepnote-notebooks
  "Hex" → hex
  "Dashboard" → dashboard-expert
  "Mixpanel" → mixpanel-auth
  "Mixpanelyst" → mixpanelyst
  "Mixpanel" → mixpanel-headless-setup
  "Posthog" → posthog
  Unklar? → Nachfrage: Welche Aufgabe, welcher Anbieter?
```

## 📋 Sub-Skill-Register

| # | Skill | Pfad |
|---|---|---|
| 1 | `airtable-cli` | `data-analytics/airtable/airtable-cli` |
| 2 | `airtable-filters` | `data-analytics/airtable/airtable-filters` |
| 3 | `airtable-overview` | `data-analytics/airtable/airtable-overview` |
| 4 | `deepnote` | `data-analytics/deepnote/deepnote` |
| 5 | `deepnote-data-execution` | `data-analytics/deepnote/deepnote-data-execution` |
| 6 | `deepnote-links` | `data-analytics/deepnote/deepnote-links` |
| 7 | `deepnote-notebook-editing` | `data-analytics/deepnote/deepnote-notebook-editing` |
| 8 | `deepnote-notebooks` | `data-analytics/deepnote/deepnote-notebooks` |
| 9 | `hex` | `data-analytics/hex/hex` |
| 10 | `dashboard-expert` | `data-analytics/mixpanel-headless/dashboard-expert` |
| 11 | `mixpanel-auth` | `data-analytics/mixpanel-headless/mixpanel-auth` |
| 12 | `mixpanelyst` | `data-analytics/mixpanel-headless/mixpanelyst` |
| 13 | `mixpanel-headless-setup` | `data-analytics/mixpanel-headless/setup` |
| 14 | `posthog` | `data-analytics/posthog/posthog` |

_14 Skills · data-analytics · 2026-08-12_
