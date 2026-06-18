# WILQ Progress Ledger

Aktualizuj ten plik przy istotnym postępie, zmianie blockerów albo wyniku
testu skilla. Nie rób tu pełnego changeloga; szczegóły ma mieć Git i test
artifacts.

## Current Snapshot

Data: 2026-06-18

- API działa lokalnie: `http://127.0.0.1:8000`.
- Dashboard działa lokalnie: `http://127.0.0.1:5173/command-center`.
- `/api/marketing/brief` został zawężony do marketer decision brief:
  `what_we_know=6`, `what_blocks_us=0`, `safe_next_actions=3`,
  `recommended_focus=2`.
- Brief nie promuje już LinkedIn/Facebook/Sheets jako globalnych blockerów.
- Brief pokazuje tylko core działania:
  `act_review_merchant_feed_issues`,
  `act_review_ga4_tracking_quality`,
  `act_prepare_content_refresh_queue`.
- `/api/dashboard/command-center` po restarcie zwraca `sections={}` i action
  plan bez Localo status-only taska:
  `plan_review_merchant_feed_issues`,
  `plan_prepare_content_refresh_queue`,
  `plan_review_ga4_landing_quality`,
  `plan_review_ads_campaign_metrics`.
- Localo access działa na poziomie MCP initialize, ale ranking/GBP/competitor
  facts nadal są blocked.

## Latest Verified Checks

- `uv run ruff check apps/api/wilq_api/main.py wilq/briefing/command_center.py tests/test_api_contracts.py`
- `uv run mypy apps/api/wilq_api/main.py wilq/briefing/command_center.py`
- `uv run pytest tests/test_api_contracts.py::test_command_center_returns_valid_shape tests/test_api_contracts.py::test_command_center_exposes_polish_operator_brief tests/test_api_contracts.py::test_command_center_treats_localo_mcp_initialize_as_access_ready -q`
- `uv run ruff check wilq/briefing/marketing_brief.py tests/test_api_contracts.py`
- `uv run mypy wilq/briefing/marketing_brief.py`
- `uv run pytest tests/test_api_contracts.py::test_marketing_brief_aggregates_metric_facts_and_blockers tests/test_api_contracts.py::test_marketing_brief_exposes_metric_backed_prepare_actions -q`
- `CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-content-strategist --api-base http://127.0.0.1:8000`

Full `scripts/verify.sh` is still pending after the latest changes.

Update after final gate:

```text
scripts/verify.sh passed
backend API contracts: 90 passed
dashboard route tests: 12 passed
Playwright e2e: 8 passed
dashboard production build: passed
```

## Current Gaps

1. Every WILQ skill must be tested against a real Polish marketer prompt and
   logged in `docs/evals/skill-eval-ledger.md`.
2. `scripts/codex_skill_eval.sh` exists, but current cases are still mostly
   smoke/schema oriented. They need richer usefulness scoring per skill.
3. `POST /api/codex/context-pack` is very large and expensive because it embeds
   many broad surfaces at once. This is a likely source of Codex skill latency.
4. `GET /api/dashboard/command-center` still computes several diagnostics and
   tactical queue data live. It is faster than the old baseline but should move
   toward a lightweight decision view model/cache.
5. Content workflow gap: WordPress inventory matching misses several URLs that
   GSC/GA4 see. This forces create/refresh/block uncertainty.

## Performance Snapshot

Measured locally on 2026-06-18 before skill-scoped context-pack:

```text
/api/dashboard/command-center    3.217814 s    23790 bytes
/api/marketing/brief             0.640781 s    25392 bytes
/api/content/diagnostics         1.062442 s    91342 bytes
/api/marketing/tactical-queue    0.450769 s    82420 bytes
/api/codex/context-pack          9.152960 s    940864 bytes
```

Main causes:

- `context-pack` embeds broad product state for every skill, including 979
  `evidence_summaries`, 10 refresh runs, command center, marketing brief,
  tactical queue and multiple full diagnostic responses.
- `command-center` builds several diagnostic surfaces and tactical queue live.
- Skill runs often fetch both narrow diagnostics and the huge context-pack,
  causing repeated work.

Next performance direction:

- Add skill-scoped context-pack modes that return only the diagnostics,
  evidence IDs, ActionObjects and knowledge cards needed by the selected skill.
