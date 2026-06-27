# WILQ Progress Ledger

This is the short recovery ledger. It is not a changelog and must not become an
archive of old broken wording.

Full execution plan: `PLAN.md`
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
- Do not preserve outdated fields, old wording or route-local cleanup helpers
  as a compatibility strategy. Migrate touched active consumers directly.

## Canonical Documents

- `PLAN.md` is the current canonical execution plan for cleanup and product
  semantics.
- `docs/goals/001-goal.md` is the active execution goal.
- `PLANS.md` is the longer product roadmap after the cleanup state is accepted.
- Proof artifacts live under `.local-lab/proof/**`; keep detailed scan terms and
  historical transcripts there, not in this ledger.

## Latest Important Facts

- The core marketer path remains:
  `/command-center -> /merchant -> /content-planner -> /ads-doctor -> /ga4`.
- Active content semantics have been corrected toward public/final URL language.
  Removed old review packet script/test artifacts are still visible in git
  status as deletions.
- Command Center, Localo, dashboard fallback labels, context-pack condensation,
  action review-gate condensation, Ads context condensation, secondary route
  condensation, Knowledge, Workflows and Settings have runtime or browser proof
  from the current cleanup goal.
- Current session live proof confirms the local WILQ API and dashboard are
  reachable after a managed stack restart. API health returns `ok`, and focused
  Ads, GA4 and Merchant skill smokes pass against the live local API.
- The current cleanup slice focuses on marketer-facing language, action safety
  wording, stale dev-preview strategy removal and full condensation of active
  operator surfaces.
- Daily/skill context-pack cleanup now avoids stale-field exception lists in the
  API. Audit events in compact operator context expose event type and a plain
  detail pointer; full notes and technical details stay in action detail.
- First-class `ContentPreflight` contract is now started as a typed API layer
  derived from current content diagnostics. It answers preserve/refresh/merge/
  create/block before any future sales brief or draft work; draft and WordPress
  draft remain blocked in this slice.
- Ads/GA4/Demand Gen action and route copy now removes active marketer-facing
  Polglish such as `landing page`, `source/medium`, `message match`, `impact
  metrics`, `Target ROAS/CPA`, `developer token` and `target verdict`. The guard
  now blocks those phrases in active source and skill/eval contracts.
- Ads Doctor primary summary and evidence proof panels now render
  `missing_read_contract_labels` and `blocked_claim_labels` from WILQ API
  instead of mapping raw Ads contract keys in the route. Browser proof for
  `/ads-doctor` shows Polish labels for missing inputs and blocked promises
  without raw `target_roas_or_cpa`, `profit_margin` or `human_strategy_review`.
- Ads Doctor optimizer-readiness labels now also come from WILQ API/shared
  schema: mode, status, risk, item labels, missing-data labels and blocked
  promises. The route-local optimizer readiness dictionaries were removed, and
  expanded browser proof shows Polish labels such as `kampanie do oceny`,
  `historia zmian` and `ocena bez zapisu` without raw optimizer contract keys.
- Ads Doctor business-target interpretation and strategy-readiness labels now
  also come from WILQ API/shared schema. The dashboard no longer renders raw
  `ads_business_target_interpretation_v1`, `preliminary`,
  `target_roas_or_cpa`, `human_strategy_review` or business-use enum values in
  the expanded Ads review panel. Browser proof:
  `.local-lab/proof/20260627-ads-business-context-api-labels/browser/ads-doctor-expanded.txt`.
- Ads Doctor campaign-triage rows now use API-owned campaign channel/status,
  missing-data and blocked-promise labels. Budget safety reviews also expose
  API-owned status and validation labels, including budget operation and
  mutation-audit checks. Browser proof:
  `.local-lab/proof/20260627-ads-triage-api-labels/browser/ads-doctor-expanded.txt`.
- Ads Doctor derived-KPI, budget-pacing and campaign queue copy now uses
  API-owned labels/reasons for blocked promises, campaign channel/status,
  budget period/status and budget operation type. The dashboard no longer
  renders raw `CampaignBudgetOperation`, `SEARCH`, `ENABLED`, `DAILY`, `typ=`,
  `wskaźniki=` or `udział_w_wyświetleniach` in the expanded Ads proof.
  Browser proof:
  `.local-lab/proof/20260627-ads-kpi-budget-api-labels/browser/ads-doctor-expanded.txt`.
- Ads Doctor recommendation and impression-share rows now use API-owned labels
  for recommendation type, operation type, missing impact metrics, campaign
  status, channel and blocked promises. Live Ads proof after managed stack
  restart confirmed real `DISPLAY_EXPANSION_OPT_IN` and
  `recommendation_impact` values are not exposed in recommendation copy; the
  expanded browser proof has no raw recommendation/impression-share terms from
  this slice. Browser proof:
  `.local-lab/proof/20260627-ads-recommendations-api-labels/browser/ads-doctor-expanded.txt`.
- Ads Doctor change-history and change-impact panels now use API-owned labels
  for status, metrics, missing data, changed fields, client type and blocked
  promises. Live Ads proof after managed stack restart and expanded browser
  proof found no raw `change_event`, `GOOGLE_ADS_WEB_CLIENT`,
  `resource_change_operation`, `changed_fields`, `readiness` or `change rows`
  text in this slice. Browser proof:
  `.local-lab/proof/20260627-ads-change-history-api-labels/browser/ads-doctor-expanded.txt`.
- Ads Doctor budget and impression-share empty states now come from WILQ API
  contracts, not hardcoded React blocker copy. Budget and lost-impression copy
  no longer exposes raw `campaign_budget.amount_micros`,
  `budget_amount_micros`, `recommended budget`, `impression share`,
  `budget-lost`, `rank-lost` or `impression share facts` in the checked live
  API output. Proof:
  `.local-lab/proof/20260627-ads-budget-impression-empty-state-api-labels/ads-budget-impression.json`.
- Ads Doctor negative-keyword review now uses API-owned labels for safety
  status, validation status, required checks, match type, exclusion level,
  keyword context and blocked promises. The expanded browser proof shows Polish
  labels such as `dopasowanie ścisłe`, `grupa reklam` and `90-dniowy odczyt
  gotowy` without raw `EXACT`, `BROAD`, `ad_group`, `pending_validation` or
  `read_ready_needs_human_review` in this slice. Proof:
  `.local-lab/proof/20260627-ads-negative-keyword-api-labels/`.
- Custom Segments now render missing-contract, safety, validation, confidence
  and blocked-promise labels from WILQ API/shared schema. The dedicated
  `/ads-doctor/custom-segments` route no longer imports route-local Ads label
  translators and the browser proof hides raw connector, evidence and action IDs
  from the marketer surface while keeping them in API contracts.
- Merchant product/performance and price-readiness blocked claims now use
  Polish source values from API/action/knowledge contracts. Dashboard fixtures
  and route labels no longer depend on Merchant legacy claim translators such
  as old feed/write and approval-recovery values.
- Social publisher context-pack and draft actions now use Polish blocked-claim
  source values for publishing and social-performance promises. The language
  guard now blocks the previous English social-publishing phrases in active
  skill/eval contracts.
- Content and Ahrefs blocked-claim contracts now use Polish source values for
  ranking, lead, revenue, traffic, authority, duplicate and WordPress-publish
  promises. Obsolete dashboard/backend label-map entries for those old values
  were removed instead of kept as compatibility aliases.
- Content action detail now gets content mode labels and audit-review wording
  from the WILQ API/domain layer. The route-local content mode translator was
  removed, WordPress draft-preview selection no longer depends on parsing raw
  `candidate:` text from summaries, and old content review audit summaries are
  condensed before reaching the dashboard.
- Demand Gen readiness blocked-claim contracts now use Polish source values for
  launch, transition, creative quality, asset effectiveness and effectiveness
  promises. Obsolete route/backend label-map entries for old Demand Gen values
  were removed instead of kept as compatibility aliases. The language guard now
  blocks the old Demand Gen phrases.
- Action review-gate labels now come from the WILQ API and shared schema, not
  from route-local cleanup logic. The dashboard review panel renders API-owned
  Polish labels for checklist and write blockers; raw blocker keys remain only
  as internal traceability fields. Proof:
  `.local-lab/proof/20260627-action-review-gate-api-labels/browser/content-action-review-gate-body.txt`.
- Action preview validation and missing-data labels now also come from the WILQ
  API. The action service hydrates labels for active preview rows, nested safety
  reviews and action review gates; `DetailPanels` prefers API labels instead of
  translating raw keys. A focused API guard fails on generic `warunek techniczny
  do sprawdzenia` labels. Browser proof:
  `.local-lab/proof/20260627-action-preview-api-labels/browser/demand-gen-action-detail-body.txt`.
- Action preview, confirmation and impact-check result blockers now expose
  `blocker_labels` from the WILQ API/shared schema. `ActionObjectPanels` renders
  those API-owned Polish labels instead of mapping raw blocker keys in React.
  Live proof after managed stack restart: `POST /api/actions/act_review_demand_gen_readiness/impact-check`
  returned `blocker_labels=["wymagane potwierdzenie podglądu zmian"]`.
- Action Detail source-label hardening removed the remaining route-local
  generic fallbacks for missing-data, validation and after-confirmation rows.
  Unknown technical keys are no longer converted into fake marketer labels;
  active API/action sources must provide explicit Polish label arrays. Live
  proof for `act_confirm_ads_target_guardrails` shows Polish labels for missing
  target, validation and after-confirmation uses with no generic fallback hits.
