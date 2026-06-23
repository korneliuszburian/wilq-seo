# Goal 001 - WILQ Marketing OS Active Goal

Last updated: 2026-06-23 23:19 CEST.

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

## Current Stack Map

Use this map before adding tasks, so work lands in the right layer instead of
becoming dashboard copy, skill prose or test theater:

1. **Source adapters**: connector modules under `wilq/connectors/**` perform
   read-only vendor reads, sanitize responses and persist evidence/metric facts.
2. **Typed product contracts**: diagnostics, briefing, tactical queue and
   ActionObject services under `wilq/**` turn source facts into decisions,
   blockers, payload previews and safe next steps.
3. **API surface**: `apps/api/wilq_api/main.py` exposes the shared contracts
   used by dashboard and Codex skills.
4. **Dashboard**: `apps/dashboard/src/**` renders decision cockpit and
   drilldown routes. It should not invent ranking, grouping or safety logic.
5. **Codex skills**: `.agents/skills/wilq-*` describe how an operator uses the
   API contracts. They must not repair missing product behavior in references.
6. **Eval and release gates**: `scripts/**`, `tests/**`, `docs/evals/**` prove
   contracts, evidence, Polish output, safety and no invented metrics.

## Current Thematic Stack Assessment

Use these workstreams to pick the next slice. Do not reopen a ready item unless
fresh API/browser proof shows a regression.

1. **Acquisition/source proof**
   - Ready: Google Ads OAuth/customer selection and live campaign/search-term
     reads; Merchant aggregate issues plus product sample readiness; GSC query
     pages; WordPress inventory matching for current Ekologus URLs; Localo
     aggregate visibility, rankings, GBP visibility, competitor visibility and
     reviews; GA4 behavior/landing facts plus key-event/ecommerce/revenue
     metric facts.
   - External blockers: Google Ads Keyword Planner is blocked by developer
     token approval, not missing `.env`; Ads change-history may be empty for a
     chosen window; Localo `local_tasks` must stay blocked unless a
     side-effect-free task read exists.
   - Real gaps: Ads pacing/recommendation/impression-share decision context,
     Ahrefs granular URL/query/backlink gap evidence and cross-source joins
     that prove business decisions rather than isolated facts. GA4 still blocks
     ROAS/profitability/conversion-drop verdicts without cost, attribution and
     history context even though conversion/ecommerce metrics are now readable.
2. **Decision contracts**
   - Ready: core diagnostics, tactical queue, marketing brief, command-center
     decisions and ActionObject surfaces share WILQ API contracts.
   - Real gaps: one shared daily decision view-model, stable per-domain queues,
     explicit freshness/ready/blocked semantics and ranking that favors
     marketer value over connector readiness.
3. **Action safety**
   - Ready: demo-safe prepare/review ActionObjects for Ads, Merchant, Content,
     GA4 and Localo with blocked apply state where required.
   - Real gaps: apply path contracts with `dry_run -> preview -> confirm ->
     audit`, SafetyLimits, partial-failure handling, and write-specific guards
     for Ads, Merchant, Localo/GBP and social publishing.
4. **Codex skill layer**
   - Ready: 12 WILQ skills have API/evidence/Polish/safety smoke and
     non-interactive eval coverage.
   - Real gaps: decision-quality evals, semantic reference audit, practical
     dashboard prompts and tighter context packs for each domain.
5. **Dashboard/product UI**
   - Ready: strong demo path exists across command center, Merchant, Content,
     Ads, GA4, Localo and action details.
   - Real gaps: route-by-route marketer audit, shared data boundaries to avoid
     repeated heavy aggregation, removal of leftover technical/meta cards, and
     targeted extraction of large frontend modules only where it improves
     velocity/reviewability.
6. **Testing/release**
   - Ready: broad `scripts/verify.sh`, focused API/dashboard tests, skill
     smokes/evals and hygiene/security gates exist.
   - Real gaps: fixture-vs-live smoke split, smaller pre-demo gate, production
     readiness checks and operational alerts for stale contracts, missing facts,
     unsafe apply attempts and secret leakage.

## Active Demo Backlog

Finish these before claiming the Ekologus demo is done:

