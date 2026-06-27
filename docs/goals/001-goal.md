# Goal 001 - Clean Product Semantics And Marketer Cockpit

Status: active

Date: 2026-06-27

## Objective

Clean WILQ's active product semantics and marketer-facing surfaces before
starting the next product layer.

The goal is not to finish the full WILQ Marketing Operating System. The goal is
to make the current review cockpit coherent, condensed and usable enough that
Wilku can inspect it without reading technical internals.

## Identity

- WILQ = system/product.
- Wilku = human marketer/operator persona.
- Ekologus = first depth-first workspace/client.
- `ekologus.pl` = public canonical content home.
- Dev preview hosts = optional design/staging context only when explicitly
  configured for a workflow.

## Product Rules

- No evidence ID -> no recommendation.
- No source connector -> no recommendation.
- No preflight verdict -> no writing.
- No sales brief -> no draft.
- No claim review -> no publish-ready language.
- Brak sprawdzenia przez człowieka -> brak WordPress draft handoff.
- No audit -> no zapis zmian.
- No measurement window -> no success/failure claim.
- No business logic in prompts or skill references.
- No React/UI translator functions for product semantics.
- No hardcoded label replacement.
- No compatibility aliases or deprecated active fields when a direct migration
  is feasible.
- Dirty marketer-facing copy must be fixed in typed API/schema/view-model/domain
  source.
- Every repeated issue becomes a typed API/schema/view-model field or a test
  guard.

## Current State

- Core route path remains:
  `/command-center -> /merchant -> /content-planner -> /ads-doctor -> /ga4`.
- Current cleanup has already moved many Command Center, Content, Ads, GA4,
  Merchant, Localo, Ahrefs and Action Detail labels from dashboard helpers into
  API/domain/shared-schema labels.
- Recent committed cleanup slices:
  - `6497044 fix(ads): source negative keyword labels from api`
  - `df4c750 fix(ads): clean recommendation and keyword context copy`
  - `5a805aa fix(merchant): condense source and evidence labels`
  - `d783636 fix(ga4): clean measurement labels`
  - `0a7414e fix(localo): clean access proof labels`
  - `6e93975 fix(dashboard): hide raw trace ids in detail panels`
  - `e6001a5 fix(dashboard): source proof labels from api`
  - `f74c770 fix(demand-gen): expose clean proof labels`
  - `be6205b fix(brief): use clean action wording`
  - `709a4cc fix(dashboard): remove id jargon from proof copy`
- The Ads recommendation/keyword-context cleanup removes raw
  recommendation enum summaries, mixed English/Polish recommendation-review
  wording, raw keyword match/status rendering and fixed English shorthand
  labels.
- The Merchant cleanup adds API-owned source connector labels
  and evidence summaries, then uses them in Merchant panels instead of raw
  connector IDs, evidence IDs and read-contract/debug labels.
- The GA4 cleanup is committed. It adds API-owned source connector labels,
  evidence summaries and safe reporting-dimension labels, then uses them in GA4
  panels instead of raw `(not set)`, `tracking-gap`, connector IDs, evidence IDs
  and `ID` evidence counts.
- The Demand Gen cleanup is committed. It adds API-owned source labels and
  evidence summaries, then uses them instead of raw source IDs and `ID` proof
  counts.
- The latest proof-copy cleanup is committed. Merchant, Content Planner and
  Ahrefs no longer show `ID` proof counts or "przykładowe ID produktów" in
  normal route proof copy; Marketing Brief and action validation no longer
  expose `akcji WILQ`, `ID dowodu` or English validation messages.
- Current active slice: remaining secondary dashboard/action cleanup outside
  the latest cleaned paths.
- Recovery docs are being condensed because long append-only progress logs made
  the active goal harder to resume.

## Active Findings

Use these as the next work queue. Do not start future product layers until these
are resolved or explicitly deferred.

1. Ads Doctor still has route-local raw-key fallback debt in secondary helper
   paths. These should disappear as API labels cover the remaining panels.
2. Action impact and detail panels still have raw connector/evidence fallback
   risk outside the first-screen panels already cleaned.
3. `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and `docs/CONTEXT.md` must stay
   short and aligned. History belongs in git and proof artifacts, not active
   recovery docs.

## Execution Policy

- Use `rtk` before every shell command.
- Inspect existing implementation before editing.
- Prefer small verified slices and conventional commits.
- Use subagents for parallel read-only audits or disjoint write scopes.
- Do not let multiple workers edit the same files without explicit ownership.
- After each slice:
  - run focused tests,
  - capture browser/API proof when a marketer route changes,
  - update only current recovery facts,
  - commit and push a coherent green slice.

## Verification

Focused checks:

- Docs-only: `rtk git diff --check`.
- API/schema/action: focused `rtk uv run pytest ...`.
- Dashboard: touched route test plus `rtk pnpm --dir apps/dashboard typecheck`.
- Skill changes: deterministic smoke and targeted eval.
- Marketer copy: `rtk uv run python scripts/marketer_language_guard.py`.
- Browser: `agent-browser` snapshot for touched marketer routes.

Broad checks:

- `rtk scripts/verify.sh` before cross-surface completion claims.

## Completion Definition

Goal 001 is complete when:

- Active docs agree on the corrected product model.
- Active product paths no longer depend on dev-site migration semantics.
- Primary marketer surfaces no longer show forbidden technical jargon.
- UI translators/string replacement cleanup helpers are removed or proven
  out-of-scope internal utilities.
- Focused API/dashboard/skill checks pass for all touched slices.
- Browser proof verifies touched marketer routes.
- Remaining historical mentions are archived or explicitly tracked as removal
  debt.

The final WILQ Marketing Operating System remains a later goal. It still
requires ContentPreflight, sales brief, claim ledger, sprawdzenie przez
człowieka, WordPress draft handoff, measurement loop, workspace profiles,
knowledge lifecycle and safe execution gates.