- Action status, risk, mode, validation, review-gate, result and audit-event
  labels now come from the WILQ API/shared schema, not route-local React
  dictionaries. Action audit summaries are hydrated by the API into plain
  operator language, so the action history no longer exposes `status=...`, raw
  audit IDs or raw connector IDs on the marketer surface. Live proof:
  `/api/actions/act_review_merchant_feed_issues`,
  `scripts/live_contract_smoke.py`, and browser route
  `/actions/act_review_merchant_feed_issues`.
- Action Detail now receives `evidence_summary_label` from the WILQ API and no
  longer renders raw evidence IDs on the first screen. Merchant action diagnosis
  now uses Polish metric labels such as `zgłoszenia problemów` instead of raw
  metric keys like `issue_product_count`. Browser proof:
  `.local-lab/proof/20260627-action-evidence-condensation/browser/action-detail-body-final.txt`.
- Merchant action preview labels now come from the shared Merchant domain label
  module and WILQ API payload. Action Detail renders issue, attribute, context,
  severity, resolution and metric labels from API fields; route-local generic
  fallbacks no longer invent marketer copy. Live API/browser proof:
  `.local-lab/proof/20260627-merchant-action-preview-labels/browser/action-detail-body-final.txt`.
- Budget and Custom Segment action preview safety labels now come from domain/API
  payloads. `DetailPanels` no longer translates custom segment member type or
  safety status with route-local dictionaries; it renders `member_type_label`
  and nested `status_label` from WILQ API. Browser proof:
  `.local-lab/proof/20260627-action-preview-source-labels/browser/`.
- Localo action, skill eval and knowledge sources now use Polish source values
  for blocked local claims: ukończone zadanie lokalne, zapis zmian w profilu
  firmy and poprawa widoczności lokalnej. Old active values such as
  `GBP performance`, `competitor visibility`, `GBP write`, `write path` and
  `local visibility uplift` are guarded by `scripts/marketer_language_guard.py`.
  Live API proof for `act_review_localo_visibility_facts` confirms no old
  Localo claim strings in the action payload.
- Custom segments and Keyword Planner blocked-claim contracts now use Polish
  source values for rozmiar odbiorców, prognozę, wzrost konwersji, zapis
  kierowania reklam, skuteczność kampanii i zwrot z reklam. Obsolete
  backend/dashboard label aliases for old values were removed instead of kept
  as compatibility aliases. Ads target status defaults now use `brak celu`.
- Demand Gen readiness now sources campaign-channel labels, missing-data
  labels, review-gate labels, blocked promises and route metrics from the WILQ
  API/domain contract. The dashboard no longer renders raw Demand Gen action
  IDs, raw read-contract keys, `DG rows`, `asset`, `payload`, `ActionObject` or
  local React label dictionaries on the `/ads-doctor/demand-gen` marketer
  surface. Browser proof:
  `.local-lab/proof/20260627-demand-gen-api-labels/browser/demand-gen-body.txt`.
- Ahrefs readiness/status labels now come from the WILQ API and shared schema:
  connector status, live-data status, latest-refresh status, decision status,
  priority, gap-contract status and section status. `/ahrefs` no longer has
  Ahrefs route-local label helpers and no longer renders raw metric-fact values
  such as `subdomains`, `completed`, `domain_rating=` or `content_gap` on the
  marketer surface. Proof:
  `.local-lab/proof/20260627-ahrefs-api-status-labels/`.
- Ads Doctor primary connector, refresh, live-data, decision, priority, risk,
  missing-input and blocked-promise labels now come from the WILQ API/shared
  schema. The route no longer owns helper copy for primary Ads decision titles,
  summaries, rationale, next step or top status labels. Ads diagnostics source
  summaries now avoid visible `koszt_micros=`, `wartość_konwersji=`,
  `search-term rows` and `wiersze_bez_konwersji` wording. Proof:
  `.local-lab/proof/20260627-ads-api-decision-labels/`.
- GA4 primary connector, refresh, live-data, freshness, conversion-readiness,
  section, decision, risk, WordPress-match and blocked-claim labels now come
  from the WILQ API/shared schema. `/ga4` no longer owns route-local helpers
  for those marketer-facing meanings. Live browser proof shows Polish labels
  such as `dane do odświeżenia`, `problem pomiaru`, `niskie ryzyko` and
  `dopasowanie ścieżki` with no raw GA4 enum hits in the rendered surface.
  Proof: `.local-lab/proof/20260627-ga4-api-status-labels/`.
- Merchant primary connector, refresh, live-data, freshness, product-readiness,
  decision, section, risk and blocked-promise labels now come from the WILQ
  API/shared schema. `/merchant` no longer owns route-local helpers for those
  marketer-facing meanings, and the expanded browser scan found no
  old product-scaling shorthand, raw Merchant vendor enum, queue-key or
  debug/payload hits in rendered text. Proof:
  `.local-lab/proof/20260627-merchant-api-status-labels/`.
- Action panels no longer carry the unused route-local action gate label
  dictionary. Existing action detail panels rely on API-owned label arrays
  such as blocker, checklist, missing-data and validation labels instead of
  translating raw gate keys in React. The stale dashboard test expectation for
  raw Merchant vendor text (`availability_updated / n:availability`) was
  inverted so the test now protects the marketer surface from that raw string.
  Browser proof:
  `.local-lab/proof/20260627-remove-action-gate-ui-map/`.
- Merchant skill context-pack is now actually skill-scoped for both `skill` and
  `skill_id` request bodies. The default Merchant context no longer falls back
  to the full 6.8 MB cross-system pack and no longer includes raw Merchant
  vendor enums such as `landing_page_error`, `SHOPPING_ADS` or
  `MERCHANT_ACTION`; the full endpoint remains available explicitly. Live proof:
  `.local-lab/proof/20260627-merchant-context-pack-condensation/`.
- Social Publisher action/context contracts now use `source_inputs` and
  `missing_publish_access` instead of stale `candidate_inputs` and publish
  permissions wording. The social context-pack no longer includes raw Merchant
  dimensions such as `availability_updated`, `FREE_LISTINGS`, `MERCHANT_ACTION`
  or `n:availability`; source inputs carry short `context_summary` strings.
  Merchant issue labels were moved to a shared domain label module so tactical
  queue and Merchant diagnostics use the same Polish labels. Browser/API proof:
  `.local-lab/proof/20260627-social-source-inputs/`.
- GA4 readiness now sources missing-data labels from the WILQ API/domain
  contract, and GA4 route cards render condensed API metric tiles instead of
  raw metric facts. Browser proof for `/ga4` found no hits for `landing page`,
  `Landing:`, `message match`, `key events`, `ecommerce_purchases`,
  `engagement`, raw action IDs, `payload` or `ActionObject`:
  `.local-lab/proof/20260627-ga4-api-labels/ga4.txt`.
- GA4 expanded action preview now also sources metric snapshot labels from the
  action payload/API. The marketer-facing expanded panel shows Polish labels
  such as `aktywni użytkownicy`, `zakupy e-commerce`, `zaangażowanie` and
  `zdarzenia kluczowe` instead of raw metric names such as `active_users` or
  `ecommerce_purchases`. Proof:
  `.local-lab/proof/20260627-ga4-preview-snapshot-labels/`.
- Merchant decision, issue-cluster and product-row surfaces now source Polish
  issue/context/status labels from the WILQ API/domain contract. The `/merchant`
  browser proof after expanding the full review found no active hits for raw
  Merchant vendor terms such as `landing_page_error`, `n:link`, `SHOPPING_ADS`,
  `MERCHANT_ACTION`, `decision_queue`, `issue_clusters` or
  `reported_issue_occurrences`. Proof:
  `.local-lab/proof/20260627-merchant-expanded-audit/merchant-expanded-final.txt`.
- Content Planner and content skill context now use `plan treści` for active
  marketer-facing copy instead of visible `brief` wording. The backend/action
  source strings, dashboard route copy and tests were updated at the source;
  internal schema/type names such as `content_brief_preview` remain internal
  contract names only. Live proof after managed stack restart: API health and
  live contract smoke pass, content skill smoke has no old visible brief terms,
  and `/content-planner` browser scan has no `Brief`, `Przygotuj brief`,
  `Podgląd briefów`, `Pokaż briefy` or `Zapisz sprawdzenie briefu` hits.
  Proof:
  `.local-lab/proof/20260627-content-plan-language/content-planner-final.txt`.
- Action Detail content preview now also uses `Plan treści do sprawdzenia` and
  `Cel planu treści` instead of the old visible `brief` headings. The generic
  content operating surface and tactical queue test fixtures were cleaned in
  the same slice, and `scripts/marketer_language_guard.py` now blocks those old
  headings in active source. Browser proof:
  `.local-lab/proof/20260627-action-detail-content-plan-language/action-detail-content.txt`.
- Generic operating route config no longer exposes `/api/marketing/brief`,
  `MarketingBrief`, `spend` or `inventory` as marketer-facing fallback copy.
  The fallback surface now says `w WILQ`, `wydatki`, `dane z ...` and
  `spis treści` language, while endpoint/type names remain internal code only.
  Browser proof for `/social-publisher`:
  `.local-lab/proof/20260627-brief-workflow-copy/social-publisher.txt`.
