# WILQ Ekologus Demo ExecPlan

This is the canonical overnight execution plan for WILQ Marketing Operating
System in this checkout. It is written as a living plan: every agent working on
the active demo goal should update this file when a milestone is completed, a
task is reclassified, or a blocker is proven. Keep `docs/PROGRESS.md` short and
use this file for the full execution map.

## Purpose

WILQ should become a useful daily cockpit for the Ekologus marketer, not a
prompt pack, static report, or fake automation demo. The useful demo is narrow:
the marketer starts in Command Center, follows Merchant, Content Planner, Ads
Doctor and GA4, and sees one strong content workflow that turns current
Ekologus evidence into a safe Polish brief or draft plan for the new site
context `ekologus.dev.proudsite.pl`.

Success does not mean full BDOS, full Ads optimizer, feed repair, publishing
automation, revenue recovery, approval recovery or automated apply. Success
means the current review cockpit is evidence-backed, honest about missing data,
usable by a marketer, and guarded by typed WILQ API contracts, ActionObject
validation, preview, confirmation and audit.

This plan follows two Codex operating patterns from official OpenAI docs:
ExecPlans are self-contained living documents with progress, discoveries,
decisions, milestones and validation; Goals are durable completion contracts
with outcome, verification surface, constraints, boundaries, iteration policy
and blocked stop condition.

## Repository Context

Work from `/home/krn/coding/krn/active/wilq-seo`.

Important files:

- `AGENTS.md`: project rules, command style and WILQ product constraints.
- `docs/CONTEXT.md`: recovery index for runtime, skills and docs.
- `docs/PROGRESS.md`: short recovery ledger only.
- `docs/goals/001-goal.md`: older active goal and final A-Z audit checklist.
- `docs/audits/002-2026-06-24-second-opinion-synthesis.md`: condensed external
  2nd opinion.
- `docs/evals/skill-eval-ledger.md`: skill eval evidence.
- `docs/evals/skill-coverage-audit.md`: 12-skill coverage table.
- `.agents/skills/wilq-*`: WILQ operator skills.
- `apps/api/wilq_api/main.py`, `wilq/**`: WILQ API, diagnostics, schemas,
  actions and knowledge/expert logic.
- `apps/dashboard/src/**`: dashboard route and component surfaces.
- `packages/shared-schemas/src/index.ts`: frontend/backend shared contracts.

Command rules:

- Prefix shell commands with `rtk`.
- Use `uv run ...` for Python commands that import WILQ API.
- Use `scripts/local_stack.sh start|status|restart|logs` for the local API and
  dashboard stack.
- Use focused verification first. Use `scripts/verify.sh` only for broad/final
  gates.

Canonical runtime URLs:

- WILQ API: `http://127.0.0.1:8000`
- Dashboard: `http://127.0.0.1:5173/command-center`

## Current State On 2026-06-24

Ready for current demo:

- Command Center gives the narrow daily path and links to the core work.
- Merchant shows feed issue review, freshness and safety boundaries. It must
  not treat reported issue occurrences as unique products.
- Content Planner shows GSC/WP-backed refresh or merge decisions, source/target
  context, H1/H2/FAQ/CTA/source facts, missing evidence and forbidden claims.
- Ads Doctor shows review candidates, KPI context and search-term/recommendation
  surfaces while blocking CPA, ROAS, wasted-budget, profitability and apply
  claims without missing contracts.
- GA4 shows tracking and landing/source/campaign quality while treating
  `(not set)` as a measurement/attribution problem, not campaign failure.
- Action detail now uses marketer-facing "podgląd zmian" copy instead of
  visible "dry-run" proof-run language.
- `scripts/pre_demo_gate.sh` previously passed the solid demo gate. Treat this
  as contract/demo proof, not marketer UAT or full production proof.
- Skill/reference/eval baseline is current-demo ready. Reopen only with a
  concrete failing or misleading current proof.

Still incomplete:

- No real marketer UAT has proven that the dashboard saves time or improves
  decisions.
- The new site `ekologus.dev.proudsite.pl` is target context, not a complete
  source inventory or staging publish path.
- Content has typed source/target/gate fields and now exposes target-site
  migration candidates and mapping status in the operator summary, but it still
  lacks a confirmed full migration map, staging handoff and post-publication
  loop.
- Ads lacks confirmed target CPA/ROAS, approved Keyword Planner enrichment,
  change-impact windows and apply/audit contracts.
- Merchant lacks product IDs/SKU as a full product queue, historical price
  changes and before/after performance windows.
- GA4 lacks enough attribution/revenue confidence for ROAS/profitability/funnel
  verdicts.
- Localo read evidence must not be inflated into tasks, writes or uplift.
- Full BDOS/agency-grade production remains deferred.

## Completion Definition

This goal is complete only when a requirement-by-requirement audit can prove all
of the following from the current checkout:

- the local stack is healthy and the core pre-demo gate passes;
- the dashboard path `Command Center -> Merchant -> Content Planner -> Ads
  Doctor -> GA4` works from live WILQ API contracts;
- each core route tells a Polish marketer what to do next without requiring raw
  JSON, raw IDs or internal model names on the first screen;
- one content workflow for the new-site context shows source evidence,
  target context, inventory/canonical/duplicate gates, brief or draft-plan
  fields, missing evidence, forbidden claims, evidence IDs and source
  connectors;
- focused adversarial skill evals prove that Content, Ads, Merchant, GA4 and
  Localo do not overclaim from partial evidence;
- any remaining missing contract is labelled as blocked or deferred, not hidden;
- marketer UAT is captured, or explicitly deferred by the owner with the
  remaining confusion converted into tasks;
- this `PLAN.md` and short `docs/PROGRESS.md` identify the exact next item so a
  future continuation does not repeat completed checks.

Do not mark the goal complete only because tests pass. Test and browser proof
must support a useful marketer workflow, and unsafe product claims must remain
blocked.

## Full Task Inventory

Use this inventory to prevent task loss after compaction. Reclassify tasks as
`ready`, `hardening`, `task`, `blocked`, `deferred_bdos` or `obsolete` before
touching code. Remove items from the active queue once proof says they are
ready.

### A. Solid Ekologus Demo Must-Haves

Active demo work is narrow and depth-first.

- `task`: Run or explicitly defer the marketer UAT script. This is the only
  remaining proof gap between browser/eval readiness and "marketer gets value".
- `hardening`: Keep `ActionObject`/raw payload/technical ID language out of
  first-screen marketer copy while preserving traceability in details.
- `hardening`: Keep Command Center CTAs aligned to the narrow path:
  `/merchant`, `/content-planner`, `/ads-doctor`, `/ga4`.
- `ready`: Pre-demo gate passed after current hardening; rerun only after a
  material API/dashboard/skill slice.
- `ready`: Content, Ads, Merchant, GA4 and Localo adversarial evals have fresh
  2026-06-24 proof artifacts.

### B. Content Generation And New-Site Workflow

This is the highest-value product direction after the current demo proof. It
must be built as a typed WILQ pipeline, not a prompt-only drafting trick.

- `ready`: Content Planner exposes source/target context plus inventory,
  canonical and duplicate gate fields.
- `ready`: Content operator summary exposes `ekologus.dev.proudsite.pl`
  target-site mapping status without pretending that current-site inventory is
  already a migration map.
- `ready`: Current-site content decisions expose old-to-new candidate URLs for
  `ekologus.dev.proudsite.pl` and mark them `needs_review` before draft or
  staging work.
- `ready`: WordPress vendor reads now enrich REST/public-sitemap inventory with
  safe page metadata fields `title_or_h1` and `canonical_url` when available,
  using a short metadata timeout and without storing full HTML bodies. The
  fields flow through content diagnostics, ActionObject previews, reviewed draft
  previews, dashboard cards, shared schemas and content-strategist context-pack.
  Proof: focused API/dashboard/shared-schema tests and
  `.local-lab/proof/content-target-metadata/content-strategist-smoke.json`.
- `blocked`: Current live content decisions still need explicit old-to-new
  mapping review for `ekologus.dev.proudsite.pl`; the latest read-only
  WordPress run has inventory metadata facts, but `/api/content/diagnostics`
  still reports `target_site_mapping_review_needed` for the active queue.
- `ready`: Content decisions, content ActionObject previews, reviewed draft
  previews, dashboard cards and content-strategist context-pack now expose the
  WordPress inventory facts WILQ actually has for target URLs:
  `content_type`, `status`, `inventory_source`, `modified_gmt`, plus missing
  fields such as `title_or_h1` and `canonical_url`. This increases migration
  review confidence without unlocking draft, staging or publish.
- `task`: Confirm explicit old-to-new URL mapping against dev-site inventory
  when both old/current and `ekologus.dev.proudsite.pl` inventory exist for
  related content.
- `ready`: Content ActionObject payload, reviewed draft preview and
  content-strategist context-pack preserve target-site migration candidate,
  status and summary fields. Current old-site rows are `needs_review`, so draft
  or staging work remains blocked until mapping is confirmed.
- `ready`: Content decision queue, ActionObject previews, reviewed draft
  previews and content-strategist context-pack expose
  `target_site_review_requirements`, including target inventory mapping,
  canonical review, duplicate/cannibalization check and human confirmation.
- `ready`: Reviewed WordPress draft previews expose `draft_generation_status`
  and `draft_blockers`. A reviewed candidate with `needs_review` target mapping
  stays `blocked_pending_target_mapping`; preview/review is allowed for audit,
  but staging, publish and apply remain blocked.
