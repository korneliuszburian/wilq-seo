# BDOS-Class WILQ Operating System Bar

Last updated: 2026-06-17.

This is the product bar for Goal 001 and the next implementation slices. WILQ is
not a connector dashboard and not a prompt pack. It must become a Polish
marketing operating system where Codex, dashboard, API, skills, expert rules and
ActionObjects all use the same evidence.

BDOS is the closest public Ads-OS reference: account diagnostics, search-term
analysis, campaign creation, dry-run/preview/confirm safety, GAQL protection,
reports, account folders, mutation logs and built-in expert knowledge. WILQ must
match that operating-system discipline, then expand it across Ads, Merchant,
GA4, GSC, Ahrefs, Localo, WordPress and social.

## Research-Backed Operating Principles

| Source | Principle for WILQ |
| --- | --- |
| BDOS.ai public product model | Treat Ads work as command workflows with diagnostics, safe mutations, reporting, account context and expert rules. WILQ copies the operating-system standard, not BDOS internals. |
| Google Ads API Developer Assistant | Treat Ads engineering as a mission-control workflow: intent-level operator request, API/version/schema inspection, GAQL/code validation, read-only execution and diagnostic output before business action. |
| Google Ads API GAQL docs | Ads data must be read through explicit query contracts over resources, attributes, segments and metrics. GAQL is not free text in prompts. |
| Google Ads Query Validator and GAQL rules | WILQ needs a GAQL validation/autofix layer before any Ads read workflow is considered mature. |
| Google Ads mutate docs | Mutations must be modeled as typed operations. WILQ never jumps from recommendation to external write. |
| Google Ads partial failure docs | Bulk operations need partial-failure-aware previews and error surfaces instead of hiding failed operations. |
| ReAct paper | Codex skills should interleave reasoning with API actions, but every action must fetch or validate evidence instead of relying on model memory. |
| Self-RAG paper | WILQ should retrieve only necessary evidence, then critique whether it is sufficient before generating recommendations. |
| WILQ source registry and expert rules | Knowledge belongs in cards/rules/schemas first, then skills and dashboard consume it. Long prompts are not a product foundation. |

Sources:

- BDOS.ai: https://bdos.ai/
- Google Ads API Developer Assistant: https://developers.google.com/google-ads/api/docs/developer-toolkit/what-is-developer-assistant
- Google Ads API Developer Assistant install/use: https://developers.google.com/google-ads/api/docs/developer-toolkit/ai-assistant
- Google Ads Query Language: https://developers.google.com/google-ads/api/docs/query/overview
- Google Ads partial failures: https://developers.google.com/google-ads/api/docs/best-practices/partial-failures
- Google Ads REST mutate: https://developers.google.com/google-ads/api/rest/common/mutate
- ReAct: https://arxiv.org/abs/2210.03629
- Self-RAG: https://arxiv.org/abs/2310.11511

## Non-Negotiable Product Invariants

- Every marketing claim must cite WILQ evidence IDs, source connectors and metric facts.
- Every blocker must say which connector, OAuth scope, API permission, quota, account link or unsupported adapter blocks the work.
- Every write path must be `dry_run -> preview -> confirm -> audit`, even when the first implementation only supports prepare/preview.
- Every ActionObject must show payload preview, validation result, risk, supported/blocked status and audit trail.
- Every dashboard section must be useful for a Polish marketer without reading developer docs.
- Every Codex skill output must be in Polish with Polish diacritics, except stable IDs, schema fields and API enum values.
- No view may show readiness-only state as performance insight.
- No generated Ads, content, social or feed recommendation may be produced from model memory alone.
- No destructive Ads/feed/WordPress/social write is allowed until the action model explicitly supports it.

## Operating Loop

1. Connector read or status probe creates a redacted run.
2. Connector adapter normalizes vendor data into metric facts and evidence IDs.
3. Knowledge compiler links the evidence to playbooks and expert rules.
4. Rule engine creates opportunities with diagnosis, severity, risk and evidence.
5. Action service creates prepare-mode ActionObjects with payload preview.
6. Validator performs schema, GAQL/API, safety-limit and support checks.
7. Dashboard and Codex skills show the same action/evidence state.
8. Human confirms only after preview; WILQ writes an audit event for every apply attempt.

## BDOS-Class Capability Matrix