- GA4 and Merchant active copy no longer expose `mapowanie` as marketer-facing
  wording for conversion, landing-page or product-state checks. Source labels
  now use `powiązanie konwersji`, `sprawdź stronę wejścia` and `powiązane
  produkty`; `scripts/marketer_language_guard.py` blocks the old phrases.
  Live API and browser proof:
  `.local-lab/proof/20260627-mapping-language-cleanup/`.
- Action and opportunity detail views now keep raw JSON/source identifiers out
  of the default marketer surface. Action payload data, evidence source IDs and
  metric fact JSON render only after opening a technical panel; opportunity
  detail uses API `metric_tiles` for the visible metric summary. The language
  guard now blocks visible `debugowaniu` wording. Browser proof:
  `.local-lab/proof/20260627-technical-details-hidden/`.
- Ads diagnostics no longer expose the mixed-language title `Akcje do
  sprawdzenia negative keywords`; the API source now says `Akcje do
  sprawdzenia wykluczeń`. Obsolete `search terms` blocked-claim aliases were
  removed instead of kept as compatibility labels. Live API and browser proof:
  `.local-lab/proof/20260627-ads-negative-keyword-language/`.
- The Actions route no longer exposes old `podgląd briefu` wording for the
  content action. The action source now says `Traktuj plan treści jako materiał
  do sprawdzenia`, active eval fixtures expect `podgląd planu treści`, and the
  language guard blocks the old phrases. Browser proof:
  `.local-lab/proof/20260627-actions-content-plan-language/actions.txt`.
- Legacy content-review audit events are now normalized when actions are loaded,
  so `/api/actions` no longer leaks old dev-preview review terms from local
  state. Live API proof found zero hits for `target_site`, `mapping_review`,
  `mapping_outcome`, `selected_target_url`, `staging handoff` and
  `ekologus.dev.proudsite.pl`; `/actions` browser proof also found zero hits
  for those terms plus `payload` and `ActionObject`. Proof:
  `.local-lab/proof/20260627-legacy-content-audit-cleanup/actions.txt`.
- Ahrefs decision, gap-contract, metric-fact and gap-record labels now come
  from the WILQ API/domain contract. The `/ahrefs` route no longer maps Ahrefs
  enum names in React and the browser proof found no visible hits for
  `domain_rating=`, `ahrefs_rank=`, `status=completed`, `rows=`,
  `mode=subdomains`, `content_gap`, `organic_keyword_gap`, `top_page_gap`,
  `backlink_gap`, `competitor_page`, `Ahrefs Rank` or `DR`. Proof:
  `.local-lab/proof/20260627-ahrefs-api-labels/ahrefs-rendered-final.txt`.
- Localo status, access, decision-type, priority, allowed-evidence,
  missing-data, contract-status and blocked-claim labels now come from the WILQ
  API/shared schema. `/localo` no longer carries route-local Localo enum
  translators. Live API proof and browser screenshot:
  `.local-lab/proof/20260627-localo-api-labels/`.
- Marketing brief blocker logic now treats successful vendor reads as evidence,
  not blockers. `/api/marketing/brief` no longer puts completed
  GSC/GA4/Merchant reads or the non-marketing `openai_codex` adapter into
  `what_blocks_us`; live proof shows only real decision blockers for GA4
  claims and Ads business context:
  `.local-lab/proof/20260627-marketing-brief-blockers/`.
- Command Center daily-decision labels now come from WILQ API/shared schema,
  not from route-local React copy maps. The API exposes operator labels for
  decision state, route, CTA, priority, source connectors, evidence summary,
  action summary, skill label and blocked promises. `CommandCenterRoute` renders
  those API fields directly and no longer carries local helpers such as
  `decisionCopy`, `codexSkillLabel`, `marketerConnectorLabel`,
  `routeCtaLabel`, `marketerMetricLabel`, `marketerBlockedClaimLabels` or
  `priorityLabel`. Live API/browser proof:
  `.local-lab/proof/20260627-command-center-api-labels/`.
- Content Planner decision, preflight and Ahrefs-row labels now come from the
  WILQ API/domain contract. The route consumes API fields such as
  `decision_type_label`, gate labels, preflight labels and Ahrefs candidate
  labels instead of React helper maps for active content decisions. Browser/API
  proof:
  `.local-lab/proof/20260627-content-api-labels/`.
- Dashboard status chips now include text-reader separators, so compact header
  status rows no longer collapse into unreadable strings such as `brakuje
  dostępudane do odświeżenia`. Browser proof across Command Center, Merchant,
  Content Planner, Ads Doctor, GA4, Localo and Ahrefs:
  `.local-lab/proof/20260627-status-chip-separators/`.
- Ads, GA4 and Merchant blocked-claim contracts now also use Polish source
  values for budget-loss checks, query review, profitability boundaries, margin
  checks, campaign write paths, change assessment, GA4 write/fix states,
  attribution, funnel/conversion caveats and product/feed outcome promises. Connector
  success summaries now use Polish operator wording instead of `vendor read
  completed` status text. Remaining `profitability_verdict` hits are internal
  policy IDs, not marketer-facing labels.
- Command Center API and route copy now use Polish source wording for Ads
  metrics and status language: `wartość konwersji`, `wskaźniki do sprawdzenia`,
  `wiersze kosztu pozyskania celu`, `blokada` and `blokady`. The live
  `/api/dashboard/command-center` scan found no marketer-payload hits for the
  previous English/technical phrases after the managed stack restart; the
  browser read of `/command-center` matched the cleaned wording.
- Ads Doctor API/action sources and first-screen route copy now use Polish
  marketer wording for campaign review, budget review, search-term review,
  n-grams, negative keyword safety and OAuth handoff. The live
  `/api/ads/diagnostics` scan after managed stack restart found no active
  marketer-text hits for `KPI`, `CPA`, `werdykt`, `waste`, `search terms`,
  `blocker`, `campaign facts` or `evidence IDs`; browser read of
  `/ads-doctor` shows the condensed first-step Ads decision and Polish
  missing-data/measurement wording.
- Ads Doctor skill and active Codex eval prompts now use Polish operator
  wording for wyszukiwane hasła, wykluczające słowa kluczowe, koszt pozyskania
  celu, blokady and optional design preview. `tests/test_codex_skill_eval_cases.py`
  now prevents reintroducing the old Ads eval prompt phrases `search terms`,
  `negative keywords`, `CPA`, `optional preview`, `blocked claims`,
  `read-only rows`, `campaign review queue` and `spend` in active Ads eval/skill
  prose.
- Content Strategist skill and active Codex eval prompts now use Polish
  operator wording for brief preview, source facts, missing evidence and
  forbidden promises. The eval now expects a safe blocker for full drafting when
  fresh GSC/GA4 credentials are missing, while preserving actionable Content
  Planner recommendations from available API evidence.
- Content Planner no longer translates content action contract values in the
  route for brief blockers, draft gates, WordPress handoff and measurement
  summaries. `wilq/actions/content_refresh.py` now owns the Polish source
  labels/summaries for those payloads, including metric labels, draft block
  labels and review gate summaries. Browser proof on `/content-planner`
  expanded brief/draft panels found no active hits for the previous raw
  contract/version phrases, `inventory:`, `canonical:` or `human review
  outcome`.
- Action Detail content previews now consume API-sourced Polish labels for
  content brief options, publication blockers, draft gates, WordPress draft
  handoff and post-publication measurement. The context-pack compactor now
  preserves those condensed labels for `wilq-content-strategist`, and summary
  ordering keeps duplicate/canonical checks plus "no success verdict yet"
  visible before lower-priority measurement details.
- Custom Segments and Keyword Planner language now comes from API-owned labels
  and source summaries instead of route-local cleanup logic. The active
  `/ads-doctor/custom-segments` browser proof shows Polish segment names,
  Polish intent, `słowa kluczowe`, `sprawdzenie zapisu zmian w Google Ads` and a
  plain blocked Keyword Planner explanation; the scan found no hits for old
  `Search terms:`, raw intent/member type, raw API error details, `uplift`,
  `KP` shortcut or mutation-audit wording.

## Latest Proof Pointers

- WordPress draft handoff contract cleanup:
  `.local-lab/proof/20260626-wordpress-draft-handoff-contract-cleanup/summary.json`.
- Command Center blocked-claim cleanup:
  `.local-lab/proof/20260625-command-center-claim-cleanup/api-context/summary.json`.
- Localo marketer-language cleanup:
  `.local-lab/proof/20260625-localo-language-cleanup/api-context/summary.json`
  and `.local-lab/proof/20260625-localo-language-cleanup/browser/summary-after-wait.json`.
- Dashboard fallback cleanup:
  `.local-lab/proof/20260625-dashboard-fallback-cleanup/browser/fallback-scan-summary.json`.
- Status badge fallback cleanup:
  `.local-lab/proof/20260626-status-badge-fallback-cleanup/browser/summary.json`.
- Ads/Merchant action-language cleanup:
  `.local-lab/proof/20260626-contract-check-language-cleanup/api-context/ads-merchant-string-scan-summary.json`.
- Command Center freshness-language cleanup:
  `.local-lab/proof/20260626-command-center-freshness-language-cleanup/api-context/command-center-string-scan.json`
  and
  `.local-lab/proof/20260626-command-center-freshness-language-cleanup/browser/command-center-browser-scan.json`.
- Content strategist context-pack condensation:
  `.local-lab/proof/20260625-context-pack-condensation/api-context/content-context-pack-final.json`.
- Ads Doctor first-screen/API language cleanup: live API scan and browser read
  were run directly after `scripts/local_stack.sh restart` in the 2026-06-27
  cleanup slice; detailed proof was not persisted beyond command output.
