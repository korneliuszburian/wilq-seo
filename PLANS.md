# PLANS.md - Goal 002 Content Production Engine

This is the long-running ExecPlan for the next WILQ product layer.

Current cleanup truth remains in `PLAN.md`, `docs/PROGRESS.md`,
`docs/goals/001-goal.md` and Beads. This file describes the durable path for
Goal 002 and must stay restartable without chat history.

## How To Use This File

- Read `AGENTS.md`, `PLAN.md`, `docs/CONTEXT.md` and `docs/PROGRESS.md` first.
- Run `bd prime` and `bd ready --json` before choosing work.
- Use Beads for operational task tracking. Do not copy the Beads issue list into
  markdown TODOs.
- Update this file only when the product plan, decisions, proof or blocker
  changes.
- Keep `Progress`, `Surprises & Discoveries`, `Decision Log` and
  `Outcomes & Retrospective` current.
- Every milestone is written as goal, work, result and proof.
- Every implementation slice must end with focused verification or an explicit
  blocker.

## Active Goal

Goal 002: Content Production Engine bez slopu.

Outcome:

WILQ can take one real Ekologus content item from evidence to a safe WordPress
draft handoff and measurement window without skipping preflight, preserve-first
planning, sales brief, claim ledger or human review.

This goal does not build:

- multi-client SaaS,
- automatic WordPress publishing,
- prompt-only content generation,
- broad RAG/vector memory,
- Ads/Merchant/Localo write automation,
- agency admin, billing or workspace switching.

## Product Thesis

WILQ is not an AI text generator. WILQ is an API-first marketing operating
system that decides whether writing is allowed, what mode is safe, what claims
are forbidden, what a human must approve and how the effect will be measured.

Content production must follow this path:

```text
evidence bundle
-> content inventory
-> canonical / duplicate / cannibalization check
-> preflight verdict
-> preserve-first decision
-> sales brief
-> claim ledger
-> draft package
-> human review
-> WordPress draft handoff
-> measurement window
```

## Naming And URL Semantics

- WILQ = system/product.
- Wilku = human marketer/operator persona.
- Ekologus = first depth-first workspace/client.
- `ekologus.pl` = final public canonical content home unless a real public
  source proves otherwise.
- `sklep.ekologus.pl` = public shop/product source where relevant.
- `ekologus.dev.proudsite.pl` and any dev preview host = optional
  design/staging context only, never historical SEO evidence and never final
  canonical URL.

Required active URL fields:

- `source_public_url`
- `final_canonical_url`
- `intended_final_url`
- `preview_url`

Do not preserve stale `target_site`, migration-map or dev-preview aliases when a
direct migration is feasible.

## Non-Negotiable Rules

- No evidence ID -> no recommendation.
- No source connector -> no recommendation.
- No preflight verdict -> no writing.
- No sales brief -> no draft.
- No claim ledger -> no draft.
- No human review -> no WordPress draft handoff.
- No audit -> no write/apply.
- No measurement window -> no success/failure claim.
- Existing content is preserve-first.
- React renders API-owned view models; React does not decide product logic.
- Codex skills consume WILQ API; skills do not invent business logic.
- Dashboard text for the marketer is Polish and action-oriented.

## Frozen Growth Areas

The following files are frozen for new feature growth. They may be touched only
for extraction, thin routing, test parity or direct cleanup required by this
plan:

- `apps/api/wilq_api/main.py`
- `wilq/schemas.py`
- `wilq/actions/service.py`
- `wilq/briefing/content_diagnostics.py`
- `tests/test_api_contracts.py`
- `apps/dashboard/src/routes/ContentDiagnosticSurface.tsx`

If a new content feature needs one of these files, create a domain module first
and move behavior out instead of adding another branch to the monolith.

## Beads Operational Graph

Goal 002 epic:

- `wilq-seo-zu4` - Goal 002: Content Production Engine bez slopu.

Current first ready slice:

- `wilq-seo-0zb` - Goal 002 anti-slop baseline.

