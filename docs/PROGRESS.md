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
- GA4 diagnostics now attach API-owned `metric_label`, `dimension_labels` and
  `dimension_value_labels` to GA4 metric facts. The GA4 route no longer owns a
  local metric-label dictionary for proof metric tiles.
- GA4 tracking-quality action previews now carry API-owned
  `operation_type_label` and `tracking_dimension_gap_labels`. The GA4 route no
  longer owns local translators for GA4 preview operation or missing-dimension
  labels.
- Merchant action preview payloads now carry API-owned `preview_contract_label`.
  The Merchant route no longer owns a local preview-contract label dictionary.
- Merchant issue clusters and decisions now render API-owned
  `reporting_context_label` values. The Merchant route no longer owns a local
  reporting-context fallback, including grouped multi-context decisions.
- Command Center daily decisions now render API-owned `freshness_label` values
  for source freshness. The route no longer falls back to raw freshness enum
  states.
- Google Ads recommendation action details now receive API-owned preview cards.
  The marketer-facing card shows Polish recommendation type and neutral
  campaign/budget labels instead of raw recommendation enums or Google Ads IDs.
- Google Ads campaign budget action details now receive API-owned preview
  cards. The marketer-facing card shows campaign/budget names and budget values
  instead of raw `CampaignBudgetOperation` or Google Ads IDs.
- Google Ads negative-keyword action details now receive API-owned preview
  cards. The marketer-facing card shows Polish match/level labels and campaign
  names instead of raw `EXACT`, `ad_group` or Google Ads IDs.
- Google Ads custom-segment action details now receive API-owned preview cards.
  The marketer-facing card shows Polish audience/source/safety rows instead of
  raw `KEYWORD`, the old English internal segment name or Google Ads IDs.
- Demand Gen action details now receive API-owned preview cards. The
  marketer-facing card shows labelled channel counts instead of raw Google Ads
  channel enum keys such as `PERFORMANCE_MAX` or `UNKNOWN`.
- Keyword Planner access blocker action details now receive API-owned preview
  cards. The marketer-facing card shows a clean access reason and next step
  instead of raw Google Ads API error strings.
- Social draft action details now receive API-owned preview cards. The
  marketer-facing cards show clean source and metric labels instead of raw
  connector IDs or metric keys, and the old `source_inputs` payload fallback
  was removed from Action Detail.
- WordPress draft handoff action details now receive API-owned preview cards.
  The marketer-facing cards show URL/checklist rows instead of raw candidate
  IDs, preview-contract names or operation names.
- Content refresh action details now receive API-owned preview cards for
  content brief review and WordPress draft payload review. The marketer-facing
  cards show public/final URL rows and safe writing blockers instead of raw
  content payload contracts, `target_site`, `target_url` or mapping-review
  wording.
- Google Ads search-term n-gram action details now receive API-owned preview
  cards. The marketer-facing cards show topic, examples, cost and blockers
  without raw `SearchTermNgramReview`, preview-contract names or
  n-gram-to-negative-keyword contract keys. The live route passed browser proof
  but remains slow enough to keep as a performance risk.
