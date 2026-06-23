# Goal 001 - WILQ Marketing OS Active Goal

Last updated: 2026-06-23 22:24 CEST.

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

1. **Localo beyond aggregate read contracts**
   - Current Localo diagnostics expose live aggregate facts and typed
     read-contract status after a managed stack restart:
     `live_data_available=true`, `visibility_fact_count=17`,
     `act_review_localo_visibility_facts` ready, and `place_inventory`,
     `local_rankings` and `reviews` ready.
   - Remaining Localo work is narrower: add `gbp_visibility`,
     `competitor_visibility` and `local_tasks` typed read contracts before
     claiming GBP performance, competitor visibility, local task completion, GBP
     writes or local visibility uplift.
   - If Localo appears empty while `/api/metrics?connector_id=localo` has facts,
     restart via `scripts/local_stack.sh restart` before changing product logic.

2. **Skill/reference hygiene audit**
   - `scripts/skill_hygiene_check.py` now guards obvious hygiene failures:
     `Goal 001`/workaround/bugfix/outdated/slop prose, English safety headings,
     English `with mode=vendor_read` endpoint notes and English imperative
     workflow steps in WILQ skill docs.
   - Current WILQ `SKILL.md` and `references/output-contract.md` files have
     Polish operator prose with unchanged API IDs, endpoint paths and enum
     values.
   - Remaining audit: deeper semantic review of references. References may
     describe API usage, required evidence, output shape and safety rules.
   - References must not become the place for product behavior, workaround
     rules, dashboard cleanup, dedupe decisions, ranking logic or bug fixes.
   - If a skill needs a smarter decision, implement typed API/schema/view-model
     and eval contract first, then make the skill consume it.

3. **Remaining Ads optimizer value**
   - Current Ads is review-only and intentionally blocks unsupported claims.
   - Current live blockers are not OAuth setup gaps: `change_history` is blocked
     because Google Ads returned zero change_event rows for the current window;
     `keyword_planner_read_contract` is blocked by
     `authorizationError.DEVELOPER_TOKEN_NOT_APPROVED`.
   - Next value contracts: approved/live Keyword Planner enrichment,
     forecast/audience size, budget pacing, change-history impact context,
     campaign recommendations with safety, custom segment apply/audit and
     negative keyword apply/audit.
   - Do not claim wasted budget, profitability, CPA/ROAS verdicts, budget
     scaling or apply until these contracts exist.

4. **Dashboard code quality only where it helps velocity**
   - `App.tsx` shell has been reduced, but large route modules still exist.
   - Do not spend time on aesthetic refactors. Extract only when a file blocks
     product velocity, focused tests, browser QA or reviewability.

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

1. Continue with missing Localo GBP/competitor/local task read contracts, deeper
   semantic skill/reference audit or remaining Ads optimizer value,
   depending on the strongest remaining demo blocker in live API/browser proof.

## Stop Condition

Goal 001 is not done until the Ekologus marketer can open the dashboard, follow
the daily plan, inspect Ads/Merchant/Content/GA4/Localo decisions, copy/run the
matching Codex skill prompt, and receive Polish evidence-backed recommendations
with safe next actions and blocked claims. The demo must prove real API
evidence, not static artifacts, prompt-only reasoning or mock data.
