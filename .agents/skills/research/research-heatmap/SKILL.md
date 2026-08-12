---
name: research-heatmap
description:  "Convert structured community-research evidence into an honest, accessible heatmap that shows where themes, problems, stances, or intensity concentrate across public forums. Use this skill whenever the user asks for a heatmap, hotspot map, forum-by-topic matrix, discussion density visualization, or visual summary of research findings, especially when a community-evidence.json file or forum research report is available. It validates the evidence, makes the scoring transparent, and outputs reusable data alongside a standalone visual."
category: research
stack: LOGISCH + MEMORY
risk: low
side_effects: network_calls
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
compatibility: Works with community-evidence.json, CSV, or a cited Markdown report. Prefer a local standalone HTML/SVG output with no external analytics or tracking dependencies.
---

# Research Heatmap

A heatmap is a compact view of an evidence corpus, not a measurement of the whole population. Make the denominator, scoring, missing data, and source diversity visible so a bright cell cannot be mistaken for certainty.

## Inputs and defaults

Accept, in this order:

1. `community-evidence.json` produced by **community-deep-research**;
2. a CSV with one row per evidence item;
3. a Markdown report, only after extracting and verifying its cited source list.

Confirm or infer these settings and state the choice in the output:

- **X axis**: forum/domain by default;
- **Y axis**: theme by default;
- optional secondary dimension: stance, evidence type, time bucket, or intensity band;
- date range, language, and whether duplicate/cross-post groups are excluded;
- display mode: raw mention count, confidence-weighted intensity, or both.

If the input has no source URL, forum, theme, or evidence ID, stop and request a better structured input. Do not fabricate missing values.

## Normalize before plotting

Create one normalized row per evidence item. Preserve the original ID and URL. Normalize forum names and themes with a documented mapping, but retain `original_forum` and `original_theme` when merging labels. Treat blank, `unclear`, and missing as explicit **Unknown**, not as zero.

Deduplicate only when the research record identifies a duplicate group or when the same canonical post URL and claim are clearly repeated. Cross-posts may count as separate forum observations only if the visualization is explicitly about distribution across platforms; otherwise mark them and count one underlying observation.

Validate:

- intensity is numeric and clipped to 1–5;
- confidence is `high`, `medium`, or `low`;
- stance is one of `positive`, `negative`, `mixed`, `neutral`, `unclear`;
- every plotted item has a canonical URL and retrieval date, or is placed in an unverified bucket;
- no single post can create an apparently authoritative result without showing source count.

## Scoring

Always publish raw counts beside any score. For each cell `(x, y)` calculate:

- `mentions`: number of deduplicated evidence items;
- `forums`: number of distinct forums represented;
- `threads`: number of distinct canonical threads;
- `confidence_weighted_intensity`: sum of `intensity × confidence_weight`, where high = 1.0, medium = 0.7, low = 0.4;
- `coverage_adjusted_score` (optional): `confidence_weighted_intensity × min(1, forums / 3)`.

The default color scale is `coverage_adjusted_score`, but the tooltip must show all measures. Never mix raw mention count and weighted intensity without labeling them. Do not use a percentage unless the denominator is explicitly defined.

A cell is a **hotspot** only relative to this collected corpus and selected axes. Prefer language such as “highest concentration in this sample” over “the biggest problem.” Flag cells with fewer than two distinct threads or one forum as low-diversity.

## Visual output

Create a self-contained `research-heatmap.html` with:

- title, research question, retrieval date, and scope;
- axis labels and visible row/column labels;
- color legend with numeric min/max and a text alternative;
- cell tooltip or details panel showing themes, counts, forums, threads, score, and source links;
- a table beneath the chart containing every cell and its metrics;
- an “unverified / unknown” section;
- accessible color contrast and a non-color textual encoding such as score labels or cell text;
- no external scripts, fonts, tracking, or network calls unless the user explicitly asks for them.

Also create:

- `research-heatmap-data.json` — normalized rows, settings, cell metrics, and source references;
- `research-heatmap.csv` — one row per cell, suitable for spreadsheets;
- `research-heatmap-notes.md` — interpretation, scoring formula, exclusions, limitations, and top hotspots.

If a chart library is already available in the project, it may be used, but do not introduce a dependency merely for this output. A plain HTML table plus inline CSS/SVG is the reliable fallback.

## Interpretation template

Use this structure in the notes and response:

```markdown
# Research heatmap notes

## What the map shows
- Corpus:
- Axes:
- Score:
- Retrieval period:

## Highest concentrations in this corpus
1. [Forum × theme] — [score], [mentions], [distinct forums], [distinct threads]

## Diversity and confidence
- High-diversity cells:
- Low-diversity cells:
- Unverified/unknown records:

## Contradictions and caveats
[Explain stance conflicts, duplicate risk, sampling bias, search-ranking bias, date/language effects.]

## Source links
[Canonical URLs grouped by cell]
```

## Integrity and privacy boundary

Do not visualize identifiable individuals, infer sensitive traits, or create a “score” for a person or pseudonymous account. Aggregate at forum/theme/time level. Keep quotes short and link to the public source rather than copying a thread. Treat sentiment as an explicitly coded evidence field, not as a psychological diagnosis. Refuse requests to use the heatmap for targeting, harassment, deanonymization, or evading platform privacy controls.

## Empty and weak inputs

- Empty evidence: produce a clear validation message and a blank template only if useful; never output a misleading empty heatmap.
- One forum or one thread: render it, but label the visualization **single-source / exploratory**.
- Conflicting stances: show mixed/unclear rather than forcing positive or negative.
- Missing dates: retain the row in `unknown_date` and exclude it from time-based axes.
- Too many categories: group only with a stated rule, preserve the raw labels in JSON, and offer a focused view rather than silently truncating.
