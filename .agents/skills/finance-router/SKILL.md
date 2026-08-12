---
name: finance-router
description: "Router für 44 Finance-Skills (Daloopa 21 + Moody's 7 + Datasite 8 + Morningstar 3 + Chronograph 4 + D&B 1). Leitet Finance-Intents an den richtigen Sub-Skill. Use bei DCF, Comps, Earnings, M&A, Credit Analysis, Fund Screening, VDR, IB-Deck, Supply Chain."
category: finance
stack: LOGISCH + GOVERNANCE
risk: high
side_effects: data_analysis
requires_approval: true
version: "1.0.0"
last_verified: "2026-08-11"

---
# 💰 Finance Router — 44 Skills

> **Router für `finance/`** — Wählt Sub-Skill basierend auf Finanzanalyse-Typ.

---

## 🗺️ Routing-Tabelle

### Daloopa (21 Skills) — `finance/daloopa/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "DCF", "discounted cash flow", "valuation" | `dcf` | `daloopa/dcf` |
| "comps", "comparable companies", "trading comps" | `comps` | `daloopa/comps` |
| "comp sheet", "comparison sheet" | `comp-sheet` | `daloopa/comp-sheet` |
| "build model", "financial model", "three statement" | `build-model` | `daloopa/build-model` |
| "earnings review", "quarterly review" | `earnings-review` | `daloopa/earnings-review` |
| "earnings prep", "earnings preparation" | `earnings-prep` | `daloopa/earnings-prep` |
| "earnings flash", "earnings summary" | `earnings-flash` | `daloopa/earnings-flash` |
| "guidance tracker", "company guidance" | `guidance-tracker` | `daloopa/guidance-tracker` |
| "IB deck", "investment banking deck", "pitchbook" | `ib-deck` | `daloopa/ib-deck` |
| "initiate coverage", "initiation report" | `initiate` | `daloopa/initiate` |
| "tearsheet", "company tearsheet" | `tearsheet` | `daloopa/tearsheet` |
| "industry analysis", "sector analysis" | `industry` | `daloopa/industry` |
| "bull bear", "bull case bear case" | `bull-bear` | `daloopa/bull-bear` |
| "inflection point", "catalyst analysis" | `inflection` | `daloopa/inflection` |
| "unit economics", "unit econ" | `unit-economics` | `daloopa/unit-economics` |
| "supply chain analysis" | `supply-chain` | `daloopa/supply-chain` |
| "working capital", "WC analysis" | `working-capital` | `daloopa/working-capital` |
| "capital allocation", "cap allocation" | `capital-allocation` | `daloopa/capital-allocation` |
| "precedent transactions", "M&A comps" | `precedent-transactions` | `daloopa/precedent-transactions` |
| "research note", "equity research" | `research-note` | `daloopa/research-note` |
| "Daloopa setup", "Daloopa install" | `setup` | `daloopa/setup` |

### Moody's (7 Skills) — `finance/moody-s/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Moody's company analysis", "credit company" | `moody-s-company-analysis` | `moody-s/moody-s-company-analysis` |
| "Moody's rating analysis", "credit rating" | `moody-s-rating-analysis` | `moody-s/moody-s-rating-analysis` |
| "Moody's peer analysis", "credit peer" | `moody-s-peer-analysis` | `moody-s/moody-s-peer-analysis` |
| "Moody's sector brief", "sector credit" | `moody-s-sector-brief` | `moody-s/moody-s-sector-brief` |
| "Moody's issuer brief", "issuer credit" | `moody-s-issuer-brief` | `moody-s/moody-s-issuer-brief` |
| "Moody's earnings brief" | `moody-s-earnings-brief` | `moody-s/moody-s-earnings-brief` |
| "Moody's MCP", "Moody's explore" | `moody-s-explore-mcp` | `moody-s/moody-s-explore-mcp` |

### Datasite (8 Skills) — `finance/datasite/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "VDR index setup", "virtual data room" | `vdr-index-setup` | `datasite/vdr-index-setup` |
| "bulk QA answers", "QA bulk" | `bulk-qa-answers` | `datasite/bulk-qa-answers` |
| "document quality check", "doc QC" | `document-quality-check` | `datasite/document-quality-check` |
| "gap analysis", "datasite gap" | `gap-analysis` | `datasite/gap-analysis` |
| "risk analysis audit", "datasite risk" | `risk-analysis-audit` | `datasite/risk-analysis-audit` |
| "launch readiness", "VDR launch" | `launch-readiness-orchestrator` | `datasite/launch-readiness-orchestrator` |
| "IRL tracker", "datasite tracker" | `irl-tracker` | `datasite/irl-tracker` |
| "smart file renaming", "VDR rename" | `smart-file-renaming` | `datasite/smart-file-renaming` |

### Morningstar (3 Skills) — `finance/morningstar/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "fund screener", "screen funds", "find funds" | `fund-screener` | `morningstar/fund-screener` |
| "fund comparison", "compare funds" | `fund-comparison` | `morningstar/fund-comparison` |
| "fund summary", "fund report", "fund analysis" | `fund-summarizer` | `morningstar/fund-summarizer` |

