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
- WILQ API remains the product brain. Dashboard and Codex skills consume typed
  API contracts, source connectors and WILQ-described evidence.
- Active cleanup removes marketer-facing jargon and old working names. The
  canonical visible language is defined in `PLAN.md`; do not repeat stale terms
  outside guardrail sections.
- Do not preserve deprecated active fields, compatibility aliases or stale
  target/dev/migration semantics when direct migration is feasible.
- Do not mask dirty copy with UI translators, `replaceAll` helpers or local
  dictionaries. Fix typed API/schema/view-model/domain source instead.
- Raw IDs belong only in technical panels, audit detail or trace views, not in
  primary marketer copy.

## Latest Verified State

- Cleanup has moved many Ads, Merchant, GA4, Localo, Ahrefs, Knowledge, Brief
  Workflow, tactical queue and Action Detail labels from dashboard helpers into
  API/domain/shared-schema fields.
- Primary navigation and touched route headings now use marketer-readable Polish
  labels such as `Centrum pracy`, `Treści` and `Google Ads`.
- Touched marketer surfaces avoid raw trace IDs, endpoint names, raw enum keys,
  stale dev-site placement language and English validation wording in normal
  copy.
- Action Detail normal preview renders typed API preview cards only. Raw action
  payloads remain available only behind the collapsed technical detail panel.
- Demand Gen diagnostics now expose typed API preview cards and the dashboard no
  longer builds the primary preview from raw `payload_preview` shape.
- Generic status routes, Demand Gen, Merchant, GA4, Ads, Content and custom
  segment first-screen labels were tightened to marketer-readable Polish.
- Legacy raw audit summary text is no longer rewritten through string
  replacements; raw historical summaries collapse to a neutral audit note.
- Ahrefs/content public contracts now use public URL wording; active
  diagnostics, source facts, tactical queue and WordPress draft handoff no
  longer expose stale target-field semantics.
- Knowledge operating map now carries API-owned labels for source connectors,
  evidence summaries, missing data and blocked claims, so the Knowledge route
  does not show playbook refusal rules or raw connector IDs on the first screen.
- Knowledge playbooks now expose Polish source rules and output contracts.
- UAT packet/result scripts now use marketer-facing Polish route names and
  markdown labels.
- Ahrefs visible copy now uses `dowody`, `SEO i treści`, `linki zwrotne`,
  `widok Treści` and `organiczne słowa dla URL`; live Ahrefs API/browser proof
  shows no `Ahrefs evidence`, `SEO/content`, `backlinków` or `per URL` residue.
- Custom Segments candidates now expose API-owned preview cards and rejection
  reason labels. The route no longer reads `candidate.payload_preview` for
  marketer-facing segment cards.
- GA4 full review now renders API-owned action preview cards and no longer
  parses `action.payload.payload_preview` for the review card.
- Ads negative keyword candidates now expose API-owned preview cards. The Ads
  route no longer reads `candidate.payload_preview` for marketer-facing
  negative-keyword cards.
- Ads recommendation rows now expose API-owned preview cards. The Ads route no
  longer reads `row.payload_preview` for marketer-facing recommendation cards.
- Ads budget rows now expose API-owned preview cards. The Ads route no longer
  reads `row.payload_preview` for marketer-facing budget cards.
- Merchant product samples and product performance rows now expose API-owned
  sample summaries, product references, Ads status labels, price labels and
  missing metric labels. The Merchant route no longer renders raw sample product
  IDs, Ads product status enums or raw Ads cost micros in those panels.
- Merchant decision and price-impact previews now expose API-owned preview
  cards. The Merchant route no longer parses raw `payload_preview` to build
  marketer-facing preview cards.
- Content URL semantics now use public/final wording in active gates. Active
  content diagnostics/actions no longer use dev-site placement semantics.
- Content preflight now uses the `service_fit_status` contract, and active
  content diagnostics no longer tell the marketer to review old URL-assignment
  wording; live API and browser proof cover the current Treści surface.
- Social source inputs no longer depend on a hardcoded dev-preview host filter;
  content objects need a public/final/canonical URL before they can drive that
  workflow.
- Content primary URL labels no longer fall back to `preview_url`.
- Shared `StatusBadge` no longer owns a product-language dictionary. Registry,
  workflow, Opportunities, tactical queue, marketing brief, Custom Segments,
  Demand Gen, Merchant and Content status/risk badges now render API/domain
  `*_label` fields.
- Opportunity, workflow run, marketing brief, tactical queue, Merchant issue
  cluster, Custom Segments read contracts and Demand Gen readiness contracts now
  expose the missing status/risk labels through typed API/shared schemas.
