# WILQ Skill Coverage Audit

Data: 2026-06-23 18:18 CEST.

Cel: jedna krótka mapa stanu 12 WILQ skillów po najnowszych evalach. Pełne
przebiegi zostają w `docs/evals/skill-eval-ledger.md`; tutaj trzymamy tylko
decyzję produktową: co działa, co jest review-only, co blokuje demo.

## Coverage Table

| Skill | Latest artifact | Score | State | What it proves | Remaining blocker |
| --- | --- | ---: | --- | --- | --- |
| `wilq-daily-command` | `.local-lab/evals/codex-skill/20260623T161009Z/wilq-daily-command/result.json` | 5 | ready | Cross-surface daily loop uses `/command-center`, `daily_decisions`, Merchant, Content, GA4 and Ads. | Keep Localo/social out of daily action candidates unless canonical daily view includes them. |
| `wilq-ads-doctor` | `.local-lab/evals/codex-skill/20260623T130149Z/wilq-ads-doctor/result.json` | 5 | ready / review-only | Live Ads reads, campaign/search-term/recommendation review and validated review ActionObjects. | No profitability, wasted-budget, CPA/ROAS verdicts or apply without business context, targets, confirmation and audit. |
| `wilq-merchant-feed-operator` | `.local-lab/evals/codex-skill/20260623T144931Z/wilq-merchant-feed-operator/result.json` | 5 | ready / review-only | Merchant decision queue, freshness, product-sample readiness and validated feed issue review. | No feed writes, approval restoration, revenue recovery or unique-product counts without row-level payload/audit contracts. |
| `wilq-gsc-content-doctor` | `.local-lab/evals/codex-skill/20260623T150248Z/wilq-gsc-content-doctor/result.json` | 5 | ready | GSC/WordPress scoped decision queue without Ahrefs leakage. | Still needs publication-quality content payloads after inventory/duplicate checks. |
| `wilq-localo-operator` | `.local-lab/evals/codex-skill/20260623T154853Z/wilq-localo-operator/result.json` | 5 | partial / blocked claims | Localo MCP access, aggregate visibility/reviews facts and validated visibility review ActionObject. | GBP performance, competitors, local tasks, writes and uplift claims remain blocked. |
| `wilq-content-strategist` | `.local-lab/evals/codex-skill/20260623T155420Z/wilq-content-strategist/result.json` | 4 | ready / stale-aware | Uses `content_diagnostics.decision_queue`, freshness and content decisions such as Zielony Ład and BDO. | Needs fresher source reads and inventory checks before publish-ready briefs. |
| `wilq-campaign-builder` | `.local-lab/evals/codex-skill/20260623T154147Z/wilq-campaign-builder/result.json` | 4 | ready / review-only | Builds campaign candidates from Ads plus GSC landing context, not generic prompts. | No campaign apply, budget scaling or performance promise without stronger Ads safety/apply contracts. |
| `wilq-custom-segments` | `.local-lab/evals/codex-skill/20260623T160335Z/wilq-custom-segments/result.json` | 4 | ready / review-only | Uses real Ads `source_terms`, `review_priority`, `review_score` and `review_reason`. | Audience size, targeting applied, ROAS and campaign-performance claims remain blocked until forecast/apply contracts exist. |
| `wilq-ga4-analyst` | `.local-lab/evals/codex-skill/20260623T141114Z/wilq-ga4-analyst/result.json` | 4 | ready / review-only | GA4 decision samples expose active users, sessions, engagement and measurement-vs-quality decisions. | Conversion readiness, ROAS/revenue and tracking-fixed claims remain blocked. |
| `wilq-demand-gen-operator` | `.local-lab/evals/codex-skill/20260623T153134Z/wilq-demand-gen-operator/result.json` | 4 | blocked correctly | Detects that no Demand Gen launch/migration/creative evidence exists; validates readiness review only. | Need actual Demand Gen campaign/ad/creative/landing/migration rows before recommendations. |
| `wilq-ahrefs-gap-finder` | `.local-lab/evals/codex-skill/20260623T151121Z/wilq-ahrefs-gap-finder/result.json` | 4 | ready / stale review | Ahrefs authority and gap records are usable as review-only SEO context. | Freshness is stale; no traffic uplift or authority improvement claims. |
| `wilq-social-publisher` | `.local-lab/evals/codex-skill/20260623T152228Z/wilq-social-publisher/result.json` | 4 | draft-ready / publish blocked | Converts WILQ evidence into LinkedIn/Facebook draft candidates and validates draft ActionObjects. | Publishing remains blocked by permissions and publish safety/audit requirements. |

## Product Readout

- 12/12 WILQ skills have current non-interactive eval artifacts.
- 12/12 return Polish operator output, call WILQ API and have zero safety findings.
- 9/12 are useful as ready or review-only workflows.
- 3/12 are intentionally blocked or partial: Localo, Demand Gen and social publishing.
- The strongest demo path today is:
  `wilq-daily-command` -> `/merchant` -> `/content-planner` -> `/ads-doctor` -> optional `/ga4`.
- The next product slice should move from skill proof to dashboard/API value.
  Best candidate: Ads business-context guardrails and apply-preview safety,
  because the daily loop and Ads Doctor already expose real Ads data but still
  block profitability, wasted-budget, CPA/ROAS and budget decisions.

## Guardrail

Do not fix future skill failures by adding edge-case prose to references. If an
eval lacks a useful decision, first check whether WILQ API exposes a typed field
for that decision. If not, add or fix the typed API/dashboard contract, then make
the skill consume it.