| Capability | Required Evidence | Metrics/Fields | Dashboard Surface | Skill Surface | ActionObject Path |
| --- | --- | --- | --- | --- | --- |
| Daily account monitoring | Google Ads campaign metrics, change events, conversion status, budget state | cost, conversions, CPA, ROAS, budget pacing, conversion lag, anomaly flags | Command Center, Ads Doctor | `wilq-daily-command`, `wilq-ads-doctor` | Prepare monitoring brief; no external write |
| Monthly review | Ads, GA4, Merchant, GSC, change/audit history | MoM/YoY deltas, CPA/ROAS, revenue, top changes, blockers | Reports/Command Center | future monthly review skill | Prepare report candidate, evidence bundle |
| Search-term waste | Search term view, campaign/ad group context, conversion metrics | spend, clicks, conversions, CPA/ROAS, match type, n-grams | Ads Doctor Search Terms | `wilq-ads-doctor` | Negative keyword candidate with 90-day safety check |
| Search-term n-gram | Search terms, 1/2/3-gram grouping, conversion protection window | n-gram spend, conversion absence, query count, protected terms | Ads Doctor Search Terms | `wilq-custom-segments`, `wilq-ads-doctor` | Negative/campaign insight candidate |
| Keyword research | Keyword Planner, existing account keywords, GSC queries | avg monthly searches, CPC, competition, 12-month trend, duplication | Ads Doctor Keyword Planner, Content Planner | `wilq-campaign-builder`, `wilq-content-strategist` | Keyword/ad group/content brief candidate |
| Custom segments | Search terms, Keyword Planner, existing campaigns | term clusters, accepted/rejected terms, source evidence | Ads Doctor Custom Segments | `wilq-custom-segments` | Custom segment candidate, prepare-only |
| Bidding analysis | Campaign bidding strategy, conversion volume, budget limits, impression share | CPA/ROAS, learning state, lost IS budget/rank, target changes | Ads Doctor Bidding | `wilq-ads-doctor` | Bid strategy review candidate |
| PMax product analysis | Ads PMax retail metrics, Merchant products, GA4 revenue | product cost, conversions, revenue, ROAS, disapprovals, availability | Merchant, Ads Doctor PMax | `wilq-merchant-feed-operator` | Product/feed/title candidate |
| PMax channel analysis | PMax channel reporting where available, GA4, Merchant | spend by channel, ROAS, engaged-view caveat, asset/channel flags | Ads Doctor PMax Channels | `wilq-demand-gen-operator` | Diagnosis only until write support |
| Product bucketing | Product-level Ads/Merchant/GA4 evidence | Platinum/Gold/Silver/Bronze buckets, ROAS, margin proxy, volume | Merchant Bucketing | `wilq-merchant-feed-operator` | Campaign/feed segmentation candidate |
| Feed optimization | Merchant product data, PMax/Shopping terms, Keyword Planner | missing terms, title match, feed issue, projected search demand | Merchant Feed Queue | `wilq-merchant-feed-operator` | Supplemental feed candidate, primary feed untouched |
| Price-impact analysis | Merchant price snapshots, Ads/GA4 before-after windows | 7d before/after ROAS, conversion rate, revenue, flip-flop/promo flags | Merchant Price Impact | future price analyst skill | Diagnosis only until pricing write model exists |
| Merchant review | Merchant product statuses, issues, data sources, free listings | disapprovals, expiring items, issue severity, affected products | Merchant Review | `wilq-merchant-feed-operator` | Product/feed issue action candidate |
| GA4 campaign analyst | GA4 campaign/source/medium and Ads campaign mapping | sessions, engagement, key events, conversion path, landing quality | GA4, Ads Doctor | `wilq-ga4-analyst` | Landing/tracking/content candidate |
| GA4 data analyst | GA4 ecommerce and behavior reports | product revenue, funnel, retention, acquisition, events | GA4 Reports | `wilq-ga4-analyst` | Analysis/report candidate |
| GSC content doctor | GSC query/page matrix, WordPress inventory | clicks, impressions, CTR, position, decay, near-top, cannibalization | SEO/GSC, Content Planner | `wilq-gsc-content-doctor` | Refresh/merge/create candidate |
| Ahrefs gap finder | Ahrefs competitors/backlinks/keywords plus inventory | competitor terms, backlinks, DR context, content gaps | Ahrefs, Content Planner | `wilq-ahrefs-gap-finder` | Content/link opportunity candidate |
| Localo visibility | Localo/GBP evidence, competitors, tasks | local rank, GBP task state, competitor gap, review blocker | Localo | `wilq-localo-operator` | GBP/local task candidate |
| WordPress inventory | WordPress pages/posts/products, freshness, metadata | object counts, stale pages, target URLs, content type | Content Inventory | `wilq-content-strategist` | Draft/update candidate |
| Social publisher | Evidence-backed claims, source content, permission state | source evidence, channel, post type, approval status | Social Publisher | `wilq-social-publisher` | LinkedIn/Facebook post candidate |
| Campaign creation | Keyword Planner, business brief, landing pages, budgets, constraints | budget, campaign type, geo, keywords, assets, sitelinks | Campaign Builder | `wilq-campaign-builder` | Campaign payload preview, dry-run only |
| Change history | Google Ads change events, WILQ audit log | who, what, when, before/after labels | Audit/Reports | Ads Doctor, Daily Command | Audit summary |

