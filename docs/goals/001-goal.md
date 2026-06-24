# Goal 001 - WILQ Marketing OS Active Goal

Last updated: 2026-06-24 11:18 CEST.

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
9. `docs/goals/archive/bdos-deferred-backlog.md` - deferred BDOS-class work
   that must not be lost but is not the active demo queue.

Update this goal only when active blockers, next tasks or quality rules change.
Do not paste finished logs, command transcripts or old proof blocks here.

## Context Hygiene Rule

Keep this goal, `docs/PROGRESS.md` and task/plan surfaces as small as possible.
Before adding a task, remove, replace or archive outdated/done text that no
longer changes the next decision. These docs are recovery maps, not append-only
logs.

## Goal Completion Contract

Treat this file as the active Goal contract, not a backlog transcript. A Codex
Goal is done only when the outcome below is verified by evidence while
preserving the constraints and boundaries.

**Outcome:** build WILQ as an API-first Marketing Operating System for
Ekologus, with the strongest current demo centered on the Polish marketer's
daily decisions, evidence-backed content generation and safe review workflows.
The new site `http://ekologus.dev.proudsite.pl/` is a later target context for
content migration/adaptation after the core demo and content-generation
pipeline are stable.

**Verification surface:** the demo is ready when the marketer can open the
dashboard, follow the daily plan, inspect Ads/Merchant/Content/GA4/Localo
decisions, copy/run the matching Codex skill prompt, and receive Polish
evidence-backed recommendations with safe next actions and blocked claims.
Content output must include a structured brief or draft plan with source facts,
intent, H1/H2/CTA direction, forbidden overclaims and review state. Proof must
come from typed WILQ API endpoints, targeted route/browser checks, focused
tests/smokes and skill eval artifacts, not screenshots or prose alone.

**Constraints:** WILQ API remains the system brain; dashboard, skills, hooks,
workflows, expert rules, opportunities and ActionObjects use the same typed API
contracts. No recommendation without evidence IDs, source connectors and clear
claim boundaries. No write/apply without validated ActionObject, preview,
confirmation and audit. Operator-facing copy is Polish with Polish diacritics;
API paths, IDs, enum values and schema fields stay unchanged.

**Boundaries:** go deep on Ekologus before multi-client/agency abstractions.
Use current `ekologus.pl`, `sklep.ekologus.pl`, GSC, GA4, Ahrefs, Ads,
Merchant, Localo and WordPress evidence as source context. Treat
`ekologus.dev.proudsite.pl` as the new-site target context, not as a substitute
for evidence. Do not move product behavior into skill references or dashboard
copy; implement typed API/schema/view-model/rule/eval contracts first.

**Iteration policy:** after every slice, compare the current evidence with this
contract, update only the smallest useful recovery docs, run focused checks
matched to touched files, then choose the next highest-value task for the demo.
Prefer content-demo usefulness, source-contract gaps and decision quality over
technical status polish.

**Blocked stop condition:** if a required vendor/API contract, permission,
data source, test surface or safe write path is unavailable, stop that claim
with: missing contract, evidence gathered, blocked claims, what remains safe to
show, and the exact input or implementation needed to unblock it.

## Codex Goal And Prompting Contract

Use the Codex Goal pattern as a completion contract:

- Outcome, verification, constraints, boundaries and blocker rules must be
  explicit before long-running work continues.
- Long details belong in this file and linked docs, not in a 4,000-character
  `/goal` prompt. The thread goal should point here.
- Codex should inspect, implement, verify and refine without waiting after
  every small step, but must stop when evidence says a claim is blocked.
- Avoid looping on the same files or broad tests. If progress stalls, report
  what was tried, what evidence exists and the next input/implementation needed.
- Use parallel reads and subagents for independent audits or disjoint
  implementation slices, then merge findings into one typed API/view-model plan
  before editing shared product surfaces.
- Prompt text exposed to the marketer is part of the product surface: it must be
  practical Polish, skill-specific, evidence-scoped and eval-covered.

## Codex Rollout Quality Gates

These gates apply before adding tasks, editing code or claiming a gap exists:

1. **Inventory before planning**
   - Search and read the current repo/API first. Use `rg`, targeted file reads
     and relevant WILQ endpoints before writing a plan or backlog item.
   - Every new task must name what already exists, what is missing, and which
     API/schema/dashboard/skill/eval surface proves that gap.
   - If live API contradicts source/tests, restart the managed stack before
     changing product logic.
2. **Reuse before building**
   - Reuse existing typed contracts, helpers, schemas, view-models, route
     components and skill smokes before adding new ones.
   - Do not create duplicate pipelines because a previous session forgot an
     implementation exists. If a contract exists but is weak, harden it.
   - Large files such as dashboard route modules are technical debt, but do not
     refactor them during unrelated slices. Extract only when the current slice
     needs it or when a dedicated quality slice is active.
3. **Smallest working slice**
   - Deliver working code or a concrete docs correction, not a plan-only turn,
     unless the user explicitly asks for a plan.
   - Keep edits surgical. Every changed line must trace to this goal, the
     user's latest request or a directly observed regression.
   - Do not add speculative flexibility, broad fallbacks, broad catches,
     success-shaped defaults or prompt-side business logic.
4. **Tool and execution discipline**
   - Batch independent reads and searches with parallel tool calls. Avoid
     sequential file-by-file exploration unless the next path truly depends on
     the previous result.
   - Use `apply_patch` for manual edits. Do not use destructive git commands.
   - Use subagents only for independent audits or implementation slices with
     disjoint files; merge findings into one typed API/view-model plan before
     editing shared surfaces.
