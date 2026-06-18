# WILQ Skill Eval Ledger

Ten plik zapisuje realne przebiegi testowania skillów. Każdy wpis ma pokazać,
czy skill faktycznie pomaga polskiemu marketerowi, a nie tylko przechodzi schema
smoke.

## Eval Protocol

For each skill:

1. Use a realistic Polish marketer prompt.
2. Confirm the skill reads its `SKILL.md` and required `references/`.
3. Confirm WILQ API calls happened through allowed endpoints.
4. Capture main evidence IDs, source connectors and ActionObject IDs.
5. Judge output usefulness:
   - Czy odpowiedź mówi po polsku i z polskimi znakami?
   - Czy daje decyzję lub kolejkę działań?
   - Czy blokuje unsupported claims?
   - Czy nie wymyśla metryk?
   - Czy wskazuje konkretny następny krok?
6. Run deterministic smoke and, where possible, non-interactive Codex eval:

```bash
uv run python .agents/skills/<skill>/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
scripts/codex_skill_eval.sh --skill <skill> --api-base http://127.0.0.1:8000
```

## 2026-06-18 - wilq-content-strategist

Prompt:

```text
Użyj skilla wilq-content-strategist. Zbuduj kolejkę content refresh, merge,
create albo block dla Ekologus na podstawie GSC, WordPress, GA4 i Ahrefs
evidence. Nie obiecuj leadów, revenue ani wzrostów pozycji.
```

Observed behavior:

- Skill read `.agents/skills/wilq-content-strategist/SKILL.md`.
- Skill read `references/output-contract.md`.
- Skill checked connector statuses for:
  `google_search_console`, `google_analytics_4`, `ahrefs`,
  `wordpress_ekologus`, `wordpress_sklep`.
- Skill called:
  - `GET /api/content/diagnostics`
  - `POST /api/codex/context-pack` with `{"skill":"wilq-content-strategist"}`
  - `uv run python .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000`
  - `POST /api/actions/act_prepare_content_refresh_queue/validate`
  - `GET /api/actions/act_prepare_content_refresh_queue`
  - `GET /api/marketing/tactical-queue`

Useful output:

- Built a real queue:
  1. refresh BDO page,
  2. merge/create-after-inventory-check for Zielony Ład cluster,
  3. low-priority refresh for homepage/brand,
  4. block GA4 `(not set)` as content task,
  5. block GA4 landing pages without WordPress match until inventory mapping improves.
- Correctly used evidence IDs including:
  `ev_refresh_refresh_google_search_console_554550c44ec7`,
  `ev_refresh_refresh_wordpress_ekologus_25f9090bdfe6`,
  `ev_refresh_refresh_wordpress_sklep_df9826df2137`,
  `ev_refresh_refresh_google_analytics_4_681b6bcefc85`,
  `ev_refresh_refresh_ahrefs_dbd57a972ce1`.
- Correctly validated `act_prepare_content_refresh_queue` as `valid=true`.
- Correctly blocked lead/revenue/ranking promises.
- Correctly identified that GA4 `(not set)` is tracking/attribution, not a
  content recommendation.

Product gaps found:

1. `POST /api/codex/context-pack` was too large for efficient skill operation.
   The first run pulled a huge context and had to narrow it manually.
2. WordPress inventory matching misses URLs visible in GSC/GA4. This weakens
   create/refresh/merge confidence.
3. Ahrefs currently contributes mostly aggregate authority facts, not
   URL/query-level content gap evidence.
4. GA4 landing path to WordPress URL mapping needs a stronger normalizer before
   it can confidently feed content actions.

Verdict:

Useful. The skill produced a marketer-readable queue and blocked unsupported
claims. It should be used as the first reference pattern for the remaining
manual skill evals.

Follow-up implemented:

- Added skill-scoped context-pack behavior for non-daily skills.
- `wilq-content-strategist` context-pack shrank from about 940 KB to 154 KB and
  from about 8.1 s to 2.68 s locally.
- Smoke still passes and now returns only content-adjacent action IDs:
  `act_review_ga4_tracking_quality`,
  `act_prepare_content_refresh_queue`.

Non-interactive Codex eval:

```bash
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 \
  scripts/codex_skill_eval.sh --skill wilq-content-strategist --api-base http://127.0.0.1:8000
```

Result:

```text
passed
artifact: .local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json
trace: .local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/trace.jsonl
```

Eval output facts:

