# 🧠 Skills Index — 666 SKILL.md · 29 Kategorien + 10 v4-Router

**Stand: 12. August 2026 (v4-Reparatur)** · Inhaltsbasiert sortiert · Global sync: `~/.agents/skills/`

> **Quelle der Wahrheit:** [`validate-catalog.py`](validate-catalog.py) — reproduzierbarer Prüfer.
> v4: 100 Description-Fixes (0 ungültige YAML), 0 Duplikate, 10 neue Router:
> `claude-tools-router` · `data-analytics-router` · `devtools-router` · `documents-router` ·
> `games-router` · `gaming-router` · `gemini-tools-router` · `meta-router` · `productivity-router` · `web-dev-router`

---

## 📊 Übersicht

| # | Kategorie | Skills | Inhalt |
|---|---|---|---|
| 1 | `communication-apis` | 108 | Twilio, Zoom — SMS, Voice, Video APIs |
| 2 | `cloud-platforms` | 89 | Vercel, Netlify, Render, Cloudflare, DO |
| 3 | `bioscience` | 76 | Life-Science, NGS, Boltz — Bioinformatik |
| 4 | `finance` | 44 | Daloopa, Moody's, Morningstar, Datasite |
| 5 | `design-tools` | 40 | Figma, Canva, Remotion, Hyperframes, DataViz |
| 6 | `communication` | 38 | Slack, Teams, Gmail, Outlook, Superhuman |
| 7 | `mobile-dev` | 35 | iOS, macOS, Expo, Android — Mobile Dev |
| 8 | `ai-ml` | 28 | HuggingFace, OpenAI, NVIDIA — AI/ML |
| 9 | `ecommerce` | 26 | Shopify, Stripe, Wix |
| 10 | `productivity` | 24 | Linear, Notion, Atlassian, SharePoint, Legal |
| 11 | `devtools` | 20 | GitHub, CircleCI, Sentry, Plugin-Eval, Base44 |
| 12 | `web-dev` | 16 | Build-Web-Apps, Superpowers — Frontend |
| 13 | `security` | 13 | Codex-Security, CodeRabbit — Audit/Scan (osint-self-audit in eigene Kategorie ausgelagert) |
| 14 | `claude-tools` | 9 | Claude Session Skills — Memory, Schedule |
| 15 | `gaming` | 9 | Game-Studio — Phaser, Three.js, R3F |
| 16 | `development` | 8 | Debug, Architecture, TypeScript, Python |
| 17 | `agents` | 7 | Orchestrator, Guide, Autorun, Hooks |
| 18 | `media` | 6 | Media-Gen, Transcribe, Screenshots, HeyGen |
| 19 | `design` | 6 | Frontend, Canvas, Tailwind, Performance |
| 20 | `research` | 5 | Deep-Research, Heatmap, Wiki, Persona |
| 21 | `documents` | 4 | .docx, .xlsx, .pptx, .pdf |
| 22 | `databases` | 10 | Supabase, Neon, Box, Google Drive |
| 23 | `meta` | 3 | Self-Improvement, Skill-Creator, Find-Skills |
| 24 | `games` | 2 | PlayCanvas, Lua-Game-Systems |
| 25 | `gemini-tools` | 2 | Antigravity Guide, Customizations |
| 26 | `testing` | 1 | Playwright-Expert |
| 27 | `content-parser` | 1 | URL-Inhalte extrahieren und normalisieren |
| 28 | `data-analytics` | 14 | Airtable, Deepnote, Hex, Mixpanel, PostHog |
| 29 | `osint-self-audit` | 1 | Read-only Privacy-Selbstaudit des anfragenden Users |
|---|---|---|---|
| | **Total** | **645** | |

---

## 🗂️ Kategorien

### agents/ (7)

| Pfad | Beschreibung |
|---|---|
| `agents/autorun` | Auto-Tab: Work vorantreiben bis fertig & gemerged |
| `agents/clerk-webhooks` | Clerk Webhook-Handler: User, Session, Org, Billing |
| `agents/delivery-tracking` | Paket-Tracking (CJ대한통운, 우체국) |
| `agents/documentation-writer` | Software-Doku nach Diátaxis-Framework |
| `agents/guide-architekt` | Guide & Architekt: Projekte von Basis bis Release |
| `agents/multi-agent-orchestrator` | Multi-Agent-Workflows mit Rollen, Gates & Preflight |
| `agents/sub-agent-prompts` | Prompt-Vorlagen für Sub-Agents |

### ai-ml/ (28)

| Pfad | Beschreibung |
|---|---|
| `ai-ml/hugging-face/` | HuggingFace Hub: CLI, Datasets, Gradio, Trainer, Transformers.js |
| `ai-ml/nvidia/` | NVIDIA: cuOpt, Dynamo, Omniverse, NemoClaw, Physical AI |
| `ai-ml/openai-developers/` | OpenAI: Agents SDK, ChatGPT Apps, API Troubleshooting |
| `ai-ml/openai-ads-conversions/` | OpenAI Ads Measurement Setup |