5. **Verification discipline**
   - Run the smallest check that proves the touched surface. Docs-only changes
     need `git diff --check`; API/schema changes need the focused pytest; route
     changes need the touched route test and type/lint only when shared types
     moved; skill changes need the touched smoke/eval.
   - Do not repeat broad test suites by habit. Use `scripts/verify.sh` only for
     final handoff, broad-risk changes or shared-regression evidence.
   - Before completion, reconcile all stated tasks as done, blocked or
     cancelled. Do not leave active docs with stale ready items.
6. **Codex harness discipline**
   - For any WILQ-owned Codex API/runtime work, preserve assistant `phase`
     metadata for commentary/final output, preserve compaction state, and keep
     tool schemas close to Codex CLI conventions.
   - Operator prompts must be practical Polish commands mapped to a specific
     WILQ skill, endpoint, evidence set, ActionObject and blocked claims.
   - If a skill needs smarter behavior, implement or expose the typed API field
     first. Skill references describe how to use contracts; they do not patch
     missing product behavior.

## Current Product State

Strong Ekologus demo is partially built, not done. Baseline demo surfaces are
tracked in git history, `docs/PROGRESS.md`, route tests and
`docs/evals/skill-coverage-audit.md`; do not keep ready/done surfaces as active
goal tasks. Only reopen a ready surface when fresh browser/API proof shows a
regression.

Latest completed slices: Merchant skill eval is hardened for product/price
readiness and blocked product ROAS / price-impact claims
(`.local-lab/evals/codex-skill/20260624T015347Z/wilq-merchant-feed-operator/result.json`).
Content target-site adaptation now stays typed across API, context-pack,
dashboard and `wilq-content-strategist`: current source URLs and target-site
URLs/hosts/status are explicit in content brief and WordPress draft previews,
including future `ekologus.dev.proudsite.pl` adaptation, while the dev site is
not treated as independent source evidence.
Content expert/knowledge lineage is now typed on `/api/content/diagnostics`
sections and decisions instead of living only in context-pack summaries:
GSC/WordPress refresh decisions, Ahrefs gap review decisions and GA4
tracking-gap blocks expose supporting knowledge card IDs and expert rule IDs
that are present in the skill context.
Non-content domain diagnostics now expose direct expert/knowledge lineage on
their decision queues too. Merchant, GA4, Localo and Ahrefs decisions carry
their existing `knowledge_card_ids` and `expert_rule_ids`, and the matching
skill context-packs include the referenced summaries. This closes the confirmed
lineage gap without moving business logic into skill references. Focused proof:
API contract subset, live diagnostics check, live context-pack check, shared
live schema smoke warm rerun and sequential skill smokes for Merchant, GA4,
Localo and Ahrefs. Parallel context-pack-heavy skill smokes can still hit the
20s script timeout, so pre-demo gates should run those sequentially or with an
explicit performance slice.
Small pre-demo gate now exists as `scripts/pre_demo_gate.sh`. It checks the
managed stack, API health, live contract smoke, shared live schemas,
API-backed dashboard route smoke and sequential WILQ skill smokes without
running the full broad `scripts/verify.sh`. Full proof on 2026-06-24 passed
with core skills in `.local-lab/pre-demo-gate.log`; follow-up proof after log
readability patch passed in `.local-lab/pre-demo-gate-core-skills.log`.
Daily Command wording/eval now treats Localo as outside the daily task list only
when it is outside typed `command_center.daily_decisions`, not because Localo
evidence is absent
(`.local-lab/evals/codex-skill/20260624T020437Z/wilq-daily-command/result.json`);
the same daily eval now validates the Ads review ActionObject instead of
leaving it pending. Ahrefs gap-finder eval now proves scoped lineage for
`/ahrefs`: `.local-lab/evals/codex-skill/20260624T021206Z/wilq-ahrefs-gap-finder/result.json`
uses only top-level `source_connectors=["ahrefs"]`, sees 8 typed stale gap
records and keeps traffic uplift / authority improvement blocked. Ahrefs gap
records now also feed `/api/marketing/tactical-queue` as review-only
`domain=content` tactical items with `act_prepare_content_refresh_queue`,
GSC/WordPress confirmation fields and no uplift/ranking claims; remaining
Ahrefs work is freshness and stronger cross-source scoring, not raw gap
visibility. Command Center daily content metric facts use the same reviewable
Ahrefs filter, so off-topic raw gaps do not leak onto the first screen.
Daily runtime now passes preloaded metric facts into Marketing Brief instead
of making the brief repeat its own metric-store read after Command Center has
already built the daily base. Focused proof: daily runtime API contract test,
ruff, mypy and live warm-cache checks for `/api/dashboard/command-center`,
`/api/marketing/brief` and `/api/marketing/tactical-queue`.
Merchant price-impact readiness is now also promoted into
`decision_queue` as `decision_type=review_price_impact_readiness` whenever
current product prices exist, so dashboard and skills can show the missing
price-history/performance contracts as a visible blocked review decision
instead of hiding them only in a top-level readiness object. The Merchant skill
smoke now requires that same decision in both `/api/merchant/diagnostics` and
skill-scoped context-pack before the skill path is trusted.
Manual pre-demo vendor refresh is usable again: `configured_vendor_read_refresh`
now includes only connectors with implemented read-only vendor adapters, so
`openai_codex` no longer blocks the job while its vendor-read adapter is absent.
Live proof `jobrun_configured_vendor_read_refresh_262817b0e1` completed with
8 source connectors and no errors, making Content fresh on Command Center.
`/merchant` live route now renders the Merchant diagnostics again after shared
schema accepted API `decision_type=review_price_impact_readiness`; this was a
frontend contract drift, not an API or route-mapping failure.
Dashboard drilldown loading is less blank for marketer routes:
`/opportunities` and `/knowledge` now render their primary heading/sections
before secondary registries finish, with ActionObject/evidence/knowledge
subsections handling their own loading/error states. Focused proof: targeted
route tests, dashboard lint/typecheck and `agent-browser` checks for quick
`main` + `h1` visibility plus final route content.
Marketing Brief empty-section proof on 2026-06-24 showed a stale long-running
API process/cache, not a current code defect: fresh `uv run` construction and
live API after `scripts/local_stack.sh restart` both returned
`what_we_know=5`, `what_blocks_us=2`, `safe_next_actions=7`,
`recommended_focus=3`, 13 ActionObject IDs and 21 evidence IDs. When live API
contradicts current source/tests, restart the managed stack before patching.
Skill-reference audit guardrail now blocks recovery/artifact prose in skills
and references: goal/progress/eval paths, `.local-lab` artifacts, previous-run
wording and prompt-fix wording. Existing typed API contract fields such as
`decision_queue`, `freshness_assessment`, `readiness.status`, `blocked_claims`
and ActionObject validation remain valid reference material.
Merchant `decision_queue` now exposes `why_it_matters` and `operator_action`
aliases filled from canonical `rationale` and `next_step`, so dashboard and
Codex can consume Merchant decisions the same way they consume daily/action-plan
decisions. Live proof after stack restart shows real sample product IDs/titles
and Ads product-state mapping in Merchant decisions; shared live schema smoke
parsed the updated API contract.
Localo live state now distinguishes ready read contracts from truly blocked
areas: `place_inventory`, `local_rankings`, `gbp_visibility`,
`competitor_visibility` and `reviews` are usable read-only evidence, while only
`local_tasks`, write path and uplift claims stay blocked. Command Center,
Localo diagnostics and Localo ActionObject payloads must not say that GBP or
competitor visibility are missing when those contracts are ready.

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
5. **Knowledge and expert rules**: `wilq/expert/**`, `wilq/knowledge/**` and
   source-lineage docs condense external standards into versioned cards/rules
   consumed by code. They are not loose prompt notes.