The graph already contains child work for API router extraction, content domain
extraction, ContentWorkItem, Content Inventory v1, ContentPreflight v2, Sales
Brief v1, Claim Ledger v1, Draft Package v1, Human Review v1, WordPress Draft
Handoff v1 and Content Measurement Window v1. Use `bd ready --json` for the
authoritative operational queue.

## Milestone A - Close Goal 001 Without False UAT Claims

Goal:

Record whether real marketer UAT happened or was explicitly deferred.

Work:

- Use `docs/handoffs/2026-06-29-marketer-uat-ready.md` for later real UAT.
- Use an explicit owner defer when the owner decides to delay marketer UAT until
  Goal 002 content production is useful.
- Validate with `scripts/goal_001_completion_check.py`.
- Update `docs/PROGRESS.md` and `docs/goals/001-goal.md`.

Result:

Goal 001 may be treated as no longer blocked by missing UAT input, but the
product must not claim real marketer UAT.

Proof:

```bash
rtk uv run python scripts/goal_001_completion_check.py --owner-defer docs/handoffs/2026-06-30-owner-defer-marketer-uat.json --format markdown
rtk git diff --check
```

Blocked stop condition:

If neither a real UAT result nor owner defer exists, do not start content
production claims.

## Milestone B - Anti-Slop Baseline

Goal:

Measure current Python and TypeScript risk before adding content workflow
behavior.

Work:

- Add or update an audit script for largest Python files, functions and classes.
- Report frozen-file growth risk.
- Run current TS Fallow summary.
- Run existing Python quality commands and record known baseline failures
  honestly.
- Do not refactor the full repo in this milestone.

Result:

The team knows which files are legacy hotspots and which files must not receive
new product behavior.

Proof:

```bash
rtk uv run python scripts/audit_complexity.py --summary
rtk uv run ruff check . --statistics
rtk uv run mypy wilq apps/api/wilq_api
rtk pnpm fallow:summary
rtk git diff --check
```

Blocked stop condition:

If the tooling cannot run, record the exact command, failure and smallest
follow-up issue. Do not silently ignore the gate.

## Milestone C - Behavior-Preserving API Extraction

Goal:

Move FastAPI route registration and route handlers out of
`apps/api/wilq_api/main.py` without changing endpoint paths or response shapes.

Work:

- Create route modules under `apps/api/wilq_api/routers/`.
- Keep `main.py` as app factory / thin entrypoint.
- Preserve all current public endpoint behavior.
- Add parity tests for moved endpoints.

Result:

The API brain becomes editable without adding more logic to the entrypoint.

Proof:

Focused API contract tests for moved routes, live `/api/health`, live content
diagnostics and `git diff --check`.

Blocked stop condition:

If an endpoint shape changes, stop and restore parity before adding new
features.

## Milestone D - Behavior-Preserving Content Domain Extraction

Goal:

Move content decision logic out of `wilq/briefing/content_diagnostics.py` into
domain services without changing `/api/content/diagnostics` behavior.

Work:

- Create `wilq/content/inventory/`.
- Create `wilq/content/preflight/`.
- Create `wilq/content/canonical/`.
- Create `wilq/content/planning/`.
- Create `wilq/content/claims/`.
- Create `wilq/content/drafting/`.
- Create `wilq/content/handoff/`.
- Create `wilq/content/measurement/`.
- Keep `wilq/briefing/content_diagnostics.py` as composer during migration.

Result:

Content product behavior has a real domain home before new features are added.

Proof:

Focused content diagnostics tests pass before/after extraction and imports show
domain modules do not depend on `wilq.briefing`.

Blocked stop condition:

If behavior parity cannot be proven, stop at extraction and do not implement new
content capabilities.

## Milestone E - ContentWorkItem And State Gates

Goal:

Represent one content item as a typed workflow state.

Work:

- Add `ContentWorkItem`.
- Track evidence, source connectors, URL semantics, inventory, canonical,
  duplicate, preflight, sales brief, claim ledger, draft, human review,
  WordPress handoff and measurement statuses.
- Add state transition guards.

Result:

WILQ can reason about content progress as a workflow, not loose diagnostics.

Proof:

Tests prove preflight, sales brief, claim ledger, human review and audit gates
cannot be skipped.

## Milestone F - Content Inventory And Preserve-First Planning