### bioscience/ (76)

| Pfad | Beschreibung |
|---|---|
| `bioscience/boltz-api-cli/` | Boltz: Protein Design, Screening, ADME, Binding |
| `bioscience/life-science-research/` | 50 Bioinfo-Skills: AlphaFold, Ensembl, UniProt, GWAS, NCBI... |
| `bioscience/ngs-analysis/` | NGS: RNA-Seq, scRNA, ATAC-Seq, Metagenomics, Variants |

### claude-tools/ (9)

| Pfad | Beschreibung |
|---|---|
| `claude-tools/consolidate-memory` | Memory-Dateien aufräumen, Duplikate mergen |
| `claude-tools/docx` | Word-Dokumente erstellen/editieren |
| `claude-tools/explain-usage` | Token-Nutzung erklären |
| `claude-tools/morning` | Morgen-Briefing als HTML-Artifact |
| `claude-tools/pdf` | PDF-Dateien verarbeiten |
| `claude-tools/pptx` | PowerPoint-Decks |
| `claude-tools/schedule` | Geplante Tasks: "every day", "remind me" |
| `claude-tools/setup-cowork` | Guided Cowork Setup |
| `claude-tools/xlsx` | Excel-Workbooks |

### cloud-platforms/ (89)

| Pfad | Beschreibung |
|---|---|
| `cloud-platforms/cloudflare/` | Cloudflare: Workers, Durable Objects, AI Gateway, Wrangler |
| `cloud-platforms/digitalocean/` | DigitalOcean: Droplets |
| `cloud-platforms/netlify/` | Netlify: Deploy, Functions, Edge, Identity, Forms, Blobs |
| `cloud-platforms/render/` | Render: Deploy, Postgres, Cron, Disks, Docker, Workflows |
| `cloud-platforms/vercel/` | Vercel (46): Next.js, AI SDK, Functions, Edge, Turborepo, v0 |

### communication/ (38)

| Pfad | Beschreibung |
|---|---|
| `communication/gmail/` | Gmail: Inbox-Triage, Search, Threads |
| `communication/google-calendar/` | Google Calendar: Daily Brief, Free-Up, Meeting Prep |
| `communication/outlook-calendar/` | Outlook Calendar: Brief, Scheduling, Shared |
| `communication/outlook-email/` | Outlook: Triage, Reply-Drafting, Tasks, Cleanup |
| `communication/slack/` | Slack: Summarization, Digest, Messages, Triage |
| `communication/superhuman/` | Superhuman: Batch-Drafts, Deal-Tracker, EOD-Wrapup |
| `communication/teams/` | Teams: Summarization, Digest, Messages, Planner |

### communication-apis/ (108)

| Pfad | Beschreibung |
|---|---|
| `communication-apis/twilio-developer-kit/` | Twilio (55): SMS, Voice, Email, Verify, SendGrid, Webhooks |
| `communication-apis/zoom/` | Zoom (53): Meeting SDK, Video SDK, OAuth, Bots, Webhooks |

### content-parser/ (1)

| Pfad | Beschreibung |
|---|---|
| `content-parser` | URL-Inhalte extrahieren und normalisieren; Ergebnis vor Nutzung verifizieren |

### data-analytics/ (14)

| Pfad | Beschreibung |
|---|---|
| `data-analytics/airtable/` | Airtable: CLI, Filters, Overview |
| `data-analytics/deepnote/` | Deepnote: Notebooks, Data Execution, Links |
| `data-analytics/hex/` | Hex: Projects & Threads |
| `data-analytics/mixpanel-headless/` | Mixpanel: Dashboard, Auth, Analytics |
| `data-analytics/posthog/` | PostHog: Product Analytics |

### databases/ (10)

| Pfad | Beschreibung |
|---|---|
| `databases/box/` | Box: Uploads, Folders, Integrations |
| `databases/google-drive/` | Google Drive: Docs, Sheets, Slides, Comments |
| `databases/neon-postgres/` | Neon: Postgres, Egress-Optimizer |
| `databases/supabase/` | Supabase: Postgres Best Practices |

### design/ (6)

| Pfad | Beschreibung |
|---|---|
| `design/canvas` | Räumliche Diagramme, Concept Maps (JSON Canvas) |
| `design/canvas-design` | Visuelle Kunst: .png/.pdf Posters & Designs |
| `design/frontend-design` | Distinctive UI-Design: Typography, Color, Layout |
| `design/performance` | Web-Performance: Core Web Vitals, Optimierung |
| `design/tailwind-design-system` | Design Systems mit Tailwind CSS v4 |
| `design/web-design-guidelines` | UI-Review nach Web Interface Guidelines |

