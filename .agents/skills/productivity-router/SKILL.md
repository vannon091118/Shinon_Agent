---
name: productivity-router
description: "Router für 24 productivity-Skills (atlassian-rovo, brighthire, catalyst-by-zoho, linear, mid...). Leitet User-Intents automatisch an den richtigen Sub-Skill weiter. Routing-Tabelle im Body."
category: productivity
stack: AUTONOM + GOVERNANCE
risk: medium
side_effects: file_changes
requires_approval: true
version: 1.0.0
last_verified: 2026-08-12

---
# 🧭 Productivity Router — 24 Skills

> **Router für `productivity/`** — Wählt automatisch den richtigen Sub-Skill basierend auf User-Intent.

## 🗺️ Routing-Tabelle

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Analyze meeting notes to find action items and create Jira tasks for assigned work", "When an agent needs to: (1) Create Jira tasks or tickets from meeting notes, (2) Extract or find action items from notes or Confluence ..." | `capture-tasks-from-meeting-notes` | `productivity/atlassian-rovo/capture-tasks-from-meeting-notes` |
| "Generate project status reports from Jira issues and publish to Confluence", "When an agent needs to: (1) Create a status report for a project, (2) Summarize project progress or updates, (3) Generate weekly/daily ..." | `generate-status-report` | `productivity/atlassian-rovo/generate-status-report` |
| "Search across company knowledge bases (Confluence, Jira, internal docs) to find and explain internal concepts, processes, and technical ...", "When an agent needs to: (1) Find or search for information about systems, terminology, processes, deployment, authentication, ..." | `search-company-knowledge` | `productivity/atlassian-rovo/search-company-knowledge` |
| "Automatically convert Confluence specification documents into structured Jira backlogs with Epics and implementation tickets", "When an agent needs to: (1) Create Jira tickets from a Confluence page, (2) Generate a backlog from a specification, (3) Break down a spec ..." | `spec-to-backlog` | `productivity/atlassian-rovo/spec-to-backlog` |
| "Intelligently triage bug reports and error messages by searching for duplicates in Jira and offering to create new issues or add comments ...", "When an agent needs to: (1) Triage a bug report or error message, (2) Check if an issue is a duplicate, (3) Find similar past issues, (4) ..." | `triage-issue` | `productivity/atlassian-rovo/triage-issue` |
| "Use BrightHire tools when a user asks about BrightHire interview intelligence, calls, candidates, roles, scorecards, transcripts, hiring ..." | `brighthire` | `productivity/brighthire/brighthire` |
| "Build business apps and workflows on the Zoho Catalyst platform: cloud functions, data store, and REST APIs" | `catalyst-by-zoho` | `productivity/catalyst-by-zoho/catalyst-by-zoho` |
| "Manage issues, projects & team workflows in Linear", "Use when the user wants to read, create or updates tickets in Linear" | `linear` | `productivity/linear/linear` |
| "Cite-checks a brief, motion, or memo (PDF/Word): verifies each cited case is real, supports the proposition, is good law, and quoted ...", "Returns one marked-up .docx with comments and redlines.\" | `cite-check` | `productivity/midpage/cite-check` |
| "Draft and format a court-ready filing and hand back the .docx", "Briefs, motions, memoranda of" | `draft-brief` | `productivity/midpage/draft-brief` |
| "Draft long-form legal memoranda: structure, citations, and arguments suitable for court filings" | `draft-long-form-memo` | `productivity/midpage/draft-long-form-memo` |
| "Write litigation update posts summarizing case status, filings, and next steps for stakeholders" | `litigation-update-post` | `productivity/midpage/litigation-update-post` |
| "Capture conversations and decisions into structured Notion pages; use when turning chats/notes into wiki entries, how-tos, decisions, or ..." | `notion-knowledge-capture` | `productivity/notion/notion-knowledge-capture` |
| "Prepare meeting materials with Notion context and Codex research; use when gathering context, drafting agendas/pre-reads, and tailoring ..." | `notion-meeting-intelligence` | `productivity/notion/notion-meeting-intelligence` |
| "Research across Notion and synthesize into structured documentation; use when gathering info from multiple Notion sources to produce ..." | `notion-research-documentation` | `productivity/notion/notion-research-documentation` |
| "Turn Notion specs into implementation plans, tasks, and progress tracking; use when implementing PRDs/feature specs and creating Notion ..." | `notion-spec-to-implementation` | `productivity/notion/notion-spec-to-implementation` |
| "Inspect Microsoft SharePoint context, discover the right site or library, and prepare safe changes", "Use when the user wants site, page, or file review, ownership and status extraction, or change planning before editing content, navigation, ..." | `sharepoint` | `productivity/sharepoint/sharepoint` |
| "Create, edit, restyle, and review PowerPoint `.pptx` files fetched from SharePoint, with emphasis on style preservation, slide cloning, ...", "Use when the user wants reliable slide edits that should match an existing deck's design language" | `sharepoint-powerpoint` | `productivity/sharepoint/sharepoint-powerpoint` |
| "Maintain shared SharePoint strategy, roadmap, planning, or status documents from changing source documents", "Use when the user wants cross-document synthesis, source-of-truth propagation, or targeted updates to a maintained shared document" | `sharepoint-shared-doc-maintenance` | `productivity/sharepoint/sharepoint-shared-doc-maintenance` |
| "Resolve the right SharePoint site, library, and folder before file work", "Use when the user needs to find the right site context, browse a known site, inspect document libraries, or narrow the correct folder ..." | `sharepoint-site-discovery` | `productivity/sharepoint/sharepoint-site-discovery` |
| "Design, repair, and roll out formulas in SharePoint-hosted workbooks with connector-aware retrieval, validation, and upload discipline", "Use when the user wants to add a formula column, fix a broken formula, choose between a fill-down formula and a spill formula, build a ..." | `sharepoint-spreadsheet-formula-builder` | `productivity/sharepoint/sharepoint-spreadsheet-formula-builder` |
| "Edit SharePoint-hosted spreadsheet files while preserving workbook structure, formulas, and formatting", "Use when the user wants to update a real spreadsheet in SharePoint rather than summarize extracted sheet text" | `sharepoint-spreadsheets` | `productivity/sharepoint/sharepoint-spreadsheets` |
| "Edit SharePoint-hosted Word `.docx` files while preserving document structure and styling", "Use when the user wants to update a real Word document in SharePoint rather than summarize it as plain text" | `sharepoint-word-docs` | `productivity/sharepoint/sharepoint-word-docs` |
| "Use Zotero Desktop from Codex to enable/probe the local API, search a local Zotero library, list items/collections/tags, export BibTeX, ...", "Use when the user mentions Zotero, citations, references.bib, BibTeX export, local Zotero API, localhost:23119, or adding citations from a ..." | `Zotero` | `productivity/zotero/zotero` |