- `language=pl-PL`, `polish_diacritics_present=true`, `api_used=true`.
- Source connectors:
  `google_search_console`, `google_analytics_4`, `ahrefs`,
  `wordpress_ekologus`, `wordpress_sklep`.
- Evidence IDs included:
  `ev_refresh_refresh_google_search_console_554550c44ec7`,
  `ev_refresh_refresh_wordpress_ekologus_25f9090bdfe6`,
  `ev_refresh_refresh_wordpress_ekologus_24cdff62889e`,
  `ev_refresh_refresh_ahrefs_20c8716fd228`,
  `ev_refresh_refresh_google_analytics_4_f7e927dd982b`.
- Action candidate:
  `act_prepare_content_refresh_queue` with `pending_validation`.
- `operator_usefulness_score=4`.
- No safety findings, no allowed endpoint violation.

Quality note:

This eval proves schema discipline, Polish output, WILQ API usage and evidence
grounding. It does not yet prove the richer manual behavior from the first run,
where Codex produced a concrete BDO/Zielony Lad/GA4 block queue. The next
generation of eval cases should require `refresh`, `merge/create-after-
inventory-check` and `block` decision items, not only broad recommendations.

## 2026-06-18 - deterministic smoke suite after scoped context-pack

Command:

```bash
for skill_dir in .agents/skills/wilq-*; do
  # uses smoke_context_pack.py for wilq-daily-command,
  # smoke_skill_contract.py for every other skill
done
```

Result:

```text
12/12 WILQ skill smoke scripts passed
summary artifact: .local-lab/evals/skill-smoke-summary-20260618T093210Z.jsonl
```

Summary:

| Skill | Evidence | Actions | Notes |
| --- | ---: | ---: | --- |
| `wilq-ads-doctor` | 80 | 0 | Live Ads mode, no OAuth repair action in main flow. |
| `wilq-ahrefs-gap-finder` | 80 | 1 | Content refresh action available as adjacent SEO action. |
| `wilq-campaign-builder` | 80 | 2 | Merchant + GA4 prepare actions only; no campaign apply action. |
| `wilq-content-strategist` | 80 | 2 | Content/GA4 actions, scoped context. |
| `wilq-custom-segments` | 80 | 0 | No safe segment ActionObject yet. |
| `wilq-daily-command` | 979 | 5 | Full context intentionally preserved. |
| `wilq-demand-gen-operator` | 80 | 2 | Ads/GA4/Merchant readiness, no Demand Gen write action. |
| `wilq-ga4-analyst` | 80 | 2 | GA4 + content adjacent actions. |
| `wilq-gsc-content-doctor` | 80 | 1 | Content refresh action. |
| `wilq-localo-operator` | 80 | 0 | Access ready, ranking/GBP facts still missing. |
| `wilq-merchant-feed-operator` | 80 | 1 | Merchant feed review action. |
| `wilq-social-publisher` | 80 | 5 | Draft actions exist; publishing remains blocked. |

Next eval need:

- Run `scripts/codex_skill_eval.sh --skill <skill>` for each skill and compare
  final JSON usefulness, not only smoke contract health.

## 2026-06-18 - wilq-merchant-feed-operator

Prompt source:

`docs/evals/cases/wilq-skill-eval-cases.json`, case
`wilq-merchant-feed-operator`.

Non-interactive Codex eval:

```bash
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 \
  scripts/codex_skill_eval.sh --skill wilq-merchant-feed-operator --api-base http://127.0.0.1:8000
```

Result:

```text
passed
artifact: .local-lab/evals/codex-skill/20260618T094236Z/wilq-merchant-feed-operator/result.json
trace: .local-lab/evals/codex-skill/20260618T094236Z/wilq-merchant-feed-operator/trace.jsonl
```

Eval output facts:

- `language=pl-PL`, `polish_diacritics_present=true`, `api_used=true`.
- Source connector: `google_merchant_center`.
- Evidence IDs:
  `ev_refresh_refresh_google_merchant_center_e34029f9f3a7`,
  `ev_connector_google_merchant_center_status`.
- Opportunity ID: `opp_connector_google_merchant_center`.
- Action candidate:
  `act_review_merchant_feed_issues` with `pending_validation`.
- Key live facts surfaced by the skill:
  `product_count=10900`, `issue_count=15`,
  `live_data_available=true`, `blocker_count=0`.
- `operator_usefulness_score=5`.
- No safety findings, no allowed endpoint violation.

Useful output:

- The skill framed Merchant Center as a feed/product evidence review workflow,
  not as an automatic fix.
