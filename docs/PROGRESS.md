# WILQ Progress Ledger

This is the short recovery ledger. It is not a changelog and must not become an
append-only transcript.

Full current plan: `PLAN.md`
Long-range product plan: `PLANS.md`
Active goal: `docs/goals/001-goal.md`

## Current Readout

Date: 2026-06-28

- WILQ is the system/product.
- Wilku is the human marketer/operator persona.
- Ekologus is the first depth-first workspace/client.
- `ekologus.pl` is the public canonical content home.
- Dev preview hosts are optional design/staging context only when explicitly
  configured. They are not canonical content targets and must not drive content
  decisions by default.
- WILQ API is the product brain. Dashboard and Codex skills consume typed API
  contracts, source connectors and WILQ-described evidence.
- Marketer-facing UI and skill output must use Polish operating language.
- Raw IDs, connector trace, raw payloads and audit details belong only in
  technical detail.
- Dirty copy must be fixed in typed API/schema/view-model/domain source, not
  with React translators or string replacement helpers.
- Do not preserve deprecated active fields, compatibility aliases or stale
  dev-preview/migration semantics when direct migration is feasible.

## Latest Verified State

- Primary navigation and touched route headings use marketer-readable Polish:
  `Centrum pracy`, `Merchant`, `Treści`, `Google Ads`, `GA4`, `Procesy`,
  `Szanse`, `Akcje`, `Baza wiedzy`.
- Touched Ads, Merchant, GA4, Localo, Ahrefs, Knowledge, tactical queue,
  Procesy and action-detail surfaces render API/domain/shared-schema labels
  instead of route-local label dictionaries.
- Action-detail normal preview uses typed API preview cards. Raw action payloads
  stay behind technical detail.
- Content active semantics use public/final URL wording. Active content
  diagnostics/actions no longer expose dev-site placement semantics as product
  logic.
- Treści selected-decision and plan/draft panels render API-owned
  view-models instead of parsing raw action payload previews.
- Treści loading/error action fallback uses the API-owned action summary label
  instead of assembling action-count copy from action IDs.
- Treści preflight, summary, decision, proof and action panels use API/domain
  evidence and action summary labels instead of route-local count formatting.
- Merchant, Ads, GA4, Demand Gen, Localo and social touched preview surfaces use
  API-owned preview cards or display labels instead of raw payload shape.
- Localo top metric tiles use API/domain missing-data summary labels instead
  of route-local count formatting.
- GA4 overview, decision and proof panels use API/domain evidence and action
  summary labels instead of route-local count formatting.
- Google Ads first-screen, condensed decision, proof and action panels use
  API/domain evidence and action summary labels instead of route-local count
  formatting.
- Google Ads start-here, business-context, strategy-readiness and campaign
  triage panels use API/domain action summary labels instead of route-local
  action count formatting.
- Google Ads optimizer-readiness and strategy review panels use API/domain
  source-contract, policy and required-validation summary labels instead of
  route-local count formatting.
- Google Ads strategy review panel uses API/domain missing-data summary labels
  instead of route-local count formatting.
- Action priority cards, action registry cards and connector refresh run cards
  use API/domain evidence summary labels instead of route-local evidence count
  formatting.
- Merchant overview, operator summary, decision, proof and action panels use
  API/domain evidence and action summary labels instead of route-local count
  formatting.
- Ahrefs decision and gap-contract panels use API/domain evidence and action
  summary labels instead of route-local count formatting.
- Ahrefs gap-contract metric tiles use API/domain missing-data and
  blocked-claim summary labels instead of route-local count formatting.
- Custom Segments candidate, forecast and proof panels use API/domain evidence
  and action summary labels instead of route-local count formatting.
- Custom Segments validation tiles use API/domain missing-data and
  required-check summary labels instead of route-local count formatting.
- Demand Gen uses API/domain evidence, action and campaign-channel labels
  instead of route-local count formatting or raw channel fallbacks.