6. **Codex skills**: `.agents/skills/wilq-*` describe how an operator uses the
   API contracts. They must not repair missing product behavior in references.
7. **Eval and release gates**: `scripts/**`, `tests/**`, `docs/evals/**` prove
   contracts, evidence, Polish output, safety and no invented metrics.

When adding tasks, assign them to one of these layers first. If the task needs
more than dashboard copy or skill prose, create or improve the typed API,
schema, view-model, expert rule or eval contract in the owning layer.

## Current Thematic Stack Assessment

Use these workstreams to pick the next slice. Do not reopen a ready item unless
fresh API/browser proof shows a regression.

1. **Acquisition/source proof**
   - Ready: Google Ads OAuth/customer selection, live campaign/search-term
     reads, budget pacing, recommendation review, impression-share context,
     search-term safety, negative-keyword review queue and custom-segment review
     queue; Merchant aggregate issues plus product sample readiness; GSC query
     pages; WordPress inventory matching for current Ekologus URLs; Localo
     aggregate visibility, rankings, GBP visibility, competitor visibility and
     reviews; GA4 behavior/landing facts plus key-event/ecommerce/revenue
     metric facts.
   - External blockers: Google Ads Keyword Planner is blocked by developer
     token approval, not missing `.env`; Localo `local_tasks` must stay blocked
     unless a side-effect-free task read exists.
   - Real gaps: Ads change-impact windows and apply/audit contracts, approved
     Keyword Planner enrichment, forecast/audience size, fresh Ahrefs gap reads
     and cross-source joins that prove business decisions rather than isolated
     facts. Empty Ads change-history reads are
     `ready/no changes`; change-impact review stays blocked until change rows
     and before/after windows exist. GA4 still blocks ROAS/profitability/
     conversion-drop verdicts without cost, attribution and history context
     even though conversion/ecommerce metrics are now readable.
2. **Decision contracts**
   - Ready: core diagnostics, tactical queue, marketing brief, command-center
     `daily_decisions`, explicit `decision_state` and ActionObject surfaces
     share WILQ API contracts. `decision_state` is the canonical
     ready/stale/blocked/missing/unknown field for dashboard and Codex
     consumers, so they do not infer state from separate `status` and
     `freshness` fields.
   - Real gaps: stable per-domain queues and ranking that favors marketer
     value over connector readiness.
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
5. **Content generation layer**
   - Ready: content diagnostics already returns typed `decision_queue` items,
     `act_prepare_content_refresh_queue` already exposes
     `content_brief_preview_v1` and `wordpress_draft_payload_preview_v1`, and
     dashboard/skills already render or consume the review-only content flow.
   - Required next shape: harden the existing content-generation contract, not
     rebuild it. The contract must consistently convert evidence into Polish
     marketer artifacts: intent cluster, audience/problem, old source URL,
     target page type, source facts, H1/H2/FAQ/CTA direction, draft
     constraints, forbidden claims and review state.
   - Techniques: evidence-first context packs, query/page clustering, search
     intent grouping, content inventory dedupe, landing/source quality checks,
     competitor/gap context as supporting evidence only, and human review before
     publish/write.
   - Prompt pattern: practical Polish commands mapped to a skill and endpoint,
     for example "zbuduj brief SEO dla tej strony", "połącz te query w jeden
     klaster", "wskaż refresh/merge/create/block", with evidence IDs,
     source connectors, ActionObject IDs and blocked claims embedded.
   - Real gaps: surface consistency between content diagnostics, tactical
     queue, context-pack and dashboard; richer draft/rewrite preview;
     duplicate/canonical checks; target-site migration fields; and evals that
     score usefulness of the generated brief, not only JSON shape.
6. **Knowledge compiler and marketing expertise**
   - Ready: structured expert YAML rules and first knowledge-card/compiler
     scaffolding exist.
   - Real gaps: source-ingestion workflow for Google/Ads/SEO/Localo/Merchant
     standards, source lineage, confidence/freshness scoring, rule/card
     promotion into code and evals that prove rules influence decisions.