- Demand Gen campaign mode review no longer exposes active
  `transition_candidate` / `demand_gen_transition_*` contracts. API, shared
  schemas, dashboard, skill smoke and playbook/rule IDs now use
  `demand_gen_campaign_mode_review`, `review_required`, `review_status_label`
  and marketer-facing labels such as `kontrola trybu kampanii`.
- Dashboard proof sections now use action-oriented `Dowody i warunki ...`
  wording, and touched routes/tests no longer expose low-value proof/audit
  jargon in primary marketer copy.
- Connector label fallbacks now use safe Polish operator labels instead of raw
  connector IDs in shared helpers, command center, marketing brief, GA4/Localo
  diagnostics and context-pack refresh-run summaries. Refresh-run summaries now
  expose `connector_label` and `status_label`.
- Route labels now use safe operator-label helpers in Centrum pracy and the
  workflow registry. Unknown routes no longer fall back to raw route paths or
  generic fallback copy.
- Ads diagnostics label fallbacks now use closed Polish labels for unknown
  vendor enums, changed fields, missing read contracts, metrics and review
  gates. Ads budget/recommendation preview cards no longer embed raw campaign or
  budget IDs in their marketer-facing card IDs.
- Ads blocked-claim source labels were cleaned from old verdict wording toward
  direct labels such as `opłacalność` and `zmarnowany budżet`.
- Shared Python schema fallbacks for marketing risk, tactical domains,
  tactical dimensions, metric dimension values and Ads/Demand Gen read statuses
  now use safe Polish fallback labels instead of raw enum values.
- Ads recommendation and change-history helper fallbacks now use safe Polish
  labels for unknown recommendation types, missing recommendation metrics,
  change resource types and change operation types.
- Tactical queue cards now show evidence/action summaries on the card face and
  keep linked trace IDs inside `Szczegóły techniczne`.
- Action confirmation and impact audit summaries now use operator labels for
  blockers and Ads targets instead of raw guardrail keys or micros field names.
- Keyword Planner access actions and Codex context now expose Polish operator
  reasons instead of raw Google Ads authorization enums or English planning copy.
- Merchant label helpers no longer turn unknown internal keys into prettified
  operator labels; known Merchant claims stay explicit and unknown values use
  safe Polish fallback labels.
- Demand Gen campaign and campaign-mode rows now expose API-owned channel/status
  labels, and the dashboard renders those labels instead of raw Ads enums.
- Marketing brief items now expose API-owned `kind_label`, and Brief Workflow
  route cards render that label instead of raw `metric` / `blocker` / `action`
  / `recommendation` enums.
- Tactical queue items now expose `dimension_value_labels`, and tactical/
  Merchant context chips plus metric chips avoid raw dimension values when API
  labels are missing.
- Content source facts now use Polish operator labels such as `Strona z GSC`
  and `Kliknięcia GSC` instead of `GSC page=` / `queries=` key-value strings,
  and the Content status heading now reads `Stan danych treści`.
- Tactical queue GSC diagnoses now use Polish metric labels such as
  `kliknięcia:` and `wyświetlenia:` instead of `clicks=` /
  `impressions=` key-value strings.
- Active WILQ skill contracts now require Polish operator wording for dowody,
  źródła danych, blokady and technical trace IDs instead of pushing
  English/Polish mixed terms into primary skill answers.
- Opportunity fallback copy and Content vendor-read blockers now use Polish
  source-data wording instead of credential/vendor/query-page/playbook jargon.
- Seeded content refresh action copy now uses Polish source-data wording instead
  of `URL/query evidence`, `GSC query/page` or WordPress inventory jargon.
- Dashboard e2e proof now checks current marketer labels such as `Centrum
  pracy`, `Treści` and `Google Ads`, and no longer expects raw Ads evidence IDs
  in the primary Ads proof panel.
- Google Ads OAuth repair and blocked Merchant feed diagnostics now use Polish
  operator wording instead of raw OAuth/credential/vendor-read jargon.
- Ads n-gram and custom-segment action/context copy now uses Polish operator
  wording instead of `N-gram review`, `search-term evidence`, `negative keyword
  queue` or English `forecast` wording.
- Workflow cards now say `Brakujące dane` and `Granice wniosków` instead of
  low-value process jargon, and workflow test fixtures no longer preserve raw
  `queued` / old verdict wording as visible labels.
- Workflow cards now use API/domain `missing_contract_labels` for expanded
  missing-data details, so raw workflow contract keys stay out of marketer
  copy.
- Detail views now render source/domain labels as neutral chips instead of
  using marketer labels as visual badge states. The shared status badge no
  longer injects hidden punctuation into browser text output.