- Keep full context-pack for deep debug only.
- Add timing/size assertions for `context-pack` and Command Center after the
  view model is narrowed.

After adding skill-scoped `POST /api/codex/context-pack` for
`wilq-content-strategist`:

```text
full pre-scope context-pack       8.106033 s    940864 bytes
scoped content context-pack       2.679348 s    154334 bytes
```

Scoped content pack now includes:

- `content_diagnostics`,
- 5 relevant connector statuses,
- 80 evidence summaries,
- 2 action objects:
  `act_review_ga4_tracking_quality`,
  `act_prepare_content_refresh_queue`,
- 4 content-adjacent opportunities,
- no `command_center`,
- no `ads_diagnostics`,
- no social ActionObjects.

Smoke after the change:

```bash
uv run python .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
```

Result: passed with `content_live=True`, `query_page_count=10`.

## Skill Smoke Snapshot

2026-06-18 deterministic smoke after skill-scoped context-pack:

```text
12/12 WILQ skill smoke scripts passed
summary artifact: .local-lab/evals/skill-smoke-summary-20260618T093210Z.jsonl
```

Notable contract corrections:

- `wilq-ads-doctor` smoke now allows live Ads mode without OAuth repair
  ActionObject. If Ads `live_data_available=false`, OAuth blocker ActionObject
  is still required.
- `wilq-daily-command` smoke now treats `demo_script=[]` as valid and checks
  `action_plan` as the marketer workflow source.

Current scoped context behavior:

- Daily command still gets full context because it is the operating brief.
- Other skills get skill-scoped context with narrower connectors, evidence,
  opportunities, actions and diagnostics.
- Several skills correctly return zero ActionObjects because current WILQ API
  has evidence/readiness but no safe prepare action for that workflow yet.

## Next Best Slice

Run skill evals one by one:

1. Manual prompt through Codex Desktop/CLI.
2. Deterministic smoke script.
3. `scripts/codex_skill_eval.sh --skill <skill> --api-base http://127.0.0.1:8000`.
4. Record prompt, endpoints, evidence IDs, useful output, hallucination risks
   and product gaps in `docs/evals/skill-eval-ledger.md`.

First non-interactive Codex eval completed:

```text
skill: wilq-content-strategist
result: passed
artifact: .local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json
```

Interpretation: the current harness proves Polish output, API usage, evidence
IDs, source connectors and safety discipline. It still needs stricter
usefulness assertions that force concrete decision queues like refresh,
merge/create-after-inventory-check and block.

Recovery note: full pipeline instructions now live in `docs/CONTEXT.md` under
`Skill Eval Pipeline`. Do not reconstruct the process from chat history. Next
recommended eval target: `wilq-merchant-feed-operator`, because it has a real
Merchant ActionObject (`act_review_merchant_feed_issues`) and high demo value.

Second non-interactive Codex eval completed:

```text
skill: wilq-merchant-feed-operator
result: passed
artifact: .local-lab/evals/codex-skill/20260618T094236Z/wilq-merchant-feed-operator/result.json
```

Interpretation: this is a strong pass. It returned `pl-PL`, evidence IDs,
`google_merchant_center`, live Merchant facts (`product_count=10900`,
`issue_count=15`), and `act_review_merchant_feed_issues` as a safe
pending-validation review ActionObject. Next stricter improvement: force
issue-level clustering and validation-call proof.

Third non-interactive Codex eval completed:

```text
skill: wilq-ga4-analyst
result: passed
artifact: .local-lab/evals/codex-skill/20260618T101220Z/wilq-ga4-analyst/result.json
```

Interpretation: safe and useful pass. It returned `pl-PL`, GA4 evidence IDs,
`google_analytics_4`, `act_review_ga4_tracking_quality`, and correctly blocked
ROAS/revenue/conversion claims without stronger evidence. Next stricter
improvement: force ranked landing/source/campaign diagnostic items and
validation-call proof.

Fourth non-interactive Codex eval completed:

```text
skill: wilq-gsc-content-doctor
result: passed
artifact: .local-lab/evals/codex-skill/20260618T101550Z/wilq-gsc-content-doctor/result.json
```

Interpretation: safe pass. It returned `pl-PL`, GSC/WordPress source
connectors, evidence IDs, `content_diagnostics.live_data_available=true`,
`query_page_count=10`, `matched_inventory_count=0`, and
`act_prepare_content_refresh_queue`. Next stricter improvement: force concrete
query/page candidates with `refresh`, `merge`, `create` or `block` decisions.