7. **Dashboard/product UI**
   - Ready: strong demo path exists across command center, Merchant, Content,
     Ads, GA4, Localo and action details.
   - Real gaps: route-by-route marketer audit, shared data boundaries to avoid
     repeated heavy aggregation, removal of leftover technical/meta cards, and
     targeted extraction of large frontend modules only where it improves
     velocity/reviewability.
8. **Testing/release**
   - Ready: broad `scripts/verify.sh`, focused API/dashboard tests, skill
     smokes/evals, hygiene/security gates and live dashboard e2e smoke that
     avoids exact assertions against changing Ekologus metric values.
   - Real gaps: fixture-vs-live smoke split, smaller pre-demo gate, production
     readiness checks and operational alerts for stale contracts, missing facts,
     unsafe apply attempts and secret leakage.

## Active Demo Backlog

Finish these before claiming the Ekologus demo is done:

1. **Core demo decision cockpit**
   - Keep Command Center and domain routes focused on marketer decisions,
     evidence, safe next actions, prompt-to-Codex and blocked claims.
   - Do not promote connector readiness, raw metric dumps or stale technical
     cards as marketing value.
   - Verification: browser/API proof that `/command-center`, `/content-planner`,
     `/ads-doctor`, `/merchant`, `/ga4`, `/localo` and action details show
     useful decisions without fake metrics.

2. **Content generation pipeline**
   - Build a typed content workflow before adapting to the dev site: evidence
     pack -> intent/query cluster -> inventory/canonical check -> brief ->
     draft/rewrite preview -> review ActionObject.
   - Output must be Polish and useful for the marketer: page goal, audience,
     key objections, evidence-backed angle, H1/H2/FAQ/CTA direction, internal
     linking ideas, source facts, missing evidence and forbidden claims.
   - Use `wilq-content-strategist` and `wilq-gsc-content-doctor` as operator
     workflows over the API, not as the place where brief logic is invented.
   - Verification: `/api/content/diagnostics`,
     `/api/marketing/tactical-queue`, content route, skill smoke and
     non-interactive eval must all agree on the same decisions.

3. **New Ekologus site adaptation**
   - Use `http://ekologus.dev.proudsite.pl/` after the core content workflow is
     stable.
   - Treat current `ekologus.pl`, `sklep.ekologus.pl`, GSC, GA4, Ahrefs, Ads,
     Merchant, Localo and WordPress inventory as evidence.
   - Treat the dev site as target context, not as evidence by itself.
   - Add typed fields for target URL, target page type, source URL, canonical
     source, migration/rewrite status and review state before exposing this in
     dashboard prompts.

4. **Source contracts and data acquisition**
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
   - Deterministic `wilq-localo-operator` smoke must validate
     `localo_diagnostics.latest_refresh` by default. Do not force a live
     Localo vendor refresh in the default smoke path; use `--refresh` only for
     explicit live proof. A transient Localo OAuth discovery HTTP 503 is a
     vendor refresh failure, not proof that existing Localo diagnostics/evidence
     are broken.
   - Current Ads is review-only and intentionally blocks unsupported claims.
     Live diagnostics expose optimizer review context across campaign triage,
     budget pacing, recommendations, impression share, search-term safety,
     custom segments and negative-keyword review. Empty `change_history` reads
     mean "ready, no changes in the current window"; change-impact review
     remains blocked until WILQ has change rows and performance windows
     before/after. `keyword_planner_read_contract` is blocked by
     `authorizationError.DEVELOPER_TOKEN_NOT_APPROVED`.
   - Ads remaining source/action work: approved/live Keyword Planner enrichment,
     forecast/audience size, change-impact windows and mutation apply/audit
     contracts for budget, recommendations, custom segments and negative
     keywords.
   - Merchant current source state: aggregate issue contracts, grouped
     decision_queue, review-only payload preview and product sample readiness
     are available for review-only queues. `product_performance_readiness`
     exists; GA4 item-level product facts are readable and persisted, and Ads
     now has live `shopping_performance_view` and `shopping_product`
     current-state read contracts. Current Ads proof
     `refresh_google_ads_72dc2a727c45` checked 30d/90d product performance
     and returned 0 product performance rows, then read 500 product-state rows.
     Merchant now joins 3 sample IDs through Ads product state, but keeps
     `product_performance_readiness.status=blocked` because no Ads/GA4
     performance metrics match those products. It also exposes a review-safe
     `review_product_state_mapping` decision and
     `merchant_product_state_review_preview_v1` plus review-only
     `merchant_supplemental_feed_review_preview_v1` candidates so the marketer
     can inspect Ads status, availability, price, Merchant issue context and
     candidate supplemental-feed review fields without apply. It also exposes
     `price_impact_readiness` response key with contract id
     `merchant_price_impact_readiness` and
     `merchant_price_impact_readiness_preview_v1`; live proof sees 3 current
     Ads prices, 0 previous price snapshots and 0 matching product performance
     windows, so price-impact remains blocked with explicit missing read
     contracts. The same readiness is also visible as a blocked
     `review_price_impact_readiness` decision when current prices exist, with
     `merchant_price_impact_readiness_preview_v1` and blocked price-impact/
     product ROAS/feed-write claims. Price preview rows now expose current/
     previous price snapshot timestamps, previous evidence IDs,
     `has_price_change`, and changed-vs-unchanged price-history counters when
     metric history exists. A second identical price snapshot is history, not a
     price-change event. Remaining Merchant work is actual historical price
     snapshots with real price changes, before/after performance windows and
     richer read-only previews where vendor APIs expose safe details. Do not
     claim approval restoration, revenue
     recovery, product ROAS, price impact or unique SKU fixes from aggregate
     issue counts, state-only rows, supplemental-feed candidates or current
     prices alone.
     `product_performance_readiness` now exposes `missing_read_contracts`, so
     state-only Ads joins are explicitly separated from missing Ads/GA4 product
     performance contracts for dashboard and skills.
   - GA4 current source state: live Data API read now requests and stores
     `keyEvents`, `ecommercePurchases`, `purchaseRevenue`, `totalRevenue` and
     `transactions` with landing/source/campaign dimensions, plus `itemId`,
     `itemName`, `itemsViewed`, `itemsAddedToCart`, `itemsCheckedOut`,
     `itemsPurchased` and `itemRevenue` as item/product facts. Current live
     proof `refresh_google_analytics_4_33a4b3fda0db` completed with 50 item
     rows. `/api/ga4/diagnostics` reports
     `conversion_readiness_contract.status=ready` with no missing conversion
     read contracts. ROAS, profitability, conversion-drop and attribution
     verdicts remain blocked until cost, history and attribution context exists.
   - Add source-contract slices in this order:
     1. Keep Localo `local_tasks` blocked unless Localo exposes a
        side-effect-free task read. Do not call task endpoints that generate
        new tasks.
     2. Merchant deepening: add historical price snapshots, before/after
        performance windows and richer read-only previews.
     3. Ahrefs/content-gap enrichment should now focus on freshness and stronger
        cross-source scoring, because typed Ahrefs gap records already exist
        and tactical queue exposes review-only content candidates with
        GSC/WordPress confirmation fields.
     4. Return to Ads only when Keyword Planner approval changes, change rows
        appear, or apply/audit contracts are the active slice.