## 🔀 Routing-Logik

```
  "Capture" → capture-tasks-from-meeting-notes
  "Generate" → generate-status-report
  "Search" → search-company-knowledge
  "Spec" → spec-to-backlog
  "Triage" → triage-issue
  "Brighthire" → brighthire
  "Catalyst" → catalyst-by-zoho
  "Linear" → linear
  "Cite" → cite-check
  "Draft" → draft-brief
  "Draft" → draft-long-form-memo
  "Litigation" → litigation-update-post
  "Notion" → notion-knowledge-capture
  "Notion" → notion-meeting-intelligence
  "Notion" → notion-research-documentation
  "Notion" → notion-spec-to-implementation
  "Sharepoint" → sharepoint
  "Sharepoint" → sharepoint-powerpoint
  "Sharepoint" → sharepoint-shared-doc-maintenance
  "Sharepoint" → sharepoint-site-discovery
  "Sharepoint" → sharepoint-spreadsheet-formula-builder
  "Sharepoint" → sharepoint-spreadsheets
  "Sharepoint" → sharepoint-word-docs
  "Zotero" → Zotero
  Unklar? → Nachfrage: Welche Aufgabe, welcher Anbieter?
```

## 📋 Sub-Skill-Register

| # | Skill | Pfad |
|---|---|---|
| 1 | `capture-tasks-from-meeting-notes` | `productivity/atlassian-rovo/capture-tasks-from-meeting-notes` |
| 2 | `generate-status-report` | `productivity/atlassian-rovo/generate-status-report` |
| 3 | `search-company-knowledge` | `productivity/atlassian-rovo/search-company-knowledge` |
| 4 | `spec-to-backlog` | `productivity/atlassian-rovo/spec-to-backlog` |
| 5 | `triage-issue` | `productivity/atlassian-rovo/triage-issue` |
| 6 | `brighthire` | `productivity/brighthire/brighthire` |
| 7 | `catalyst-by-zoho` | `productivity/catalyst-by-zoho/catalyst-by-zoho` |
| 8 | `linear` | `productivity/linear/linear` |
| 9 | `cite-check` | `productivity/midpage/cite-check` |
| 10 | `draft-brief` | `productivity/midpage/draft-brief` |
| 11 | `draft-long-form-memo` | `productivity/midpage/draft-long-form-memo` |
| 12 | `litigation-update-post` | `productivity/midpage/litigation-update-post` |
| 13 | `notion-knowledge-capture` | `productivity/notion/notion-knowledge-capture` |
| 14 | `notion-meeting-intelligence` | `productivity/notion/notion-meeting-intelligence` |
| 15 | `notion-research-documentation` | `productivity/notion/notion-research-documentation` |
| 16 | `notion-spec-to-implementation` | `productivity/notion/notion-spec-to-implementation` |
| 17 | `sharepoint` | `productivity/sharepoint/sharepoint` |
| 18 | `sharepoint-powerpoint` | `productivity/sharepoint/sharepoint-powerpoint` |
| 19 | `sharepoint-shared-doc-maintenance` | `productivity/sharepoint/sharepoint-shared-doc-maintenance` |
| 20 | `sharepoint-site-discovery` | `productivity/sharepoint/sharepoint-site-discovery` |
| 21 | `sharepoint-spreadsheet-formula-builder` | `productivity/sharepoint/sharepoint-spreadsheet-formula-builder` |
| 22 | `sharepoint-spreadsheets` | `productivity/sharepoint/sharepoint-spreadsheets` |
| 23 | `sharepoint-word-docs` | `productivity/sharepoint/sharepoint-word-docs` |
| 24 | `Zotero` | `productivity/zotero/zotero` |

_24 Skills · productivity · 2026-08-12_