- `ready`: Duplicate/canonical gates are promoted into content ActionObject
  brief previews, reviewed draft previews, dashboard draft cards and
  content-strategist context-pack. Draft preview readiness now stays blocked for
  canonical/duplicate review instead of becoming ready just because target
  inventory is found. Proof:
  `.local-lab/proof/content-draft-gates/content-strategist-smoke.json`.
- `ready`: Content ActionObject brief previews, reviewed draft previews,
  dashboard cards and content-strategist context-pack expose publication-quality
  review fields: title/meta/schema directions, legal/factual review notes,
  brand voice notes, `publication_readiness_status` and publication blockers.
  These fields improve handoff quality without unlocking staging, publish or
  apply. Proof:
  `.local-lab/proof/content-publication-brief/content-strategist-smoke.json`.
- `ready`: Reviewed WordPress draft previews expose
  `content_draft_generation_v1`, which defines language, allowed output kind,
  required gates, required draft elements and forbidden outputs. Current live
  candidates stay `outline_only_until_gates_pass` until mapping,
  canonical/duplicate, legal/factual and human checks pass. Proof:
  `.local-lab/proof/content-draft-contract/content-strategist-smoke.json`.
- `blocked`: WordPress/staging handoff remains blocked until there is a typed
  staging ActionObject with preview, human confirmation, audit and no automatic
  publish.
- `deferred_bdos`: Post-publication measurement loop is after staging handoff:
  compare GSC/GA4 windows, detect refresh/merge/kill follow-ups and feed the
  result back into knowledge cards.

### C. Data Contracts Required For Deeper Claims

These are not all demo blockers, but they are why WILQ must not overclaim.

- `task`: Ads target CPA/ROAS and business guardrail confirmation are required
  before profitability, wasted-budget or scaling verdicts.
- `task`: Ads change history, pacing windows and recommendation impact checks
  are required before optimizer language.
- `blocked`: Keyword Planner/custom segments remain limited by developer-token
  approval/readiness until the Google Ads read contract is ready.
- `task`: Merchant product IDs/SKU and unique-product semantics must become a
  first-class product queue before product-by-product review claims.
- `task`: Merchant price/performance windows and product joins with Ads/GA4 are
  required before product ROAS, revenue recovery or price-impact claims.
- `task`: GA4 conversion/key event mapping and attribution confidence are
  required before funnel, revenue, ROAS or campaign-quality verdicts.
- `task`: Localo detailed rankings, GBP, competitor and review facts can inform
  local review, but local tasks/write/uplift contracts are still separate.

### D. Skills, Evals And Prompt Quality

Skills are operator workflows over WILQ API. They are not the product brain.

- `ready`: The current 12-skill baseline has deterministic smoke/eval coverage
  and current core-skill adversarial proofs.
- `task`: Add marketer-style messy prompts to eval cases, not only clean
  operator prompts. The skill must fetch WILQ API and refuse unsupported claims.
- `task`: Add decision-quality rubrics that check usefulness, prioritization,
  blocked-claim handling and safe next steps, not only output shape.
- `task`: Add a human usefulness rubric after marketer UAT: "Czy wiem co
  zrobić?", "Czy to oszczędza czas?", "Gdzie copy jest techniczne?".
- `hardening`: Keep skill references as API usage/output contracts. Any smarter
  decision must first be added to API/schema/view-model/expert rules and then
  consumed by the skill.
- `deferred_bdos`: New skills for full content drafting, campaign building,
  social publishing and Demand Gen should stay review-only until their data and
  write contracts are implemented.

### E. Dashboard Product UX

Dashboard is the marketer cockpit. Registry and debug details are allowed only
after the first decision layer is clear.

- `ready`: Marketer-facing action wording now avoids `ActionObjecty` on the
  core runtime routes and route smoke surfaces while preserving route names,
  IDs and technical traceability. Fresh proof:
  `WILQ_E2E_API_PORT=8876 WILQ_E2E_DASHBOARD_PORT=5374 rtk pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts`.
- `ready`: Raw payload debug wording is hidden behind a technical payload
  toggle on Action detail instead of first-screen debug language.
- `task`: Keep route cards action-oriented: "what happened", "what to do next",
  "what claim is blocked", "where to click".
- `task`: Add a core-domain quick switcher or improve Command Center links if
  marketer UAT shows navigation confusion.
- `hardening`: Do not redesign the visual system broadly before UAT. Fix one
  proven blocker at a time.
- `deferred_bdos`: Split very large dashboard modules after the demo path is
  stable; do not refactor them just to make line counts smaller during demo
  hardening.

### F. Knowledge Compiler And Memory Layer

Knowledge must be structured, sourced and freshness-aware before it influences
recommendations.

- `task`: Add a source registry with source type, owner, URL/path, checked date,
  confidence and freshness state for official docs, industry sources, Ekologus
  history and marketer feedback.
