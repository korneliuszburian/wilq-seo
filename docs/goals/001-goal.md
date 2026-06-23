# Goal 001 - WILQ Marketing OS Active Goal

Last updated: 2026-06-23 22:56 CEST.

This is the only active goal file. Keep it short and current. Do not append a
chronological work log here. Completed slices belong in git history,
`docs/PROGRESS.md` short ledger or `docs/progress/archive/`.

## Recovery Contract

Every Codex session working on WILQ must read these files first:

1. `AGENTS.md` - operating rules, secrets policy, local paths and gotchas.
2. `docs/goals/001-goal.md` - current active goal and queue.
3. `docs/PROGRESS.md` - compact recovery ledger.
4. `docs/evals/skill-coverage-audit.md` - current 12-skill eval coverage table.
5. `docs/evals/skill-eval-ledger.md` - detailed skill eval evidence.
6. `docs/architecture/bdos-class-wilq-operating-system.md` - product bar.
7. `docs/infra/001.md` - original product scope.
8. `docs/audits/001-output.md` - 2026-06-18 audit and critique.

Update this goal only when active blockers, next tasks or quality rules change.
Do not paste finished logs, command transcripts or old proof blocks here.

## Product Target

Build WILQ as an API-first Marketing Operating System for Ekologus:

- WILQ API is the system brain.
- Dashboard, Codex skills, hooks, workflows, expert rules, opportunities and
  ActionObjects must use the same typed WILQ API contracts.
- The Polish marketer must see decisions, evidence, blocked claims and safe
  next actions, not connector status dumps or raw payloads.
- Codex skills are operator workflows over WILQ API, not prompt packs.
- No recommendation without evidence IDs, source connectors and clear claim
  boundaries.
- No write/apply without validated ActionObject, preview, confirmation and audit.

## Current Product State

Strong Ekologus demo is partially built, not done. Baseline demo surfaces are
tracked in git history, `docs/PROGRESS.md`, route tests and
`docs/evals/skill-coverage-audit.md`; do not keep ready/done surfaces as active
goal tasks. Only reopen a ready surface when fresh browser/API proof shows a
regression.

## Active Demo Backlog

Finish these before claiming the Ekologus demo is done:

1. **Source contracts and data acquisition**
   - Current Localo diagnostics expose live aggregate facts and typed
     read-contract status after a managed stack restart:
     `live_data_available=true`, `visibility_fact_count=17`,
     `act_review_localo_visibility_facts` ready, and `place_inventory`,
     `local_rankings` and `reviews` ready.
   - Localo remaining work is narrower: add `gbp_visibility`,
     `competitor_visibility` and `local_tasks` typed read contracts before
     claiming GBP performance, competitor visibility, local task completion, GBP
     writes or local visibility uplift.
   - If Localo appears empty while `/api/metrics?connector_id=localo` has facts,
     restart via `scripts/local_stack.sh restart` before changing product logic.
   - Current Ads is review-only and intentionally blocks unsupported claims.
   - Current live Ads blockers are not OAuth setup gaps: `change_history` is
     blocked because Google Ads returned zero change_event rows for the current
     window; `keyword_planner_read_contract` is blocked by
     `authorizationError.DEVELOPER_TOKEN_NOT_APPROVED`.
   - Ads remaining source contracts: approved/live Keyword Planner enrichment,
     forecast/audience size, budget pacing, change-history impact context,
     campaign recommendations with safety, impression-share/pacing evidence,
     custom segment apply/audit and negative keyword apply/audit.
   - Merchant remaining source contracts: row-level/product-level payloads where
     available, product performance joins with Ads/GA4 when evidence exists,
     supplemental-feed candidate contracts and price-impact snapshots. Do not
     claim approval restoration, revenue recovery or unique SKU fixes from
     aggregate issue counts.
   - GA4 remaining source contracts: conversion/key-event readiness, ecommerce
     and campaign-to-landing quality evidence before ROAS/revenue/profitability
     claims.

2. **Decision API and view-model quality**
   - Keep `/api/dashboard/command-center`, `/api/marketing/brief`,
     `/api/marketing/tactical-queue`, diagnostics endpoints and `/api/actions`
     as the shared product surface for dashboard and Codex.
   - Each useful surface must expose Polish marketer decisions, evidence IDs,
     source connectors, metric facts, blocked claims, ActionObject IDs and the
     next safe step.
   - Do not promote connector readiness as a marketing decision. Ready means
     the required evidence exists; missing/blocked means the view must explain
     what contract or permission is absent.
   - If a skill or dashboard needs smarter grouping, dedupe, ranking or copy,
     implement it in typed API/schema/view-model first, then make the UI/skill
     consume it.

3. **Action safety and apply path**
   - Current demo is mostly prepare/review-only. This is acceptable for demo,
     but not enough for BDOS-class production writes.
   - Every future write path must be `dry_run -> preview -> confirm -> audit`.
   - Required apply-path work: validation status, payload preview, support
     checks, risk labels, SafetyLimits, partial-failure handling, audit events
     and explicit blocked/destructive state.
   - Do not claim wasted budget, profitability, CPA/ROAS verdicts, budget
     scaling, feed writes, GBP writes, social publishing or campaign apply until
     the matching ActionObject contract exists and is validated.

