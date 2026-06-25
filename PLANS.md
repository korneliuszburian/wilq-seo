# WILQ Marketing Operating System ExecPlan

This is the long-range living ExecPlan for moving WILQ from the current
Ekologus review-first demo cockpit into a ClientWorkspace-ready Marketing
Operating System.

`PLAN.md` remains the narrow Ekologus demo plan. This file owns the broader
product path after the current demo proof: workspace semantics, content
operating loop, structured generation, review, draft handoff, measurement,
knowledge lifecycle, dashboard simplification and safe execution expansion.

## How To Use This File

- A fresh Codex session must be able to restart from this file without chat
  memory.
- Read `PLAN.md`, `docs/PROGRESS.md`, `docs/CONTEXT.md` and `AGENTS.md` before
  implementing a slice from this plan.
- Do not implement before inspecting the current local checkout.
- Update `Progress`, `Surprises and Discoveries`, and `Decision Log` after each
  meaningful milestone or blocker.
- Do not duplicate existing API, dashboard, schema, skill or eval layers.
- Every milestone must end with focused verification or an explicit blocked stop
  condition.
- Keep `docs/PROGRESS.md` short. It is a recovery ledger, not the full plan.
- Use broad gates only for broad-risk/final proof. Use focused checks for normal
  slices.

## Product Naming

- `WILQ` = system/product.
- `Wilku` = human marketer/operator persona.
- `Ekologus` = first depth-first workspace/client.
- Do not call the system `WILKU`.
- Do not write that WILQ is the marketer. WILQ assists the marketer.

## Active Goal

Build WILQ as a local, API-first Marketing Operating System that first works
deeply for Ekologus, then becomes ClientWorkspace-ready without prematurely
becoming multi-client SaaS.

Execution path:

1. Close or explicitly defer the current `PLAN.md` for the Ekologus
   review-first demo.
2. Preserve the current Ekologus demo path and all safety boundaries.
3. Introduce formal workspace semantics without agency admin, billing, tenant
   UI or workspace switching.
4. Build the content operating loop:
   `preflight -> sales brief -> claim ledger -> structured draft -> human review -> WordPress draft handoff -> measurement loop`.
5. Extend the same operating pattern across Ads, Merchant, GA4, Localo, Social,
   Knowledge and monthly review.

## Product Thesis

WILQ is not:

- a chatbot,
- a prompt pack,
- a static report generator,
- SEO-slop automation,
- blind autopublishing,
- a full BDOS claim before apply and measurement exist,
- multi-client SaaS from day one.

WILQ is:

- an API-first Marketing Operating System,
- a reusable marketing engine plus client-specific workspace,
- a review-first decision cockpit that can grow into safe execution,
- an operating layer over GSC, GA4, Google Ads, Merchant, Ahrefs, Localo,
  WordPress and social channels,
- an evidence, ActionObject, blocked-claim, human-review, audit and measurement
  system,
- a tool that strengthens a real marketer instead of replacing judgment with a
  magic chatbot.

## Current Local Baseline

Local recovery on 2026-06-25:

- Branch: `main...origin/main`.
- Worktree at recovery: clean.
- `PLANS.md` did not exist before this slice.
- Latest commit before this plan: `6f8878c docs(demo): record browser marketer audit`.
- `PLAN.md` is the current canonical Ekologus demo ExecPlan and `/goal` reset
  prompt.
- `docs/PROGRESS.md` is the short recovery ledger.
- The current demo path is:
  `/command-center -> /merchant -> /content-planner -> /ads-doctor -> /ga4`.
- Recent browser marketer audit says Command Center is usable, GA4 is clearest,
  Merchant is useful but deep, Content Planner is high-value but overloaded and
  Ads Doctor is too dense for an unassisted demo.
- Real marketer UAT is still the main human proof gap unless the owner
  explicitly defers it.
- Current content workflow already has typed source/target context,
  target-site mapping review inputs, inventory/canonical/duplicate gates,
  blocked staging handoff preview and blocked measurement plan.
- Current skills/evals are strong for demo guardrails, including messy marketer
  prompts and adversarial overclaim blocking.

## Current Missing Layers

These are not complete yet and must not be implied as ready:

- real marketer UAT or explicit owner deferral;
- confirmed old-to-new mapping decisions for `ekologus.dev.proudsite.pl`;
- formal `ClientWorkspace`, `SiteProfile`, `ServiceMap`, `ClaimPolicy`,
  `BrandProfile`, `ConnectorProfile`, `MeasurementProfile` and
  `KnowledgeNamespace` contracts;