Fifth non-interactive Codex eval completed:

```text
skill: wilq-ads-doctor
result: passed
artifact: .local-lab/evals/codex-skill/20260618T102132Z/wilq-ads-doctor/result.json
```

Interpretation: strong guardrail pass. The eval case was corrected away from
the stale OAuth/deleted-client blocker. Current Ads truth is
`ads_diagnostics.live_data_available=true`, source connector `google_ads`,
32 evidence IDs, and no active Ads ActionObject in the main flow. The skill
allows live campaign-level facts, but blocks `search terms`, `CPA`, `ROAS` and
`wasted budget` without stronger evidence/read contracts. Next stricter
improvement: force a ranked campaign table and blocked-claim matrix.

Sixth non-interactive Codex eval completed:

```text
skill: wilq-localo-operator
result: passed
artifact: .local-lab/evals/codex-skill/20260618T102743Z/wilq-localo-operator/result.json
```

Interpretation: strong guardrail pass. The eval case was corrected away from
the stale missing-`LOCALO_ACCESS_TOKEN` blocker. Current Localo truth is access
readiness only: connector `localo` is configured, Localo refresh is completed,
`localo_metric_summary.api=localo_mcp_oauth_probe`, and
`mcp_initialize_status=200`. The skill correctly returns `blocked=true` for
ranking, GBP, competitor and local visibility uplift claims because those facts
do not exist yet in WILQ evidence. Next stricter improvement: add a real Localo
diagnostics/read contract before expecting local SEO recommendations.

Seventh non-interactive Codex eval completed:

```text
skill: wilq-daily-command
result: passed
artifact: .local-lab/evals/codex-skill/20260618T103758Z/wilq-daily-command/result.json
```

Interpretation: strong daily-loop pass. It returned `pl-PL`, all 8 expected
source connectors, daily evidence IDs, primary opportunities, and a concrete
next step: open `/merchant` and validate `act_review_merchant_feed_issues`.
The answer correctly treats Ads as live campaign review, Localo as access-ready
but no ranking/GBP facts, and blocks unsupported claims. Product gap found:
daily action candidates still include LinkedIn/Facebook draft ActionObjects
from wider `marketing_brief.action_ids`, while `CommandCenter.action_plan` is
cleaner and has only Merchant/Content/GA4 core actions.

Eighth non-interactive Codex eval completed:

```text
skill: wilq-campaign-builder
result: passed
artifact: .local-lab/evals/codex-skill/20260618T104154Z/wilq-campaign-builder/result.json
```

Interpretation: safe blocker pass. It returned `pl-PL`, `api_used=true`,
required connectors `google_ads`, `google_analytics_4`,
`google_search_console`, and 3 evidence IDs. It correctly sets `blocked=true`
because WILQ does not expose a campaign-specific ActionObject, payload preview,
keywords, assets, budget or campaign structure. Next product slice for this
skill is not prompt polish; it is an API/action contract for safe campaign
drafts.

Ninth non-interactive Codex eval completed:

```text
skill: wilq-custom-segments
result: passed
artifact: .local-lab/evals/codex-skill/20260618T104644Z/wilq-custom-segments/result.json
```

Interpretation: anti-hallucination pass. It returned `pl-PL`, `api_used=true`,
connectors `google_ads` and `google_search_console`, and `blocked=true`.
Recommendations and action candidates are empty because WILQ currently exposes
aggregate Ads/GSC metrics, not real source terms/search terms/query evidence
for audience candidates. Next product slice: source-term read contract with
evidence lineage.

Tenth non-interactive Codex eval completed:

```text
skill: wilq-demand-gen-operator
result: passed
artifact: .local-lab/evals/codex-skill/20260618T105005Z/wilq-demand-gen-operator/result.json
```

Interpretation: safe but shallow guardrail pass. It returned `pl-PL`,
`api_used=true`, Ads/GA4/Merchant connectors, `blocked=true`, and
`operator_usefulness_score=3`. The skill correctly refuses Demand Gen
recommendations because WILQ has aggregate Ads/GA4/Merchant readiness, but no
asset, creative, landing-quality or migration diagnostics. Next product slice:
Demand Gen diagnostics/read contract plus Demand Gen-specific ActionObject.

