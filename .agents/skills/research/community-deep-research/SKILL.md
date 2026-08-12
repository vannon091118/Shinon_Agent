---
name: community-deep-research
description:  "Conduct rigorous, source-traceable research from a Google results page across every relevant public community forum represented there. Use this skill whenever the user asks to investigate forum discussions, community sentiment, recurring problems, product feedback, technical solutions, or “deep research” starting from Google, even if they do not explicitly name this skill. It enumerates forum domains, verifies findings on canonical public pages, separates evidence from inference, and produces a structured report plus machine-readable evidence for downstream analysis."
category: research
stack: LOGISCH + MEMORY
risk: low
side_effects: network_calls
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
compatibility: Requires a browser or web-search/page-reading capability. Do not bypass authentication, CAPTCHAs, paywalls, robots.txt restrictions, or access controls.
---

# Community Deep Research

Turn one Google results page into a defensible map of public community evidence. Within the declared page/forum limits, cover every relevant forum represented on that page. Search-result snippets are discovery leads, not proof. The value of this skill is traceability: another person should be able to follow each claim back to the public thread where it appeared.

## Inputs

Collect or confirm these inputs before researching:

- **Research question**: the exact question and any definitions of important terms.
- **Google source**: a Google results URL, exported results HTML/CSV, screenshot, or a query that can be run with an available search tool.
- **Coverage**: default to every distinct, relevant public forum/domain visible on the supplied results page, within the declared limits; record excluded results and why. Ask before expanding beyond the limits.
- **Depth**: default to one canonical thread/page per relevant result, up to three threads for a forum when the first thread is thin, contradictory, or unusually high-signal.
- **Time window and language**: use the requested values; otherwise state the retrieval date and use the language(s) visible in the results.
- **Limits**: default to 10 distinct forum domains, 3 threads per domain, and 30 total source pages. Ask before exceeding these limits.

If the Google page is unavailable or JavaScript-only tooling cannot render it, do not pretend to have inspected it. Ask for the URL/export/screenshot or state that you are switching to a fresh search and label that change in the provenance record. A supplied SERP export may be parsed as a discovery layer, but its snippets still require canonical-page verification.

## Operating procedure

### 1. Freeze the discovery layer

Record:

- query text, Google result URL, result-page number, filters, and retrieval timestamp;
- each candidate result's title, displayed URL, rank, forum/domain, and snippet;
- whether the result is a thread, category, search page, documentation page, or non-forum page.