- content inventory v2 for source, preview and final canonical URLs;
- a single typed `ContentPreflight` verdict aggregating existing gates;
- preserve-first engine that makes refresh/merge/update/default safer than
  create when existing content evidence exists;
- duplicate, canonical and cannibalization engine;
- typed `ContentSalesBrief`;
- claim ledger for generated claims;
- SDK structured generation that returns typed artifacts or typed refusals;
- human review as a required state transition before draft handoff;
- WordPress draft handoff with draft-only apply and audit;
- post-publication measurement loop;
- API-owned Marketing Priority view-model for Command Center copy and CTAs;
- full information condensation layer that turns raw evidence, connector state,
  diagnostics, skill outputs, knowledge cards and browser findings into one
  marketer-useful decision surface;
- knowledge compiler v2 with source registry, freshness, confidence and
  workspace namespace;
- dashboard product cleanup that hides raw IDs/payloads behind technical
  drawers;
- safe write/apply expansion beyond current review-only boundaries;
- production auth, deployment, monitoring, permissions, multi-account and
  multi-client SaaS surfaces.

## Non-Negotiable Invariants

- No evidence ID -> no recommendation.
- No source connector -> no recommendation.
- No preflight verdict -> no writing.
- No sales brief -> no draft.
- No claim review -> no publish-ready language.
- No human review -> no WordPress draft handoff.
- No audit -> no write/apply.
- No measurement window -> no success/failure claim.
- Dev URL is preview/target context, not final canonical.
- Existing content is preserve-first.
- Codex skills consume WILQ API; they do not invent product logic.
- Product behavior lives in typed API/schema/view-model/expert-rule/eval
  contracts, not prompt-side workarounds.
- Dashboard speaks marketer language first; technical traces go into detail
  drawers.
- Client-specific service, claim and tone rules live in workspace/profile/card
  layers, not reusable core defaults.
- Every marketer-facing surface must answer: what is happening, why it matters,
  what to do next, what is blocked, what evidence supports it and what would
  prove the result later.
- Browser proof through `agent-browser` is mandatory for UX/value claims about
  dashboard routes. Route tests alone do not prove marketer usefulness.

## URL Semantics To Introduce

Add these without immediately deleting existing `target_site_*` compatibility
fields:

- `source_public_url`: current public source URL with historical evidence.
- `preview_url`: preview/staging/dev URL, for example
  `ekologus.dev.proudsite.pl`.
- `intended_final_url`: intended final production URL after migration.
- `final_canonical_url`: canonical URL approved for indexing/publication.
- `target_site_url`: compatibility alias for target context.
- `target_site_host`: compatibility alias for target host.
- `target_site_migration_candidate_url`: compatibility alias for mapping
  candidate.

## Information Condensation Layer

Objective:

- Condense WILQ's raw facts into a marketer-useful operating view instead of
  exposing every connector, evidence ID, diagnostic field and technical blocker
  on first contact.

The condensation layer must combine:

- WILQ API diagnostics and metrics fetched live when marketing metrics are
  discussed;
- connector status, freshness and missing credential state;
- evidence IDs and source connectors;
- ActionObject readiness, validation, preview, review and audit state;
- skill outputs and eval findings;
- knowledge cards, expert rules, claim policies and service map context;
- browser audit findings from `agent-browser`;
- real marketer UAT findings when available.

Output contract:

- `decision`: the plain Polish decision or blocker;
- `why_it_matters`: business/marketing impact in marketer language;
- `evidence_summary`: short evidence rollup with source connectors and evidence
  IDs available in detail;
- `safe_next_action`: the next review/action the marketer can safely take;
- `blocked_claims`: what WILQ refuses to say or do;
- `missing_inputs`: exact human/vendor/API inputs needed to unblock;
- `confidence`: confidence based on freshness, source coverage, review state and
  measurement availability;
- `measurement_plan`: how WILQ will later verify whether the action helped.

Rules:

- Do not hide blockers. Condense them into a useful decision.
- Do not remove traceability. Move IDs and raw payloads into technical drawers.
- Do not infer marketing metrics from docs, browser text or stale artifacts.
  Fetch current WILQ API context for marketing metrics.
