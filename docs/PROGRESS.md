# WILQ Progress Ledger

This is the short recovery ledger. It is not a changelog and must not become an
append-only transcript.

Full current plan: `PLAN.md`
Long-range product plan: `PLANS.md`
Active goal: `docs/goals/001-goal.md`

## Current Readout

Date: 2026-06-27

- WILQ is the system/product.
- Wilku is the human marketer/operator persona.
- Ekologus is the first depth-first workspace/client.
- `ekologus.pl` is the public canonical content home.
- Dev preview hosts are optional design/staging context only when explicitly
  configured for a workflow.
- Existing Ekologus content is preserve-first. A redesign does not imply
  rewriting existing content.
- WILQ API remains the product brain. Dashboard and Codex skills must consume
  typed API contracts, evidence IDs and source connectors.
- Do not preserve outdated fields, old wording, route-local cleanup helpers or
  compatibility aliases as a strategy. Migrate touched active consumers
  directly.

## Latest Verified Slices

Recent commits:

- `6497044 fix(ads): source negative keyword labels from api`
- `5b81874 docs: condense active cleanup recovery`
- `df4c750 fix(ads): clean recommendation and keyword context copy`
- `5a805aa fix(merchant): condense source and evidence labels`
- `d783636 fix(ga4): clean measurement labels`
- `0a7414e fix(localo): clean access proof labels`
- `6e93975 fix(dashboard): hide raw trace ids in detail panels`
- `e6001a5 fix(dashboard): source proof labels from api`
- `f74c770 fix(demand-gen): expose clean proof labels`

What changed:

- Ads, Merchant, GA4, Localo, Action Detail, Merchant proof, Content proof,
  Ahrefs proof and Brief Workflow now consume API/domain/shared-schema labels
  for the cleaned paths instead of route-local label replacement.
- Cleaned panels no longer show raw evidence IDs, action IDs, connector IDs,
  `Przykładowe dowody`, `Łącznie dowodów`, `OAuth`, `access token`, PKCE/token
  wording, raw `(not set)` labels or `ID` evidence counts as normal marketer
  copy.
- Demand Gen now exposes API-owned source labels and evidence summaries, and
  the route no longer renders raw `google_ads`, `google_analytics_4` or `ID`
  evidence counts as normal proof copy.
- The cleaned surfaces keep traceability through typed contracts, but raw
  internals are moved out of first-screen marketer copy.

Current active slice: remaining secondary dashboard cleanup and browser proof.

Proof:

- Focused API tests:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "merchant_diagnostics or content_diagnostics or ahrefs_diagnostics or marketing_brief_aggregates_metric_facts_and_blockers or marketing_brief_localo_metric_headline_is_marketer_friendly or marketing_brief_localo_blocker_uses_marketer_copy" --maxfail=1`
- Dashboard typecheck:
  `rtk pnpm --dir apps/dashboard typecheck`
- Dashboard focused route tests:
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "merchant route renders dedicated feed diagnostics|content route renders condensed selected decision with expandable detail|ahrefs route renders authority context and clean gap review language" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
- Brief workflow tests:
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/BriefWorkflowSurface.test.tsx src/routes/App.test.tsx -t "BriefWorkflowSurface config|social route renders workflow-specific blockers" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
- Demand Gen focused tests:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "demand_gen_diagnostics_exposes_honest_readiness_contract or codex_context_pack_scopes_demand_gen_payload" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "demand gen route renders readiness contract instead of generic registry" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
- Live API/browser proof exists for GA4 cleanup only:
  `.local-lab/proof/20260627-ga4-measurement-copy-cleanup/`

## Active Gaps

Next cleanup queue:

1. Browser proof:
   - run the dashboard route walkthrough for the newly cleaned Merchant,
     Content, Ahrefs and Brief Workflow surfaces.
2. Ads Doctor:
   - route-local raw-key fallbacks still exist in secondary helper paths and
     should be retired as API labels cover those paths.
3. Actions:
   - scan remaining detail/impact surfaces for raw source connector fallback
     copy outside the already cleaned first-screen panels.
4. Recovery docs:
   - keep this file, `PLAN.md`, `PLANS.md`, `docs/CONTEXT.md` and the active
     goal aligned and short.

## Next Best Move

1. Capture browser proof for the newly cleaned route set.
2. Clean Ads secondary fallback copy.
3. Scan remaining action/registry panels and remove marketer-visible raw IDs
   only where they are normal UI, not intentional technical drilldown.

## Guardrails

- No React/UI translator functions for product semantics.
- No hardcoded label replacement.
- No compatibility aliases or deprecated active fields when a direct migration
  is feasible.
- Every repeated issue becomes a typed API/schema/view-model field or a test
  guard.

## Blockers

- Real marketer UAT is not recorded as complete in this session.
- The full WILQ Marketing Operating System is not complete. ContentPreflight,
  sales brief, claim ledger, sprawdzenie przez człowieka, WordPress draft
  handoff, measurement loop, workspace profiles, knowledge lifecycle and safe
  execution gates remain future product work in `PLANS.md`.