- Ads Doctor skill/eval prompt cleanup:
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q --maxfail=1`
    passed: 6 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000`
    passed against the managed local API.
  - Focused scan across active Ads skill prose, active eval cases and static
    eval tests found no remaining active hits for the old Ads eval prompt
    phrases outside the new forbidden-list assertions.
- Content Strategist skill/eval prompt cleanup:
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q --maxfail=1`
    passed: 7 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk env CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-content-strategist --api-base http://127.0.0.1:8000`
    passed against the managed local API; result artifact:
    `.local-lab/evals/codex-skill/20260627T021047Z`.
  - `rtk uv run python .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000`
    passed and confirmed API health, content diagnostics and action validation;
    required GSC/GA4 connector freshness remains blocked by local credential
    parsing status, so full drafting stays safely blocked.
- Content Planner API-sourced label cleanup:
  - `rtk uv run python -m py_compile wilq/actions/content_refresh.py` passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "metric_backed_prepare_actions_are_evidence_grounded or content_brief_preview or content_public_url or codex_context_pack_scopes_content_strategist_payload" --maxfail=1`
    passed: 4 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
    passed: 5 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - Browser proof text:
    `.local-lab/proof/20260627-content-contract-source-labels/browser/content-planner-briefs-expanded-body-final-v3.txt`.
- Action Detail content API-label cleanup:
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "metric_backed_prepare_actions_are_evidence_grounded or content_strategist_context_pack_preserves_reviewed_draft_preview" --maxfail=1`
    passed: 2 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
    passed.
- Custom Segments API-label cleanup:
  - Browser proof:
    `.local-lab/proof/20260627-custom-segments-api-labels/browser/custom-segments-body.txt`.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "keyword_planner or custom_segments" --maxfail=1`
    passed: 2 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000 -t "custom segments route renders dedicated validation contract"`
    passed: 1 test.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000`
    passed against the managed local API.
  - `rtk uv run python .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000`
    passed against the managed local API.
  - `rtk uv run python scripts/live_contract_smoke.py --api-base http://127.0.0.1:8000`
    passed.
    passed: 14 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk git diff --check` passed.
  - Live API and browser proof text:
    `.local-lab/proof/20260627-action-detail-content-api-labels/browser/content-action-detail-body.txt`.
- Action Detail source-label hardening:
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "action_operator_labels_are_specific or metric_backed_prepare_actions_are_evidence_grounded" --maxfail=1`
    passed: 2 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
    passed: 14 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - Live API proof after managed stack restart confirmed Ads target guardrail
    labels for missing target, validation and after-confirmation uses without
    generic fallback labels.
  - Browser proof text:
    `.local-lab/proof/20260627-action-detail-source-label-hardening/browser/ads-target-guardrail-body.txt`.
- Localo source-claim cleanup:
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "localo_diagnostics" --maxfail=1`
    passed: 4 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
    passed: 14 tests.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py tests/test_localo_skill_smoke.py -q --maxfail=1`
    passed: 8 tests.
  - `rtk uv run python .agents/skills/wilq-localo-operator/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000`
    passed against the managed local API.
  - `rtk pnpm --dir apps/dashboard typecheck`, `rtk uv run python scripts/marketer_language_guard.py`
    and `rtk git diff --check` passed.
  - Browser proof text:
    `.local-lab/proof/20260627-localo-source-claim-cleanup/browser/localo-route-body.txt`
    and
    `.local-lab/proof/20260627-localo-source-claim-cleanup/browser/localo-action-detail-body.txt`.
- All-skill default context-pack clean scan:
  `.local-lab/proof/20260625-all-skill-context-clean-final-v2/api-context/summary.json`.
- Knowledge route condensation:
  `.local-lab/proof/20260625-knowledge-route-condensation/browser/`.
- Workflows condensation:
  `.local-lab/proof/20260625-workflows-condensation/`.
- Secondary route condensation:
  `.local-lab/proof/20260625-secondary-route-continuation/browser/`.
- Settings access condensation:
  `.local-lab/proof/20260625-route-audit-continuation/browser/settings-after-access-condensation.txt`.
- Action detail language cleanup:
  `.local-lab/proof/20260626-action-detail-language-cleanup/browser/content-action-detail-scan.json`.
- Actions route list cleanup:
  `.local-lab/proof/20260626-actions-route-list-cleanup/browser/actions-playwright-expanded.json`.
- Opportunities list cleanup:
  `.local-lab/proof/20260626-opportunities-list-cleanup/api-context/opportunities-live-summary.json`
  and
  `.local-lab/proof/20260626-opportunities-list-cleanup/browser/browser-proof-status.json`.
- Registry panels condensation:
  `.local-lab/proof/20260626-registry-panels-condensation/summary.json`.
- Knowledge panels language cleanup:
  `.local-lab/proof/20260626-knowledge-panels-language-cleanup/summary.json`.
- Connector access language cleanup:
  `.local-lab/proof/20260626-connector-access-language-cleanup/summary.json`.
- Domain status language cleanup:
  `.local-lab/proof/20260626-domain-status-language-cleanup/summary.json`.
- Command Center API/status language cleanup:
  `.local-lab/proof/20260627-command-center-api-language-cleanup/summary.json`.
- Action detail draft-label cleanup:
  `.local-lab/proof/20260626-action-detail-draft-label-cleanup/summary.json`.
- Tactical queue metric-language cleanup:
  `.local-lab/proof/20260626-tactical-queue-metric-language-cleanup/summary.json`.
- Knowledge source-type language cleanup:
  `.local-lab/proof/20260626-knowledge-source-type-language-cleanup/summary.json`.
- Content contract version-label cleanup:
  `.local-lab/proof/20260626-content-contract-version-label-cleanup/summary.json`.
- Keyword Planner blocked-access label cleanup:
  `.local-lab/proof/20260626-keyword-planner-blocked-access-label-cleanup/summary.json`.
- Action review-gate safety-language cleanup:
  `.local-lab/proof/20260626-action-review-gate-safety-language-cleanup/summary.json`.
- Content WordPress status language cleanup:
  `.local-lab/proof/20260626-content-wordpress-status-language-cleanup/summary.json`.