- Do not treat a skill eval score as marketer value. Use it as guardrail proof.
- Do not treat browser screenshots as product completion. Use them to identify
  clutter, confusion, dead ends and unclear next actions.

## Browser Self-Audit Requirement

Every UX/value claim about the dashboard must be tested through `agent-browser`
against the local dashboard when the stack is available.

Required route path:

- `/command-center`
- `/merchant`
- `/content-planner`
- `/ads-doctor`
- `/ga4`

For each route, capture:

- page text or snapshot;
- screenshot, preferably full-page when density matters;
- count of visible sections/cards/headings if clutter is suspected;
- the first marketer-visible decision;
- the next clickable action;
- confusing labels, raw IDs, debug payloads or duplicated information;
- what should be condensed, collapsed, renamed or moved into a technical drawer.

Proof storage:

- Store browser proof under `.local-lab/proof/`.
- Summarize findings in a handoff under `docs/handoffs/`.
- Convert confirmed UX findings into `PLAN.md` or `PLANS.md` tasks.

## Execution Order

1. Milestone A: Recovery and current-state audit.
2. Milestone B: Close or explicitly defer current `PLAN.md`.
3. Milestone C: Product semantics and workspace contracts.
4. Milestone D: ContentPreflight.
5. Milestone E: Preserve-first mode.
6. Milestone F: Content inventory v2.
7. Milestone G: Duplicate/canonical/cannibalization engine.
8. Milestone H: Service map and strategy knowledge.
9. Milestone I: ContentSalesBrief.
10. Milestone J: Claim ledger.
11. Milestone K: Codex skills, hooks and subagents alignment.
12. Milestone L: SDK structured generation.
13. Milestone M: Human review.
14. Milestone N: WordPress draft handoff.
15. Milestone O: Measurement loop.
16. Milestone P: Marketing Priority Engine.
17. Milestone Q: Knowledge compiler v2.
18. Milestone R: Information condensation and dashboard for Wilku.
19. Milestone S: Safe write/apply expansion.
20. Milestone T: Final verification suite.

## Milestone A - Recovery And Current-State Audit

Objective:

- Recover current repo state before changing implementation.

Inspect first:

- `git status --branch --short`
- `git log --oneline --decorate -30`
- filtered logs for `content`, `PLAN`, `WILQ`, `UAT`, `workspace`, `client`
- `PLAN.md`, `docs/PROGRESS.md`, `docs/CONTEXT.md`, `docs/goals/001-goal.md`,
  `AGENTS.md`
- `.codex/hooks.json` if present
- `.agents/skills/**/SKILL.md`
- `.agents/skills/**/references/*`
- `wilq/briefing/content_diagnostics.py`
- `wilq/actions/content_refresh.py`
- `wilq/schemas.py`
- `packages/shared-schemas/src/index.ts`
- `apps/api/wilq_api/main.py`
- `apps/dashboard/src/routes/**`
- `tests/*`
- `docs/evals/*`

Acceptance:

- Current facts in this file match the local checkout.
- Repo-declared proof is separated from personally run live/runtime proof.
- No implementation happens before recovery is complete.

Verification:

- Docs-only recovery update: `rtk git diff --check`.

Stop condition:

- If required files or checkout are unavailable, record the exact blocker and
  continue only from accessible evidence.

## Milestone B - Close Current PLAN.md

Objective:

- Finish or explicitly defer the current Ekologus demo plan before broad product
  expansion.

Inspect first:

- `PLAN.md`
- `docs/handoffs/2026-06-24-marketer-uat-script.md`
- `docs/handoffs/2026-06-24-operator-uat-findings.md`
- `docs/handoffs/2026-06-25-browser-marketer-audit.md`
- latest pre-demo proof logs
- dashboard route smoke
- core skill eval artifacts

Tasks:

- Run real marketer UAT, or record explicit owner deferral.
- Keep the demo path narrow:
  `Command Center -> Merchant -> Content Planner -> Ads Doctor -> GA4`.
- Keep review-only boundaries visible.
- Do not expand scope to full BDOS.
- Convert UAT confusion into concrete tasks in `PLAN.md`.

Acceptance:

- `PLAN.md` says `complete`, `incomplete` or `blocked` for the current demo with
  evidence.
- Real marketer UAT pass/fail is recorded, or owner deferral is explicit.
- No unsafe apply, publish, optimizer, recovery or uplift claim is introduced.