- Google Ads search-term, negative-keyword and change-history surfaces use
  API/schema display labels for campaign, ad group, change event and changed
  resource context instead of visible raw IDs.
- Google Ads campaign triage, search-term, n-gram, 90-day safety and keyword
  context rows use API/domain evidence summary labels instead of route-local
  evidence count formatting.
- Google Ads campaign, KPI, budget, impression-share and change-history tables
  use API/domain row summary labels for human review gates, blocked claims and
  changed fields instead of route-local label joins.
- Connector settings cards use API/domain credential summary labels instead of
  route-local credential/source count formatting.
- Merchant issue-cluster cards and decision summaries use API/domain reported
  issue summary labels instead of route-local issue count formatting or broken
  Polish count forms.
- Treści expanded decision and Ahrefs review cards use API labels or neutral
  Polish operator fallbacks instead of visible raw enum/status keys.
- Knowledge details use API-owned source labels and Polish count forms instead
  of raw connector IDs.
- Knowledge first-screen decision and card summaries use API/domain source,
  action, evidence, knowledge and lineage summary labels instead of route-local
  count assembly.
- Knowledge playbook cards use API/domain evidence and action-type summary
  labels instead of route-local Polish count formatting.
- Knowledge decision cards use API/domain blocked-claim summary labels instead
  of joining blocked-claim arrays or falling back to raw counts in React.
- Knowledge decision-impact panels use API/domain missing-data,
  blocked-decision and blocked-claim summary labels. First-screen
  blocked-claim copy is condensed to count summaries, while full claim lists
  stay in details.
- Procesy cards and run summaries use API/domain source, evidence, action,
  missing-data and blocked-claim summary labels. Fresh `/workflows` loads no
  longer wait on hidden related-action data.
- Procesy expanded details use API/domain missing-data detail labels and
  condensed blocked-claim summaries instead of route-local label joins.
- Szanse cards use API/domain evidence, source, action and knowledge summary
  labels instead of route-local count assembly or raw identifiers.
- Shared `StatusBadge` does not own a product-language dictionary; touched
  surfaces pass raw state values plus API/domain visible labels.
- Unknown visible label fallbacks collapse to neutral Polish operator labels
  instead of exposing raw enum keys, snake_case or English values.
- Current proof artifacts live in `.local-lab/proof/`; detailed history lives
  in git commits.

## Active Findings