Goal:

Make existing content the default starting point.

Work:

- Extract WordPress/GSC-backed content inventory records.
- Resolve `source_public_url`, `final_canonical_url`, `intended_final_url` and
  optional `preview_url`.
- Add preserve/refresh/merge/create/block planning.
- Block create when existing relevant content or duplicate risk is unresolved.

Result:

Existing Ekologus articles are preserved, refreshed or merged before WILQ
suggests creating new content.

Proof:

Tests for existing URL, missing inventory, dev preview URL, duplicate risk and
safe create.

## Milestone G - ContentPreflight v2

Goal:

Turn "Czy można pisać?" into a first-class workflow verdict.

Work:

- Add states: `blocked`, `plan_allowed`, `brief_allowed`, `draft_allowed`,
  `handoff_allowed`.
- Draft is allowed only after sales brief and claim ledger.
- Handoff is allowed only after human review.
- Dashboard renders API-owned labels and disabled reasons.

Result:

Every writing request has a typed gate before any draft is prepared.

Proof:

Focused tests for no evidence, missing source, missing final canonical, dev URL
as canonical, duplicate risk, missing brief and missing human review.

## Milestone H - Sales Brief v1

Goal:

Create a structured sales/content brief before drafting.

Work:

- Build brief from evidence, inventory, preflight and Ekologus service context.
- Include buyer problem, buyer trigger, target reader, search intent, service
  fit, source facts, H1/H2/FAQ/CTA direction, internal links, forbidden claims,
  missing evidence and measurement plan.

Result:

Draft quality is driven by API facts and commercial context, not prompt
improvisation.

Proof:

Tests prove no brief without evidence and final URL semantics.

## Milestone I - Claim Ledger v1

Goal:

Block unsupported legal, environmental, SEO, lead, revenue and performance
claims before drafting.

Work:

- Add claim statuses: `allowed_with_evidence`, `allowed_general`,
  `needs_human_review`, `blocked`, `blocked_until_measurement`.
- Add claim types for service capability, SEO performance, lead generation,
  compliance, environmental/legal-adjacent and business outcome.
- Require review for risky claims.

Result:

WILQ cannot present risky claims as publish-ready language without source and
review.

Proof:

Tests prove blocked claims cannot appear as publish-ready draft language.

## Milestone J - Draft Package v1

Goal:

Generate only bounded, auditable draft packages.

Work:

- Generate outline first.
- Require preflight, sales brief and claim ledger.
- Include section-to-evidence map, claims used, blocked claims removed and human
  review questions.
- Set `publish_ready=false`.

Result:

Draft output is useful for review, not direct publication.

Proof:

Tests prove draft generation is blocked without all gates.

## Milestone K - Human Review v1

Goal:

Make human approval a required transition.

Work:

- Record review for brief, claims, draft and handoff.
- Store reviewer, decision, notes, checked items and evidence IDs.
- Feed review status into the workflow state.

Result:

No content is treated as WordPress-ready without explicit human review.

Proof:

Tests prove WordPress draft handoff is blocked without approved human review.

## Milestone L - WordPress Draft Handoff v1

Goal:

Create or prepare WordPress drafts safely after review.

Work:

- Draft only.
- No publish.
- No destructive update of existing canonical content without a separate
  approved action.
- Require audit envelope.

Result:

Approved content can enter WordPress as a draft with traceability.

Proof:

Tests prove no handoff without review, audit and final canonical URL.

## Milestone M - Measurement Window v1

Goal:

Prevent success/failure claims before data exists.

Work:

- Add baseline period, observation period, earliest verdict date, allowed
  metrics, source connectors and status.
- Attach measurement window to draft handoff or publication event.

Result:

WILQ can track content outcomes without overclaiming.

Proof:

Tests prove outcome claims are blocked before the measurement window is ready.

## Final Completion Definition

Goal 002 is complete only when one real Ekologus content item passes:

```text
ContentWorkItem
-> evidence IDs
-> source connectors
-> inventory/canonical resolution
-> duplicate/cannibalization check
-> preflight verdict
-> preserve-first plan
-> sales brief
-> claim ledger
-> draft package
-> human review
-> WordPress draft handoff
-> measurement window
```