- `task`: Add freshness/confidence lifecycle for knowledge cards so outdated
  cards lower confidence or become blockers.
- `task`: Add rule-to-decision lineage tests showing that a decision exposes the
  knowledge cards, playbooks or expert rules that shaped it.
- `task`: Add marketer feedback as a knowledge source after UAT and after real
  review decisions.
- `deferred_bdos`: External source ingestion, benchmark libraries and broader
  RAG/vector storage wait until the typed knowledge compiler is useful.

### G. Infrastructure, Security And Productionization

These tasks matter for production but should not steal focus from the Ekologus
demo unless they block proof.

- `task`: Keep secret handling redacted and never commit `.env`, tokens,
  credential JSON, redirect codes or raw vendor response bodies.
- `task`: Keep connector refreshes read-only and persisted with sanitized
  summaries, freshness, evidence IDs and status.
- `task`: Add observability for long-running jobs and connector refreshes before
  production deployment.
- `deferred_bdos`: Production auth/permissions, account isolation, deployment,
  monitoring and multi-client operations come after Ekologus works deeply.

### H. Better BDOS / Agency-Grade Backlog

Archive these as real future work, not active demo blockers.

- `deferred_bdos`: Full Ads apply path with SafetyLimits, mutation adapters,
  rollback/partial-failure handling and audit.
- `deferred_bdos`: Budget optimizer using confirmed business targets, change
  history, attribution and impact windows.
- `deferred_bdos`: Demand Gen builder and creative quality loop.
- `deferred_bdos`: Social publishing apply path.
- `deferred_bdos`: Merchant feed write/repair automation and approval recovery.
- `deferred_bdos`: Localo/GBP write, review response workflow and local uplift
  measurement.
- `deferred_bdos`: Multi-client, permissions, production auth, deployment,
  monitoring and agency operations.

## Quality Control Rules

Use these rules before every implementation slice:

- Search first and read enough context before editing. Prefer existing helpers
  and contracts over new abstractions.
- If a task is already ready, mark it ready and move to the next useful risk.
  Do not rerun the same test unless the touched slice could have regressed it.
- If a test checks only shape, call it a smoke test. Do not treat it as
  marketer value proof.
- If a live metric can change, assert shape, freshness, evidence and blocked
  claims rather than exact clicks, cost, rank or revenue.
- For docs-only updates, `rtk git diff --check` is enough unless generated
  contracts are affected.
- For dashboard copy/component edits, run the focused route/component test and
  typecheck only when TS props/contracts changed.
- For API/schema/action edits, run the smallest affected pytest subset first.
- For skill/eval edits, run the touched deterministic smoke and targeted
  `scripts/codex_skill_eval.sh --skill <skill>` when behavior changed.
- Use browser proof when the claim is UX comprehension or route behavior.
- Update `PLAN.md` and short `docs/PROGRESS.md` before committing a slice that
  changes task status.

## Progress

- [x] Capture external 2nd-opinion synthesis in
  `docs/audits/002-2026-06-24-second-opinion-synthesis.md`.
- [x] Keep `docs/PROGRESS.md` short and current.
- [x] Expose content source/target context through typed API, shared schema and
  Content Planner cards.
- [x] Browser-walk the narrow demo path and save snapshots under
  `.local-lab/proof/dashboard/marketer-demo-walkthrough/`.
- [x] Clean Action detail marketer-facing copy from proof-run/dry-run wording.
- [x] Verify the latest target-site adversarial content eval through the real
  non-interactive Codex harness. Proof:
  `.local-lab/evals/codex-skill/20260624T125302Z/wilq-content-strategist/result.json`;
  passed with `operator_usefulness_score=4`, API evidence, source connectors,
  canonical/duplicate/target-context wording and blocked publish/ranking/lead/
  revenue/duplicate-free/source-evidence overclaims.
- [x] Add or verify the next highest-risk adversarial overclaim eval. Proof:
  `.local-lab/evals/codex-skill/20260624T125820Z/wilq-ads-doctor/result.json`;
  passed with `operator_usefulness_score=5`, validated review-only Ads
  ActionObjects and blocked CPA/ROAS/wasted-budget/budget-scaling/
  recommendation-apply/targeting-apply/negative-keyword-apply claims.
- [x] Verify Merchant occurrences-not-unique-products eval proof. Proof:
  `.local-lab/evals/codex-skill/20260624T132303Z/wilq-merchant-feed-operator/result.json`;
  passed with `operator_usefulness_score=5`, `decision_queue` as the final
  review queue, `reported_issue_occurrences` not as unique products/SKU, samples
  not as full product queue, validated `act_review_merchant_feed_issues` and
  blocked product ROAS, product revenue recovery, price change impact, approval
  restored and feed write claims.
