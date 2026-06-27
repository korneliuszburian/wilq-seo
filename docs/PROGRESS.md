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

- `c5ea815 fix(dashboard): source ads and knowledge labels from api`
- `66a0a4d fix(dashboard): source tactical labels from api`
- `443dad4 fix(actions): drop obsolete content review audits`
- `d2f78a6 fix(actions): label impact check result sources`
- `6497044 fix(ads): source negative keyword labels from api`
- `5b81874 docs: condense active cleanup recovery`
- `df4c750 fix(ads): clean recommendation and keyword context copy`
- `5a805aa fix(merchant): condense source and evidence labels`
- `d783636 fix(ga4): clean measurement labels`
- `0a7414e fix(localo): clean access proof labels`
- `6e93975 fix(dashboard): hide raw trace ids in detail panels`
- `e6001a5 fix(dashboard): source proof labels from api`
- `f74c770 fix(demand-gen): expose clean proof labels`
- `be6205b fix(brief): use clean action wording`
- `709a4cc fix(dashboard): remove id jargon from proof copy`
- `551108f fix(ads): source secondary proof labels from api`
- `f853404 fix(dashboard): clean registry evidence counts`

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
- Marketing brief and action validation no longer expose `akcji WILQ`,
  `ID dowodu` or English validation wording as operator copy.
- Merchant, Content Planner and Ahrefs proof rows no longer render `ID`
  evidence counts or "przykładowe ID produktów" in normal marketer copy.
- Ads Doctor secondary proof rows now use API-owned evidence, source and action
  summaries instead of route-local counts or `Akcje WILQ` labels.
- Actions, Opportunities, Registry and Knowledge panels no longer render
  `Dowody: X ID` as normal route copy in the touched paths.
- Action impact-check results now return API-owned source labels and evidence
  summaries, and the dashboard no longer renders raw source connector IDs in
  that result panel.
- Old content-review audit events based on dev-site mapping are now dropped
  from active action output instead of being rewritten at response time.
- Stale 2026-06-24/25 handoff and audit docs that still mentioned dev-site
  migration now carry superseded notes.
- The cleaned surfaces keep traceability through typed contracts, but raw
  internals are moved out of first-screen marketer copy.

Latest cleanup state:

- Tactical Queue, Brief Workflow and Merchant tactical snippets now consume
  API-owned priority/source/evidence/action/blocker/dimension labels instead
  of dashboard-owned `priorityLabel`, tactical intent maps, dimension maps and
  blocker replacement helpers.
- Shared schemas now expose those label fields for marketing brief items,
  tactical queue items/groups and Merchant decisions.
- Ads Doctor no longer imports `marketingLabels.ts`; the touched Ads proof,
  summary and section label paths now use API/shared-schema label fields.
- Knowledge panels no longer own route/status/risk/card/source display maps;
  knowledge cards, playbooks and decision bindings now carry API-owned labels.
- Action detail previews no longer import the deleted `marketingLabels.ts`.
  `DetailPanels.tsx` now reads API-owned payload label fields for blocked
  claims, Localo allowed reads, Ads target options and WordPress post status.
- Ads Doctor no longer owns the start-here summary, effect-check summary or
  business-context status value in React. Those marketer-facing fields now come
  from the Ads API contract.
- Backend and dashboard tests assert the tactical, Ads, Knowledge, action
  detail and Ads Doctor presentation contracts.

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
- Latest proof-copy cleanup:
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk uv run pytest tests/test_api_contracts.py -q -k "merchant_diagnostics or marketing_brief or ahrefs_diagnostics or content_diagnostics or actions" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "content route renders condensed selected decision with expandable detail|ahrefs route renders authority context and clean gap review language|merchant route renders dedicated feed diagnostics" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk git diff --check`
- Browser proof for Merchant, Content Planner and Ahrefs cleanup:
  `.local-lab/proof/20260627-label-cleanup-browser/`
- Ads secondary label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "ads doctor route renders live metric-backed diagnostics" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  browser proof: `.local-lab/proof/20260627-ads-secondary-label-cleanup/`
- Registry/actions evidence-count cleanup:
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/RegistryPanels.test.tsx src/routes/App.test.tsx -t "connector refresh run cards summarize evidence instead of printing raw IDs|actions route starts from marketer-facing actions instead of registry dumps" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  browser proof: `.local-lab/proof/20260627-actions-registry-id-cleanup/`
- Action impact-check label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "action_impact_check" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "actions route starts from marketer-facing actions instead of registry dumps" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
- Legacy content-review audit cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "legacy_content_review or action_impact_check" --maxfail=1`
- Tactical/brief/Merchant label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "marketing_tactical_queue_uses_dimensioned_metric_facts or marketing_brief_aggregates_metric_facts_and_blockers or merchant_diagnostics" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/TacticalQueuePanel.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
- Ads/Knowledge label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics or knowledge_playbooks or knowledge_compiler or knowledge_operating_map" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/KnowledgePanels.test.tsx src/routes/App.test.tsx -t "KnowledgePanels|knowledge route maps source knowledge to decisions" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
- Action detail label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "content_brief_candidate_review_persists_audit_event or google_ads_business_context_allows_empty_preliminary_targets or localo_diagnostics_exposes_partial_visibility_contracts" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
- Ads Doctor presentation cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "google_ads_business_context_allows_empty_preliminary_targets or ads_diagnostics" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "ads doctor route renders live metric-backed diagnostics" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
- Earlier GA4 browser proof:
  `.local-lab/proof/20260627-ga4-measurement-copy-cleanup/`

## Active Gaps

Next cleanup queue:

1. Action detail previews:
   - replace `DetailPanels.tsx` payload-shape inference with typed API preview
     rows; keep raw payload only in collapsed technical detail.
2. Content Planner:
   - move active `contentLabels.ts` semantics for action preview, status,
     blocked-claim and metric labels into content/action API contracts.
3. Metric labels:
   - move repeated metric/dimension naming into API-owned metric label fields;
     keep pure numeric formatting in UI.
4. Recovery docs:
   - keep this file, `PLAN.md`, `PLANS.md`, `docs/CONTEXT.md` and the active
     goal aligned and short.

## Next Best Move

1. Start the next cleanup slice from the active queue. The highest-impact next
   target is either the Content Planner/contentLabels slice or the larger typed
   action-detail preview view-model.

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
