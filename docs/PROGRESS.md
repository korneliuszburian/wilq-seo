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
- Content Planner no longer owns local label helpers for content brief source,
  content brief mode, WordPress draft operation, WordPress post status, draft
  generation status or publication readiness. Content action payload previews
  now carry those API-owned labels, and the route renders them directly.
- Content Planner no longer owns local connector status, refresh status,
  section blocked-claim, section title or metric-name translators. Content
  diagnostics now return API-owned `status_label`, `metric_label` and
  `blocked_claim_labels`, and the old content label registry was pruned down to
  numeric value formatting only.
- Merchant action detail previews now use API-owned typed preview cards. The
  detail route renders `preview_cards` before any raw payload fallback, and
  Merchant feed issue cards no longer show raw SKU/product IDs as first-screen
  copy.
- Localo metric chips now use API-owned `metric_label` values. Localo
  diagnostics and marketing brief share one domain label source, and the
  dashboard no longer keeps a local metric-name dictionary for
  `MetricFactChips`.
- `MetricFact` now carries `dimension_labels` and `dimension_value_labels`.
  `MetricFactChips` renders those API-owned labels and no longer owns local
  dimension key/value dictionaries.
- Merchant diagnostics now attach API-owned `metric_label`, `dimension_labels`
  and `dimension_value_labels` to Merchant metric facts. The Merchant route no
  longer owns a local metric-label dictionary for the evidence/limitations
  metric tiles.
- Backend and dashboard tests assert the tactical, Ads, Knowledge, action
  detail, Ads Doctor and Content Planner presentation contracts.

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
- Content Planner action-preview label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "content_brief_preview or content_diagnostics" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "content route renders condensed selected decision with expandable detail" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
- Content Planner diagnostic label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "content_diagnostics or content_brief_preview" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "content route renders condensed selected decision with expandable detail" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk git diff --check`
  Live proof after `rtk scripts/local_stack.sh restart`: `/api/content/diagnostics`
  returned all required content `*_label` fields and `agent-browser read`
  confirmed `/content-planner` renders live marketer copy without console
  errors.
- Merchant action-detail typed preview cards:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "merchant_diagnostics or action_preview" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  Live proof after `rtk scripts/local_stack.sh restart`:
  `/api/actions/act_review_merchant_feed_issues` returned four
  `preview_cards`, Polish row labels and no raw SKU in card rows.
  `agent-browser read` for `/actions/act_review_merchant_feed_issues`
  confirmed visible Merchant preview cards without console errors.
- Localo metric label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "marketing_brief_localo_metric_headline_is_marketer_friendly or localo_diagnostics_exposes_partial_visibility_contracts" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/components/MetricFactChips.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "localo route renders workflow-specific blockers and clean metric labels" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk git diff --check`
  Live proof after `rtk scripts/local_stack.sh restart`:
  `/api/localo/diagnostics` returned Localo decision metric labels with no
  missing labels, `/api/marketing/brief` returned Localo metric labels in the
  brief and top metric facts, `/api/localo/diagnostics` returned metric
  dimension labels/value labels, and `agent-browser read` confirmed `/localo`
  shows named Localo metrics and dimensions instead of dashboard fallback copy.
- Merchant metric label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "merchant_diagnostics" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "merchant route renders dedicated feed diagnostics" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk git diff --check`
  Live proof after `rtk scripts/local_stack.sh restart`: `/api/merchant/diagnostics`
  returned Merchant metric labels and dimension value labels without raw
  `SHOPPING_ADS`, `FREE_LISTINGS`, `MERCHANT_ACTION` or `NOT_IMPACTED` in the
  label fields. `agent-browser read` for `/merchant` confirmed the primary
  Merchant route renders clean Polish decision copy.
- Earlier GA4 browser proof:
  `.local-lab/proof/20260627-ga4-measurement-copy-cleanup/`

## Active Gaps

Next cleanup queue:

1. Action detail previews:
   - Merchant feed issue previews have typed API cards.
   - migrate remaining action kinds one by one from `DetailPanels.tsx`
     payload-shape inference to typed API preview cards; keep raw payload only
     in collapsed technical detail.
2. Primary route raw fallbacks:
   - clean remaining GA4, Merchant, Demand Gen, registry/workflow and knowledge
     route fallbacks that still return raw enum keys or technical values when
     API labels are missing.
3. Metric labels:
   - metric names in `MetricFactChips` now come from `metric_label`.
   - metric dimensions in `MetricFactChips` now come from `dimension_labels`
     and `dimension_value_labels`.
   - Merchant diagnostic metric tiles now use API-owned metric labels.
   - continue removing remaining route-local dictionaries for metric,
     preview-contract or status semantics; keep pure numeric formatting in UI.
4. Recovery docs:
   - keep this file, `PLAN.md`, `PLANS.md`, `docs/CONTEXT.md` and the active
     goal aligned and short.

## Next Best Move

1. Start the next cleanup slice from the active queue. The highest-impact next
   target is the typed action-detail preview view-model, with route-specific
   raw fallback cleanup as parallel audit/worker slices.

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