- [x] Verify GA4 measurement-boundary eval proof. Proof:
  `.local-lab/evals/codex-skill/20260624T132845Z/wilq-ga4-analyst/result.json`;
  passed with `operator_usefulness_score=5`, `fix_measurement` for `(not set)`
  rows, explicit "do not judge campaign/page" handling, validated
  `act_review_ga4_tracking_quality`, no invented `review_landing_mapping` item
  when API did not return it, and blocked GA4 write, ROAS, attribution verdict,
  conversion drop, conversion rate, profitability, revenue and tracking fixed
  claims.
- [x] Verify Localo read-only visibility proof. Proof:
  `.local-lab/evals/codex-skill/20260624T133326Z/wilq-localo-operator/result.json`;
  passed with `operator_usefulness_score=5`, `mcp_initialize_status=200`,
  `access_ready`, read-only Localo facts, validated
  `act_review_localo_visibility_facts`, `local_visibility_review_preview_v1`
  and write/apply/uplift claims limited to evidence and blocked where not
  supported.
- [x] Add or verify a target-site duplicate/canonical gate for content. Proof:
  API decisions now expose `inventory_gate_status`, `canonical_gate_status`,
  `duplicate_gate_status` and `content_gate_summary`; browser snapshot
  `.local-lab/proof/dashboard/content-target-gate/content-planner-gates.txt`
  shows `Inventory gate`, `Canonical` and `Duplikaty` on `/content-planner`.
- [x] Run final pre-demo gate after the next material code/eval slice. Proof:
  `scripts/pre_demo_gate.sh --core-skills` passed after the content
  duplicate/canonical gate change.
- [x] Produce a short marketer UAT script:
  `docs/handoffs/2026-06-24-marketer-uat-script.md`.
- [x] Start dashboard language hardening by replacing first-screen
  `ActionObjecty` copy with marketer-facing action wording while preserving
  technical IDs and routes. Proof:
  `.local-lab/proof/dashboard/action-labels/actions-route-snapshot.txt`.
- [x] Expose content target-site mapping truth in typed API, shared schema and
  Content Planner operator summary. Proof: live API returns
  `target_site_host=ekologus.dev.proudsite.pl`,
  `target_site_alias_match_count=0`, `current_site_match_count=4`,
  `target_site_mapping_review_count=4`,
  `target_site_mapping_status=target_site_mapping_review_needed`; live API
  proof `.local-lab/proof/dashboard/content-migration-map/api-summary.json`
  lists old-to-new candidate URLs with `needs_review`, and browser snapshot
  `.local-lab/proof/dashboard/content-migration-map/content-planner-snapshot.txt`
  shows `do mapowania: 4`, `status: wymaga mapowania` plus migration chips on
  `/content-planner`.
- [x] Carry content target-site migration status into
  `act_prepare_content_refresh_queue`, reviewed draft previews and the
  content-strategist context-pack. Proof:
  `.local-lab/proof/dashboard/content-action-migration/action-payload-summary.json`;
  focused tests passed for content API contracts/context-pack and
  `wilq-content-strategist/scripts/smoke_skill_contract.py` passed after stack
  restart.
- [x] Expose target-site review requirements in content diagnostics,
  ActionObject brief previews, reviewed draft previews, dashboard preview cards
  and the content-strategist context-pack. Proof:
  `.local-lab/proof/dashboard/content-target-review-requirements/action-review-requirements.json`;
  focused API tests, `ContentDiagnosticSurface` dashboard test and
  `wilq-content-strategist/scripts/smoke_skill_contract.py` passed.
- [x] Harden core demo route copy from `ActionObject` wording to marketer-facing
  `akcja/akcje` labels in Content, Merchant and GA4 first-screen links/cards.
  Focused dashboard tests passed; technical component names and trace IDs remain
  unchanged.
- [ ] Run marketer UAT or explicitly defer it with owner decision.

Update this list after each slice. Do not keep done/outdated tasks in the active
queue unless they are needed as proof for the next step.

## Overnight Operating Rules

Work until the next defensible slice is complete, then verify it, update this
plan and commit. Do not stop after analysis when a safe implementation step is
available.

Before each slice:

1. Read `git status --branch --short`.
2. Read `docs/PROGRESS.md` and this `PLAN.md`.
3. Check live stack status if the slice touches runtime behavior.
4. Classify the target as `ready`, `hardening`, `task`, `blocked`,
   `deferred_bdos` or `obsolete`.
5. Choose the smallest check that proves the risk.

After each slice:

1. Run the focused check that covers the touched contract.
2. Save browser or command proof under `.local-lab/proof/...` when useful.
3. Update this file and, if recovery would otherwise be unclear,
   `docs/PROGRESS.md`.
4. Commit a coherent slice with a Conventional Commit message.
5. Do not mark the overall goal complete unless the completion audit proves all
   demo requirements.