- The next step points to `/merchant` and validation of
  `act_review_merchant_feed_issues`.
- The answer correctly blocks product data mutation, apply and approval/revenue
  recovery claims until validation and explicit operator approval exist.

Product gaps found:

1. The eval proves the high-level Merchant workflow well, but still does not
   force issue-level clustering such as `availability_updated` or affected
   attribute details. Add stricter case assertions if we want BDOS-level feed
   triage proof.
2. `validation_state=pending_validation` is correct for this harness because it
   does not call `POST /api/actions/act_review_merchant_feed_issues/validate`.
   A future manual eval should include the validation call and record the
   validation result.

Verdict:

Useful and stronger than the first content non-interactive eval. It gives a
clear Polish operator next step backed by Merchant evidence and a safe
ActionObject.

## 2026-06-18 - wilq-ga4-analyst

Prompt source:

`docs/evals/cases/wilq-skill-eval-cases.json`, case `wilq-ga4-analyst`.

Non-interactive Codex eval:

```bash
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 \
  scripts/codex_skill_eval.sh --skill wilq-ga4-analyst --api-base http://127.0.0.1:8000
```

Result:

```text
passed
artifact: .local-lab/evals/codex-skill/20260618T101220Z/wilq-ga4-analyst/result.json
trace: .local-lab/evals/codex-skill/20260618T101220Z/wilq-ga4-analyst/trace.jsonl
```

Eval output facts:

- `language=pl-PL`, `polish_diacritics_present=true`, `api_used=true`.
- Source connector: `google_analytics_4`.
- Evidence IDs included 12 GA4/status IDs, including:
  `ev_refresh_refresh_google_analytics_4_681b6bcefc85`,
  `ev_refresh_refresh_google_analytics_4_a45fa03e453b`,
  `ev_connector_google_analytics_4_status`.
- Opportunity IDs:
  `opp_connector_google_analytics_4`,
  `opp_connector_wordpress_ekologus`.
- Action candidate:
  `act_review_ga4_tracking_quality` with `pending_validation`.
- Key live facts surfaced by the skill:
  `live_data_available=true`, `blocker_count=0`,
  `landing_group_count=10`, `low_engagement_count=0`,
  `wordpress_match_count=0`, plus `active_users=20` and `sessions=30` from the
  current brief context.
- `operator_usefulness_score=4`.
- No safety findings, no allowed endpoint violation.

Useful output:

- The skill correctly treats GA4 as behavior/tracking review, not as direct
  profitability proof.
- It explicitly blocks `ROAS`, `revenue`, `conversion rate`,
  `conversion drop`, attribution verdicts and funnel diagnosis without stronger
  conversion evidence.
- The next step points to `/ga4` and review of
  `act_review_ga4_tracking_quality`.

Product gaps found:

1. The eval is safe and useful, but still not detailed enough for BDOS-class
   GA4 work. It does not force a ranked landing/source/campaign queue, even
   though `ga4_diagnostics` exposes `landing_group_count=10`.
2. `validation_state=pending_validation` is correct for this harness because it
   does not call `POST /api/actions/act_review_ga4_tracking_quality/validate`.
   A future manual eval should include the validation call and record the
   result.
3. The skill should eventually distinguish tracking problems, weak landing
   match and campaign/source issues with a stricter output case. Current eval
   proves safe review, not deep GA4 diagnosis.

Verdict:

Useful as a guardrailed GA4 readiness and behavior-review skill. It is not yet a
deep landing/source/campaign analyst until eval cases require concrete ranked
diagnostic items.

## 2026-06-18 - wilq-gsc-content-doctor

Prompt source:

`docs/evals/cases/wilq-skill-eval-cases.json`, case
`wilq-gsc-content-doctor`.

Non-interactive Codex eval:

```bash
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 \
  scripts/codex_skill_eval.sh --skill wilq-gsc-content-doctor --api-base http://127.0.0.1:8000
```

Result:

```text
passed
artifact: .local-lab/evals/codex-skill/20260618T101550Z/wilq-gsc-content-doctor/result.json
trace: .local-lab/evals/codex-skill/20260618T101550Z/wilq-gsc-content-doctor/trace.jsonl
```

Eval output facts:

- `language=pl-PL`, `polish_diacritics_present=true`, `api_used=true`.
- Source connectors:
  `google_search_console`, `wordpress_ekologus`, `wordpress_sklep`.
- Evidence IDs:
  `ev_refresh_refresh_google_search_console_554550c44ec7`,
  `ev_refresh_refresh_wordpress_ekologus_48a29f72b86c`.