5. **Decision API and view-model quality**
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
   - Current Command Center `daily_decisions` expose stable `domain`
     identifiers (`merchant`, `content`, `ga4`, `google_ads`) and typed
     `freshness` state derived from latest source `vendor_read` with
     connector-freshness fallback. Live smoke asserts both fields exist without
     checking changing live metric values. The dashboard status badge now shows
     stale ready decisions as `do odświeżenia`, so stale data is not visually
     presented as fully fresh/ready. Daily decisions now also expose capped
     `metric_facts` from their own source connectors; multi-source decisions
     use connector round-robin so Ahrefs/GSC/WordPress style evidence is not
     dominated by the first connector. They also expose stable
     `why_it_matters` and `operator_action` aliases beside Polish display
     fields, so Codex skills and dashboard code do not need prompt-side field
     inference.
   - Add decision/view-model slices:
     1. Domain-specific decision queues for Ads, Merchant, Content, GA4 and
        Localo with stable fields: `why_it_matters`, `operator_action`,
        `evidence_ids`, `source_connectors`, `metric_facts`,
        `blocked_claims`, `action_ids`, `freshness`.
        Content diagnostics now returns `block_until_vendor_read` when no
        evidence-backed content decisions exist, so empty content data becomes
        a typed blocker instead of an empty queue.
     2. Decision-quality ranking that prefers high-value marketer actions over
        connector readiness or technical status.
     3. Explicit stale/ready/blocked semantics per contract, so `ready` never
        hides missing conversion, GBP, product or Ads safety evidence.

6. **Action safety and apply path**
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
     2. Merchant feed actions: review queue and supplemental-feed candidates now
        show row-level evidence and marketer aliases when available. Next work must keep
        primary-feed mutation blocked while adding before/after price-performance
        proof.
     3. Content actions: refresh/merge/create/block payload previews must
        reference GSC/GA4/WordPress/Ahrefs evidence and show duplicate checks.
     4. Localo/GBP actions: no GBP post, ranking, review reply or task apply
        until Localo evidence and ActionObject validation exist.
     5. Social actions: draft-only is acceptable; publishing stays blocked
        until page/org permissions, preview, confirm and audit exist.

7. **Codex skills, prompts and eval quality**
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
   - `wilq-merchant-feed-operator` now consumes the typed
     `price_impact_readiness` contract instead of carrying price-impact logic in
     prose. Its smoke checks endpoint/context-pack consistency, required
     historical price/performance read contracts, review-only preview flags and
     blocked product ROAS/profitability/price-impact claims.
   - First semantic reference audit removed two prompt-side product behaviors:
     Daily Command no longer hardcodes domain ranking, and GA4 Analyst no
     longer classifies decision items in prose. Both must use WILQ API
     decision order/types. `scripts/skill_hygiene_check.py` blocks those exact
     regressions.
   - Ads Doctor semantic cleanup removed long prompt-pack logic from
     `wilq-ads-doctor/SKILL.md`. It now consumes typed
     `/api/ads/diagnostics` contracts for `allowed_metrics`,
     `missing_read_contracts`, `blocked_claims`, `action_ids` and
     `payload_preview`. The hygiene gate blocks `Inspiracja produktowa` prose
     and body lines over 900 characters. Ads Doctor context-pack must use
     summary diagnostics before compaction and stay under the deterministic
     smoke budget.
   - Diagnostics-first skill cleanup normalized Ahrefs, Demand Gen and Localo:
     their `SKILL.md` and `references/output-contract.md` files now require the
     dedicated diagnostics endpoint before scoped context-pack consistency
     checks. `scripts/skill_hygiene_check.py` blocks context-pack-first
     regressions for skills with dedicated diagnostics endpoints.
   - Recovery/artifact prose is now blocked from skill docs and references:
     goal/progress/eval paths, `.local-lab` artifacts, previous-run wording and
     prompt-fix wording fail `scripts/skill_hygiene_check.py`.
   - Remaining semantic audit is only for concrete proof that a reference hides
     product behavior without a matching typed API field. References may
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