Do not:

- invent marketing metrics;
- treat screenshots as the only product proof;
- repair business logic in skill references or dashboard copy;
- hide missing credentials or stale data;
- claim apply, publish, feed repair, Ads optimization, ROAS, revenue recovery,
  approval recovery, local uplift or ranking gain without typed evidence and
  validated ActionObject flow;
- add new broad surfaces before the core Ekologus workflow is deep.

## Milestone 0: Recovery And State Audit

At the start of any continuation, recover current truth before acting. This
protects the project from repeating old tests or implementing tasks that are
already done.

Run from repo root:

    rtk git status --branch --short
    rtk sed -n '1,220p' PLAN.md
    rtk sed -n '1,180p' docs/PROGRESS.md
    rtk scripts/local_stack.sh status

Acceptance:

- The agent can state the current dirty files.
- The agent can state the next unchecked item from `Progress`.
- If stack is needed, API and dashboard are managed and ready, or the blocker
  is recorded.

## Milestone 1: Adversarial Eval Hardening

This milestone proves that WILQ skills do not pass while making unsafe or
unsupported claims. It is more valuable than adding another dashboard surface.

Preferred order:

1. Content target-site boundary:
   `ekologus.dev.proudsite.pl` is target context, not source evidence. The skill
   must not claim duplicate-free content, publish readiness, ranking gain, lead
   uplift or revenue impact without validated evidence and write/apply path.
2. Ads CPA/ROAS/wasted-budget boundary:
   live Ads facts can order review, but cannot make profitability or wasted
   budget verdicts without confirmed target CPA/ROAS, strategy review, history
   and apply/audit contracts.
3. Merchant occurrence/Product boundary:
   reported issue occurrences are not unique products; no product ROAS, approval
   recovery, price-impact or feed repair without product IDs/SKU, history and
   performance windows.
4. GA4 measurement boundary:
   `(not set)` is a tracking or attribution blocker, not proof of bad campaign
   or landing performance.
5. Localo access boundary:
   access/readiness is not local task completion, GBP write, review response or
   local uplift.

Files likely involved:

- `docs/evals/cases/wilq-skill-eval-cases.json`
- `tests/test_codex_skill_eval_cases.py`
- `docs/evals/skill-eval-ledger.md`
- `.agents/skills/<skill>/scripts/smoke_skill_contract.py`

Focused verification examples:

    rtk uv run pytest tests/test_codex_skill_eval_cases.py -q
    rtk scripts/codex_skill_eval.sh --skill wilq-content-strategist
    rtk git diff --check

Acceptance:

- A bad output that makes the unsafe claim would fail.
- The good output still includes Polish operator guidance, evidence IDs/source
  connectors, ActionObject IDs where applicable, and blocked claims.
- The ledger records the eval artifact path only after the run succeeds.

## Milestone 2: Content Target-Site Duplicate And Canonical Gate

This milestone makes the strongest demo value deeper: content for the new site
must use current Ekologus evidence without creating SEO duplicates.

Plain meaning:

- Source evidence is current data from `ekologus.pl`, `sklep.ekologus.pl`, GSC,
  GA4, Ahrefs, Ads, Merchant, Localo and WordPress inventory.
- Target context is where content may eventually go, currently
  `ekologus.dev.proudsite.pl`.
- A duplicate/canonical gate answers whether the topic should be refresh,
  merge, create or block before any brief or draft is treated as useful.

Expected behavior:

- Existing BDO/Zielony Lad style topics should prefer refresh or merge when
  WordPress/GSC evidence shows a current URL.
- Create should be blocked or downgraded when inventory/canonical evidence is
  missing.
- A brief can propose H1/H2/FAQ/CTA/source facts, but must keep missing
  evidence and forbidden claims visible.
- No WordPress staging/publish claim is allowed without ActionObject validation,
  preview, human confirmation and audit.

Files likely involved:

- `wilq/briefing/content_diagnostics.py`
- `wilq/schemas.py`
- `packages/shared-schemas/src/index.ts`
- `apps/dashboard/src/routes/ContentDiagnosticSurface.tsx`
- `apps/dashboard/src/routes/DetailPanels.tsx`
- `tests/test_api_contracts.py`
- content skill smoke/eval files if the API contract changes

Focused verification examples:

    rtk uv run pytest tests/test_api_contracts.py -k content
    rtk pnpm --filter @wilq/dashboard test -- ContentDiagnosticSurface
    rtk proxy pnpm --filter @wilq/dashboard typecheck
    rtk scripts/local_stack.sh restart
    rtk curl -sS http://127.0.0.1:8000/api/content/diagnostics

Browser proof:

Use `agent-browser` with `XDG_RUNTIME_DIR=$PWD/.local-lab/xdg-runtime` and save
snapshots under `.local-lab/proof/dashboard/content-target-gate/`.