Verification:

- `rtk scripts/pre_demo_gate.sh --core-skills`
- Dashboard/browser walkthrough for the narrow path when UX changes.
- Marketer UAT packet/result recorder if UAT is performed.

Stop condition:

- If UAT fails, stop expansion and fix the first confirmed UX/product blocker.

## Milestone C - Product Semantics / ClientWorkspace

Objective:

- Introduce formal workspace semantics without building multi-client SaaS.

Tasks:

- Add typed contracts for `ClientWorkspace`, `SiteProfile`, `BrandProfile`,
  `ServiceMap`, `ClaimPolicy`, `ConnectorProfile`, `MeasurementProfile` and
  `KnowledgeNamespace`.
- Create an Ekologus workspace seed/profile.
- Keep current Ekologus behavior compatible.
- Move naming and client-specific assumptions out of global prose where safe.

Acceptance:

- Existing Ekologus demo behavior is preserved.
- Contracts load an Ekologus workspace profile.
- No agency admin, billing, workspace switcher or tenant UI is added.

Verification:

- Focused schema/unit tests.
- Existing affected content/API/dashboard checks.

Stop condition:

- If extraction risks demo regression, add a read-only profile layer first and
  defer deeper migration.

## Milestone D - ContentPreflight

Objective:

- Create a typed preflight verdict before writing or drafting content.

Tasks:

- Define `ContentPreflight`.
- Aggregate existing `inventory_gate_status`, `canonical_gate_status`,
  `duplicate_gate_status`, target mapping state, claim risk and missing evidence.
- Include URL semantics for source, preview, intended final and canonical.
- Add typed refusal/blocker states.

Acceptance:

- No content writing or draft path can proceed without `ContentPreflight`.
- Existing `target_site_*` fields remain compatible.
- Content Planner and skills show a concise preflight summary.

Verification:

- Fixture tests for blocked create when inventory is unknown.
- Fixture tests for refresh/merge when source URL exists.
- Content skill smoke requires preflight fields.

## Milestone E - Preserve-First Mode

Objective:

- Make existing content preservation the default strategy.

Tasks:

- Add `preserve_first_recommendation`.
- Prefer refresh, merge, update or redirect over create when existing content
  evidence exists.
- Block create until inventory/canonical/duplicate checks pass.

Acceptance:

- BDO and Zielony Lad fixture cases prefer refresh/merge unless the API proves
  create is safe.
- Dashboard explains why create is blocked.

Verification:

- BDO refresh eval.
- Zielony Lad merge/refresh eval.
- Duplicate/canonical fixtures.

## Milestone F - Content Inventory v2

Objective:

- Build durable inventory for source, preview and final sites.

Tasks:

- Define `ContentInventoryItem`.
- Capture source public URL, preview URL, final canonical URL, title/H1/meta,
  content type, status and canonical.
- Store freshness and evidence IDs.
- Do not store full HTML bodies by default.

Acceptance:

- Inventory can answer whether a source exists, a target candidate exists,
  canonical is known and duplicate risk is known.

Verification:

- Fixture inventory tests.
- Live smoke checks shape/freshness, not exact counts.

## Milestone G - Duplicate / Canonical / Cannibalization

Objective:

- Create an explainable duplicate, canonical and cannibalization engine.

Tasks:

- Define `DuplicateCanonicalVerdict`.
- Compare source/target inventory, query overlap, topic similarity and canonical
  conflicts.
- Use deterministic explainable rules first.
- Do not add broad vector/RAG as the product brain.

Acceptance:

- Every create/merge/refresh decision has a verdict or blocker.
- Reasons are inspectable in a dashboard technical drawer.

Verification:

- BDO/Zielony Lad fixtures.
- False-positive and false-negative fixtures.
- Skill eval prohibits create when duplicate risk is unresolved.

## Milestone H - Service Map / Strategy Knowledge

Objective:

- Separate Ekologus offer, voice and claim logic from reusable core.

Tasks:

- Define `ServiceMap`.
- Move service-specific terms into the Ekologus workspace.
- Define buyer problems, triggers, offers, proof requirements, CTAs and
  forbidden claims.
- Preserve current Ekologus decisions.

Acceptance:

- Core modules no longer contain Ekologus-only service vocabulary as global
  defaults.
- Ekologus workspace produces the same current decisions.

Verification:

- Workspace service map load tests.
- Regression tests for current content decisions.