4. **Codex skills, prompts and eval quality**
   - `scripts/skill_hygiene_check.py` now guards obvious hygiene failures:
     `Goal 001`/workaround/bugfix/outdated/slop prose, English safety headings,
     English `with mode=vendor_read` endpoint notes and English imperative
     workflow steps in WILQ skill docs, plus mixed-language `API identifiers`
     wording in output contracts.
   - Current WILQ `SKILL.md` and `references/output-contract.md` files have
     Polish operator prose with unchanged API IDs, endpoint paths and enum
     values.
   - Current cleanup normalized the repeated language-contract wording across
     WILQ output contracts and removed leftover English GA4/Merchant contract
     fragments.
   - Remaining audit: deeper semantic review of references. References may
     describe API usage, required evidence, output shape and safety rules.
   - References must not become the place for product behavior, workaround
     rules, dashboard cleanup, dedupe decisions, ranking logic or bug fixes.
   - If a skill needs a smarter decision, implement typed API/schema/view-model
     and eval contract first, then make the skill consume it.
   - Current eval coverage proves 12/12 skills can run non-interactively with
     API usage, Polish output, evidence IDs and safety checks. Remaining eval
     work is decision quality: each skill should prove the concrete useful
     decision for its domain, not just output shape.
   - Marketer prompts should be practical Polish commands such as “pokaż
     przestrzeń do poprawy Ads”, “przejrzyj Merchant feed”, “zbuduj kolejkę
     content refresh” and must map to the right skill/context pack.

5. **Dashboard usefulness, performance and code quality**
   - Command Center must stay a decision cockpit, not a connector registry or
     raw metric dump. First screen should prioritize today's marketer decisions,
     prompts to Codex, action focus and source freshness.
   - Dedicated routes may show drilldown details: `/merchant`,
     `/content-planner`, `/ads-doctor`, `/ga4`, `/localo`, `/actions`.
   - Reduce duplicate sections and outdated copy when browser/API proof shows
     confusion.
   - Performance work should target shared daily view-model/cache and route
     split points that reduce repeated heavy aggregation.
   - `App.tsx` shell has been reduced, but large route modules still exist.
   - Do not spend time on aesthetic refactors. Extract only when a file blocks
     product velocity, focused tests, browser QA or reviewability.

6. **Release, staging and live-test strategy**
   - Blocking CI/release tests must verify contracts, schemas, evidence IDs,
     source connectors, secret redaction, ActionObject safety, Polish output and
     no invented metrics.
   - Exact numeric values belong only in deterministic fixtures/seed tests.
     Live Ekologus metrics change over time and must not become flaky release
     assertions.
   - Live smoke checks may assert freshness, nonempty expected facts,
     ready/missing/blocked contract status and correct blocker rendering, not
     exact clicks, reviews, costs or ranking values.
   - Production monitoring should alert on source failures, stale freshness,
     zero facts where a contract is expected, secret leaks or unsafe apply
     attempts. Those are operational alerts, not brittle CI assertions.

## Quality Rules For Remaining Work

- Use focused verification. Do not run broad suites after every tiny edit.
- Run `scripts/verify.sh` only before final handoff, after broad cross-surface
  changes or when a failure pattern suggests shared regression risk.
- For API contract changes, run the affected pytest subset.
- For dashboard route/component changes, run the touched route test plus
  dashboard typecheck/lint when props/types moved.
- For skill changes, run the deterministic smoke and the targeted
  `scripts/codex_skill_eval.sh --skill <skill>` when the harness/schema changed.
- Use subagents for independent audits or implementation slices with disjoint
  files, but merge findings into one plan before editing shared surfaces.
- Keep operator-facing copy Polish with Polish diacritics. Keep endpoint paths,
  IDs, enum values and schema fields unchanged.
- Never commit `.env`, `.local-lab`, traces, screenshots, secrets or protected
  client data.

## Immediate Next Tasks

1. Work in this order unless live proof shows a stronger blocker:
   source contracts -> decision API/view-model -> ActionObject safety -> Codex
   skill/eval quality -> dashboard usefulness/performance -> release/live-test
   hardening.
2. Next concrete slice should be one of:
   - Localo `gbp_visibility` / `competitor_visibility` / `local_tasks` research
     and read-only contract if the MCP/API exposes it.
   - Ads Keyword Planner/developer-token readiness and budget/change-history
     context if Google API state allows it.
   - Semantic skill-reference audit where references are still carrying
     product behavior instead of API contracts.
   - Dashboard performance/shared daily view-model if command-center latency or
     duplicate aggregation blocks demo speed.

## Stop Condition

Goal 001 is not done until the Ekologus marketer can open the dashboard, follow
the daily plan, inspect Ads/Merchant/Content/GA4/Localo decisions, copy/run the
matching Codex skill prompt, and receive Polish evidence-backed recommendations
with safe next actions and blocked claims. The demo must prove real API
evidence, not static artifacts, prompt-only reasoning or mock data.