- Central blocked-claim labels now keep known Polish claim labels specific and
  collapse unknown raw technical values to `obietnica do sprawdzenia`.
- Google Sheets compact route copy now says safe export/testing language
  instead of export contract/UAT jargon.
- Metric chips now use `zmiana:` and `Etykieta: wartość` formatting instead of
  `delta:` and key=value display.
- Action preview API results now return typed/redacted `preview_items` and
  `preview_cards`. Raw action payload preview details stay in action payloads
  and technical detail, not in the primary preview result used by marketer
  surfaces.
- Centrum pracy daily-decision badges now render API-owned
  `decision_state_label` instead of raw decision-state enum text. API titles use
  `Google Ads` and `Treści` wording, and old drilldown wording was removed from
  the active action plan copy.
- Unknown active labels in Knowledge, Content, tactical queue, content actions
  and Ads recommendation helpers now fall back to neutral Polish operator
  wording instead of humanizing raw enum keys by replacing underscores.
- Ahrefs, GA4, Localo and Merchant diagnostic label helpers now use neutral
  Polish fallback labels for unknown statuses, read contracts and risks instead
  of exposing raw enum values or `status: ...` strings.
- Workflow registry and workflow-run labels now use neutral Polish fallback
  labels for unknown process statuses and risks instead of exposing raw values.
- GA4 tracking-quality actions, Ads campaign triage and Opportunities now use
  neutral Polish fallback labels for unknown operation types, dimensions,
  validation gates, channels and risks.
- Content draft handoff, post-publication measurement and tactical WordPress
  match summaries now use `stan ...` wording instead of `status:` prefixes in
  marketer-facing summaries.
- Dashboard StatusBadge usage now passes raw state values with API labels for
  Knowledge, Action, GA4 and Merchant status/risk/validation badges instead of
  using the visible label as the visual state.
- Knowledge cards now render confidence as a neutral Polish label instead of
  using confidence text as a status state; browser proof covers the expanded
  knowledge-source panel.
- Dashboard e2e proof for Action Detail and Merchant no longer expects raw
  evidence IDs in the primary surface; trace IDs stay reachable through
  technical detail after using marketer-facing `dowód 1` links.
- Unknown Knowledge card types/routes, Localo contracts/metrics, GA4 read
  contracts, Demand Gen conditions, opportunity domains and Merchant tactical
  issue labels now fall back to neutral Polish operator labels instead of raw
  enum/source values.
- Content Planner's expandable plan/draft panel now renders API-owned
  `ActionObject.preview_cards` for content brief and WordPress draft previews
  instead of building marketer-facing cards from raw action payload arrays.
- Content Planner's selected-decision first screen now uses API-owned
  `marketer_decision` fields for metrics, content angle, H1/H2/FAQ/CTA and
  source facts instead of reading `action.payload.content_brief_preview`.
- Action review badges now keep visual state separate from visible review copy;
  the last-review label is not used as a `StatusBadge` state value.
- Action review gate summaries now sanitize raw historical review notes before
  they reach Action Detail; legacy `candidate`, `source_type`, payload and
  blocked-claim fragments collapse to a neutral legacy-audit note.
- Content refresh review gates now use Polish operator wording for intent
  review; the Action Detail conditions no longer show `query/topic`.
- Content strategist context-pack now preserves API-owned labels for content
  brief and WordPress draft previews, including source type, mode, draft
  operation, post status and concrete blocked-claim labels.
- Blocked-claim labels now use one API/domain source in `wilq/operator_labels.py`.
  Command Center and Knowledge no longer surface generic `blokada do
  sprawdzenia`; browser proofs are in
  `.local-lab/proof/command-center-blocked-claims-clean.txt` and
  `.local-lab/proof/knowledge-blocked-claims-clean.txt`.
- Command Center Merchant daily-decision metric facts now use Merchant domain
  labels for product examples, issue types, attributes and reporting contexts;
  API proof is in `.local-lab/proof/merchant-command-center-metric-labels-clean.json`.
- Recent guardrails cover tactical, Ads, Knowledge, action detail, Content
  Planner and marketer-language presentation contracts.

## Active Findings

