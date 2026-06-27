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

## Latest Verified Slice

Commit:

- `6497044 fix(ads): source negative keyword labels from api`

What changed:

- Ads Doctor negative-keyword review now uses API-owned labels for:
  - safety status,
  - validation status,
  - required checks,
  - match type,
  - exclusion level,
  - keyword context,
  - blocked promises.
- The dashboard consumes those labels instead of rendering raw Google Ads enum
  values or route-local translations.

Proof:

- Focused API test:
  `rtk uv run pytest tests/test_api_contracts.py -k "ads_diagnostics_exposes_live_campaign_metric_facts" --maxfail=1`
- Dashboard typecheck:
  `rtk pnpm --dir apps/dashboard typecheck`
- Dashboard route test:
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "ads doctor route renders live metric-backed diagnostics" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
- Marketer language guard:
  `rtk uv run python scripts/marketer_language_guard.py`
- Live API/browser proof:
  `.local-lab/proof/20260627-ads-negative-keyword-api-labels/`

## Active Gaps

Next cleanup queue:

1. Ads Doctor:
   - recommendation rationale still contains `Google Ads recommendations` and
     `RMF/compliance review`,
   - recommendation summaries can expose raw enum values such as
     `CAMPAIGN_BUDGET`,
   - keyword context table can render raw match/status enum values,
   - visible labels still include `Safety 90d`, `Keywords`, `Źródłowe query`,
   - route-local raw-key fallbacks still exist.
2. Merchant:
   - primary decision screen can expose raw source connector IDs and evidence
     IDs,
   - expanded review uses contract/debug wording,
   - write-readiness preview says `API gotowe do zapisu`.
3. GA4:
   - visible copy can expose `(not set)`, `tracking-gap` and evidence counts as
     `ID`.
4. Localo:
   - visible proof panels can expose `OAuth code`, `PKCE S256`, `Token` and raw
     `localo` connector ID.
5. Actions:
   - impact result can expose raw source connector IDs,
   - missing label fallbacks can become visible copy.
6. Recovery docs:
   - keep this file, `PLAN.md`, `PLANS.md`, `docs/CONTEXT.md` and the active
     goal aligned and short.

## Next Best Move

1. Finish the docs-only condensation slice and push it.
2. Start the Ads Doctor recommendation/keyword-context cleanup slice from API
   source, not from dashboard string replacement.
3. Run focused Ads API/dashboard checks and browser proof.
4. Commit and push.
5. Continue with Merchant first-screen source/evidence condensation.

## Blockers

- Real marketer UAT is not recorded as complete in this session.
- The full WILQ Marketing Operating System is not complete. ContentPreflight,
  sales brief, claim ledger, sprawdzenie przez człowieka, WordPress draft
  handoff, measurement loop, workspace profiles, knowledge lifecycle and safe
  execution gates remain future product work in `PLANS.md`.