8. **Knowledge compiler and source condensation**
   - Goal: turn external marketing knowledge into versioned, source-linked
     rules/cards that improve WILQ decisions without bloating prompts.
   - Required contract for each accepted source: source URL/file, author/vendor,
     date checked, domain, claims, confidence, freshness, allowed use, forbidden
     overclaims and linked WILQ rule/card IDs.
   - Research may use official docs, reputable PPC/SEO/analytics sources,
     papers and expert playbooks, but nothing becomes product behavior until it
     is condensed into structured rules/cards and covered by evals.
   - Do not add a vector database before the knowledge compiler, evidence model
     and source-lineage contract are working.
   - Add knowledge/compiler slices:
     1. Create a compact source-ingestion contract for marketing knowledge:
        source metadata, extracted claim, applicable connector/domain, risk,
        evidence requirement and target rule/card.
     2. Promote only high-confidence items into `wilq/expert/**` or
        `wilq/knowledge/**`; keep raw research notes out of dashboard and skill
        prompts.
     3. Add eval checks that prove selected rules/cards affect decisions while
        still blocking unsupported claims.
     4. Build first domain batches in this order: Ads safety/optimizer,
        Merchant feed diagnostics, GA4 measurement/commerce, GSC/content,
        Localo/GBP and Ahrefs gap analysis.

9. **Dashboard usefulness, performance and code quality**
   - Command Center must stay a decision cockpit, not a connector registry or
     raw metric dump. First screen should prioritize today's marketer decisions,
     prompts to Codex, action focus and source freshness.
   - Dedicated routes may show drilldown details: `/merchant`,
     `/content-planner`, `/ads-doctor`, `/ga4`, `/localo`, `/actions`.
   - Reduce duplicate sections and outdated copy when browser/API proof shows
     confusion.
   - Performance work should target shared daily view-model/cache and route
     split points that reduce repeated heavy aggregation.
   - Current daily runtime already shares Command Center and Marketing Brief
     inputs. Next performance work should be based on fresh latency proof and
     should not recreate a second cache layer.
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

10. **Release, staging and live-test strategy**
   - Blocking CI/release tests must verify contracts, schemas, evidence IDs,
     source connectors, secret redaction, ActionObject safety, Polish output and
     no invented metrics.
   - Exact numeric values belong only in deterministic fixtures/seed tests.
     Live Ekologus metrics change over time and must not become flaky release
     assertions.
   - Live smoke checks may assert freshness, nonempty expected facts,
     ready/missing/blocked contract status and correct blocker rendering, not
     exact clicks, reviews, costs or ranking values.
   - Frontend schema drift must be caught before browser QA: use
     `pnpm --filter @wilq/shared-schemas test:live-contracts` to parse live API
     payloads with the same shared Zod schemas consumed by the dashboard.
   - Dashboard live e2e smoke should assert marketer-facing decision sections,
     safety copy, drilldown headings and absence of technical dumps, not stale
     copy or changing live counts.
   - Production monitoring should alert on source failures, stale freshness,
     zero facts where a contract is expected, secret leaks or unsafe apply
     attempts. Those are operational alerts, not brittle CI assertions.
   - Add release/live-test slices:
     1. Split deterministic fixture tests from live smoke checks. Fixture tests
        may assert exact values; live checks assert contract state, freshness,
        nonempty facts and correct blockers.
     2. Remove brittle release assertions against live metric values such as
        exact clicks, costs, revenue, reviews, rankings or issue counts. Keep
        those exact numbers only in fixtures or proof notes.
     3. Keep `scripts/pre_demo_gate.sh` as the small demo readiness gate:
        managed stack status, API health, live contract smoke, shared live
        schemas, dashboard API-backed route smoke and sequential core/all WILQ
        skill smokes. Add secret redaction and browser walkthrough checks only
        when the current slice touches those surfaces.
     4. Define the production gate separately: full `scripts/verify.sh`, API
        health, dashboard build, skill smokes/evals, security gate and live
        read-only connector checks.
     5. Add operational alerts for stale connector contracts, missing expected
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

1. First stabilize the core demo cockpit: Command Center and domain routes must
   show useful marketer decisions, prompt-to-Codex, evidence, blocked claims and
   safe next actions without technical filler.
2. Then harden the existing content-generation pipeline: evidence pack ->
   intent cluster -> inventory/canonical check -> brief -> draft/rewrite
   preview -> review ActionObject. Before coding, inventory the existing
   `content_diagnostics`, `content_refresh.py`, dashboard content route,
   ActionObject payload and content skills so we do not rebuild what already
   exists. Verify through content diagnostics, tactical queue, dashboard route
   and `wilq-content-strategist` / `wilq-gsc-content-doctor` evals.
3. Use `http://ekologus.dev.proudsite.pl/` only after the content pipeline is
   stable enough to adapt old evidence into target-site briefs without
   inventing metrics or page claims.
4. Run knowledge/source condensation in parallel when it directly improves a
   decision: ingest reputable source -> create knowledge card/rule -> link
   evidence requirement -> prove in eval that the rule changes the decision or
   blocks an unsafe claim.
5. If a task is blocked, take the next slice that increases demo truthfulness
   or marketer usefulness:
   - Merchant historical price/performance proof and safer product previews.
   - Localo `local_tasks` only if a side-effect-free read contract exists.
   - Ads Keyword Planner/change-impact/apply contracts only when source
     approval or change rows exist.
   - Semantic skill-reference cleanup only with fresh proof that a reference is
     carrying product behavior without a typed API field.
   - Dashboard performance/shared data-boundary work only with fresh latency or
     duplicate-aggregation evidence.
6. Do not advance a slice by prose alone. Each slice needs a concrete API,
   dashboard, skill, eval or docs proof matched to the changed surface.

## Stop Condition