### design-tools/ (40)

| Pfad | Beschreibung |
|---|---|
| `design-tools/build-web-data-visualization/` | D3, Canvas2D, ThreeJS, Dashboards, Geospatial, Scrollytelling |
| `design-tools/canva/` | Canva: Branded Presentations, Social Media, Translate |
| `design-tools/figma/` | Figma: Design-to-Code, Code-Connect, Motion, FigJam |
| `design-tools/hyperframes/` | Hyperframes: GSAP, CLI, Registry |
| `design-tools/magicpath/` | MagicPath: UI Components, Themes, Canvas |
| `design-tools/remotion/` | Remotion: Video Creation in React |

### development/ (8)

| Pfad | Beschreibung |
|---|---|
| `development/improve-codebase-architecture` | Architektur-Friction analysieren & refactorn |
| `development/python-performance-optimization` | cProfile, Memory-Profiler, Bottleneck-Analyse |
| `development/python-testing-patterns` | pytest, Fixtures, Mocking, TDD |
| `development/receiving-code-review` | Review-Feedback verifizieren, nicht blind umsetzen |
| `development/systematic-debugging` | Bugs & Test-Failures systematisch debuggen |
| `development/typescript-expert` | Typed/JS: Type-Level, Monorepos, Migration |
| `development/upgrade-react-native` | React-Native-Upgrades mit nativen Änderungen |
| `development/writing-plans` | Specs in umsetzbare Pläne übersetzen |

### devtools/ (20)

| Pfad | Beschreibung |
|---|---|
| `devtools/base44/` | Base44: CLI, SDK, Troubleshooter |
| `devtools/circleci/` | CircleCI: Builds, Config, CLI, Chunk |
| `devtools/github/` | GitHub: PR-Comments, CI-Fix, Yeet-Publish |
| `devtools/plugin-eval/` | Plugin/Skill-Evaluation & Metric-Packs |
| `devtools/replayio/` | Replay: QA-API, Browser-Recording |
| `devtools/sentry/` | Sentry: Issues & Events inspizieren |
| `devtools/temporal/` | Temporal: Workflow-Entwicklung |

### documents/ (4)

| Pfad | Beschreibung |
|---|---|
| `documents/document-tools` | Word .docx: erstellen, editieren, reviewen |
| `documents/pdf-tools` | PDF: lesen, extrahieren, erstellen, Formulare |
| `documents/presentation-tools` | PowerPoint .pptx: Slide-Decks |
| `documents/spreadsheet-tools` | Excel .xlsx: Workbooks, Analyse, Audit |

### ecommerce/ (26)

| Pfad | Beschreibung |
|---|---|
| `ecommerce/shopify/` | Shopify (20): Admin, Hydrogen, Liquid, Polaris, POS, Functions |
| `ecommerce/stripe/` | Stripe: Best Practices, API-Upgrades |
| `ecommerce/wix/` | Wix: Apps, Design-System, Headless, Management |

### finance/ (44)

| Pfad | Beschreibung |
|---|---|
| `finance/chronograph-gp/` | Chronograph GP: Portfolio One-Pager |
| `finance/chronograph-lp/` | Chronograph LP: Cashflow, Meeting Prep |
| `finance/daloopa/` | Daloopa (21): DCF, Comps, Earnings, IB-Deck, Supply-Chain... |
| `finance/datasite/` | Datasite: QA, Gap-Analysis, Risk-Audit, VDR-Setup |
| `finance/dnb-finance-analytics/` | D&B Finance Analytics |
| `finance/moody-s/` | Moody's: Company, Rating, Peer, Sector Analysis |
| `finance/morningstar/` | Morningstar: Fund-Comparison, Screener, Summarizer |

### games/ (2)

| Pfad | Beschreibung |
|---|---|
| `games/lua-game-systems` | Lua Game Mods: multiplayer-safe, balanced |
| `games/playcanvas-engine` | WebGL/WebGPU Game Engine: Entity-Component |

### gaming/ (9)

| Pfad | Beschreibung |
|---|---|
| `gaming/game-studio/` | Game-Studio: Phaser 2D, Three.js, R3F, Sprite-Pipeline |

### gemini-tools/ (2)

| Pfad | Beschreibung |
|---|---|
| `gemini-tools/agy-customizations` | Antigravity Customizations |
| `gemini-tools/antigravity_guide` | Google Antigravity Guide & Sitemap |

### media/ (6)

| Pfad | Beschreibung |
|---|---|
| `media/audio-transcription` | Audio lokal mit Whisper transkribieren |
| `media/desktop-automation` | Native Desktop-Apps steuern |
| `media/heygen/` | HeyGen: Avatar & Video-Generierung |
| `media/media-generation` | KI-Medien: Bilder, Videos, Audio, 3D |
| `media/screenshot-tools` | Desktop-Screenshots |