- Ads/GA4 marketer-language cleanup without live API/browser proof in current
  session:
  - `rtk uv run python scripts/marketer_language_guard.py`
  - `rtk uv run python -m py_compile wilq/briefing/ads_diagnostics.py wilq/briefing/ga4_diagnostics.py wilq/briefing/command_center.py wilq/briefing/tactical_queue.py wilq/briefing/content_diagnostics.py wilq/briefing/marketing_brief.py wilq/actions/service.py wilq/actions/google_ads/business_context.py wilq/actions/google_ads/campaign_triage.py wilq/actions/google_ads/demand_gen.py wilq/actions/google_ads/keyword_planner.py wilq/actions/ga4/tracking_quality.py scripts/marketer_language_guard.py`
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "ga4 or ads_business_context or keyword_match" --maxfail=1`
  - `rtk pnpm --dir apps/dashboard test src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 --testTimeout=20000`
  - `rtk pnpm --dir apps/dashboard typecheck`
- Merchant product/performance language cleanup without live API/browser proof
  in current session:
  - Focused stale-term scan for old Merchant feed/approval/product/price claim
    language across active API, dashboard, tests, evals and Merchant skill files
    found no active hits.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile wilq/briefing/merchant_diagnostics.py wilq/actions/service.py wilq/briefing/tactical_queue.py wilq/briefing/blocked_claim_labels.py scripts/marketer_language_guard.py .agents/skills/wilq-merchant-feed-operator/scripts/smoke_skill_contract.py` passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "merchant_diagnostics_exposes_feed_issue_queue or merchant_product_performance_readiness or merchant_diagnostics_promotes_ads_product_state_review_decision or merchant_price_impact_blocks_snapshot_history_without_price_change or codex_context_pack_scopes_merchant_payload_preview" --maxfail=1` passed: 7 tests.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py tests/test_marketer_uat_packet.py -q --maxfail=1` passed: 7 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx src/routes/CommandCenterRoute.test.tsx src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 -t "merchant route renders dedicated feed diagnostics|Command Center|action detail|Zakazane obietnice|connector status renders" --testTimeout=20000` passed: 3 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
- Social publisher blocked-claim language cleanup without live API/browser proof
  in current session:
  - Focused stale-term scan for the previous English publishing/outcome phrases
    across active API, dashboard, tests, evals and the social skill found no
    active hits outside the guard rule definitions.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile apps/api/wilq_api/main.py wilq/actions/service.py wilq/briefing/blocked_claim_labels.py scripts/marketer_language_guard.py .agents/skills/wilq-social-publisher/scripts/smoke_skill_contract.py` passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "social_context_pack or social_draft_actions" --maxfail=1` passed: 3 tests.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q --maxfail=1` passed: 5 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 -t "social route renders workflow-specific blockers" --testTimeout=20000` passed: 1 test.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
- Content/Ahrefs blocked-claim language cleanup without live API/browser proof
  in current session:
  - Focused stale-term scan for old content/Ahrefs blocked-claim terms across
    active WILQ sources, dashboard source, eval cases and content skill files
    found no active hits.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile wilq/actions/content_refresh.py wilq/actions/service.py wilq/briefing/content_diagnostics.py wilq/briefing/ahrefs_diagnostics.py wilq/briefing/blocked_claim_labels.py wilq/briefing/command_center.py wilq/briefing/tactical_queue.py scripts/marketer_language_guard.py .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py` passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "ahrefs or content_brief_preview or content_diagnostics or codex_context_pack_scopes_content_strategist_payload or content_public_url" --maxfail=1` passed: 16 tests.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q --maxfail=1` passed: 5 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx src/routes/ActionDetailRoute.test.tsx src/routes/CommandCenterRoute.test.tsx src/routes/TacticalQueuePanel.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 -t "content planner|ahrefs|Content|action detail|Command Center|compact decision groups" --testTimeout=20000` passed: 3 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
- Demand Gen blocked-claim language cleanup without live API/browser proof in
  current session:
  - Focused stale-term scan for old Demand Gen blocked-claim terms across
    active WILQ sources, dashboard source, eval cases and the Demand Gen skill
    found no active hits outside guard rule definitions.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile wilq/actions/google_ads/demand_gen.py wilq/briefing/blocked_claim_labels.py scripts/marketer_language_guard.py` passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "demand_gen" --maxfail=1` passed: 6 tests.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q --maxfail=1` passed: 5 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 -t "Demand Gen|demand gen|action detail" --testTimeout=20000` passed: 3 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
- Custom segments and Keyword Planner blocked-claim language cleanup with live
  local API proof in current session:
  - Focused stale-term scans for old Custom Segments/Keyword Planner phrases
    and stale Ads target wording across active WILQ sources, dashboard source,
    eval cases and skill contracts found no active hits except technical
    `WILQ_ADS_TARGET_ROAS` env names and guard definitions.
  - `rtk scripts/local_stack.sh restart` brought the local WILQ API and
    dashboard back to ready state.
  - `rtk scripts/local_stack.sh status` confirmed managed API and dashboard are
    ready.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile wilq/actions/google_ads/custom_segments.py wilq/actions/google_ads/keyword_planner.py wilq/actions/google_ads/negative_keywords.py wilq/actions/google_ads/search_term_ngrams.py wilq/actions/google_ads/campaign_review.py wilq/actions/ga4/tracking_quality.py wilq/actions/service.py wilq/briefing/ads_diagnostics.py wilq/briefing/ga4_diagnostics.py wilq/briefing/tactical_queue.py wilq/briefing/content_diagnostics.py wilq/briefing/command_center.py wilq/briefing/blocked_claim_labels.py wilq/schemas.py scripts/marketer_language_guard.py .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py` passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "custom_segment or keyword_planner or ads_diagnostics_exposes_live_campaign_metric_facts or command_center_ads_plan or ga4" --maxfail=1` passed: 17 tests.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py tests/test_marketer_uat_packet.py -q --maxfail=1` passed: 7 tests.
  - `rtk uv run python .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py` passed against live local API.
  - `rtk uv run python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py` passed against live local API.
  - `rtk uv run python .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py` passed against live local API.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 -t "custom segments|segmenty|Keyword Planner|action detail|Ads Doctor|GA4" --testTimeout=20000` passed: 4 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
- Brief workflow focus-language cleanup:
  `.local-lab/proof/20260626-brief-workflow-focus-language-cleanup/summary.json`.
- Generic surface registry fallback removal:
  `.local-lab/proof/20260626-generic-surface-registry-fallback-removal/summary.json`.
- Content Planner Polish language cleanup:
  `.local-lab/proof/20260626-content-planner-polish-language/browser/content-planner-text.txt`
  and
  `.local-lab/proof/20260626-content-planner-polish-language/content-diagnostics.json`.
- Marketer fixture/backend language cleanup:
  `.local-lab/proof/20260626-marketer-fixture-language-cleanup/summary.json`.
- Ads custom-segment context-pack contract cleanup:
  `.local-lab/proof/20260626-ads-custom-segment-context-pack-contract/summary.json`.
- Marketer language guard self-improvement:
  `.local-lab/proof/20260626-marketer-language-guard-self-improvement/summary.json`.
- Ahrefs capability and Polglish cleanup:
  `.local-lab/proof/20260626-ahrefs-capability-and-polglish-cleanup/summary.json`.
- Ads/GA4/Merchant blocked-claim and connector-summary cleanup with live local
  API proof in current session:
  - `rtk scripts/local_stack.sh restart` brought the local WILQ API and
    dashboard back to ready state.
  - `rtk scripts/local_stack.sh status` confirmed managed API and dashboard are
    ready.
  - `rtk curl -fsS http://127.0.0.1:8000/api/health` returned `ok`.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "ads or ga4 or merchant or command_center" --maxfail=1`
    passed: 66 tests.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py tests/test_marketer_uat_packet.py tests/test_marketer_uat_result.py -q --maxfail=1`
    passed: 10 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx src/routes/ActionDetailRoute.test.tsx src/routes/CommandCenterRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 -t "Ads|GA4|merchant|action detail|Command Center" --testTimeout=20000`
    passed: 7 tests.
  - `rtk uv run python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py`
    passed against live local API.
  - `rtk uv run python .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py`
    passed against live local API.
  - `rtk uv run python .agents/skills/wilq-merchant-feed-operator/scripts/smoke_skill_contract.py`
    passed against live local API.
  - `agent-browser` scans for `/ads-doctor`, `/ga4` and `/merchant` found no
    visible hits for the cleaned stale Ads/GA4/Merchant phrases.

## Latest Verification

- ContentPreflight first contract slice:
  - Added typed backend and shared-schema preflight response.
  - Added `/api/content/preflight`.
  - Added `content_preflight` to content strategist/GSC context packs.
  - Existing-content fixture returns `recommended_mode=refresh`,
    `create_allowed=false`, `draft_allowed=false`,
    `wordpress_draft_allowed=false`, `sales_brief_allowed=true`.
  - No-evidence fixture returns `recommended_mode=block`.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "content_diagnostics_blocks_until_vendor_read or content_diagnostics_exposes_query_page_inventory_queue or codex_context_pack_scopes_content_strategist_payload" --maxfail=1`
    passed: 3 tests.
  - `rtk pnpm --filter @wilq/shared-schemas test -- --runInBand` passed.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
- Context-pack stale-field exception cleanup:
  - Removed active API filters that knew about old dev-preview/mapping field
    names.
  - Updated context-pack tests so compact daily context preserves audit type and
    review outcome without copying raw notes or detail keys.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "context_pack or content_public_url or dev_site or content_action_payload or wordpress_draft_handoff" --maxfail=1`
    passed: 27 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
- Full cleanup verification on 2026-06-26:
  - `scripts/verify.sh` passed end-to-end.
  - Backend pytest: 214 passed.
  - Dashboard Vitest: 52 passed.
  - Playwright dashboard smoke/demo proof: 14 passed.
  - Dashboard production build passed.
  - Non-failing warnings remain: Starlette `httpx` deprecation, `nosec` B105
    warnings in OAuth helper literals, semgrep unavailable, local package not on
    PyPI for audit.
- Ahrefs capability and Polglish cleanup:
  - WILQ remains valid as the product/system name. The cleanup targets
    unnecessary English and internal wording in visible/operator copy.
  - Visible phrases like `brakujące credentiale`, `credential names`,
    `gotowość connectora` and `awarię connectora` were replaced with plain
    Polish access/source wording where they were shown to the operator.
  - Added structured Ahrefs expert capabilities so the Ahrefs skill context
    pack exposes SEO gap review capability through typed rules, not prompt
    workaround text.
  - Updated the Ahrefs context-pack contract test to enforce full condensation:
    full diagnostics keep gap records, while the Codex context-pack carries the
    record count and full endpoint pointer.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "command_center or ahrefs or codex_context_pack_scopes_ads_doctor_payload" --maxfail=1`
    passed: 28 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 -t "connector status renders|localo route renders workflow-specific blockers and clean metric labels|social route renders workflow-specific blockers|Command Center" --testTimeout=15000`
    passed: 3 tests, 17 skipped.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
  - `rtk git diff --check -- apps/api/wilq_api/main.py wilq/briefing/command_center.py wilq/briefing/ahrefs_diagnostics.py apps/dashboard/src/routes/OperatingRouteSurfaces.tsx scripts/marketer_language_guard.py wilq/expert/seo/ahrefs_capabilities.yaml tests/test_api_contracts.py`
    passed.
- Marketer language guard self-improvement:
  - `scripts/marketer_language_guard.py` now blocks newly found visible
    regressions: `Blockery`, `Metric facts`, `GSC clicks`,
    `content opportunities`, `post candidates`, `LinkedIn credentials` and old
    adapter wording.
  - WILQ remains allowed as the system/product name. The guard does not
    blanket-ban `WILQ API`, `source_connectors` or `missing_credentials`
    because those are still valid technical contract terms in skill/API
    surfaces.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
- Ads custom-segment context-pack contract cleanup:
  - `act_prepare_custom_segments_from_search_terms` context-pack compaction now
    keeps one compacted `payload_preview` row for the existing
    `custom_segment_change_preview_v1` contract.
  - Removed the stale compaction check for unused
    `custom_segment_payload_preview_v1` wording instead of preserving an alias.
  - `rtk uv run python -m py_compile apps/api/wilq_api/main.py` passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "codex_context_pack_scopes_ads_doctor_payload or codex_context_pack_scopes_custom_segments_payload" --maxfail=1`
    passed: 2 tests.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "marketing_brief or command_center or localo or ads" --maxfail=1`
    passed.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