Goal 001 is not done until the Ekologus marketer can open the dashboard, follow
the daily plan, inspect Ads/Merchant/Content/GA4/Localo decisions, copy/run the
matching Codex skill prompt, and receive Polish evidence-backed recommendations
with safe next actions and blocked claims. The strongest near-term finish line
is a solid Ekologus demo, not full BDOS-class production automation. The demo
must prove real API evidence, not static artifacts, prompt-only reasoning or
mock data. Full production is a later goal that adds multi-client support,
write/apply safety, alerts, agency operations and long-term knowledge memory.
The deferred production backlog is preserved in
`docs/goals/archive/bdos-deferred-backlog.md`; promote items from that file one
at a time only when they become the next evidence-backed slice.

## Final A-Z Audit Checklist

Run this checklist before claiming percent completion, "solid demo ready",
"dashboard done" or "all remaining tasks are known". The output of this audit
must be a compact task map: `ready`, `suspicious`, `task`, `blocked`,
`deferred` or `obsolete`. Do not leave findings only in chat.

**Continuation rule:** after every audit slice, update `docs/PROGRESS.md` with
the last completed checklist item, the next item to run, suspicious findings and
the verification command/result. After context loss, read that progress entry
and continue from the next unchecked item. Do not restart the A-Z audit from the
top unless the managed stack or source state changed enough to invalidate prior
proof.

1. **Repo/API inventory**
   - Read `docs/goals/001-goal.md`, `docs/PROGRESS.md`,
     `docs/evals/skill-coverage-audit.md` and the relevant source files before
     adding or removing tasks.
   - For every claimed gap, show the exact existing file/API endpoint first.
     If the thing already exists, classify the task as hardening, wiring or
     eval improvement, not build-from-zero.
   - Check live API health and managed stack state before judging product
     logic: `scripts/local_stack.sh status`, `/api/health`.
2. **Dashboard route audit**
   - Verify every route that a marketer can open:
     `/command-center`, `/ads-doctor`, `/ads-doctor/search-terms`,
     `/ads-doctor/custom-segments`, `/ads-doctor/demand-gen`, `/ga4`,
     `/seo-gsc`, `/content-planner`, `/merchant`, `/localo`, `/ahrefs`,
     `/opportunities`, `/actions`, `/actions/<id>`, `/workflows`,
     `/knowledge`, `/settings`.
   - Use the existing Playwright API-backed smoke as the first dashboard gate:
     `pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-api.spec.ts --workers=1`.
   - Current suspicious proof from 2026-06-24: this gate passed 9 tests and
     failed Content, Action Detail, Knowledge and Ahrefs route checks. Do not
     claim dashboard completeness until those are explained as fixed product
     issues or obsolete test expectations.
   - Each route must show marketer decisions, evidence counts/links, blocked
     claims, safe next actions and no registry/debug dumps unless the route is
     explicitly technical.
3. **API contract audit**
   - Check command center, marketing brief, tactical queue, actions, evidence,
     connector status and every domain diagnostic endpoint.
   - Confirm evidence/action lineage is where consumers expect it. Example:
     Command Center currently carries evidence/action IDs on `daily_decisions`;
     if a consumer expects top-level IDs, classify that as contract drift or
     adjust the consumer.
   - Confirm payload preview shape per ActionObject. Example: content action
     previews currently live under `payload`, not `payload_preview`; dashboard
     and tests must agree with the typed contract.
4. **Domain workflow audit**
   - Ads: verify campaign review, search terms, recommendations, budget pacing,
     impression share, custom segments and negative keyword review remain
     read-only until apply/audit contracts exist.
   - Merchant: verify issue clusters, sample products, product-state mapping,
     price-impact readiness and feed write blockers.
   - Content/GSC/Ahrefs/WordPress: verify `decision_queue`, brief previews,
     WordPress draft preview, inventory/canonical checks and Ahrefs support
     evidence are consistent across diagnostics, tactical queue, context-pack,
     dashboard and skills.
   - GA4: verify tracking-quality decisions, `(not set)` handling and blocked
     ROAS/revenue/profitability claims.
   - Localo: verify read contracts ready for rankings/GBP/competitors/reviews
     while `local_tasks`, writes and uplift claims remain blocked.
5. **Skills and Codex workflow audit**
   - For each of the 12 WILQ skills, run deterministic smoke first, then
     non-interactive eval only when the skill contract or prompt path changed.
   - Confirm each skill uses typed WILQ API contracts, returns Polish operator
     output, carries evidence IDs/source connectors/action IDs and blocks
     unsafe claims.
   - Confirm dashboard "prompt to Codex" copy maps to the right skill,
     endpoint, evidence set, ActionObject and blocked claims.
   - Skill references may explain contracts and output format only. If a
     reference contains product behavior, workaround prose or bugfix logic,
     move that behavior into API/schema/view-model/eval.
6. **Expert rules and knowledge audit**
   - `wilq/expert/**` is the structured expert-rule layer: versioned YAML rules
     for Ads, SEO, content, analytics, local, merchant and social decisions.
   - Verify expert rules are loaded through code and affect decisions or
     blocked claims through typed contracts, not loose prompt text.
   - Verify knowledge cards/playbooks have source lineage, confidence/freshness
     and at least one eval proving that the rule/card improves a decision or
     blocks an unsafe claim before promoting it as product value.
7. **Test strategy audit**
   - Split deterministic fixture tests from live smoke checks. Live metrics
     change and must not be asserted as exact values.
   - Keep broad `scripts/verify.sh` for final/broad-risk gates. For daily
     slices, run the smallest test that proves the touched surface.
   - Flag test failures as one of: product bug, schema drift, stale test
     expectation, slow endpoint/performance issue, or environment issue.
8. **Code quality audit**
   - Identify monoliths that slow development, especially dashboard route files
     and large shared panels. Do not refactor them opportunistically; create a
     dedicated quality slice only when extraction makes current work faster or
     safer.
   - Check for duplicated decision logic between API, dashboard and skills.
     Dashboard and skills must consume the API's typed decisions instead of
     rebuilding ranking/grouping in UI or prompt prose.