### meta/ (3)

| Pfad | Beschreibung |
|---|---|
| `meta/find-skills` | Community-Skills entdecken & installieren |
| `meta/self-improvement` | Learnings, Errors, Corrections — kontinuierlich |
| `meta/skill-creator` | Skills erstellen, evaluieren, benchmarken |

### mobile-dev/ (35)

| Pfad | Beschreibung |
|---|---|
| `mobile-dev/build-ios-apps/` | iOS: SwiftUI, App-Intents, Debugger, Performance |
| `mobile-dev/build-macos-apps/` | macOS: AppKit, SwiftUI, Signing, Packaging |
| `mobile-dev/expo/` | Expo: Router, API-Routes, CICD, Dev-Client, Tailwind |
| `mobile-dev/test-android-apps/` | Android: Emulator-QA, Performance |

### osint-self-audit/ (1)

| Pfad | Beschreibung |
|---|---|
| `osint-self-audit` | Read-only Selbstprüfung des eigenen digitalen Fußabdrucks; niemals für Dritte |

### productivity/ (24)

| Pfad | Beschreibung |
|---|---|
| `productivity/atlassian-rovo/` | Atlassian: Tasks, Status, Knowledge, Spec-to-Backlog |
| `productivity/brighthire/` | BrightHire: Interview Intelligence |
| `productivity/catalyst-by-zoho/` | Zoho Catalyst Business-Plattform |
| `productivity/linear/` | Linear: Issues, Projects & Workflows |
| `productivity/midpage/` | Midpage: Legal Briefs, Memos, Cite-Checks |
| `productivity/notion/` | Notion: Knowledge, Meetings, Research, Spec-to-Impl |
| `productivity/sharepoint/` | SharePoint: Docs, Sheets, PowerPoint, Discovery |
| `productivity/zotero/` | Zotero: Desktop-API, Search |

### research/ (5)

| Pfad | Beschreibung |
|---|---|
| `research/community-deep-research` | Foren-Recherche mit Quellen-Traceability |
| `research/parallel-deep-research` | Exhaustive Deep Research |
| `research/persona-researcher` | Google Workspace: Papers, Notes, Drive |
| `research/research-heatmap` | Heatmaps aus Community-Research |
| `research/wiki-system` | Persönliches Markdown-Wiki |

### security/ (13)

| Pfad | Beschreibung |
|---|---|
| `security/coderabbit/` | CodeRabbit: AI Code-Review |
| `security/codex-security/` | Security (12): Scan, Threat-Model, Fix-Finding, Validation, Writeup |

### testing/ (1)

| Pfad | Beschreibung |
|---|---|
| `testing/playwright-expert` | E2E-Testing mit Playwright |

### web-dev/ (16)

| Pfad | Beschreibung |
|---|---|
| `web-dev/build-web-apps/` | Frontend: App-Builder, React, shadcn, Testing, Supabase |
| `web-dev/superpowers/` | Superpowers: Brainstorming, Parallel-Agents, TDD, Git-Worktrees |

---

## 📋 Alphabetischer Index (Auszug Top-50)

| Skill-Pfad | Kategorie |
|---|---|
| `agents/autorun` | agents |
| `ai-ml/hugging-face/cli` | ai-ml |
| `bioscience/life-science-research/alphafold-skill` | bioscience |
| `claude-tools/schedule` | claude-tools |
| `cloud-platforms/vercel/nextjs` | cloud-platforms |
| `communication/slack/slack` | communication |
| `communication-apis/twilio-developer-kit/twilio-send-message` | communication-apis |
| `data-analytics/posthog/posthog` | data-analytics |
| `databases/supabase/supabase` | databases |
| `design/frontend-design` | design |
| `design-tools/figma/figma-design-to-code` | design-tools |
| `development/systematic-debugging` | development |
| `devtools/github/github` | devtools |
| `documents/spreadsheet-tools` | documents |
| `ecommerce/shopify/shopify-admin` | ecommerce |
| `finance/daloopa/dcf` | finance |
| `games/playcanvas-engine` | games |
| `gaming/game-studio/phaser-2d-game` | gaming |
| `gemini-tools/antigravity_guide` | gemini-tools |
| `media/audio-transcription` | media |
| `meta/skill-creator` | meta |
| `mobile-dev/expo/building-native-ui` | mobile-dev |
| `productivity/notion/notion-knowledge-capture` | productivity |
| `research/wiki-system` | research |
| `security/codex-security/security-scan` | security |
| `testing/playwright-expert` | testing |
| `web-dev/superpowers/brainstorming` | web-dev |

---

_666 SKILL.md · 29 Kategorien + 10 v4-Router · verifiziert am 12. August 2026 (v4-Reparatur) · Global sync: ~/.agents/skills/_