1. Keep `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and
   `docs/goals/001-goal.md` short and aligned. History belongs in git and proof
   artifacts.
2. Continue raw fallback cleanup in active API/helper modules. Any new visible
   raw fallback must be fixed at typed API/schema/view-model source.
3. Add typed contract/vendor-enum label registries outside the already-cleaned
   Ads diagnostics helper path so unknown read contracts and vendor enums do not
   fall back to raw snake_case or English values in marketer-facing copy.
4. Continue moving repeated metric, dimension, source, blocker and evidence
   naming into API/domain labels. Pure numeric formatting can stay in UI.
5. Dashboard still needs focused cleanup for remaining payload-derived panels.
6. Remaining active `replace("_", " ")` scan hits are Merchant attribute-key
   normalizers used for equality matching, not visible operator labels; keep
   them out of copy paths.
7. Continue checking compacted context-packs after dashboard/API cleanup; the
   content strategist context currently preserves content preview labels.
8. Ads full-review detail still contains some long blocked-claim and review-gate
   lists outside the cleaned row tables; continue condensing those at API/domain
   source instead of trimming them in React.
9. Real marketer UAT is still required for a usefulness claim unless the owner
   explicitly defers it.

## Latest Accepted Proof

Most recent verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics_summary_view_compacts_heavy_payload or ads_campaign_read_contract or ads_budget_pacing or ads_impression_share or ads_change_history" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "ads doctor route renders live metric-backed diagnostics"`
- `rtk pnpm --dir packages/shared-schemas exec vitest run src/index.test.ts --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- Live API proof: `/api/ads/diagnostics?view=summary` returns
  `human_review_gate_summary_label="7 wymaganych sprawdzeń"`,
  `blocked_claim_summary_label="8 zablokowanych obietnic"` for a budget row and
  `blocked_claim_summary_label="4 zablokowane obietnice"` for an
  impression-share row.
- Browser proof: expanded `/ads-doctor` tables render condensed row labels such
  as `4 zablokowane obietnice` and `7 wymaganych sprawdzeń`; the proof scan has
  no raw `payload`, `ActionObject`, migration, `human_review_gate_labels`,
  `blocked_claim_labels`, `changed_field_labels`, `CAMPAIGN`, `UPDATE` or raw
  changed-field key wording.

Previous verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "workflows_are_decision_backed_operator_contracts or workflow_label_fallbacks_do_not_expose_raw_values" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/WorkflowPanels.test.tsx src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "workflow|Workflow|Procesy"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- Live API proof: `/api/workflows` returns
  `missing_contract_detail_label="lokalne pozycje, wyniki profilu firmy, opinie"`
  for `localo_visibility_review` and condensed
  `blocked_claim_summary_label="2 zablokowane obietnice"`.
- Browser proof: expanded `/workflows` process detail renders
  `Brakujące dane: brak` and `Granice wniosków: 17 zablokowanych obietnic`
  without raw workflow keys, payload wording, `ActionObject`, migration wording
  or raw blocked-claim detail such as `werdykt zwrotu z reklam`.

Previous verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "operator_label_fallbacks_do_not_humanize_raw_unknown_enums or knowledge_operating_map_binds_sources_to_decisions" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/KnowledgePanels.test.tsx src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "knowledge|Knowledge"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- Live API proof: `/api/knowledge/operating-map` returns
  `blocked_binding_summary_label="4 zablokowane decyzje"`,
  `missing_contract_summary_label="13 brakujących zakresów danych"` and
  `blocked_claim_count_summary_label="29 zablokowanych obietnic"`.
- Browser proof: `/knowledge` renders condensed labels such as
  `17 zablokowanych obietnic` without raw Knowledge field names, payload
  wording, migration wording or raw playbook IDs.

Previous verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics_summary_view_compacts_heavy_payload" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "ads doctor route renders live metric-backed diagnostics"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- Live API proof: `/api/ads/diagnostics` returns
  `business_context_read_contract.strategy_review_readiness_contract.missing_read_contract_summary_label="2 brakujące zakresy danych"`.
- Browser proof: expanded `/ads-doctor` renders `2 brakujące zakresy danych`
  without raw strategy-readiness fields, `payload` or `ActionObject` wording.

Previous verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "custom_segments" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "custom segments route renders dedicated validation contract"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- Live API proof: `/api/ads/diagnostics?view=summary` returns
  `missing_read_contract_summary_label="2 brakujące zakresy danych"` and
  `operator_review_gate_summary_label="5 wymaganych sprawdzeń"`.
- Browser proof: `/ads-doctor/custom-segments` renders those labels without
  raw contract fields, `payload` or `ActionObject` wording.

Previous verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "localo_diagnostics" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "localo route renders workflow-specific blockers and clean metric labels"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- Live API proof: `/api/localo/diagnostics` returns
  `missing_read_contract_summary_label="1 brakujący zakres danych"`.
- Browser proof: `/localo` renders `1 brakujący zakres danych` without raw
  Localo contract fields, `payload` or `ActionObject` wording.

Previous verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "ahrefs_diagnostics" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "ahrefs route renders authority context and clean gap review language"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/ahrefs/diagnostics` returns
  `missing_read_contract_summary_label="brak brakujących danych"` and
  `blocked_claim_summary_label="2 zablokowane obietnice"`.
- Browser proof: `/ahrefs` renders the same clean summary labels without raw
  gap-contract field names, `payload` or `ActionObject` wording.

Previous verified local slice:

- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionObjectPanels.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "content route renders condensed selected decision with expandable detail"`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/content/diagnostics` returns
  `action_summary_label="2 akcje do sprawdzenia"`.