- Marketer fixture/backend language cleanup:
  - WILQ remains the product/system name. The cleanup targets unnecessary
    English and technical visible wording, not the WILQ brand.
  - Dashboard fixture and backend brief copy was cleaned for visible terms like
    `Social Publisher`, `Blockery`, `Metric facts`, `GSC clicks`,
    `content opportunities`, `WILQ API`, adapter/connector wording and raw
    access wording where the marketer does not need contract details.
  - Technical contract fields such as `missing_credentials`,
    `checked_credentials`, `source_connectors` and metric fact names were not
    renamed mechanically.
  - `rtk uv run python -m py_compile wilq/briefing/localo_diagnostics.py wilq/briefing/marketing_brief.py wilq/briefing/command_center.py wilq/briefing/ads_diagnostics.py`
    passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "marketing_brief or command_center or localo" --maxfail=1`
    passed: 32 tests.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q --maxfail=1`
    passed: 5 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx src/routes/CommandCenterRoute.test.tsx src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 -t "connector status renders|workflow route renders persisted workflow runs|localo route renders workflow-specific blockers and clean metric labels|social route renders workflow-specific blockers|Command Center|content" --testTimeout=15000`
    passed: 8 tests, 17 skipped, 1 file skipped.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - The broad Ads-inclusive API subset blocker found during this slice was
    fixed in the Ads custom-segment context-pack cleanup above.
- WordPress draft handoff contract cleanup:
  - Active content/WordPress handoff naming was migrated from
    `staging_*` / `wordpress_staging_*` to `wordpress_draft_handoff_*` /
    `wordpress_draft_*` in the backend payload, context-pack compaction,
    dashboard renderers, content strategist smoke contract and content tests.
  - Touched dashboard domain surfaces now use `WILQ` / data-in-WILQ language
    instead of visible `WILQ API` wording where the marketer does not need API
    boundary language.
  - `rtk uv run python -m py_compile apps/api/wilq_api/main.py wilq/actions/content_refresh.py wilq/actions/service.py wilq/briefing/content_diagnostics.py .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py`
    passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "content" --maxfail=1`
    passed: 13 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ContentDiagnosticSurface.test.ts src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 18 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - Scoped stale-term scan over touched active sources returned no hits for
    `staging_handoff`, `wordpress_staging`, `staging_draft`,
    `WordPressStaging`, `contentStaging`, generic Focus/Safety Gate registry
    labels, `migration-map` or `mapping-review`.
  - Live WILQ API/browser proof was not refreshed in this slice because the
    current session reports WILQ API unreachable.
- Ads/Merchant action-language cleanup:
  - `rtk uv run python -m py_compile wilq/briefing/ads_diagnostics.py wilq/briefing/merchant_diagnostics.py wilq/actions/google_ads/negative_keywords.py wilq/actions/google_ads/custom_segments.py wilq/actions/google_ads/search_term_ngrams.py`
    passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics or merchant_diagnostics" --maxfail=1`
    passed: 10 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "ads doctor route renders live metric-backed diagnostics|custom segments route renders dedicated validation contract" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 2 tests.
- Command Center freshness-language cleanup:
  - `rtk uv run python -m py_compile wilq/briefing/command_center.py`
    passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "command_center" --maxfail=1`
    passed: 18 tests.
  - `agent-browser` snapshot scan for `/command-center` passed.
- Skill language cleanup:
  - Stale mixed-language scans over WILQ skill instructions and output contracts
    returned no hits.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
- Action detail language cleanup:
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx -t "content brief and WordPress" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test.
  - Browser scan for `/actions/act_prepare_content_refresh_queue` returned no
    stale action/detail wording hits.
- Connector access language cleanup:
  - Command Center now says `źródła danych`, not `connectorów`, in the source
    health summary.
  - Settings access details now summarize missing access/configuration counts
    without exposing connector IDs, credential variable names or raw source
    labels in the expanded card.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/RegistryPanels.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 3 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "connector status renders" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test; startup/collection remained slow, but the route assertion
    completed.
  - Stale visible-copy scan over the touched sources returned no component hits;
    remaining raw strings are fixture inputs or negative assertions.
  - `rtk git diff --check` passed.
- Domain status language cleanup:
  - Ads Doctor, Ahrefs, Merchant and GA4 connector status labels now render
    `brakuje dostępu` instead of credential wording.
  - Social Publisher empty state now asks to `uzupełnij dostęp LinkedIn/Facebook`
    instead of configuring credentials.
  - Active route source scan returned no visible component hits for stale
    credential wording; the only remaining hit was a negative test assertion.
  - `rtk git diff --check` passed.
  - Focused `App.test.tsx -t "social route renders workflow-specific blockers"`
    did not collect tests and failed in Vitest worker transform/fetch for
    `OperatingRouteSurfaces.tsx`; do not count it as route proof.
- Action detail draft-label cleanup:
  - Action detail preview cards now use `Materiały do posta social`,
    `Tytuł szkicu`, `Przekazanie do WordPress`, `Blokady przekazania` and
    `gotowość systemu` instead of draft/staging/API wording.
  - Stale-label scan over `DetailPanels.tsx` and `ActionDetailRoute.test.tsx`
    returned no hits for the removed visible strings.
  - `rtk git diff --check` passed.
  - Focused `ActionDetailRoute.test.tsx -t "social draft evidence inputs|content brief and WordPress"`
    failed: one action-detail route assertion did not find the heading, and one
    case timed out. Treat this as missing runtime proof for this slice.
- Tactical queue metric-language cleanup:
  - Tactical queue first-screen copy now says `metryki z WILQ API` instead of
    `metric facts`.
  - Empty-state blocker now says `Potrzebne są metryki z WILQ API`.
  - Source scan over Tactical Queue returned no production `metric facts` hits;
    remaining hits are fixture input or negative assertions.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/TacticalQueuePanel.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test.
  - `rtk git diff --check` passed.
- Knowledge source-type language cleanup:
  - Knowledge cards now render `marketing_playbook` source type as `zasada pracy`
    instead of `playbook marketingowy`.
  - Added focused card-list coverage and test cleanup in
    `KnowledgePanels.test.tsx`.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/KnowledgePanels.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 3 tests.
  - Source scan returned no active `playbook marketingowy`/visible playbook
    label hits; the remaining hit is a negative assertion.
  - `rtk git diff --check` passed.
- Content contract version-label cleanup:
  - Content contract labels now hide internal `_v1` suffixes for draft
    generation, URL preflight and WordPress draft preview/write labels.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 3 tests.
  - Label scan over `contentLabels.ts` and the focused test found no visible
    ` v1` label strings; remaining hits are enum inputs in tests.
  - `rtk git diff --check` passed.
- Keyword Planner blocked-access label cleanup:
  - Keyword Planner action detail now renders `Zablokowany dostęp` instead of
    `Blokowane API`.
  - Source scan over `DetailPanels.tsx` and `ActionDetailRoute.test.tsx`
    returned no stale `Blokowane API` hits.
  - `rtk git diff --check` passed.
  - Focused `ActionDetailRoute.test.tsx -t "Keyword Planner access blocker"`
    failed before reaching the expected detail heading; do not count it as
    route proof for this slice.
- Action review-gate safety-language cleanup:
  - Action review gate now renders `Ostatni zapis bezpieczeństwa`,
    `Ślad bezpieczeństwa`, `Czy próbowano zapisu` and
    `brak bezpiecznej ścieżki zapisu w zewnętrznym systemie` instead of
    default audit/adapter/mutation wording.
  - Preview, confirm and impact result panels now use `Ślad bezpieczeństwa`
    instead of `Zdarzenie audytu`.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionObjectPanels.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test.
  - Stale wording scan over `ActionObjectPanels.tsx`,
    `ActionObjectPanels.test.tsx` and `App.test.tsx` found old terms only in
    negative assertions.
  - `rtk git diff --check -- apps/dashboard/src/routes/ActionObjectPanels.tsx apps/dashboard/src/routes/ActionObjectPanels.test.tsx apps/dashboard/src/routes/App.test.tsx`
    passed.
  - Focused `App.test.tsx -t "merchant route renders dedicated feed diagnostics"`
    failed before reaching the action safety panel because the route test did
    not find heading `Merchant Center`; do not count it as proof for this slice.
- Content WordPress status language cleanup:
  - Added a shared `contentWordPressPostStatusLabel` so WordPress status
    `draft` renders as `szkic` before it reaches Content Planner or Action
    Detail cards.
  - Content Planner no longer renders `wersja robocza istniejącej treści /
    draft`; tests now expect `wersja robocza istniejącej treści / szkic`.
  - Action Detail WordPress cards now use `Szkic WordPress do sprawdzenia` and
    `Przekazanie` instead of staging-facing labels.
  - `scripts/marketer_language_guard.py` now blocks raw ` / draft`,
    raw draft-status copy and visible staging labels in active surfaces.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 4 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run python -m py_compile scripts/marketer_language_guard.py`
    passed.
  - `rtk git diff --check -- apps/dashboard/src/lib/contentLabels.ts apps/dashboard/src/routes/ContentDiagnosticSurface.tsx apps/dashboard/src/routes/DetailPanels.tsx apps/dashboard/src/routes/ContentDiagnosticSurface.test.ts apps/dashboard/src/routes/App.test.tsx scripts/marketer_language_guard.py`
    passed.