Acceptance:

- Dashboard and API agree on source URL, target context, decision mode and
  blocked claims.
- The content skill consumes the same API fields instead of re-deciding in
  prompt prose.

## Milestone 3: Marketer Demo UX Hardening

This milestone removes UI friction only when browser proof shows it blocks
understanding. Do not do broad visual cleanup.

Candidate fixes:

- Done 2026-06-24: marketer-facing action labels use `Akcje do walidacji` /
  action wording in the core route smoke path, while ActionObject IDs and route
  names remain stable for traceability.
- Done 2026-06-24: Action detail no longer exposes `Surowy payload debug` copy;
  payload inspection is a technical toggle.
- Add clearer CTA copy to core route cards when a marketer cannot tell what to
  click next.
- Keep Command Center, Merchant, Content Planner, Ads Doctor and GA4 as the
  main demo path. Do not make Opportunities, Knowledge, Social or Demand Gen
  the demo entry point unless a fresh proof says they are ready.

Files likely involved:

- `apps/dashboard/src/components/Shell.tsx`
- `apps/dashboard/src/routes/CommandCenterRoute.tsx`
- `apps/dashboard/src/routes/ActionObjectPanels.tsx`
- `apps/dashboard/src/routes/DetailPanels.tsx`
- route-specific tests under `apps/dashboard/src/routes/*.test.tsx`
- `apps/dashboard/e2e/dashboard-api.spec.ts`

Focused verification examples:

    rtk pnpm --filter @wilq/dashboard test -- App.test.tsx --runInBand
    rtk proxy pnpm --filter @wilq/dashboard typecheck
    rtk pnpm --filter @wilq/dashboard exec playwright test e2e/dashboard-api.spec.ts -g "action detail route"

Acceptance:

- The first screen says what the marketer should do next.
- Traceability remains available in details.
- No API contract or ActionObject ID is renamed.

## Milestone 4: Marketer UAT Script And Proof

This milestone turns "it renders" into "a marketer gets value".

Write a short UAT script under `docs/handoffs/` only if it will be used. Keep
it short enough that a marketer can run it in 15 minutes.

Script should ask the marketer to:

1. Open `/command-center`.
2. Pick one daily decision.
3. Open Merchant and identify one feed blocker without claiming feed repair.
4. Open Content Planner and pick one refresh/merge brief.
5. Open Ads Doctor and identify one review item without CPA/ROAS/wasted-budget
   verdict.
6. Open GA4 and identify one measurement issue without judging campaign
   quality from `(not set)`.
7. Answer: "Czy wiesz, co zrobic dalej?" and "Ile czasu to oszczedza?"

Acceptance:

- Feedback is saved in a short handoff/progress note.
- Any confusion becomes a classified task, not vague UX commentary.

## Milestone 5: Final Demo Gate

Run this only after the next material code/eval slice is complete.

Commands:

    rtk scripts/local_stack.sh status
    rtk scripts/pre_demo_gate.sh --core-skills

Use `scripts/verify.sh` only when broad API/dashboard/skill changes justify the
cost:

    rtk scripts/verify.sh

Acceptance:

- Core gate passes, or blocker is precise and actionable.
- `docs/PROGRESS.md` states the current proof and next step in under a few
  bullets.
- `PLAN.md` progress is updated.
- No ready/done surfaces remain in the active task queue.

## Deferred BDOS Backlog

These are real tasks, but they are not blockers for the solid Ekologus demo
unless explicitly promoted:

- Full Ads apply path with SafetyLimits, mutation adapters, partial failure
  handling and audit.
- Budget optimizer using confirmed target CPA/ROAS, business guardrails,
  change-history windows and attribution proof.
- Keyword Planner/custom-segments production loop after developer-token
  approval/readiness.
- Demand Gen automation and creative quality loop.
- Social publishing apply path.
- Merchant feed writes, product IDs/SKU queue, historical price snapshots,
  product ROAS and price-impact windows.
- Localo/GBP write, review-response and local uplift automation.
- Multi-client/account model, permissions, production auth, deployment,
  monitoring and operational alerts.
- Full knowledge compiler with external source registry, freshness/confidence,
  owner review and rule-to-decision evals.

## Surprises And Discoveries

- Browser proof is stronger than route smoke for marketer language. The route
  tests passed before the Action detail copy was cleaned up, but the snapshot
  exposed proof-run wording that would confuse a demo.
- `scripts/pre_demo_gate.sh` proves contract and route readiness; it does not
  prove marketer usefulness or full BDOS.
- `docs/PROGRESS.md` can become too long quickly. Keep it as a recovery ledger;
  keep the fuller plan here.
- `pytest -k content` did not match any test names in
  `tests/test_codex_skill_eval_cases.py`, so it is not valid proof. Use the
  full focused file or an explicit matching test selector.