- Browser proof: `/content-planner` renders `2 akcje do sprawdzenia` without
  fallback action-count wording, raw payload wording or stale
  target/migration terms.

Previous verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics_summary_view_compacts_heavy_payload" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "ads doctor route renders live metric-backed diagnostics"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/ads/diagnostics?view=summary` returns
  `source_contract_summary_label`, `policy_summary_label` and
  `required_validation_summary_label`.
- Browser proof: `/ads-doctor` expanded Ads review renders
  `1 warunek źródłowy`, `5 polityk` and `5 wymaganych sprawdzeń`
  without raw field names, `payload` or `ActionObject` wording.

Previous verified local slice:

- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "merchant route renders dedicated feed diagnostics"`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "merchant_diagnostics_groups_reporting_contexts_into_one_operator_decision" --maxfail=2`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Backend model proof: `MerchantIssueCluster` hydrates
  `reported_issue_summary_label` with Polish count forms.
- Live API proof: `/api/merchant/diagnostics` returns
  `reported_issue_summary_label` and decision summaries with
  `3 zgłoszenia problemu`.
- Browser proof: `/merchant` expanded Merchant review renders
  `Największy raport pokazuje 3 zgłoszenia problemu` without raw issue keys,
  action internals or payload wording.

Previous verified local slice:

- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/RegistryPanels.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Backend model proof: `ConnectorStatus` hydrates credential summary labels.
- Live API proof: `/api/connectors` returns
  `missing_credentials_summary_label` and `credential_source_summary_label`.
- Browser proof: `/settings` expanded access panel renders credential/source
  summaries without raw secret names, connector IDs or credential source IDs.

Previous verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics_summary_view_compacts_heavy_payload or ads_search_terms" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "ads doctor route renders live metric-backed diagnostics"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/ads/diagnostics?view=summary` returns evidence
  summary labels for Ads campaign triage, search-term, n-gram, safety and
  keyword context rows.
- Browser proof: `/ads-doctor` renders Ads evidence summary labels without raw
  payloads, `ActionObject` wording, raw connector IDs or the old route label.

Previous verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "tactical_queue_uses_short_ttl_cache or tactical_queue_uses_latest_metric_fact_batch_for_speed" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/RegistryPanels.test.tsx src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "connector refresh|ads doctor route renders live metric-backed diagnostics"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/connectors/refresh-runs` returns
  `evidence_summary_label` for connector refresh runs.
- Browser proof: `/actions` renders action evidence summary labels without raw
  action payloads, `ActionObject` wording or connector IDs.

Previous verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics_summary_view_compacts_heavy_payload" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "ads doctor route renders live metric-backed diagnostics"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/ads/diagnostics?view=summary` returns nested Ads
  action summary labels for target interpretation, strategy readiness,
  campaign triage contract/rows and change-impact readiness.
- Browser proof: `.local-lab/proof/ads-deep-action-summary-labels-clean.txt`

Previous verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics_summary_view_compacts_heavy_payload" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "ads doctor route renders live metric-backed diagnostics"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/ads/diagnostics` returns response, operator summary,
  decision and section evidence/action summary labels.
- Browser proof: `.local-lab/proof/ads-summary-labels-clean.txt`

Earlier verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "content_diagnostics" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "content route renders condensed selected decision with expandable detail"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/content/diagnostics` and `/api/content/preflight`
  return response, operator summary, decision, section and preflight evidence/action
  summary labels.
- Browser proof: `.local-lab/proof/content-summary-labels-clean.txt`

Earlier verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "merchant" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "merchant route renders dedicated feed diagnostics"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/merchant/diagnostics` returns response, operator
  summary, decision and section evidence/action summary labels.
- Browser proof: `.local-lab/proof/merchant-summary-labels-clean.txt`

- `rtk uv run pytest tests/test_api_contracts.py -q -k "demand_gen" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "demand gen route renders readiness contract instead of generic registry"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/demand-gen/diagnostics` returns response-level
  evidence/action summary labels; current live data has no Demand Gen row
  records to display, and fixture tests cover row-level labels.