## Milestone I - ContentSalesBrief

Objective:

- Create a typed sales/content brief between evidence and draft generation.

Tasks:

- Define `ContentSalesBrief`.
- Include buyer problem, service match, CTA, proof requirements, source facts,
  claim boundaries, review notes, preflight verdict, evidence IDs and source
  connectors.
- Require `ContentPreflight`.

Acceptance:

- Draft generation cannot run without `ContentSalesBrief`.
- Dashboard renders a marketer-friendly sales brief summary.
- Content skill emits sales brief fields.

Verification:

- Content skill smoke.
- Fixture tests for missing `ServiceMap` or `ClaimPolicy`.

## Milestone J - Claim Ledger

Objective:

- Track every generated claim and its evidence/review state.

Tasks:

- Define `ClaimLedgerEntry`.
- Link each claim to evidence IDs, source connectors, policy status and review
  state.
- Use statuses: `allowed`, `needs_review`, `forbidden`, `unsupported`.
- Add claim ledger to content brief/draft artifacts.

Acceptance:

- Draft artifacts cannot contain unledgered claims.
- Unsupported lead, ranking, revenue, legal or compliance claims are blocked.

Verification:

- Claim ledger unit tests.
- Adversarial generation tests.

## Milestone K - Codex Skills / Hooks / Subagents

Objective:

- Keep skills as procedural API workflows and add bounded audit subagent
  profiles.

Tasks:

- Update skills only after API contracts exist.
- Add ContentPreflight/ContentSalesBrief skill behavior after backend fields
  exist.
- Add or document subagent profiles for repo exploration, product architecture,
  eval review, dashboard review and security guardrails.
- Extend hygiene checks to ban workspace-specific logic in generic references.

Acceptance:

- Skills consume API contracts only.
- References describe API usage, not workaround product logic.
- Subagents do not create conflicting architecture.

Verification:

- Skill hygiene.
- Focused skill smokes.
- Non-interactive eval when output behavior changes.

## Milestone L - SDK Structured Generation

Objective:

- Generate typed content artifacts through strict schemas.

Tasks:

- Define strict schemas for `GeneratedContentDraft`, `DraftSection`,
  `ClaimReference` and `GenerationRefusal`.
- Use Structured Outputs with explicit refusal/error states.
- Require ContentPreflight, ContentSalesBrief and ClaimLedger.

Acceptance:

- Generated artifacts validate locally.
- Missing preflight, brief or claim ledger returns typed refusal.
- No loose freeform draft path exists.

Verification:

- Schema tests.
- Golden fixture for blocked generation.
- Adversarial claim tests.

## Milestone M - Human Review

Objective:

- Make human review a required transition before handoff/apply.

Tasks:

- Define review state transitions.
- Add reviewer identity, checklist, claim approval and mapping approval.
- Display review history in marketer language.

Acceptance:

- Draft handoff is blocked until human review is complete.
- Review state is visible in dashboard and ActionObject.

Verification:

- Review endpoint tests.
- Dashboard review flow test.
- Claim review fixture.

## Milestone N - WordPress Draft Handoff

Objective:

- Create safe WordPress draft/staging handoff.

Tasks:

- Define `WordPressDraftHandoff`.
- Produce draft payload with `post_status=draft`.
- Never publish by default.
- Require preflight, sales brief, claim ledger, human review, preview,
  confirmation and audit.

Acceptance:

- WILQ can prepare or create a draft only when gates pass.
- Publish remains a separate explicit future action.

Verification:

- Preview tests.
- Blocked apply without confirmation/audit.
- Mutation audit tests.

## Milestone O - Measurement Loop

Objective:

- Measure effect of actions after defined windows.

Tasks:

- Define `MeasurementOutcome`.
- Set pre/post windows per action type.
- Store baseline and post-action evidence IDs.
- Distinguish observed change from causal claim.

Acceptance:

- No success/failure claim without a measurement window.
- Measurement blockers are visible.

Verification:

- Fixture outcome tests.
- Missing-window tests.
- Dashboard monthly review smoke.

## Milestone P - Marketing Priority Engine

Objective:

- Formalize daily prioritization across domains.

Tasks:

- Define `MarketingPriority`.
- Rank by evidence strength, freshness, business priority, blocked risk and
  actionability.
- Move canonical display copy and CTA from dashboard hardcoding into API
  view-models.

Acceptance:

- Command Center renders API-owned decision copy.
- Ranking rationale is visible.
- Existing demo path is preserved.

Verification:

- Priority fixture tests.
- Command Center route tests.
- Daily command skill eval.

## Milestone Q - Knowledge Compiler v2

Objective:

- Make knowledge typed, versioned, fresh and workspace-scoped.

Tasks:

- Add source registry.
- Add card freshness, confidence, review owner and namespace binding.
- Add eval proving card/rule improves a decision or blocks a claim.
- Do not build broad vector/RAG as product brain.

Acceptance:

- Knowledge cards are not raw long prompts.
- Workspace-specific cards do not leak into core defaults.
- Rule-to-decision lineage is testable.

Verification:

- Knowledge compiler tests.
- Rule-to-decision lineage tests.
- Stale-card behavior tests.

## Milestone R - Information Condensation And Dashboard For Wilku

Objective:

- Make dashboard a condensed marketer cockpit, not a registry or raw diagnostic
  dump.

Tasks:

- Define the marketer-facing condensation view-model.
- Pull WILQ API context for marketing metrics instead of relying on docs,
  screenshots or stale artifacts.
- Convert raw diagnostics into: decision, why it matters, evidence summary,
  safe next action, blocker, missing input, confidence and measurement plan.
- Keep domain nav first.
- Move raw IDs/payloads into technical drawers.
- Show for every decision: what to do, why, blocker, safe action and later
  measurement.
- Use `agent-browser` to walk the core route path and judge the UI like a
  marketer practicing AI engineering: remove or collapse information that does
  not help the next decision.
- Run UAT with Wilku/marketer.

Acceptance:

- Wilku can choose next action without developer narration.
- Core path has no raw-debug or ActionObject-first language on first screen.
- Dense routes such as Ads Doctor and Content Planner have a condensed first
  screen with detail drawers for traceability.
- Browser findings are either fixed, converted into tasks or explicitly
  deferred.

Verification:

- Marketer UAT.
- Dashboard e2e checks.
- `agent-browser` snapshots/screenshots/text extraction for the core route path.
- Browser proof as value/UX evidence, not the sole completion proof.

## Milestone S - Safe Write/Apply Expansion

Objective:

- Expand execution only after review-first system is stable.

Tasks:

- Add SafetyLimits.
- Add partial failure handling.
- Add connector-specific preview/apply adapters one at a time.
- Start with the lowest-risk write.
- Keep publish, budget and feed writes blocked until all gates exist.

Acceptance:

- Every write has typed payload, preview, confirmation, audit and failure story.
- Blocked write paths remain honest.

Verification:

- Apply-blocked tests.
- Preview tests.
- Mutation audit tests.
- Secret redaction tests.

## Milestone T - Final Verification Suite

Objective:

- Define final confidence gates for WILQ.

Tasks:

- Separate fixture tests, live smokes, UAT scripts, non-interactive skill evals
  and structured generation evals.
- Add regression suite for previous failures.
- Add final WILQ completion gate.
- Avoid brittle exact live metric assertions.

Acceptance:

- Final gate proves current demo closure, workspace semantics, content loop,
  skill safety, dashboard UX, write blockers and measurement blockers.

Verification:

- Focused subsets per slice.
- `rtk scripts/pre_demo_gate.sh --core-skills` for demo.
- Full `rtk scripts/verify.sh` for final/broad-risk.
- UAT notes.
- Structured generation schema tests.

## Final Completion Definition

This long-range plan is complete when:

- current Ekologus `PLAN.md` is honestly closed or explicitly deferred with
  blockers;
- WILQ/Wilku/Ekologus naming is consistent;
- workspace contracts exist and preserve Ekologus behavior;
- Command Center uses typed Marketing Priority view-models;
- ContentPreflight blocks unsafe writing;
- ContentSalesBrief is required before draft generation;
- Claim Ledger blocks unsupported publish-ready language;
- structured generation returns typed artifacts or typed refusals;
- Human Review is required before WordPress handoff;
- WordPress Draft Handoff is draft-only and audited;
- Measurement Loop blocks success/failure claims without windows;
- skills consume API contracts and pass decision-quality evals;
- dashboard is usable by Wilku without developer narration;
- final verification suite passes or exact blockers are recorded.

## Deferred Future

Do not implement these before Ekologus works deeply:

- full multi-client SaaS;
- agency admin panel;
- workspace switcher;
- billing;
- production permissions model beyond what current safe writes require;
- full Ads budget optimizer;
- full feed repair/approval recovery;
- Localo write/uplift automation;
- social publishing apply;
- production deployment/monitoring as a product claim.

## Progress

- [x] Local recovery confirmed `PLANS.md` was missing and branch `main` was
  clean on 2026-06-25.
- [x] Current demo plan stays in `PLAN.md`.
- [x] Long-range product plan is now separated into this `PLANS.md`.
- [x] Naming policy is explicit: WILQ system, Wilku operator persona, Ekologus
  first workspace/client.
- [x] Fresh `agent-browser` self-audit for the condensation layer captured
  current API-backed route text/snapshots under
  `.local-lab/proof/condensation-browser-audit-20260625/` and summarized
  concrete route-condensation tasks in
  `docs/handoffs/2026-06-25-condensation-browser-audit.md`.
- [x] First dashboard condensation implementation shipped for Ads Doctor: a
  live primary decision panel before the diagnostic wall, with safe next step,
  evidence/source summary, blocked claims, missing inputs and measurement plan.
  Browser proof:
  `.local-lab/proof/ads-condensed-decision-panel-20260625/`.
- [x] Second dashboard condensation implementation shipped for Content Planner:
  a selected-first content review panel before the full drilldown, including
  live WILQ API metrics, source evidence, target mapping, H1/H2/FAQ/CTA
  direction, blocked claims, missing inputs and measurement plan. It explicitly
  separates old-site source-of-truth inventory from dev-site preview/design
  context. Browser proof:
  `.local-lab/proof/content-selected-decision-panel-20260625/`.
- [ ] Run or explicitly defer real marketer UAT from current `PLAN.md`.
- [ ] Close or mark blocked current `PLAN.md`.
- [ ] Start Milestone C only after current demo closure/deferral is explicit.

## Surprises And Discoveries

- The repo was already further than the pasted audit assumed in several places:
  browser marketer audit exists, messy prompt evals exist, mapping review packet
  exists, and content staging/measurement blockers are already typed.
- The pasted audit was right that `PLANS.md` was missing.
- The pasted audit was right that `AGENTS.md` still had the misleading sentence
  "WILQ is the marketer".
- The largest current human proof gap is still marketer UAT or explicit owner
  deferral.
- Ads Doctor needed implementation, not just planning: the route was formally
  correct but too dense, so the first condensation slice moves the decision,
  blockers and measurement plan ahead of the raw diagnostic wall.
- Content semantics needed first-screen product language: `ekologus.pl` and
  `sklep.ekologus.pl` are source-of-truth inventory, while
  `ekologus.dev.proudsite.pl` is preview/design context for mapping.

## Decision Log

- 2026-06-25: Keep `PLAN.md` as current Ekologus demo ExecPlan.
- 2026-06-25: Add `PLANS.md` as the broader product ExecPlan.
- 2026-06-25: Treat WILQ as the system, Wilku as operator persona and Ekologus
  as first workspace/client.
- 2026-06-25: Build ClientWorkspace-ready contracts next, not multi-client SaaS.
- 2026-06-25: Preserve `target_site_*` compatibility while introducing clearer
  source/preview/final URL semantics.
- 2026-06-25: Do not begin ContentPreflight implementation until current demo
  closure/deferral and workspace semantics are handled.

## Prompt For `/goal`