## What The Dashboard Must Show

### Command Center

- Top daily blockers with freshness and next action.
- Money leaks ordered by estimated waste, not connector order.
- Traffic wins from Ads/GSC/Ahrefs/GA4 evidence.
- Content and product queues with action candidates.
- OAuth/API/permission blockers with exact next step.
- Cross-surface evidence links, not isolated cards.

### Ads Doctor

- Account health: conversion tracking, budget pacing, anomalies, change events.
- Spend waste: search terms, n-grams, broad match, geo gaps, low-value placements where supported.
- Quality: quality score components, RSA/ad strength, landing alignment.
- Recommendations: Google Ads recommendation type, optimization score context, accept/reject rationale.
- Bidding/scaling: target CPA/ROAS, budget caps, impression share lost to budget/rank.
- PMax/Demand Gen: separate reporting models, product/channel/asset readiness, no Search-only assumptions.
- Actions: negative keyword candidates, campaign build previews, custom segment candidates, Demand Gen plans.

### Merchant

- Product/feed health: product count, disapprovals, expiring items, feed/data-source state.
- Product performance: product cost/revenue/ROAS where Ads/GA4 allow.
- Feed optimization queue: evidence-backed title/feed candidates, supplemental feed preference.
- Price-impact queue: only after price snapshots exist.

### GA4

- Campaign traffic quality: sessions, engagement, key events, source/medium and campaign mapping.
- Landing quality: landing path, engagement, conversion path and measurement gaps.
- Ecommerce/product views where available.

### SEO/GSC/Ahrefs/WordPress

- Query/page matrix: clicks, impressions, CTR, position, decay and near-top wins.
- Inventory protection: refresh/merge before new content, duplicate avoidance.
- Ahrefs gap opportunities only after checking existing inventory.

### Social/Local

- Social post candidates grounded in source evidence and permission status.
- Localo/GBP moves only when Localo evidence exists; otherwise exact blocker.

## Safety Model

WILQ safety must be stricter than a chat assistant:

- GAQL validator before live query execution.
- Query contracts per workflow; no arbitrary GAQL from model output in apply paths.
- `validate_only`/dry-run equivalents before every supported mutate.
- Preview includes full payload, diff/risk, evidence, validation status and rollback/blocked notes.
- Confirm requires explicit user approval and writes audit event.
- SafetyLimits block deletions, destructive bulk edits, unsupported writes and budget jumps above configured thresholds.
- Bulk operations must surface per-operation partial failures.
- Every applied Ads change should carry a transparent WILQ/BDOS-style label once write support exists.

## Research-To-Implementation Requirements

Before any new route or skill is called useful:

- API endpoint exists and returns typed evidence.
- Connector vendor_read exists or a precise blocker is shown.
- Expert rule or knowledge card maps evidence to diagnosis.
- Dashboard shows metric facts, evidence IDs and ActionObject candidates.
- Codex skill eval proves Polish output, evidence IDs, API use, no invented metrics and safe ActionObject behavior.
- Browser proof shows the same evidence/action state visible to the marketer.

## Immediate Next Slices

1. Finish Google Ads OAuth consent and prove live `google_ads vendor_read`.
2. Expand Google Ads read adapter from campaign summary to a capability-oriented read pack:
   - campaign overview,
   - search terms,
   - recommendations,
   - quality/asset indicators,
   - change events,
   - budget/impression share,
   - PMax/Demand Gen capability blockers.
3. Add `ads_diagnostics` API view model that joins metric facts, evidence, rules and action candidates.
4. Replace generic `/ads-doctor` route with this view model.
5. Add non-interactive Codex eval cases for wasted spend, negative keyword refusal, campaign build preview and OAuth blocker.
6. Repeat the same pattern for Merchant and GA4 before expanding visual dashboard polish.

## Slop Rejection Checklist

Reject a slice if any of these are true:

- It shows connector status as a marketing insight.
- It creates a dashboard card without metric/evidence/action meaning.
- It suggests an Ads/feed/content/social action without evidence IDs.
- It hides OAuth/API blockers behind generic “not configured” text.
- It puts business rules only in a skill prompt.
- It adds a route before the API view model exists.
- It claims “BDOS-like” while missing validation, preview, confirmation, audit or safety checks.