- Brief workflow focus-language cleanup:
  - Brief workflow config no longer exposes `Local Visibility Focus`,
    `Social Publishing Focus`, `Content Growth Focus`, `Feed/Product Focus` or
    generic `Safety Gate` headings.
  - Route config now uses `Lokalna widoczność do sprawdzenia`,
    `Publikacje social do sprawdzenia`, `Priorytety treści do sprawdzenia`,
    `Feed i produkty do sprawdzenia` and `Brama bezpieczeństwa...` labels.
  - Added `BriefWorkflowSurface.test.tsx` to guard the config against returning
    generic Focus/Safety Gate labels.
  - `scripts/marketer_language_guard.py` now blocks those visible headings in
    active surfaces.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/BriefWorkflowSurface.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk git diff --check -- apps/dashboard/src/routes/BriefWorkflowSurface.tsx apps/dashboard/src/routes/BriefWorkflowSurface.test.tsx apps/dashboard/src/routes/App.test.tsx scripts/marketer_language_guard.py`
    passed.
- Generic surface registry fallback removal:
  - Removed the dead generic registry fallback branch from `GenericSurface`
    instead of renaming its headings.
  - Removed disabled registry queries and unused ExpertRule filtering helpers
    from `GenericSurface`.
  - Added `GenericSurface.test.tsx` to prove compact fallback routes do not
    render `Evidence Registry`, `Connector Refresh Runs`, `Connector Status`,
    `Opportunities`, `Actions` or `Expert Rules`.
  - `scripts/marketer_language_guard.py` now blocks registry fallback headings
    in active surfaces.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/GenericSurface.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk git diff --check -- apps/dashboard/src/routes/GenericSurface.tsx apps/dashboard/src/routes/GenericSurface.test.tsx scripts/marketer_language_guard.py`
    passed.
  - Focused `App.test.tsx -t "legacy operating routes do not fall back to registry dumps"`
    was interrupted after a worker timeout fetching `RegistryPanels.tsx`; no
    tests were collected, so it is not proof for this slice.
- Actions route list cleanup:
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "actions route starts from marketer-facing actions instead of registry dumps" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test.
  - Runtime proof for expanded `/actions` list returned no stale action-list
    wording hits.
- Opportunities list cleanup:
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/OpportunitiesRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 2 tests.
  - Live API proof for `/api/opportunities` returned 5 decisions with evidence
    and source counts.
  - Browser proof for `/opportunities` was not completed because both browser
    tools hung while waiting for the route render in this session.
- Registry panels condensation:
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/RegistryPanels.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 2 tests.
  - Evidence and source-read lists no longer print raw source/run identifiers or
    raw metric key-value summaries in the card view.
- Knowledge panels language cleanup:
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/KnowledgePanels.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 2 tests.
  - Visible knowledge-panel wording now uses plain Polish for rules and actions
    instead of internal workflow labels.
- Localo metric-label cleanup:
  - `rtk uv run pytest tests/test_api_contracts.py -k "localo_diagnostics" -q`
    passed: 4 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/components/MetricFactChips.test.tsx src/routes/App.test.tsx -t "MetricFactChips|localo route renders workflow-specific blockers and clean metric labels" --reporter=verbose --testTimeout=30000`
    passed: 2 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
  - Browser proof for `/localo`:
    `.local-lab/proof/20260626-localo-metric-label-cleanup/browser/summary.json`
    has zero hits for `metryka WILQ`, raw Localo contract IDs and stale
    dimension wording, while confirming the visible labels `Zmiany konkurencji`,
    `obszar=widoczność konkurencji` and `zakres=aktywne miejsca`.
- Candidate-language cleanup:
  - Active dashboard/API source scan returned no hits for stale visible
    `kandydat*`, legacy dry-run, migration-map, mapping-review or `target_site`
    wording in active marketer-facing sources.
  - `rtk uv run python -m py_compile wilq/briefing/ads_diagnostics.py wilq/actions/content_refresh.py wilq/schemas.py`
    passed.
  - Live WILQ API diagnostics/context proof under
    `.local-lab/proof/20260626-candidate-language-cleanup/api-context/`
    scanned clean for stale candidate/dev/migration wording across Ads,
    Content, Merchant and custom-segments context output.
  - Focused dashboard vitest attempts for touched routes did not reach test
    collection and timed out in the worker fetch/transform phase; do not count
    them as proof.
  - `agent-browser` snapshot attempts hit `Resource temporarily unavailable`;
    do not count browser proof for this slice until the daemon is healthy.
- Marketer language guard:
  - Added `scripts/marketer_language_guard.py` and wired it into
    `scripts/quality.sh` so repeated stale marketer-facing wording becomes a
    fast shared guardrail instead of a chat-only correction.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed after the Merchant
    skill output contract wording cleanup.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
- Skill/eval gate language cleanup:
  - `scripts/verify.sh` now checks the current output labels
    `Akcje do sprawdzenia` and `Sprawdzenie w WILQ` instead of old action
    candidate wording.
  - `scripts/codex_skill_eval.sh` no longer prompts for old action-candidate
    wording or visible ActionObject IDs.
  - `docs/evals/cases/wilq-skill-eval-cases.json` now expects
    `do sprawdzenia w WILQ` in affected skill cases.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
  - `rtk bash -n scripts/verify.sh scripts/codex_skill_eval.sh scripts/quality.sh`
    passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py scripts/skill_hygiene_check.py`
    passed.
- Campaign/custom-segment skill wording cleanup:
  - `wilq-campaign-builder` eval prompt now asks for a campaign proposal and
    `Sprawdzenie w WILQ`, not old candidate/validation wording.
  - `wilq-custom-segments` output contract now describes `Segment do
    sprawdzenia` and proposals from the API contract, not marketer-facing
    candidates.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
  - `rtk rg -n "kandydata|kandydat|kandydaci|kandydatów|kandydatem|Kandydat" docs/evals/cases/wilq-skill-eval-cases.json .agents/skills scripts/verify.sh scripts/codex_skill_eval.sh`
    returned no active hits.
- Codex eval prompt cleanup:
  - Ads eval markers now use `zapis zmian rekomendacji`, not old execution
    wording.
  - `scripts/codex_skill_eval.sh` now asks for `sprawdzenie w WILQ` instead of
    old validation wording in the operator prompt.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
  - `rtk rg -n "wykonanie rekomendacji|gdy walidacja przejdzie|walidacja przejdzie|Walidacja|tylko do sprawdzenia|Dry-run|dry-run|ActionObject IDs|ActionObjecty" docs/evals/cases/wilq-skill-eval-cases.json .agents/skills scripts/verify.sh scripts/codex_skill_eval.sh tests/test_codex_skill_eval_cases.py`
    returned no active hits.
- Content strategist smoke guard cleanup:
  - The content strategist smoke no longer keeps old URL placement names as
    literal sentinels. It now asserts the current content URL allowlist:
    `source_public_url`, `final_canonical_url`, `intended_final_url`,
    `preview_url`.
  - `rtk uv run python -m py_compile .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py`
    passed.
  - `rtk uv run --extra dev ruff check .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py`
    passed.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
  - `rtk rg -n "target_site|mapping_review|migration_candidate|current_migration_candidate_url|wykonanie rekomendacji|gdy walidacja przejdzie|walidacja przejdzie|ActionObject IDs|ActionObjecty|kandydat" docs/evals/cases/wilq-skill-eval-cases.json .agents/skills scripts/verify.sh scripts/codex_skill_eval.sh tests/test_codex_skill_eval_cases.py`
    returned no active hits.
  - Live `wilq-content-strategist` smoke against `/api/codex/context-pack`
    timed out. `scripts/local_stack.sh status` and `/api/health` were ready, so
    do not count live content context-pack proof for this slice.
- Marketer language guard expansion:
  - `scripts/marketer_language_guard.py` now also scans active eval/prompt
    contract files: `docs/evals/cases/wilq-skill-eval-cases.json`,
    `scripts/codex_skill_eval.sh`, `scripts/verify.sh` and
    `tests/test_codex_skill_eval_cases.py`.
  - The guard now catches the recurring action-candidate, old validation,
    old recommendation execution and old URL-placement phrases that already
    appeared during this cleanup.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run python -m py_compile scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
- Command Center and action-language browser cleanup:
  - Browser text proof for `/command-center` showed no stale candidate/dev
    wording, but did show `akcję WILQ` in the Ads next step.
  - Command Center, Content Planner preview copy, Ads action count labels and
    Ads business-context next step now use `sprawdzenie w WILQ`,
    `zatwierdzenie w WILQ` and `akcje do sprawdzenia` instead of `akcja WILQ`.
  - `wilq/briefing/ads_diagnostics.py` now says the write path requires
    separate WILQ review, preview, confirmation and audit instead of a separate
    WILQ action.
  - `scripts/marketer_language_guard.py` now blocks `akcja WILQ` variants in
    active scanned sources.
  - `rtk uv run python -m py_compile wilq/briefing/ads_diagnostics.py` passed.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run python -m py_compile scripts/marketer_language_guard.py` passed.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/CommandCenterRoute.test.tsx src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    did not fully pass: `ContentDiagnosticSurface.test.ts` passed 2 tests, but
    `CommandCenterRoute.test.tsx` timed out in the vitest worker while fetching
    `lucide-react`.
  - Follow-up `agent-browser open /command-center` failed with `Resource
    temporarily unavailable`; do not count post-change browser proof for this
    slice.
- Action wording guard hardening:
  - Active dashboard/API/skill wording now uses `propozycja w WILQ`,
    `sprawdzenie w WILQ` or `akcje do sprawdzenia` instead of `akcja w WILQ`
    phrasing.
  - Command Center now says `dopasowania WordPress`, not `mapowanie WordPress`.
  - `scripts/marketer_language_guard.py` now blocks `akcja WILQ` and
    `akcja w WILQ` variants across active source and eval/prompt contracts.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile wilq/actions/service.py wilq/briefing/merchant_diagnostics.py wilq/briefing/ga4_diagnostics.py wilq/briefing/tactical_queue.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
- Command Center Polish source-language cleanup:
  - Command Center strict instruction now says `dane źródłowe`, not
    `API/evidence`.
  - Command Center evidence labels now say `Dowody w WILQ`, not `Dowody w API`
    or `WILQ API`.
  - Skill output contracts now say `brakujące dane źródłowe albo dowody`
    instead of `brakujące API/evidence`.
  - `scripts/marketer_language_guard.py` now blocks `API/evidence` and
    `Dowody w API` in active scanned sources.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile wilq/briefing/command_center.py wilq/briefing/marketing_brief.py scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "command_center or marketing_brief" --maxfail=1`
    passed: 24 tests.
  - `rtk uv run pytest tests/test_live_contract_smoke.py -q` passed: 3 tests.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
  - Browser proof after `scripts/local_stack.sh restart`:
    `.local-lab/proof/20260626-command-center-polish-language-restarted/browser/command-center-text.txt`
    has no hits for `API/evidence`, `Dowody w API`, `WILQ API`,
    stale action-language, dev-preview or candidate wording.