No skipped gates. No prompt-only product logic. No dev URL as canonical. No
WordPress publish. No unsupported marketing claims. No new monolith growth. No
dashboard logic fork.

## Progress

2026-06-30:

- Goal 001 real marketer UAT was explicitly deferred by the owner in
  `docs/handoffs/2026-06-30-owner-defer-marketer-uat.json`.
- The defer was validated with
  `scripts/goal_001_completion_check.py --owner-defer`.
- Goal 002 Beads epic `wilq-seo-zu4` was created.
- First ready Goal 002 slice is `wilq-seo-0zb`: anti-slop baseline.
- Goal 002 operational child issues were created for router extraction, content
  domain extraction, ContentWorkItem, Content Inventory v1, ContentPreflight v2,
  Sales Brief v1, Claim Ledger v1, Draft Package v1, Human Review v1, WordPress
  Draft Handoff v1 and Content Measurement Window v1.
- Anti-slop baseline proof was recorded in
  `docs/handoffs/2026-06-30-goal-002-anti-slop-baseline.md`.
- `scripts/audit_complexity.py` now reports largest Python files, functions and
  classes plus frozen-file growth risk.
- Baseline result: frozen growth files are clean in the current diff, but full
  Ruff, mypy and Fallow still report historical debt. Treat these as known
  baseline failures, not as proof that future slices may add more debt.
- First content domain extraction moved canonical/public URL semantics from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/canonical/urls.py` without changing content diagnostics
  behavior.
- Second content domain extraction moved preflight verdict helpers from
  `wilq/briefing/content_diagnostics.py` to
  `wilq/content/preflight/verdicts.py` without changing content diagnostics
  behavior.

Current next action:

Continue with the next ready extraction slice from `bd ready --json`.
Current ready/in-progress Goal 002 slices are:

- `wilq-seo-hdl` - behavior-preserving API router extraction.
- `wilq-seo-x4u` - behavior-preserving content domain extraction; currently
  in progress after the canonical URL and preflight verdict extraction slices.

Do not add new content workflow behavior before behavior-preserving extraction
begins.

## Surprises & Discoveries

- The previous `PLANS.md` content had become a prompt-like implementation
  brief, not a restartable ExecPlan. It has been condensed into this structured
  plan.
- Goal 001 parent epic still has historical in-progress children in Beads, so
  only the UAT/defer child was closed in this slice. Do not close the parent
  epic without a separate completion audit.

## Decision Log

2026-06-30:

- Decision: Defer marketer UAT instead of showing the current cockpit as a
  content-production tool.
  Reason: owner direction is to build real content-production value first.
- Decision: Goal 002 starts with anti-slop baseline.
  Reason: Python and TypeScript hotspots are already visible, and new content
  workflow work must not be added to monoliths.
- Decision: Beads tracks operational slices while this file keeps product
  milestones.
  Reason: avoids duplicate TODO systems and keeps recovery concise.

## Outcomes & Retrospective

Current outcome:

- Goal 001 is no longer blocked by missing UAT input because owner defer exists,
  but WILQ still cannot claim real marketer UAT or full content-production
  readiness.
- Goal 002 now has a concrete product plan and operational Beads graph.
- Anti-slop baseline is implemented and recorded as proof.
- Content canonical URL semantics have a domain home. This is only the first
  part of `wilq-seo-x4u`; preflight verdict helpers now also have a domain
  home. Inventory, full preflight contracts, planning, claims, drafting, handoff
  and measurement modules still need behavior extraction.

Current risk:

- Anti-slop baseline exists, but it is a reporting and guardrail baseline, not
  a cleanup of the historical debt.
- `main.py`, `wilq/schemas.py`, `actions/service.py`,
  `content_diagnostics.py`, `test_api_contracts.py` and
  `ContentDiagnosticSurface.tsx` remain legacy hotspots until the next slices
  move behavior out.
- Full `ruff check . --statistics` currently reports 68 issues.
- `mypy wilq apps/api/wilq_api` currently reports 5 existing type errors.
- `pnpm fallow:summary` currently fails on 21.0% duplication and 13 functions
  above threshold.