- Browser proof: `.local-lab/proof/demand-gen-row-evidence-labels-clean.txt`

Earlier verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "custom_segments" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "custom segments route renders dedicated validation contract"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/ads/diagnostics` returns evidence/action summary
  labels for Custom Segments contract, candidates, forecast contract and
  forecast rows.
- Browser proof: `.local-lab/proof/custom-segments-summary-labels-clean.txt`

Earlier verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "ahrefs_diagnostics_exposes_authority_context_and_blocks_gap_claims or ahrefs_diagnostics_builds_gap_review_records_from_metric_facts or ahrefs_diagnostics_keeps_gap_records_when_newer_authority_reads_are_noisy" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "ahrefs route renders authority context"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/ahrefs/diagnostics` returns evidence/action summary
  labels for the response, gap contract, operator summary, decisions and
  sections.
- Browser proof: `.local-lab/proof/ahrefs-summary-labels-clean.txt`

Earlier verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "ga4_measurement_decision_titles_include_reporting_context" --maxfail=1`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "ga4 route renders workflow-specific brief focus"`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/ga4/diagnostics` returns `evidence_summary_label`,
  `action_summary_label`, `operator_summary.action_summary_label` and
  decision `action_summary_label`.
- Browser proof: `.local-lab/proof/ga4-summary-labels-clean.txt`

Earlier verified local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "operator_label_fallbacks_do_not_expose_raw_connector_ids or knowledge_operating_map_binds_sources_to_decisions" --maxfail=2`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/KnowledgePanels.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Live API proof: `/api/knowledge/operating-map` returns
  `blocked_claim_summary_label` for knowledge bindings.
- Browser proof:
  `.local-lab/proof/knowledge-blocked-claim-summary-labels-clean.txt`

Earlier local slice:

- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "content route renders condensed selected decision with expandable detail"`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Source scan: no visible fallback patterns from Treści decision/Ahrefs enum
  fields remain in `ContentDiagnosticSurface.tsx`.
- Browser proof: `.local-lab/proof/content-enum-labels-clean.txt`

Earlier local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "ads_entity_display_labels_do_not_expose_raw_ids or ads_label_fallbacks_do_not_expose_raw_vendor_values or ads_helper_label_fallbacks_do_not_expose_raw_vendor_values" --maxfail=3`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "ads doctor route renders live metric-backed diagnostics"`
- `rtk uv run python scripts/marketer_language_guard.py`
- Live API proof: `/api/ads/diagnostics?view=summary` returns `campaign_label`
  and `ad_group_label` for checked search-term, safety, keyword-context and
  negative-keyword rows.
- Browser proof: `.local-lab/proof/ads-display-labels-clean.txt`

Earlier local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "knowledge_operating_map_binds_sources_to_decisions or operator_label_fallbacks_do_not_expose_raw_connector_ids" --maxfail=3`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/KnowledgePanels.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Browser proof: `.local-lab/proof/knowledge-summary-labels-clean.txt`

Earlier local slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "opportunities_are_derived_from_evidence_and_rule_mappings or operator_label_fallbacks_do_not_expose_raw_connector_ids" --maxfail=3`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/RegistryPanels.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Browser proof: `.local-lab/proof/opportunity-summary-labels-clean.txt`

Most recent committed slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "workflows_are_decision_backed_operator_contracts or workflow_label_fallbacks_do_not_expose_raw_values or workflow_run_persists_to_local_state_with_redaction" --maxfail=3`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/WorkflowPanels.test.tsx src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "workflow"`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Browser proof: `.local-lab/proof/workflow-labels-clean.txt`

Recent broad guardrails that remain relevant:

- `rtk uv run python scripts/skill_hygiene_check.py`
- `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q`
- Focused API/dashboard tests named in recent commits.

Do not paste long historical proof lists here. Use git history and
`.local-lab/proof/` when older evidence is needed.
