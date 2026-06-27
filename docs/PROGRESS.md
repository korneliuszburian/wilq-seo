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

What changed:

- GA4 diagnostics now expose API-owned source connector labels, evidence
  summaries and safe dimension labels for decision queue, operator summary,
  sections and conversion readiness.
- GA4 action preview rows now carry labels for landing page, source/medium,
  campaign, required checks, blocked promises and evidence summaries.
- GA4 dashboard no longer shows raw `(not set)`, `tracking-gap`, connector IDs,
  evidence IDs or `ID` evidence counts on the cleaned route.

Current active slice: Localo cleanup.

Proof:

- Focused GA4 API tests:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "ga4_diagnostics_exposes_landing_quality_contract or ga4_measurement_decision_titles_include_reporting_context" --maxfail=1`
- Dashboard typecheck:
  `rtk pnpm --dir apps/dashboard typecheck`
- Dashboard GA4 route test:
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "ga4 route renders workflow-specific brief focus" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
- Live API/browser proof:
  `.local-lab/proof/20260627-ga4-measurement-copy-cleanup/`

## Active Gaps

Next cleanup queue:

1. Localo:
   - visible proof panels can expose `OAuth code`, `PKCE S256`, `Token` and raw
     `localo` connector ID.
2. Ads Doctor:
   - route-local raw-key fallbacks still exist in secondary helper paths and
     should be retired as API labels cover those paths.
3. Actions:
   - impact result can expose raw source connector IDs,
   - missing label fallbacks can become visible copy.
4. Recovery docs:
   - keep this file, `PLAN.md`, `PLANS.md`, `docs/CONTEXT.md` and the active
     goal aligned and short.

## Next Best Move

1. Clean Localo credential/protocol language from API/domain labels, not React
   string replacement.
2. Clean Ads secondary fallback copy.
3. Clean Action detail impact/source fallback copy.

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