1. Keep `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and
   `docs/goals/001-goal.md` short and aligned. History belongs in git and proof
   artifacts.
2. Continue raw fallback cleanup in active API/helper modules. Current scan is
   down to non-marketer connector normalization and title fallbacks; any new
   visible raw fallback must be fixed at typed API/schema/view-model source.
3. Add typed contract/vendor-enum label registries outside the already-cleaned
   Ads diagnostics helper path so unknown read contracts and vendor enums do not
   fall back to raw snake_case or English values in marketer-facing copy.
4. Continue moving repeated metric, dimension, source, blocker and evidence
   naming into API/domain labels. Pure numeric formatting can stay in UI.
5. The remaining active `replace("_", " ")` scan hits are Merchant attribute-key
   normalizers used for equality matching, not visible operator labels; keep
   them out of copy paths.
6. Continue checking compacted context-packs after dashboard/API cleanup; the
   content strategist context now preserves the current content preview labels.

## Latest Accepted Proof

- `rtk uv run pytest tests/test_api_contracts.py -q -k "action_preview or content_action_preview or localo_visibility or merchant_feed_preview" --maxfail=5`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "command_center" --maxfail=3`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionObjectPanels.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/CommandCenterRoute.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "operator_label_fallbacks or route_label_fallbacks or tactical_queue" --maxfail=3`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "content route renders condensed selected decision with expandable detail" --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionObjectPanels.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "legacy_raw_audit_summary or action_review_gate_hides_raw_legacy_review_summary or action_review_records_human_outcome_without_apply" --maxfail=3`
- `agent-browser` proof: `.local-lab/proof/action-detail-review-badge-state-clean.txt`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "content_refresh_review_gates_use_polish_operator_language or content_refresh_empty_state_uses_operator_source_language" --maxfail=3`
- `agent-browser` proof: `.local-lab/proof/action-detail-content-review-gates-polish.txt`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "content_strategist_context_pack_preserves_reviewed_draft_preview or codex_context_pack_scopes_content_strategist_payload or content_refresh_review_gates_use_polish_operator_language" --maxfail=3`
- API proof: `.local-lab/proof/content-strategist-context-pack-labels.json`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "content_diagnostics_exposes_marketer_decision or content_diagnostics_exposes_query_page_inventory_queue" --maxfail=3`
- `rtk uv run python scripts/marketer_language_guard.py`
- `agent-browser` proof: `.local-lab/proof/content-planner-selected-decision-api-viewmodel.txt`
- `agent-browser` proof: `.local-lab/proof/content-planner-preview-cards-clean.txt`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "knowledge_operating_map or content_diagnostics or tactical_queue or action_preview or operator_label_fallbacks" --maxfail=3`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "marketing_brief" --maxfail=3`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/BriefWorkflowSurface.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "marketing_tactical_queue_uses_dimensioned_metric_facts or operator_label_fallbacks_do_not_humanize_raw_unknown_enums or merchant_diagnostics_exposes_feed_issue_queue" --maxfail=3`
- `rtk pnpm --dir apps/dashboard exec vitest run src/components/MetricFactChips.test.tsx src/routes/TacticalQueuePanel.test.tsx --reporter=verbose --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "content_action_preview" --maxfail=3`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx src/routes/ActionDetailRoute.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "marketing_tactical_queue_uses_dimensioned_metric_facts" --maxfail=3`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/TacticalQueuePanel.test.tsx src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `agent-browser` proof: `.local-lab/proof/content-planner-tactical-metrics-clean.txt`
- `rtk uv run python scripts/skill_hygiene_check.py`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "opportunities_are_derived_from_evidence_and_rule_mappings or content_diagnostics_blocks_until_vendor_read_when_no_content_evidence" --maxfail=3`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "actions_api_drops_legacy_content_review_audit_terms or content_refresh_empty_state_uses_operator_source_language" --maxfail=3`
- `rtk pnpm --dir apps/dashboard exec playwright test e2e/dashboard-api.spec.ts --workers=1 --grep "command center|ads doctor|seo and content"`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "content route renders condensed selected decision with expandable detail" --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "operator_label_fallbacks_do_not_humanize_raw_unknown_enums" --maxfail=3`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "workflow_label_fallbacks_do_not_expose_raw_values or workflows_are_decision_backed_operator_contracts" --maxfail=3`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "operator_label_fallbacks_do_not_humanize_raw_unknown_enums or content_action_preview or marketing_tactical_queue_keeps_exact_wordpress_url_matches_after_inventory_noise" --maxfail=3`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/StatusBadgeUsage.test.ts src/routes/KnowledgePanels.test.tsx src/routes/ActionObjectPanels.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk pnpm --dir apps/dashboard exec playwright test e2e/dashboard-api.spec.ts --workers=1 --grep "ga4|merchant|knowledge|action"`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "google_ads_oauth_repair_action_is_explicit_and_redacted or merchant_blocked_feed_section_uses_operator_read_wording" --maxfail=3`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics_exposes_live_campaign_metric_facts or codex_context_pack_scopes_ads_doctor_payload" --maxfail=3`

Detailed historical proof belongs in git commits and `.local-lab/proof/`
artifacts, not in this recovery ledger.
