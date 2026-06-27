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
- Current Merchant source/evidence condensation is verified locally and ready
  to commit.

What changed:

- Merchant diagnostics now expose API-owned source connector labels and evidence
  summaries for decision queue, operator summary, product performance readiness,
  product rows and price-impact readiness.
- Merchant dashboard no longer shows raw connector IDs, evidence IDs or read
  contract/debug labels on the cleaned panels. It shows `Merchant Center`,
  `1 dowód źródłowy`, `Stan danych` and safer write-readiness wording instead.

Proof:

- Focused Merchant API tests:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "merchant_diagnostics_exposes_feed_issue_queue or merchant_product_performance_readiness" --maxfail=1`
- Dashboard typecheck:
  `rtk pnpm --dir apps/dashboard typecheck`
- Dashboard Merchant route test:
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "merchant route renders dedicated feed diagnostics" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`

## Active Gaps

Next cleanup queue:

1. Ads Doctor:
   - route-local raw-key fallbacks still exist in secondary helper paths and
     should be retired as API labels cover those paths.
2. GA4:
   - visible copy can expose `(not set)`, `tracking-gap` and evidence counts as
     `ID`.
3. Localo:
   - visible proof panels can expose `OAuth code`, `PKCE S256`, `Token` and raw
     `localo` connector ID.
4. Actions:
   - impact result can expose raw source connector IDs,
   - missing label fallbacks can become visible copy.
5. Recovery docs:
   - keep this file, `PLAN.md`, `PLANS.md`, `docs/CONTEXT.md` and the active
     goal aligned and short.

## Next Best Move

1. Commit and push the Merchant source/evidence condensation slice after live
   proof.
2. Continue with GA4 route cleanup from API/domain labels, not React string
   replacement.
3. Then clean Localo credential/protocol language.
4. Then clean Action detail impact/source fallback copy.

## Blockers

- Real marketer UAT is not recorded as complete in this session.
- The full WILQ Marketing Operating System is not complete. ContentPreflight,
  sales brief, claim ledger, sprawdzenie przez człowieka, WordPress draft
  handoff, measurement loop, workspace profiles, knowledge lifecycle and safe
  execution gates remain future product work in `PLANS.md`.