1. **Source contracts and data acquisition**
   - Current Localo diagnostics expose live aggregate facts and typed
     read-contract status after a managed stack restart. Live proof
     `refresh_localo_a1b33cd17835` completed with
     `live_data_available=true`, `visibility_fact_count=23`,
     `act_review_localo_visibility_facts` ready, and `place_inventory`,
     `local_rankings`, `gbp_visibility`, `competitor_visibility` and `reviews`
     ready.
   - Localo remaining work is now narrower: `local_tasks` stays missing/blocked
     unless Localo exposes a side-effect-free task read. Do not claim local task
     completion, GBP writes or local visibility uplift from current Localo
     facts.
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
   - Merchant current source state: aggregate issue contracts and product
     sample readiness are available for review-only queues. Remaining Merchant
     work is deeper product performance joins with Ads/GA4, supplemental-feed
     candidate contracts, price-impact snapshots and richer payload previews
     where the vendor API exposes safe read-only details. Do not claim approval
     restoration, revenue recovery or unique SKU fixes from aggregate issue
     counts.
   - GA4 current source state: live Data API read now requests and stores
     `keyEvents`, `ecommercePurchases`, `purchaseRevenue`, `totalRevenue` and
     `transactions` with landing/source/campaign dimensions. Current live proof
     `refresh_google_analytics_4_6acb3a6c9be8` completed and `/api/ga4/diagnostics`
     reports `conversion_readiness_contract.status=ready` with no missing read
     contracts. ROAS, profitability, conversion-drop and attribution verdicts
     remain blocked until cost, history and attribution context exists.
   - Add source-contract slices in this order:
     1. Keep Localo `local_tasks` blocked unless Localo exposes a
        side-effect-free task read. Do not call task endpoints that generate
        new tasks.
     2. Ads optimizer evidence: budget pacing, recommendation safety,
        impression-share context, approved Keyword Planner readiness and
        change-history windows.
     3. Merchant deepening: product performance joins, supplemental-feed
        candidates, price-impact snapshots and richer read-only previews.
     4. Ahrefs/content-gap enrichment only where API evidence is granular
        enough to support URL/query/backlink decisions.

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
   - Add decision/view-model slices:
     1. One shared daily decision view-model for command center and marketing
        brief, so the same decisions are not rebuilt or phrased twice.
     2. Domain-specific decision queues for Ads, Merchant, Content, GA4 and
        Localo with stable fields: `why_it_matters`, `operator_action`,
        `evidence_ids`, `source_connectors`, `metric_facts`,
        `blocked_claims`, `action_ids`, `freshness`.
     3. Decision-quality ranking that prefers high-value marketer actions over
        connector readiness or technical status.
     4. Explicit stale/ready/blocked semantics per contract, so `ready` never
        hides missing conversion, GBP, product or Ads safety evidence.

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
   - Add ActionObject slices:
     1. Ads review actions: negative keyword review, custom segment review,
        campaign strategy review and target guardrails stay prepare-only until
        payload preview, 90-day safety checks, audit and explicit confirm exist.
     2. Merchant feed actions: review queue and supplemental-feed candidates
        must show row-level evidence when available and keep primary-feed
        mutation blocked.
     3. Content actions: refresh/merge/create/block payload previews must
        reference GSC/GA4/WordPress/Ahrefs evidence and show duplicate checks.
     4. Localo/GBP actions: no GBP post, ranking, review reply or task apply
        until Localo evidence and ActionObject validation exist.
     5. Social actions: draft-only is acceptable; publishing stays blocked
        until page/org permissions, preview, confirm and audit exist.

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
   - Add skill/eval slices:
     1. Run manual and non-interactive eval for every WILQ skill after its
        domain API contract is strong enough. Record results in
        `docs/evals/skill-eval-ledger.md` and coverage in
        `docs/evals/skill-coverage-audit.md`.
     2. Upgrade evals from format checks to decision checks. Examples:
        content must identify BDO refresh, Zielony Ład merge/check and GA4
        `(not set)` as blocker; Merchant must use `decision_queue` before
        drilldown clusters and not treat reporting sums as unique products;
        Ads must separate review candidates from CPA/ROAS/waste verdicts.
     3. Audit `.agents/skills/**/references` semantically. Remove or move any
        product behavior, workaround, bugfix, ranking/dedupe rule or dashboard
        cleanup rule into typed API/eval code.
     4. Normalize skill prompts exposed in dashboard: Polish marketer command,
        skill name, source connectors, evidence IDs, ActionObject IDs and
        blocked-claim instruction. No vague “analyze this” prompts.
     5. Keep skill context packs scoped. Do not send the full system context
        when a narrow diagnostics endpoint and skill-scoped pack are enough.

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
   - Add dashboard/code slices:
     1. Keep Command Center as the first-screen decision cockpit: max useful
        daily decisions, prompt-to-Codex, action focus and source freshness.
        Move registries, raw metric dumps and long evidence lists to drilldown
        routes.
     2. Audit each route from a marketer perspective:
        `/command-center`, `/ads-doctor`, `/merchant`, `/content-planner`,
        `/ga4`, `/localo`, `/actions`, `/opportunities`, `/knowledge`,
        `/settings`. Mark cards as keep, rewrite, move to drilldown or delete.
     3. Build shared route data boundaries so Command Center, brief and
        drilldowns do not independently request and format the same heavy
        surfaces.
     4. Reduce large frontend modules only where the split makes slices faster:
        detail panels, prompt cards, decision cards, metric chips, route
        loaders and domain-specific panels.
     5. Browser QA should prove user-visible decisions, not screenshots as
        artifacts. Use `agent-browser` when checking real routes and record
        only concise proof paths.

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
   - Add release/live-test slices:
     1. Split deterministic fixture tests from live smoke checks. Fixture tests
        may assert exact values; live checks assert contract state, freshness,
        nonempty facts and correct blockers.
     2. Define the pre-demo gate: targeted API tests, targeted dashboard route
        tests, touched skill smoke/eval, secret redaction check and one browser
        walkthrough of the strong demo path.
     3. Define the production gate separately: full `scripts/verify.sh`, API
        health, dashboard build, skill smokes/evals, security gate and live
        read-only connector checks.
     4. Add operational alerts for stale connector contracts, missing expected
        facts, unsafe apply attempts and secret leakage.

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
   - Ads budget pacing, recommendation safety, impression-share context or
     change-history window handling; keep Keyword Planner as developer-token
     readiness until Google approval changes.
   - Merchant deepening beyond current product samples: performance joins,
     supplemental-feed candidates, price-impact snapshots or safer product
     preview boundaries.
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
