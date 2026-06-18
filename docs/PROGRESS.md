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