- The 2026-06-24 content strategist non-interactive eval passed the target-site
  boundary with usefulness score 4, not 5. Treat it as a guardrail proof, not
  marketer UAT or proof of a complete draft/staging workflow.
- The 2026-06-24 Ads Doctor eval passed with usefulness score 5 on live API.
  It proves review-only Ads guidance and overclaim blocking, not optimizer or
  apply readiness.
- The 2026-06-24 Merchant eval passed with usefulness score 5 on live API. It
  proves safe feed issue review wording and count semantics, not product-level
  performance, approval recovery, price impact, revenue recovery or feed write
  readiness.
- The 2026-06-24 GA4 eval passed with usefulness score 5 on live API. It proves
  measurement-vs-traffic-quality separation, not GA4 write, tracking repair,
  attribution verdict, ROAS, revenue, profitability or conversion-drop
  readiness.
- The 2026-06-24 Localo eval passed with usefulness score 5 on live API. It
  proves Localo is no longer merely OAuth/access proof: read-only visibility,
  GBP, competitor and review aggregates are available for review. It still does
  not unlock local tasks, GBP write, write/apply automation or local visibility
  uplift claims.

## Decision Log

- 2026-06-24: Keep WILQ as review-first for demo. Reason: current typed API and
  dashboard already provide value, while apply/publish/optimizer claims are not
  supported by enough contracts.
- 2026-06-24: Treat `ekologus.dev.proudsite.pl` as target context, not source
  evidence. Reason: source truth currently comes from existing Ekologus
  properties and vendor reads; the new site needs inventory/canonical checks
  before it can guide content.
- 2026-06-24: Use adversarial evals before adding new surfaces. Reason: the main
  product risk is overclaiming from partial data, not lack of route count.
- 2026-06-24: Do not fix product logic in skill references. Reason: WILQ API is
  the system brain; skills should consume contracts, not invent behavior.

## Outcomes And Retrospective

Current outcome: WILQ has a credible solid-demo path and a strong content
planning direction, but the goal is not complete until marketer UAT feedback is
captured or explicitly deferred.

When the full demo goal is complete, add a final retrospective here with:

- what the marketer can now do;
- proof commands and artifact paths;
- blocked claims that remain blocked;
- which deferred BDOS items should be promoted next.

## Prompt For `/goal`

Use this prompt in a fresh thread if you want a clean continuation:

    /goal Doprowadź WILQ Marketing Operating System do solidnego, uczciwego demo dla marketera Ekologus, zweryfikowanego aktualnym repo, live WILQ API, dashboardem, focused tests, browser proof i skill smokes/evals, używając PLAN.md jako kanonicznego ExecPlanu i docs/PROGRESS.md jako krótkiego recovery ledgeru. Najpierw przeczytaj PLAN.md, docs/PROGRESS.md, docs/CONTEXT.md i git status, potem wybierz następny nieukończony slice z Full Task Inventory zamiast powtarzać skończone testy. Demo ma prowadzić przez Command Center -> Merchant -> Content Planner -> Ads Doctor -> GA4 oraz pokazać jeden mocny content workflow: current Ekologus evidence z ekologus.pl/sklep.ekologus.pl/GSC/GA4/Ahrefs/Ads/Merchant/Localo/WordPress -> target context dla ekologus.dev.proudsite.pl -> inventory/canonical/duplicate gate -> polski brief albo draft plan z source facts, intent, audience, H1/H2/FAQ/CTA, internal links, missing evidence, forbidden claims, evidence IDs, source connectors i review state. Zweryfikuj wynik przez live API endpoints, browser walkthrough, focused tests, skill eval artifacts i requirement-by-requirement audit z Completion Definition w PLAN.md, zachowując WILQ API jako mózg systemu. Nie naprawiaj product logic w skill references ani dashboard copy; jeśli decyzja ma być mądrzejsza, dodaj typed API/schema/view-model/expert-rule/eval contract. Nie claimuj pełnego BDOS, Ads optimizera, feed repair, Localo uplift, publish/apply automation, approval recovery, revenue recovery, CPA/ROAS/wasted-budget verdict ani ranking gain bez validated ActionObject, preview, human confirmation, audit i wymaganych source contracts. Po każdym slice sprawdź, czy capability już istnieje, klasyfikuj findings jako ready/hardening/task/blocked/deferred_bdos/obsolete, uruchamiaj najmniejszy sensowny check, zapisuj postęp w PLAN.md i krótkim docs/PROGRESS.md, commituj zielone slice'y. Jeśli zablokowane, zapisz próby, dowody, dokładny blocker, zablokowane claimy i jeden input odblokowujący dalszą pracę; nie oznaczaj celu complete, dopóki requirement-by-requirement audit nie potwierdzi całego demo albo owner jawnie deferuje brak marketer UAT.
