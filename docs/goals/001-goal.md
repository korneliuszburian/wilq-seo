# Goal 001 - WILQ Marketing OS Active Goal

Last updated: 2026-06-23 21:20 CEST.

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

Strong Ekologus demo is partially built, not done.

Ready enough for demo walkthrough:

- Command Center daily plan based on WILQ API decisions.
- Merchant issue review route and feed ActionObject review flow.
- Content Planner with GSC, GA4, Ahrefs and WordPress evidence boundaries.
- Ads Doctor with live campaign/search-term/recommendation review, target and
  strategy guardrails, negative keyword/custom segment review and blocked
  apply claims.
- GA4 route separates measurement issues from traffic-quality review.
- Localo route has MCP access and aggregate Localo visibility/reviews evidence,
  but not full GBP/competitor/ranking/task workflow.
- 12/12 WILQ skills have non-interactive eval artifacts and current coverage in
  `docs/evals/skill-coverage-audit.md`.

Do not turn these ready surfaces back into active tasks unless browser/API proof
shows regression.

## Active Demo Backlog

Finish these before claiming the Ekologus demo is done:

1. **Skill decision-quality evals**
   - Current evals prove API usage, Polish output, evidence IDs and safety
     shape.
   - Missing: explicit quality-of-decision assertions.
   - Add an eval result contract/checklist that fails when a skill has evidence
     but no actionable decision, no safe next step, no blocked-claims handling
     or no workflow-specific interpretation.

2. **Merchant product-row depth**
   - Keep `decision_queue` as the main queue and `issue_clusters` as drilldown.
   - Preserve freshness and `count_semantics`.
   - Expose product IDs/titles/SKU-level previews where vendor/API allows.
   - Do not claim product fixes, approval restoration, feed writes or recovered
     revenue without exact row-level payload, validation and audit contracts.

3. **Content inventory matching**
   - Reconcile GSC/GA4 URL evidence with WordPress inventory.
   - Prevent false `WordPress missing` states when URL normalization, host alias,
     trailing slash, sitemap source or post/page type is the real issue.
   - Improve refresh/merge/create/block decisions through typed diagnostics,
     not prompt/reference patches.

4. **Localo beyond OAuth and aggregate facts**
   - Current Localo evidence supports aggregate review only.
   - Add typed read contracts before claiming rankings, GBP performance,
     competitor visibility, local tasks, GBP writes or local visibility uplift.

5. **Skill/reference hygiene audit**
   - Audit `.agents/skills/**/SKILL.md` and `.agents/skills/**/references/*.md`.
   - References may describe API usage, required evidence, output shape and
     safety rules.
   - References must not become the place for product behavior, workaround
     rules, dashboard cleanup, dedupe decisions, ranking logic or bug fixes.
   - If a skill needs a smarter decision, implement typed API/schema/view-model
     and eval contract first, then make the skill consume it.

6. **Remaining Ads optimizer value**
   - Current Ads is review-only and intentionally blocks unsupported claims.
   - Next value contracts: approved/live Keyword Planner enrichment,
     forecast/audience size, budget pacing, change-history impact context,
     campaign recommendations with safety, custom segment apply/audit and
     negative keyword apply/audit.
   - Do not claim wasted budget, profitability, CPA/ROAS verdicts, budget
     scaling or apply until these contracts exist.

7. **Dashboard code quality only where it helps velocity**
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

1. Tighten `docs/evals/schemas/wilq-skill-eval-result.schema.json` and
   `scripts/codex_skill_eval.sh` with explicit decision-quality checks.
2. Run focused eval-contract tests and one targeted skill eval if schema/harness
   changes require it.
3. Update `docs/PROGRESS.md` and `docs/evals/skill-coverage-audit.md` with the
   new decision-quality state.
4. Commit and push.
5. Continue with Merchant product-row depth or content inventory matching,
   depending on the strongest remaining demo blocker in live API/browser proof.

## Stop Condition

Goal 001 is not done until the Ekologus marketer can open the dashboard, follow
the daily plan, inspect Ads/Merchant/Content/GA4/Localo decisions, copy/run the
matching Codex skill prompt, and receive Polish evidence-backed recommendations
with safe next actions and blocked claims. The demo must prove real API
evidence, not static artifacts, prompt-only reasoning or mock data.
