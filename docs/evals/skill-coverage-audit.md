# WILQ Skill Coverage Audit

Data: 2026-07-02 05:02 CEST.

Cel: krótka mapa recovery dla WILQ skills po aktualnych evalach. Pełne
przebiegi zostają w `docs/evals/skill-eval-ledger.md`; tutaj trzymamy tylko
decyzję produktową: co działa, co jest review-only, co blokuje BDOS-class
workflow.

Live context at refresh time:

- WILQ API: `ok`.
- Connector inventory: 12 total, 9 configured, 2 with missing credentials.
- Eval coverage gate: `scripts/audit_skill_eval_coverage.py --strict` passed
  with 13 skill cases and 13 skill directories.

## Coverage Table

| Skill | Latest artifact | Score | State | What it proves | Remaining blocker |
| --- | --- | ---: | --- | --- | --- |
| `wilq-daily-command` | `.local-lab/evals/codex-skill/20260702T024250Z/wilq-daily-command/result.json` | 5 | ready / daily loop checked | Uses `/command-center`, `daily_decisions`, `primary_next_step`, Merchant, Content, GA4 and Ads; validates four daily review actions; keeps Localo/social out of the main day plan unless canonical daily view includes them. | Keep daily loop tied to `command_center.daily_decisions`; do not promote Localo/social from broader context. |
| `wilq-ads-doctor` | `.local-lab/evals/codex-skill/20260702T025015Z/wilq-ads-doctor/result.json` | 5 | ready / review-only | Uses full Ads diagnostics/full context, returns five review priorities, validates four Ads review actions and keeps Keyword Planner/forecast blockers explicit. | No CPA/ROAS, wasted-budget, budget scaling, negative-keyword apply or writes without human review, confirmation, write contract and audit. |
| `wilq-merchant-feed-operator` | `.local-lab/evals/codex-skill/20260702T025422Z/wilq-merchant-feed-operator/result.json` | 5 | ready / review-only | Groups feed work by `decision_queue`, treats `product_count` as reported issue occurrences, validates feed issue review, and uses product samples only as review samples. | No product-level ROAS/revenue, price-impact, product reapproval or feed writes without missing contracts and audit. |
| `wilq-ga4-analyst` | `.local-lab/evals/codex-skill/20260702T025826Z/wilq-ga4-analyst/result.json` | 4 | ready / review-only | Separates `fix_measurement` `(not set)` rows from `review_traffic_quality` rows, validates GA4 tracking-quality review and avoids inventing absent `review_landing_mapping` queue items. | No profitability, revenue, conversion-rate, ROAS, GA4 write or "measurement fixed" claims without separate contracts. |
| `wilq-gsc-content-doctor` | `.local-lab/evals/codex-skill/20260702T001627Z/wilq-gsc-content-doctor/result.json` | 4 | ready / partial-data caveats checked | Uses GSC/WordPress evidence, handles Search Analytics date/detail limitations, validates content refresh action and blocks unsupported SEO success claims. | Publication-ready copy still requires inventory/canonical checks, reviewed knowledge and human review. |
| `wilq-content-strategist` | `.local-lab/evals/codex-skill/20260702T023811Z/wilq-content-strategist/result.json` | 4 | ready / anti-slop checked | Plans content from WILQ evidence, handles BDO and `art 400` as refresh/merge, blocks `zielony ład` until evidence/inventory, and treats GA4 measurement rows as not content topics. | Still review-only: no final publish-ready content or WordPress write without approved knowledge, claim ledger and audit. |
| `wilq-content-operator` | `.local-lab/evals/codex-skill/20260701T222739Z/wilq-content-operator/result.json` | 4 | blocked correctly / UAT-prep | Handles stale content workflow decisions as refresh-first blockers and keeps Service Profile/UAT blockers visible. | Full Wilku content UAT still needs owner session or explicit defer with residual risk. |
| `wilq-social-publisher` | `.local-lab/evals/codex-skill/20260702T021742Z/wilq-social-publisher/result.json` | 4 | draft-ready / publish blocked | Converts WILQ-backed insight into reviewable social draft candidates while exposing missing publish access and review-only action state. | LinkedIn/Facebook credentials and publish safety/audit remain missing; no autopublish or social performance claims. |
| `wilq-campaign-builder` | `.local-lab/evals/codex-skill/20260702T021145Z/wilq-campaign-builder/result.json` | 4 | ready / review-only | Builds campaign candidates from Ads/GSC evidence and action contracts, not generic prompt ideas. | No campaign apply, budget scaling or performance promise without Ads apply contracts, confirmation and audit. |
| `wilq-custom-segments` | `.local-lab/evals/codex-skill/20260623T160335Z/wilq-custom-segments/result.json` | 4 | ready / review-only | Uses real Ads source terms and review triage for custom segment candidates. | Audience size, targeting applied, forecast and performance claims remain blocked until Keyword Planner/forecast/apply contracts exist. |
| `wilq-demand-gen-operator` | `.local-lab/evals/codex-skill/20260623T153134Z/wilq-demand-gen-operator/result.json` | 4 | blocked correctly | Detects missing Demand Gen launch/migration/creative evidence and validates readiness review only. | Need real Demand Gen campaign/ad/creative/landing/migration rows before recommendations. |
| `wilq-ahrefs-gap-finder` | `.local-lab/evals/codex-skill/20260624T021206Z/wilq-ahrefs-gap-finder/result.json` | 4 | ready / stale review | Ahrefs authority and typed gap records are usable as review-only SEO context with scoped lineage. | Ahrefs freshness and cross-source joins still limit uplift/authority claims. |
| `wilq-localo-operator` | `.local-lab/evals/codex-skill/20260623T154853Z/wilq-localo-operator/result.json` | 5 | partial / local review-only | Localo access and aggregate visibility/review facts can support local visibility review with validated action state. | GBP performance, competitors, local tasks, writes and visibility uplift remain blocked unless current Localo evidence/action contracts support them. |

## Product Readout

- 13/13 WILQ skills have eval cases and skill directories.
- 13/13 pass the static coverage audit with OpenAI-aligned hard gates:
  evidence/source connector handling, blocked claims, action validation,
  freshness/blocker handling and workflow specificity.
- The strongest current operator path is:
  `wilq-daily-command` -> `/merchant` -> `/ads-doctor` -> `/ga4` ->
  `/content-planner`.
- The strongest content path is not yet "publish": it is review/traceability
  through Content Strategist, Content Operator and Service Profile blockers.
- The weakest product gaps are now above the skill layer: approved Ekologus
  knowledge, Wilku UAT proof, claim-level generation gate, measurement
  provenance and write/apply contracts.

## Guardrail

Do not fix future skill failures by adding edge-case prose to references. If an
eval lacks a useful decision, first check whether WILQ API exposes a typed field
for that decision. If not, add or fix the typed API/dashboard contract, then make
the skill consume it.

`scripts/skill_hygiene_check.py` blocks recovery/artifact prose in skills and
references. Typed API contract fields such as `decision_queue`,
`freshness_assessment`, `readiness.status`, `blocked_claims` and ActionObject
validation remain valid reference material only when they describe existing API
fields.
