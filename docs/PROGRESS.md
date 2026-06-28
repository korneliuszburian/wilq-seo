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
- Workflow cards now say `Brakujące dane` and `Granice wniosków` instead of
  low-value process jargon, and workflow test fixtures no longer preserve raw
  `queued` / old verdict wording as visible labels.
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
- Recent guardrails cover tactical, Ads, Knowledge, action detail, Content
  Planner and marketer-language presentation contracts.

## Active Findings

1. Keep `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and
   `docs/goals/001-goal.md` short and aligned. History belongs in git and proof
   artifacts.
2. Remove remaining scattered raw fallback paths in knowledge, Content, GA4,
   Localo, Merchant and Ads helper modules by adding API/schema/view-model
   labels.
3. Remove remaining status/risk label-as-value calls in dashboard surfaces when
   the caller can pass both visual state and API label.
4. Add typed contract/vendor-enum label registries outside the already-cleaned
   Ads diagnostics helper path so unknown read contracts and vendor enums do not
   fall back to raw snake_case or English values in marketer-facing copy.
5. Continue moving repeated metric, dimension, source, blocker and evidence
   naming into API/domain labels. Pure numeric formatting can stay in UI.

## Latest Accepted Proof

- `rtk uv run pytest tests/test_api_contracts.py -q -k "action_preview or content_action_preview or localo_visibility or merchant_feed_preview" --maxfail=5`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "command_center" --maxfail=3`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionObjectPanels.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/CommandCenterRoute.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "knowledge_operating_map or content_diagnostics or tactical_queue or action_preview or operator_label_fallbacks" --maxfail=3`

Detailed historical proof belongs in git commits and `.local-lab/proof/`
artifacts, not in this recovery ledger.