Eleventh non-interactive Codex eval completed:

```text
skill: wilq-ahrefs-gap-finder
result: passed
artifact: .local-lab/evals/codex-skill/20260618T105335Z/wilq-ahrefs-gap-finder/result.json
```

Interpretation: safe but shallow guardrail pass. It returned `pl-PL`,
`api_used=true`, connectors `ahrefs`, `google_search_console`,
`wordpress_ekologus`, and `blocked=true` with `operator_usefulness_score=3`.
The skill blocks backlink/competitor/content gap claims because WILQ currently
exposes aggregate Ahrefs authority metrics and adjacent GSC/WordPress facts, not
specific gap records. Next product slice: Ahrefs competitor/backlink/content
gap read contracts with evidence IDs.

Twelfth non-interactive Codex eval completed:

```text
skill: wilq-social-publisher
result: passed
artifact: .local-lab/evals/codex-skill/20260618T105649Z/wilq-social-publisher/result.json
```

Interpretation: strong safety pass. It returned `pl-PL`, `api_used=true`,
connectors `linkedin` and `facebook`, `blocked=true`, and
`operator_usefulness_score=5`. The skill exposes draft ActionObjects
`act_prepare_linkedin_social_drafts` and `act_prepare_facebook_social_drafts`,
but blocks them because social credentials and validation are missing. It does
not publish, does not call write/apply, and does not pretend permissions exist.

## Current Skill Eval Coverage

12/12 WILQ skills now have recorded non-interactive Codex evals.

The eval pass proves guardrails and API integration, not full product
completion. Highest-priority implementation fixes from the eval series:

1. Filter social draft ActionObjects out of daily primary action candidates.
2. Add Ads search-term/spend/conversion read contracts.
3. Add campaign-specific ActionObject + payload preview contracts.
4. Add source-term evidence for custom segments.
5. Add Localo ranking/GBP/competitor facts.
6. Add Ahrefs competitor/backlink/content gap records.
7. Add Demand Gen asset/creative/landing-quality diagnostics.
8. Upgrade evals from schema/safety checks to strict usefulness checks.

## Daily Social Action Filtering

Implemented the first eval-driven cleanup after 12/12 skill eval coverage.

Result:

- `/api/actions` still exposes `act_prepare_linkedin_social_drafts` and
  `act_prepare_facebook_social_drafts` for the explicit `/social-publisher`
  workflow.
- `/api/marketing/brief` no longer includes social draft ActionObjects in
  top-level daily `action_ids`.
- `POST /api/codex/context-pack` for `wilq-daily-command` now exposes only core
  daily `active_action_objects`.
- `POST /api/codex/context-pack` for `wilq-social-publisher` still includes
  the social draft ActionObjects.

Focused proof:

```bash
uv run ruff check apps/api/wilq_api/main.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
uv run mypy apps/api/wilq_api/main.py wilq/briefing/marketing_brief.py
uv run pytest tests/test_api_contracts.py -q -k 'marketing_brief_exposes_metric_backed_prepare_actions or codex_context_pack_embeds_marketing_brief_contract or daily_context_pack_excludes_social_draft_action_objects or social_context_pack_keeps_explicit_social_draft_action_objects or command_center_exposes_polish_operator_brief'
uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
```

Live API note: the previously running `uvicorn` process did not use `--reload`,
so the first smoke still showed stale social action IDs. Restarted WILQ API on
`127.0.0.1:8000`; the repeated smoke returned only the three core daily actions.

## Localo Command Center Demotion

Cleaned the next Command Center readiness-only card.

Result:

- Current Localo state is configured/access-ready, not an OAuth/access blocker.
- Access-ready Localo no longer appears in primary `/api/dashboard/command-center`
  `operator_brief`, because WILQ still has no ranking/GBP/competitor facts.
- If Localo credentials are actually missing, Command Center still keeps a
  `daily_localo_readiness` blocker card.
- `/localo` remains the place for Localo readiness/access status until WILQ has
  a concrete local visibility read contract.

Focused proof:

```bash
uv run ruff check wilq/briefing/command_center.py tests/test_api_contracts.py
uv run mypy wilq/briefing/command_center.py
uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief or command_center_demotes_localo_access_ready_without_visibility_facts or command_center_keeps_localo_access_blocker_in_primary_brief'
```