- Ads Doctor no longer carries unused route-local decision status/risk
  translators or the unused connector label import; tests guard against
  reintroducing those route-local helpers.
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
- Merchant reporting-context label cleanup:
  `TMPDIR=$PWD/.local-lab/tmp rtk uv run pytest tests/test_api_contracts.py -q -k "merchant_diagnostics" --maxfail=1`
  `TMPDIR=$PWD/.local-lab/tmp rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "merchant route renders dedicated feed diagnostics" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  Live proof: `/api/merchant/diagnostics` returned 14 issue clusters and 5
  issue decisions with zero missing `reporting_context_label` values.
- Command Center freshness label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "command_center" --maxfail=1`
  `TMPDIR=$PWD/.local-lab/tmp rtk pnpm --dir apps/dashboard exec vitest run src/routes/CommandCenterRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  Live proof after `rtk scripts/local_stack.sh restart`: `/api/dashboard/command-center`
  returned 4 daily decisions and zero missing `freshness_label` values.
- Google Ads recommendation action preview card cleanup:
  `TMPDIR=$PWD/.local-lab/tmp rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics_exposes_live_campaign_metric_facts" --maxfail=1`
  `TMPDIR=$PWD/.local-lab/tmp rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  Live proof after `rtk scripts/local_stack.sh restart`:
  `/api/actions/act_prepare_google_ads_recommendation_review_queue` returned 4
  `google_ads_recommendation_review` preview cards with no raw recommendation
  enum or raw campaign/budget IDs in card text.
- Google Ads budget action preview card cleanup:
  `TMPDIR=$PWD/.local-lab/tmp rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics_exposes_live_campaign_metric_facts" --maxfail=1`
  `TMPDIR=$PWD/.local-lab/tmp rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  Live proof after `rtk scripts/local_stack.sh restart`:
  `/api/actions/act_prepare_ads_campaign_review_queue` returned 4
  `google_ads_budget_review` preview cards with no raw operation name or raw
  campaign/budget IDs in card text.
- Google Ads negative-keyword action preview card cleanup:
  `TMPDIR=$PWD/.local-lab/tmp rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics_exposes_live_campaign_metric_facts" --maxfail=1`
  `TMPDIR=$PWD/.local-lab/tmp rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk git diff --check`
  Live proof after `rtk scripts/local_stack.sh restart`:
  `/api/actions/act_prepare_negative_keyword_review_queue` returned 4
  `google_ads_negative_keyword_review` preview cards with no raw match type,
  level enum or campaign/ad-group IDs in card text.
- Google Ads custom-segment action preview card cleanup:
  `TMPDIR=$PWD/.local-lab/tmp rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics_exposes_live_campaign_metric_facts" --maxfail=1`
  `TMPDIR=$PWD/.local-lab/tmp rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk git diff --check`
  Live proof after `rtk scripts/local_stack.sh restart`:
  `/api/actions/act_prepare_custom_segments_from_search_terms` returned 1
  `google_ads_custom_segment_review` preview card with no raw member type, old
  English internal segment name or campaign IDs in card text.
- Demand Gen action preview card cleanup:
  `TMPDIR=$PWD/.local-lab/tmp rtk uv run pytest tests/test_api_contracts.py -q -k "demand_gen_review_action_is_validate_only_and_scoped" --maxfail=1`
  `TMPDIR=$PWD/.local-lab/tmp rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk git diff --check`
  Live proof after `rtk scripts/local_stack.sh restart`:
  `/api/actions/act_review_demand_gen_readiness` returned 1
  `google_ads_demand_gen_readiness_review` preview card with labelled channel
  counts and no raw `PERFORMANCE_MAX` or `UNKNOWN` channel keys in card text.
- Keyword Planner access blocker preview card cleanup:
  `TMPDIR=$PWD/.local-lab/tmp rtk uv run pytest tests/test_api_contracts.py -q -k "google_ads_keyword_planner_access_blocker_action_is_review_only" --maxfail=1`
  `TMPDIR=$PWD/.local-lab/tmp rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk git diff --check`
  Live proof after `rtk scripts/local_stack.sh restart`:
  `/api/actions/act_configure_google_ads_keyword_planner_access` returned 1
  `google_ads_keyword_planner_access_review` preview card with no raw
  `api_code=403`, `DEVELOPER_TOKEN_NOT_APPROVED`, `PERMISSION_DENIED`,
  `Basic Access`, `API Center` or `WILQ CLI` in card text.