- Content Planner Polish language cleanup:
  - Content Planner visible copy now says `dane WILQ`, `Szkic`, `punkt
    odniesienia`, `dane po publikacji` and `okna sprawdzenia` instead of
    `WILQ API`, `Draft`, `baseline`, `follow-up` and raw execution wording.
  - Content blocked-claim labels now render `jakość leadów`, `wpływ na
    przychód`, `nowy artykuł bez kontroli spisu treści` and `gwarancja braku
    duplikatów` instead of raw English claims.
  - Content action count now renders Polish plural forms such as `2 akcje`.
  - Live API context for `/api/content/diagnostics` confirmed 3 sections, 5
    decisions, 24 evidence IDs and configured GSC, WordPress, GA4 and Ahrefs
    connectors.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile wilq/briefing/content_diagnostics.py wilq/briefing/blocked_claim_labels.py`
    passed.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 4 tests.
  - Browser proof after `scripts/local_stack.sh restart`:
    `.local-lab/proof/20260626-content-planner-polish-language/browser/content-planner-text.txt`
    has no hits for raw `revenue impact`, `new article without inventory check`,
    `duplicate-free guarantee`, `lead quality`, `2 akcji`, `Draft:`,
    `follow-up`, `baseline`, `credentiali`, `WILQ API`, `target_site`,
    `migration-map` or `mapping-review`.
- Content preflight dashboard gate:
  - Content Planner now reads `/api/content/preflight` and shows a primary
    `Czy można pisać?` panel before the detailed content decision.
  - The panel answers the marketer-facing first question: zachować,
    odświeżyć, scalić, utworzyć or block, plus what remains blocked before a
    draft or WordPress handoff.
  - The dashboard imports `ContentPreflightResponse` from the shared API
    boundary instead of duplicating a local route type.
  - Focused `App.test.tsx -t "content route"` passed: 2 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk git diff --check` passed.
- Content preflight language cleanup:
  - Browser proof showed `sales brief`, `claimy`, `claimów`, `revenue` and
    `lead uplift` leaking into Content Planner text.
  - The producing API/action sources now say `brief`, `ryzykowne obietnice`,
    `obietnica przychodu` and `wzrost leadów` instead of Polglish wording.
  - Content Planner labels now say `Nie wolno twierdzić` / `Nie wolno obiecać`
    instead of `Zablokowane claimy`.
  - `scripts/marketer_language_guard.py` now blocks `sales brief`,
    `claim review`, `revenue albo lead uplift`, `revenue/lead uplift` and
    `Overlap:` in active scanned sources.
  - Live `/api/content/preflight` after stack restart returned refresh-first
    preflight for `https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/`
    with `preview_url=null`, `draft_allowed=false`,
    `wordpress_draft_allowed=false`, 4 evidence IDs and 2 source connectors.
  - Browser proof:
    `.local-lab/proof/20260626-content-preflight-language-clean/browser/content-planner-snapshot.txt`
    shows `Czy można pisać?`, `brief odświeżenia`, `ryzykownych obietnic` and
    `Wspólne zapytania`; scan found no `sales brief`, `claimy`, `claimów`,
    `claim review`, `revenue albo lead uplift`, `revenue/lead uplift`,
    `Overlap:`, `target_site`, `migration-map`, `mapping-review`, `Dry-run`,
    `ActionObjecty`, `payload` or `WILQ API`.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "content_preflight or content_action_preview or content_draft" --maxfail=1`
    passed: 2 tests.
  - Focused `App.test.tsx -t "content route"` passed: 2 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
  - `rtk uv run python -m py_compile wilq/briefing/content_diagnostics.py wilq/actions/content_refresh.py scripts/marketer_language_guard.py`
    passed.
  - `rtk git diff --check` passed.
- Cross-dashboard `claimy` language cleanup:
  - Tactical Queue, Ads Doctor, GA4, Merchant, Knowledge, BriefWorkflow, GA4
    skill prompts, Social skill trigger text, Codex skill eval wording and
    touched API/domain copy now use `twierdzenia`, `obietnice`,
    `ryzykowne obietnice` or `Nie wolno twierdzić` instead of `claimy`,
    `claimów`, `Zablokowane claimy` and `Blokady claimów`.
  - `scripts/marketer_language_guard.py` now blocks `claimy`, `claimów`,
    `Blokady claimów` and `Zablokowane claimy` in active scanned sources.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - Focused dashboard route test passed: `App.test.tsx -t "tactical|ga4|merchant|ads|content route"`
    with 5 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q --maxfail=1`
    passed: 5 tests.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "ga4 or merchant or ads or ahrefs or command_center" --maxfail=1`
    passed.
  - Browser proof after `scripts/local_stack.sh restart`:
    `.local-lab/proof/20260626-claimy-language-clean/browser/{command-center,ads-doctor,merchant,ga4}-snapshot.txt`
    showed plain Polish labels such as `Nie wolno twierdzić`; scan found no
    `claimy`, `claimów`, `Zablokowane claimy`, `Blokady claimów`,
    `Blokuje claimy`, `sales brief`, `claim review`, `revenue albo lead uplift`,
    `revenue/lead uplift`, `Overlap:`, `target_site`, `migration-map`,
    `mapping-review`, `Dry-run`, `ActionObjecty`, `payload` or `WILQ API`.
  - `rtk uv run python -m py_compile wilq/briefing/ads_diagnostics.py wilq/briefing/ga4_diagnostics.py wilq/briefing/merchant_diagnostics.py wilq/briefing/ahrefs_diagnostics.py wilq/briefing/command_center.py wilq/actions/service.py wilq/actions/ga4/tracking_quality.py scripts/marketer_language_guard.py`
    passed.
  - `rtk git diff --check` passed.
- Ledger condensation:
  - `docs/PROGRESS.md` was reduced back to a short recovery ledger.
  - `rtk git diff --check` passed after the latest cleanup slices.

## Active Gaps

- `PLAN.md` and `docs/goals/001-goal.md` intentionally contain forbidden wording
  examples as policy. They are not active UI/API copy.
- Some internal contract names are still technical. If they reach the marketer
  surface, migrate the contract or view-model in a focused slice rather than
  adding UI-only masking.
- The next language cleanup slice should use live smokes and browser scans to
  find the next real operator-facing issue. Do not keep old English phrases in
  fixtures as a compatibility layer; if a fixture uses old language, migrate it
  to the current API/domain wording or delete the obsolete fixture.
- Explicit debug context can expose more detail than default skill context. It
  must remain operator-only and must not become the normal skill prompt surface.
- Some default skill context-packs are still large by operator standards.
  Continue shrinking only where size comes from raw/debug duplication instead of
  useful decision context.
- `wilq-daily-command` context-pack budget blocker is cleared for the current
  live state. Daily default evidence summaries are capped at 32 embedded
  summaries while decision/brief evidence IDs remain available for drilldown.
  Live smoke passed and measured `177573` bytes against the `180000` byte cap.
- Dashboard route vitest/typecheck can exceed current timeout before collecting
  tests on this dirty worktree. Treat that as a test-runtime cleanup task, not a
  product proof.
- `agent-browser` can become temporarily unresponsive in this WSL session. When
  it fails, record it as missing browser proof instead of pretending the route
  was checked.
- Real marketer UAT or explicit owner deferral is still required before claiming
  usefulness as proven.
- Final WILQ is still incomplete. Major missing layers include richer content
  inventory, duplicate/canonical checks, sales brief, claim ledger, human
  review flow, WordPress draft handoff, measurement loop,
  workspace/profile contracts and safe write expansion.

## Next Step

1. Continue active-source cleanup from `PLAN.md`, starting with the next active
   marketer-facing dashboard/API/skill surface that still makes Wilku parse
   technical internals.
2. Do not add route-local masking helpers. Fix the producing API, schema,
   view-model, domain source or skill contract.
3. Use real marketer UAT or owner deferral before claiming the cleanup state is
   accepted.
4. Move to `PLANS.md` product layers only after the cleanup state is accepted or
   the remaining documentation/internal-contract debt is explicitly scheduled.