9. **Task extraction**
   - Convert every suspicious finding into a concrete task with: owner layer,
     proof, smallest fix, focused verification and demo impact.
   - Remove ready/done/outdated tasks from the active goal. Archive deferred
     BDOS-class work in `docs/goals/archive/bdos-deferred-backlog.md`.
   - Do not claim "100% certainty" until this checklist has a fresh result and
     every suspicious item is either fixed, deliberately deferred or explicitly
     marked blocked with the missing contract/input.

2026-06-24 domain workflow checkpoint: dashboard route smoke and API contract
first pass are complete. Domain workflow audit found and fixed three confirmed
contract-drift issues: Content and Merchant dashboard summaries no longer invent
fallback ActionObject IDs, Ads diagnostic proof reads blocked/missing/gate
rollups from `operator_summary`, and GA4 now exposes
`decision_blocker_count` to distinguish blocked decision-queue items from
section/contract blockers. Focused proof passed: GA4 API pytest subset,
shared-schema live contracts, dashboard route tests for Ads/Merchant/GA4/Ahrefs
and dashboard typecheck. Continue from the remaining domain workflow queue:
scan other marketer routes for local product-decision rebuilding, then proceed
to skill/Codex workflow audit. Follow-up same day: GA4 route fallback to
`act_review_ga4_tracking_quality` was removed and GA4 now displays
`decision_blocker_count` from the API. Custom Segments route magic decision ID
for a status badge was removed; remaining `decision_queue.find(...)` usages in
Content and Localo are classified as presentational focus/readout helpers unless
fresh route proof shows otherwise.

2026-06-24 content-skill checkpoint: content brief usefulness is now guarded
across API, context-pack and skill eval. `act_prepare_content_refresh_queue`
already exposed richer `content_brief_preview_v1` fields for writer work, but
`POST /api/codex/context-pack` compacted them away for
`wilq-content-strategist`. Fixed compaction to preserve `content_angle`,
`audience`, `key_objections`, `cta_direction`, `internal_link_direction`,
`source_facts`, `missing_evidence` and `forbidden_claims` in compact form.
Focused proof passed: content context-pack API pytest, codex skill eval case
pytest, managed stack restart, content strategist smoke and non-interactive
`wilq-content-strategist` eval
`.local-lab/evals/codex-skill/20260624T075942Z/wilq-content-strategist/result.json`.
Continue from skill/reference semantic audit and remaining content usefulness
gaps; do not reopen the rich brief eval unless the content preview contract
changes.

2026-06-24 skill/reference semantic checkpoint: the hygiene checker passed and
manual semantic pass found no broad skill-reference workaround pattern. Two
references were tightened to name existing typed context-pack fields rather than
invent behavior: `wilq-campaign-builder` uses `ads_diagnostics` plus
`content_landing_context`, and `wilq-social-publisher` uses
`social_draft_context`. Confirmed API-layer drift fixed: social draft
ActionObjects now exclude `ekologus.dev.proudsite.pl` inventory rows from
candidate inputs/evidence, because the dev site is a later target context, not
current source evidence. Focused proof passed: social API pytest subset, managed
stack restart, social/campaign skill smokes, live social context-pack URL check,
skill hygiene and `git diff --check`. Continue from remaining content
usefulness/target-site adaptation, then expert/knowledge rule audit.

2026-06-24 content target-site checkpoint: content brief and WordPress draft
previews now expose source URL/host and target-site URL/host/status through the
typed ActionObject payload, skill-scoped context-pack and dashboard preview
cards. Public content `target_site_url` is preserved by redaction under explicit
safe keys. Deterministic API proof covers `ekologus.dev.proudsite.pl` as
`target_site_alias_match`; live current data still resolves to
`current_site_match` when WordPress inventory points at `www.ekologus.pl`.
Focused proof passed: content API subset 4 passed, content route test passed,
Action Detail content preview test passed, dashboard typecheck passed, content
strategist smoke passed and `git diff --check` passed. Continue Final A-Z from
expert rules and knowledge audit.

2026-06-24 expert/knowledge checkpoint: first confirmed issue fixed in the
content workflow. Expert rules and knowledge cards existed and were scoped into
`wilq-content-strategist`, but content diagnostic decisions/sections did not
carry `knowledge_card_ids` or `expert_rule_ids`, so the decision queue did not
prove which rule/card supported a refresh, Ahrefs review or GA4 tracking block.
Follow-up at 2026-06-24 11:02 CEST: the same direct decision-lineage gap is
fixed for Merchant, GA4, Localo and Ahrefs diagnostics. Live API previously
returned null lineage on the first decision in each domain; live API now
returns Merchant cards/rules, GA4 diagnostics card/rule, Localo local SEO
card/rules and Ahrefs content-gap card/rule on domain decision queues. The
matching skill context-packs include the referenced summaries. Focused checks:
Python compile, ruff, API contract subset 4 passed, managed stack restart, live
diagnostics/context-pack checks, shared live schema smoke 10 passed on warm
rerun and four sequential deterministic skill smokes passed. Continue Final
A-Z from test strategy/code-quality audit and task extraction; record the
parallel smoke timeout as a performance/pre-demo-gate gotcha, not as a lineage
failure.
`ContentDiagnosticSection` and `ContentDecisionItem` now expose those IDs, and
live API/context-pack proof shows the IDs on content decisions while the scoped
skill context contains the matching summaries. Focused proof passed: content
API pytest subset, Python compile, managed stack restart, live API/context-pack
check, content strategist smoke and shared live schema smoke. Continue the
expert/knowledge audit by checking other non-Ads domain diagnostics for the
same direct decision-lineage gap before moving to test strategy/code quality.