- Social draft preview card cleanup:
  `TMPDIR=$PWD/.local-lab/tmp rtk uv run pytest tests/test_api_contracts.py -q -k "metric_backed_prepare_actions_are_evidence_grounded" --maxfail=1`
  `TMPDIR=$PWD/.local-lab/tmp rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --pool=threads --poolOptions.threads.singleThread=true`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk git diff --check`
  Live proof after `rtk scripts/local_stack.sh restart`:
  `/api/actions/act_prepare_linkedin_social_drafts` returned 4
  `social_draft_input_review` preview cards with no raw
  `google_search_console`, `google_merchant_center`, `clicks` or
  `issue_product_count` in card text.
- WordPress draft handoff preview card cleanup:
  `TMPDIR=$PWD/.local-lab/tmp rtk uv run pytest tests/test_api_contracts.py -q -k "metric_backed_prepare_actions_are_evidence_grounded" --maxfail=1`
  `TMPDIR=$PWD/.local-lab/tmp rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --pool=threads --poolOptions.threads.singleThread=true`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk git diff --check`
  Live proof after `rtk scripts/local_stack.sh restart` through `/api/actions`:
  `act_prepare_wordpress_draft_handoff` returned 4
  `wordpress_draft_handoff_review` preview cards with no raw `candidate_id`,
  `content_brief_`, `wordpress_draft_handoff_preview_v1` or
  `wordpress_draft_handoff_review` in card text.
- GA4 metric label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "ga4_diagnostics" --maxfail=1`
  `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "ga4 route renders workflow-specific brief focus" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk git diff --check`
  Live proof after `rtk scripts/local_stack.sh restart`: `/api/ga4/diagnostics`
  returned 25 GA4 metric facts with no missing `metric_label`, Polish
  dimension labels and no raw `(not set)` in `dimension_value_labels`.
  Browser proof is blocked in this session by local browser tooling:
  `agent-browser` returns CDP `Connection refused`, and Playwright cannot launch
  the available Chrome (`SIGTRAP`) or its own browser is not installed.
- GA4 tracking preview label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "ga4_diagnostics" --maxfail=1`
  `TMPDIR=$PWD/.local-lab/tmp rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "ga4 route renders workflow-specific brief focus" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk git diff --check`
  Live proof after `rtk scripts/local_stack.sh restart`:
  `/api/actions/act_review_ga4_tracking_quality` returned
  `operation_type_label="ocena jakości pomiaru"` and matching
  `tracking_dimension_gap_labels`.
- Merchant preview-contract label cleanup:
  `rtk uv run pytest tests/test_api_contracts.py -q -k "merchant_diagnostics" --maxfail=1`
  `TMPDIR=$PWD/.local-lab/tmp rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "merchant route renders dedicated feed diagnostics" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  `rtk pnpm --dir apps/dashboard typecheck`
  `rtk uv run python scripts/marketer_language_guard.py`
  `rtk git diff --check`
  Live proof after `rtk scripts/local_stack.sh restart`:
  `/api/actions/act_review_merchant_feed_issues` returned 8 preview rows with
  no missing `preview_contract_label`; first label was
  `sprawdzenie problemów feedu`.
- Earlier GA4 browser proof:
  `.local-lab/proof/20260627-ga4-measurement-copy-cleanup/`

## Active Gaps

Next cleanup queue:

1. Action detail previews:
   - Merchant feed issue previews have typed API cards.
   - Google Ads budget, recommendation, negative-keyword and custom-segment
     previews have typed API cards.
   - Demand Gen readiness previews have typed API cards.
   - Keyword Planner access blocker previews have typed API cards.
   - Social draft source-input previews have typed API cards.
   - WordPress draft handoff previews have typed API cards.
   - migrate remaining action kinds one by one from `DetailPanels.tsx`
     payload-shape inference to typed API preview cards; keep raw payload only
     in collapsed technical detail.
2. Primary route raw fallbacks:
   - clean remaining Merchant, Demand Gen, registry/workflow and knowledge
     route fallbacks that still return raw enum keys or technical values when
     API labels are missing.
3. Metric labels:
   - metric names in `MetricFactChips` now come from `metric_label`.
   - metric dimensions in `MetricFactChips` now come from `dimension_labels`
     and `dimension_value_labels`.
   - Merchant diagnostic metric tiles now use API-owned metric labels.
   - GA4 diagnostic proof metric tiles now use API-owned metric labels.
   - Merchant preview-contract labels now come from API-owned payload labels.
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