```text
/goal

Work in the WILQ repository.

Repository:
https://github.com/korneliuszburian/wilq-seo

Preferred local path:
`/home/krn/coding/krn/active/wilq-seo`

If that path is missing, find the local `wilq-seo` checkout before proceeding.
If no checkout exists, stop with an exact blocker.

Read first, in this order:

1. `PLANS.md`
2. `PLAN.md`
3. `AGENTS.md`
4. `docs/CONTEXT.md`
5. `docs/PROGRESS.md`
6. `docs/goals/001-goal.md`
7. `.codex/hooks.json` if present
8. Relevant dashboard/API/schema/skill/eval files named by `PLANS.md`

Do not implement before recovery.

First perform recovery:

- `rtk git status --branch --short`
- `rtk git log --oneline --decorate -30`
- `rtk git log --oneline --grep="content" -30`
- `rtk git log --oneline --grep="PLAN" -30`
- `rtk git log --oneline --grep="WILQ" -30`
- `rtk git log --oneline --grep="UAT" -30`
- `rtk git log --oneline --grep="workspace" -30`
- `rtk git log --oneline --grep="client" -30`
- repo search for the terms listed in `PLANS.md`

Then update `PLANS.md` recovery/progress sections if current repo state differs
from the checked-in plan.

Product naming is non-negotiable:

- WILQ = system/product.
- Wilku = human marketer/operator persona.
- Ekologus = first depth-first workspace/client.
- Do not call the system WILKU.
- Fix old docs or prompts that say WILQ is the marketer.

Main outcome:

Move WILQ from the current Ekologus review-first cockpit toward the final
ClientWorkspace-ready Marketing Operating System described in `PLANS.md`, while
preserving the current Ekologus demo path and not building multi-client SaaS now.

Work policy:

- Always inspect existing implementation first.
- Do not duplicate existing API/dashboard/schema/skill/eval layers.
- Do not add prompt-side workarounds for product behavior.
- If a skill needs smarter behavior, add or fix the typed API/schema/view-model
  first.
- Update `PLANS.md` after every meaningful milestone or blocker.
- Do not ask for next steps when the next step is explicit in `PLANS.md`.
- Never claim completion without verification surface.
- Stop only when the final completion definition is true or an exact blocker is
  recorded in `PLANS.md`.

Architecture constraints:

- Build Ekologus depth-first.
- Design reusable WILQ Core as ClientWorkspace-ready.
- Do not build multi-client SaaS, agency admin, workspace switcher, billing or
  tenant UI in this goal.
- Client-specific service/claim/tone/content rules must live in
  workspace/profile/card layers, not reusable core.
- Keep `target_site_*` compatibility fields while introducing
  `source_public_url`, `preview_url`, `intended_final_url`,
  `final_canonical_url`.

Safety invariants:

- No evidence ID -> no recommendation.
- No source connector -> no recommendation.
- No preflight verdict -> no writing.
- No sales brief -> no draft.
- No claim review -> no publish-ready language.
- No human review -> no WordPress draft handoff.
- No audit -> no write/apply.
- No measurement window -> no claim of success/failure.
- Dev URL is preview/target context, not final canonical.
- Existing content is preserve-first.
- SDK generation returns typed artifacts or typed refusal, not loose prose.
- Dashboard speaks marketer language, with technical drawer for raw details.
- Build a full information condensation layer so raw diagnostics, metrics,
  evidence, skill findings, knowledge cards and browser/UAT findings become a
  useful marketer decision surface.
- For marketing metrics, fetch current WILQ API context. Do not infer metrics
  from docs, browser text or stale artifacts.
- Use `agent-browser` to inspect the dashboard yourself on the core path:
  `/command-center -> /merchant -> /content-planner -> /ads-doctor -> /ga4`.
  Capture proof under `.local-lab/proof/`, summarize findings in
  `docs/handoffs/`, and convert clutter/confusion into tasks.
- Judge every route from Wilku's perspective: what is the decision, why does it
  matter, what should I do next, what is blocked, what evidence supports it,
  and what information is noise.

Execution order:

1. Complete Milestone A: recovery and current-state audit.
2. Complete Milestone B: close or explicitly defer current `PLAN.md`.
3. Complete Milestone C: product semantics / ClientWorkspace contracts.
4. Continue milestones D-T in order unless a blocking regression requires
   returning to an earlier milestone.
5. Use focused verification after each slice; use broad gates only for
   broad-risk/final proof.

Verification surface:

- Docs-only: `rtk git diff --check`.
- API/schema: focused pytest subsets and shared schema tests.
- Dashboard: touched route tests and e2e smoke for affected routes.
- Skills: skill hygiene, deterministic smoke, non-interactive eval when
  behavior/output changes.
- Demo: `rtk scripts/pre_demo_gate.sh --core-skills`.
- Final: full final verification suite defined in Milestone T.
- UAT: real marketer UAT or explicit blocker/defer note.

Blocked stop condition:

If a vendor/API contract, credential, site inventory, mapping, human review,
measurement window or safe write path is unavailable, stop that claim with:

- missing contract/input,
- evidence gathered,
- blocked claims,
- what remains safe to show,
- exact implementation/input needed to unblock,
- `PLANS.md` updated.

Begin with recovery. Do not edit implementation until recovery is complete and
`PLANS.md` reflects current truth.
```