### Chronograph (4 Skills) — `finance/chronograph-gp/` + `finance/chronograph-lp/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "portfolio company one-pager GP" | `chronograph-portfolio-company-one-pager` | `chronograph-gp/chronograph-portfolio-company-one-pager` |
| "portfolio company one-pager LP" | `chronograph-portfolio-company-one-pager` | `chronograph-lp/chronograph-portfolio-company-one-pager` |
| "cashflow forecast", "LP cashflow" | `chronograph-cashflow-forecast` | `chronograph-lp/chronograph-cashflow-forecast` |
| "GP meeting prep", "LP meeting prep" | `chronograph-gp-meeting-prep` | `chronograph-lp/chronograph-gp-meeting-prep` |

### D&B Finance Analytics (1 Skill)

| User sagt... | → Skill | Pfad |
|---|---|---|
| "D&B", "Dun Bradstreet", "finance analytics" | `fa-jobs-to-be-done` | `dnb-finance-analytics/fa-jobs-to-be-done` |

---

## 🔀 Routing-Logik

```
User-Intent erkennen:
├─ "DCF", "Comps", "Earnings", "IB Deck", "Model", "Valuation"
│  → finance/daloopa/<skill>
│
├─ "Moody's", "Credit Rating", "Credit Analysis"
│  → finance/moody-s/<skill>
│
├─ "Datasite", "VDR", "Data Room", "QA answers"
│  → finance/datasite/<skill>
│
├─ "Morningstar", "Fund", "Mutual Fund"
│  → finance/morningstar/<skill>
│
├─ "Chronograph", "Portfolio One-Pager", "Cashflow"
│  → finance/chronograph-gp/ ODER chronograph-lp/
│
├─ "D&B", "Dun & Bradstreet"
│  → finance/dnb-finance-analytics/<skill>
│
└── Unklar? → Frage: "Equity Research, Credit, Fund Analysis, oder M&A?"
```

---

## 📋 Vollständiges Sub-Skill-Register

### Daloopa (21)
| # | Skill | Pfad |
|---|---|------|
| 1 | dcf | daloopa/dcf |
| 2 | comps | daloopa/comps |
| 3 | comp-sheet | daloopa/comp-sheet |
| 4 | build-model | daloopa/build-model |
| 5 | earnings-review | daloopa/earnings-review |
| 6 | earnings-prep | daloopa/earnings-prep |
| 7 | earnings-flash | daloopa/earnings-flash |
| 8 | guidance-tracker | daloopa/guidance-tracker |
| 9 | ib-deck | daloopa/ib-deck |
| 10 | initiate | daloopa/initiate |
| 11 | tearsheet | daloopa/tearsheet |
| 12 | industry | daloopa/industry |
| 13 | bull-bear | daloopa/bull-bear |
| 14 | inflection | daloopa/inflection |
| 15 | unit-economics | daloopa/unit-economics |
| 16 | supply-chain | daloopa/supply-chain |
| 17 | working-capital | daloopa/working-capital |
| 18 | capital-allocation | daloopa/capital-allocation |
| 19 | precedent-transactions | daloopa/precedent-transactions |
| 20 | research-note | daloopa/research-note |
| 21 | setup | daloopa/setup |

### Moody's (7)
| # | Skill | Pfad |
|---|---|------|
| 1 | moody-s-company-analysis | moody-s/moody-s-company-analysis |
| 2 | moody-s-rating-analysis | moody-s/moody-s-rating-analysis |
| 3 | moody-s-peer-analysis | moody-s/moody-s-peer-analysis |
| 4 | moody-s-sector-brief | moody-s/moody-s-sector-brief |
| 5 | moody-s-issuer-brief | moody-s/moody-s-issuer-brief |
| 6 | moody-s-earnings-brief | moody-s/moody-s-earnings-brief |
| 7 | moody-s-explore-mcp | moody-s/moody-s-explore-mcp |

### Datasite (8)
| # | Skill | Pfad |
|---|---|------|
| 1 | vdr-index-setup | datasite/vdr-index-setup |
| 2 | bulk-qa-answers | datasite/bulk-qa-answers |
| 3 | document-quality-check | datasite/document-quality-check |
| 4 | gap-analysis | datasite/gap-analysis |
| 5 | risk-analysis-audit | datasite/risk-analysis-audit |
| 6 | launch-readiness-orchestrator | datasite/launch-readiness-orchestrator |
| 7 | irl-tracker | datasite/irl-tracker |
| 8 | smart-file-renaming | datasite/smart-file-renaming |

### Morningstar, Chronograph, D&B
| Skill | Pfad |
|---|---|
| fund-screener | morningstar/fund-screener |
| fund-comparison | morningstar/fund-comparison |
| fund-summarizer | morningstar/fund-summarizer |
| chronograph-portfolio-company-one-pager (GP) | chronograph-gp/chronograph-portfolio-company-one-pager |
| chronograph-portfolio-company-one-pager (LP) | chronograph-lp/chronograph-portfolio-company-one-pager |
| chronograph-cashflow-forecast | chronograph-lp/chronograph-cashflow-forecast |
| chronograph-gp-meeting-prep | chronograph-lp/chronograph-gp-meeting-prep |
| fa-jobs-to-be-done | dnb-finance-analytics/fa-jobs-to-be-done |

---

## Verwendung

```
User: "Erstelle ein DCF-Modell für Apple"
→ Router: finance/daloopa/dcf

User: "Moody's Credit Rating für Tesla"
→ Router: finance/moody-s/moody-s-rating-analysis

User: "VDR Index für M&A Deal einrichten"
→ Router: finance/datasite/vdr-index-setup
```

_44 Skills · Daloopa 21 + Moody's 7 + Datasite 8 + Morningstar 3 + Chronograph 4 + D&B 1 · August 2026_