Normalize URLs only for comparison. Keep the original URL as provenance. Resolve redirects and prefer the canonical URL (`rel="canonical"`, stable thread ID, or the forum's own permalink).

### 2. Build a forum coverage ledger

Create one row per distinct community/forum, not one row per search result. Classify each as relevant, borderline, or excluded. For every exclusion, record a short reason such as “duplicate mirror,” “not a community discussion,” “private/login required,” or “off-topic.” This makes “every relevant forum” auditable rather than an uncheckable claim.

A forum may be Reddit, Stack Exchange, GitHub Discussions/Issues, a vendor community, Discourse, a mailing-list archive, or another public discussion platform. The coverage claim means every relevant forum within the declared limit, not every forum on the internet. Do not treat a search-engine result page itself as a forum.

### 3. Access public pages responsibly

Before broad access to a domain:

- respect robots.txt and visible terms or crawl guidance;
- use the least number of requests needed, cache pages, and wait at least 1–3 seconds between requests to the same domain when tooling permits;
- honor 429/403 responses and stop or back off rather than retrying aggressively;
- never bypass a login, CAPTCHA, paywall, rate limit, anti-bot mechanism, or deleted/private content.

If a page cannot be accessed, retain the discovery record but mark it **unverified**. A snippet alone cannot support a factual claim.

### 4. Verify and extract evidence

For each accessible canonical thread, read the opening post and enough replies to understand context, disagreement, and resolution. Extract small, necessary quotes only; paraphrase the remainder. For every evidence item record:

- `claim`: a neutral, checkable statement;
- `evidence_type`: problem, solution, experience, request, comparison, disagreement, or meta;
- `quote`: a short quote when useful, otherwise an empty string;
- `context`: what the quote means and what it does not establish;
- `forum`, `thread_title`, `author_handle` (optional, preferably omit), `posted_at`, `retrieved_at`;
- `url`, `locator` (post number, anchor, or visible heading), and `canonical_url`;
- `stance`: positive, negative, mixed, neutral, or unclear; never infer stance from a single ambiguous word;
- `intensity`: 1–5, only when the wording supports it;
- `confidence`: high, medium, or low;
- `limitations`: missing context, deleted replies, translation uncertainty, or likely duplicate/cross-post.

Do not collect or reproduce unnecessary personal data. Preserve usernames only when essential to disambiguate a public expert statement, and otherwise use “community member.” Never infer identity, demographics, or sensitive attributes.

### 5. Synthesize without inflating the evidence

Separate these layers in the report:

1. **Observed**: directly supported by one or more cited public posts.
2. **Corroborated**: independently observed across distinct threads or forums.
3. **Interpretation**: a reasoned synthesis; label it as such.
4. **Unknown**: what the corpus cannot answer.

Count mentions only within the collected corpus. Do not call a theme “most users” or “the market” unless the sampling method supports that claim. Note forum-selection bias, search-ranking bias, language bias, date bias, survivorship bias, and cross-posting.

Explicitly surface contradictions. A disagreement is a finding, not noise to be averaged away. Distinguish “no evidence found” from “evidence of absence.”

### 6. Validate completeness

Before finishing, check:

- every relevant forum/domain from the discovery layer has a ledger row;
- every included claim has a canonical public URL and retrieval timestamp;
- snippets are not used as sole evidence;
- duplicates and cross-posts are flagged;
- inaccessible pages are visibly marked unverified;
- totals in the narrative match the evidence JSON;
- the report states the exact scope and limits.

If a tool fails or the source changes while researching, log the failure and continue only with clearly marked gaps.

## Output contract

Produce both artifacts:

1. `community-research-report.md` — human-readable report.
2. `community-evidence.json` — structured evidence for the `research-heatmap` skill.

Use this report structure:

```markdown
# Community research: [question]

## Scope and provenance
- Google source/query:
- Retrieved:
- Coverage rule and limits:
- Included forums:
- Excluded/unverified sources:

## Executive answer
[Short answer with confidence and the strongest citations.]

## Findings by theme
### [Theme]
- Finding — [forum/thread citation]
- Corroboration or disagreement — [citations]
- Interpretation and limitation:

## Forum coverage ledger
| Forum | Results found | Pages verified | Included? | Reason/gap |

## Evidence gaps and bias

## Sources
[Canonical links with retrieval dates]
```

Use this JSON shape (additional fields are allowed only when they preserve provenance):

```json
{
  "schema_version": "1.0",
  "question": "string",
  "provenance": {
    "google_url": "string",
    "query": "string",
    "retrieved_at": "ISO-8601",
    "result_page": 1,
    "limits": {"max_forums": 10, "max_threads_per_forum": 3, "max_pages": 30}
  },
  "coverage": [
    {
      "forum": "string",
      "domain": "example.org",
      "results_found": 0,
      "pages_verified": 0,
      "status": "included|excluded|unverified",
      "reason": "string"
    }
  ],
  "evidence": [
    {
      "id": "EV-001",
      "claim": "string",
      "theme": "string",
      "evidence_type": "problem|solution|experience|request|comparison|disagreement|meta",
      "quote": "short quote or empty string",
      "context": "string",
      "forum": "string",
      "thread_title": "string",
      "canonical_url": "https://…",
      "locator": "post anchor or heading",
      "posted_at": "ISO-8601 or null",
      "retrieved_at": "ISO-8601",
      "stance": "positive|negative|mixed|neutral|unclear",
      "intensity": 1,
      "confidence": "high|medium|low",
      "duplicate_group": null,
      "limitations": []
    }
  ],
  "synthesis": {
    "themes": [],
    "contradictions": [],
    "unknowns": []
  }
}
```

End with a short handoff: tell the user that `community-evidence.json` can be passed to **research-heatmap** and state whether the heatmap should use forum × theme (default), theme × stance, or another axis.

## Safety and integrity boundary

This skill is for public, permission-respecting research. It must not facilitate harassment, doxxing, deanonymization, credential discovery, bulk profiling of individuals, evasion of platform controls, or republication of large amounts of user-generated content. If the request would require those actions, refuse that portion and offer an aggregated, privacy-preserving alternative.