- Opportunity IDs:
  `opp_connector_google_search_console`,
  `opp_connector_wordpress_ekologus`.
- Action candidate:
  `act_prepare_content_refresh_queue` with `pending_validation`.
- Key live facts surfaced by the skill:
  `content_diagnostics.live_data_available=true`,
  `query_page_count=10`, `matched_inventory_count=0`,
  section IDs `content_query_page_matrix`, `content_inventory_match`,
  `content_action_safety`.
- `operator_usefulness_score=4`.
- No safety findings, no allowed endpoint violation.

Useful output:

- The skill correctly turns GSC evidence into a prepare-only content queue
  direction.
- It names the route `/seo-gsc`, `content_diagnostics`, query/page matrix and
  `act_prepare_content_refresh_queue`.
- It blocks ranking uplift, WordPress write/apply and publication claims without
  validation and audit.

Product gaps found:

1. The eval is safe, but too generic for final marketer value. It does not force
   concrete query/URL items such as BDO or Zielony Lad clusters, even though the
   richer manual `wilq-content-strategist` run showed that this is possible.
2. `matched_inventory_count=0` means the current WordPress inventory matching is
   still a blocker for confident refresh/create/merge decisions.
3. Future GSC eval cases should require at least one explicit query/page
   candidate, evidence IDs, and whether it is `refresh`, `merge`, `create` or
   `block`.

Verdict:

Useful as a safe GSC/content readiness and queue-preparation skill. Not yet
strong enough as a standalone SEO operator until evals require concrete
query/page decisions.

## 2026-06-18 - wilq-ads-doctor

Prompt source:

`docs/evals/cases/wilq-skill-eval-cases.json`, case `wilq-ads-doctor`.

Important contract correction:

The old eval case still expected an OAuth/deleted-client blocker and
`act_configure_google_ads_env`. That was stale. Current WILQ API state for Ads
is live campaign-level evidence, not OAuth repair. The eval case and its unit
test now assert the current truth:

- `ads_diagnostics.live_data_available=true`,
- source connector `google_ads`,
- live campaign facts are allowed,
- `search terms`, `CPA`, `ROAS` and `wasted budget` must stay blocked unless
  stronger evidence/read contracts exist,
- no Ads ActionObject is expected in the current main flow.

Non-interactive Codex eval:

```bash
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 \
  scripts/codex_skill_eval.sh --skill wilq-ads-doctor --api-base http://127.0.0.1:8000
```

Result:

```text
passed
artifact: .local-lab/evals/codex-skill/20260618T102132Z/wilq-ads-doctor/result.json
```

Eval output facts:

- `language=pl-PL`, `polish_diacritics_present=true`, `api_used=true`.
- Source connector: `google_ads`.
- Evidence IDs: 32 Ads/status IDs, including
  `ev_connector_google_ads_status` and current Google Ads refresh evidence.
- Opportunity ID: `opp_connector_google_ads`.
- Action candidates: none.
- Key live facts surfaced by the skill:
  `ads_diagnostics.live_data_available=true`,
  latest refresh status `completed`, sections `ads_live_data_status`,
  `ads_campaign_overview`, `ads_search_terms`, `ads_action_safety`, and
  campaign overview facts such as `clicks=3`, `row_count=2` from current
  context.
- `operator_usefulness_score=5`.
- No safety findings, no allowed endpoint violation.

Useful output:

- The skill correctly says what can be claimed from campaign-level evidence.
- It explicitly blocks search-term waste, negative keyword candidates, query
  exclusions, CPA, ROAS and wasted budget without the needed evidence.
- It points the operator to `/ads-doctor` and says not to propose apply/write
  without a validated ActionObject and explicit consent.

Product gaps found:

1. Ads Doctor is useful for campaign-level live review, but it cannot yet be a
   BDOS-class waste/search-term operator until the API exposes search-term read
   contracts, spend/cost/conversion facts and validated Ads ActionObjects.
2. Current `ads_action_safety` still references the old OAuth repair idea in a
   section summary even though no active repair ActionObject is promoted. This
   should be cleaned in a future dashboard/API wording pass if it still appears
   in UI.
3. Future eval cases should force a ranked campaign table and blocked-claim
   matrix, not only generic safe recommendations.

Verdict:

Strong guardrail pass. `wilq-ads-doctor` is currently a safe live campaign
review skill with explicit blockers for unsupported performance claims, not yet
a search-term/ROAS/wasted-budget optimizer.
