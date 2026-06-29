# Goal 001 - Clean Product Semantics And Marketer Cockpit

Status: active

Date: 2026-06-28

## Objective

Clean WILQ's active product semantics and marketer-facing surfaces before
starting the next product layer.

This goal does not finish the full WILQ Marketing Operating System. It makes
the current review cockpit coherent, condensed and usable enough that Wilku can
inspect it without reading technical internals.

## Identity

- WILQ = system/product.
- Wilku = human marketer/operator persona.
- Ekologus = first depth-first workspace/client.
- `ekologus.pl` = public canonical content home.
- Dev preview hosts = optional design/staging context only when explicitly
  configured.

## Product Rules

- No evidence ID -> no recommendation.
- No source connector -> no recommendation.
- No preflight verdict -> no writing.
- No sales brief -> no draft.
- No claim review -> no publish-ready language.
- Brak sprawdzenia przez człowieka -> brak WordPress draft handoff.
- No audit -> no zapis zmian.
- No measurement window -> no success/failure claim.
- No business logic in prompts or skill references.
- No React/UI translator functions, `replaceAll` helpers or route-local
  dictionaries for product semantics.
- No compatibility aliases or deprecated active fields when direct migration is
  feasible.
- Remove stale target/dev/migration semantics from active contracts.
- Dirty marketer-facing copy must be fixed in typed API/schema/view-model/domain
  source.
- Raw IDs may appear in technical panels, audit detail and trace views only.
- Every repeated issue becomes a typed API/schema/view-model field or a test
  guard.

## Current Cleanup Vocabulary

Use `PLAN.md` as the canonical visible-language source.

Preferred visible terms include:

- `Centrum pracy`
- `Treści`
- `Google Ads`
- `akcja do sprawdzenia`
- `podgląd zmian`
- `zapis zmian`
- `zatwierdzenie zmian`
- `blokada`
- `dowody`
- `źródła danych`
- `co zrobić dalej`
- `czego nie wolno obiecać`

Forbidden primary-surface terms include:

- `Command Center`
- `Content Planner`
- `Ads Doctor`
- `payload`
- `evidence IDs`
- `blockery`
- raw connector/debug wording
- legacy dev-preview placement wording
- migration-map or mapping-review wording

Technical route slugs, schema fields, enum values, connector IDs, evidence IDs,
action IDs and audit fields may stay in technical contracts or drawers.

## Current State

- Cleanup has moved many Ads, Merchant, GA4, Localo, Ahrefs, Knowledge,
  tactical queue, Procesy and action-detail labels from dashboard helpers into
  API/domain/shared-schema fields.
- Touched primary surfaces avoid raw trace IDs, endpoint names, raw enum keys,
  stale dev-site placement language and English validation wording in normal
  copy.
- Content active semantics use public/final URL wording; dev-preview placement
  is not active product logic.
- Action-detail normal preview uses typed API preview cards; raw payloads stay
  behind technical detail.
- Action-detail review gates use API/domain blocker summary labels in normal
  panels. Full blocker lists stay in technical detail.
- Action-detail effect checks use plain before/after comparison wording from
  API/domain labels, including historical stored summaries.
- Impact-check label handling no longer rewrites old window wording with
  string replacement; historical summaries are normalized through typed
  prefix labels.
- Raw historical audit details are sanitized by a generic raw-contract guard.
  Legacy raw review events remain visible only as neutral history and do not
  unlock review gates.
- Content, Merchant, Ads and Localo normal route copy avoids technical-evidence
  wording such as `dowody techniczne`, `techniczne warunki akcji` and
  `techniczne potwierdzenie`. Technical detail drawers remain allowed.
- Codex skill eval cases and harness no longer require old working route names,
  English evidence wording or action-model jargon in operator-facing output.
  The harness now fails final operator-facing JSON values that reintroduce
  those terms.
- Daily and content-strategist context-pack tests now scan string values for
  old working route names, stale content URL terms and technical jargon.
- Daily context-pack metric facts now use API/schema-owned `metric_label`,
  `dimension_labels` and `dimension_value_labels`, so Codex skills do not get
  raw metric keys or raw vendor dimension enums in compact top metric facts.
- Marketer-useful free-text metric dimensions now stay useful in compact
  context where safe: GSC queries, GA4 source/campaign/landing-page values and
  country labels do not collapse to generic placeholder copy.
- Compact Codex skill context active actions now omit raw action payloads,
  payload key lists, payload-preview field names and raw apply-blocker keys.
  Skills get typed preview cards, Polish blocker labels and
  `/api/actions/{action_id}` for drilldown.
- Compact Codex skill context also strips raw Ahrefs read-contract keys,
  raw Ahrefs metric-label dictionary keys, raw Merchant preview-card IDs and
  raw Merchant issue-type values. Live daily, content, Merchant, Ads, GA4,
  Localo and Ahrefs context-pack scans are clean for the guarded terms.
- `scripts/context_pack_language_guard.py` now makes the live context-pack scan
  repeatable. `scripts/verify.sh` runs it against the temporary skill API, and
  `scripts/pre_demo_gate.sh` runs it against the managed local API before
  dashboard/skill demo checks.
- On 2026-06-29T00:20-00:43Z, GSC, GA4, Merchant, Google Ads, Ahrefs, Localo,
  WordPress ekologus.pl and WordPress sklep.ekologus.pl refreshed live with
  `vendor_data_collected=true`, and `/api/connectors` reported every configured
  first-party/source connector as fresh. LinkedIn and Facebook remain
  missing-credential optional social connectors; Google Sheets remains disabled
  by current scope. Google Ads Keyword Planner remains blocked by
  developer-token approval, not missing OAuth credentials.
- Active skill interface names, prompts and response contracts now use Polish
  operator wording instead of old English working names, raw proof-ID wording
  or blocker phrasing. The marketer language guard now fails that class of
  phrases in active skill/docs/test contracts.
- Active actions with operator preview payloads now have a focused guard that
  requires typed preview cards, so new preview payloads do not fall back to raw
  shape-derived rows.
- Expanded DOM/browser audit across core marketer routes and action details is
  clean for old route names, stale content URL terms and technical action-model
  jargon outside technical drawers. Fresh `agent-browser` proof on 2026-06-29
  covered `command-center`, `merchant`, `content-planner`, `ads-doctor`, `ga4`,
  `localo`, `ahrefs`, `knowledge`, `actions` and `workflows`.
- Treści selected-decision and preview panels use API-owned view-models
  instead of parsing raw action payload shape.
- Treści loading/error action fallback uses the API-owned action summary label
  instead of assembling action-count copy from action IDs.
- Treści preflight, summary, decision, proof and action panels use API/domain
  evidence and action summary labels instead of route-local count formatting.
- GA4 overview, decision and proof panels use API/domain evidence and action
  summary labels instead of route-local count formatting.
- Google Ads first-screen, condensed decision, proof and action panels use
  API/domain evidence and action summary labels instead of route-local count
  formatting.
- Google Ads and GA4 diagnostics expose top-level API-owned
  `source_connector_labels`, and touched proof panels use those labels instead
  of reconstructing source labels from nested route data.
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
- WordPress handoff action review gates use operator-safe check keys and labels;
  normal `/actions` proof no longer exposes technical checklist jargon.
- Merchant overview, operator summary, decision, proof and action panels use
  API/domain evidence and action summary labels instead of route-local count
  formatting.
- Merchant feed summaries, product-sample next steps and blocked-claim labels
  use API/domain Polish wording; fresh `/merchant` proof no longer exposes raw
  Merchant metric keys, vendor endpoint names, action IDs or generic Merchant
  fallback labels in normal copy.
- Ahrefs decision and gap-contract panels use API/domain evidence and action
  summary labels instead of route-local count formatting.
- Ahrefs gap-contract metric tiles use API/domain missing-data and
  blocked-claim summary labels instead of route-local count formatting.
- Custom Segments candidate, forecast and proof panels use API/domain evidence
  and action summary labels instead of route-local count formatting.
- Custom Segments validation tiles use API/domain missing-data and
  required-check summary labels instead of route-local count formatting.
- Localo top metric tiles use API/domain missing-data summary labels instead
  of route-local count formatting.
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
- Google Ads full-review optimizer, strategy-readiness, change-impact,
  campaign-triage and recommendation panels use API/domain summary labels for
  missing data, required checks and blocked claims instead of rendering long
  review/blocker arrays. Change-impact copy uses plain before/after comparison
  wording instead of old technical result-window wording.
- Connector settings cards use API/domain credential summary labels instead of
  route-local credential/source count formatting.
- Merchant issue-cluster cards and decision summaries use API/domain reported
  issue summary labels instead of route-local issue count formatting or broken
  Polish count forms.
- Treści expanded decision and Ahrefs review cards use API labels or neutral
  Polish operator fallbacks instead of visible raw enum/status keys.
- Knowledge details use API-owned source labels and Polish count forms.
- Knowledge seed cards use Polish marketer-facing summaries instead of English
  wording about evidence identifiers.
- Dashboard API smoke and demo proof no longer require stale proof language such
  as raw Merchant issue keys, raw proof IDs in normal demo flow, `audience size`,
  `launchu`, `DR`, `brak facts` or `competitor_page`.
- Dashboard API smoke includes a shared runtime visible-copy guard over `main`,
  so core routes fail if old working route names, registry headings, stale
  URL/mapping terms, raw `payload` wording or vendor fallback keys return to
  the visible marketer surface.
- The old `Goal 002` draft is archived under `docs/goals/archive/`, and the
  marketer language guard now prevents additional first-level active goal files
  beside `docs/goals/001-goal.md`.
- Knowledge first-screen decision and card summaries use API/domain source,
  action, evidence, knowledge and lineage summary labels.
- Knowledge playbook cards use API/domain evidence and action-type summary
  labels instead of route-local Polish count formatting.
- Knowledge decision cards use API/domain blocked-claim summary labels instead
  of joining blocked-claim arrays or falling back to raw counts in React.
- Knowledge decision-impact panels use API/domain missing-data,
  blocked-decision and blocked-claim summary labels. First-screen
  blocked-claim copy is condensed to count summaries, while full claim lists
  stay in details.
- Procesy cards and run summaries use API/domain summary labels and no longer
  block fresh `/workflows` loads on hidden related-action data.
- Procesy expanded details use API/domain missing-data detail labels and
  condensed blocked-claim summaries instead of route-local label joins.
- Szanse cards use API/domain summary labels for evidence, sources, related
  actions and knowledge references instead of route-local raw counts.
- Shared status, route, source, metric, risk, blocker and preview labels are
  increasingly centralized in API/domain helpers.
- Connector refresh runs hydrate Polish status labels at the shared schema
  boundary; fresh GSC, GA4 and Merchant reads on 2026-06-29 completed with
  vendor data collected.
- Connector status now reuses the latest successful vendor read for freshness
  and `last_success_at`. GSC, GA4 and Merchant live refreshes on
  2026-06-29T00:20-00:22Z completed with `vendor_data_collected=true`.
  Merchant refresh retries transient `ReadTimeout` responses after a live
  `aggregateProductStatuses` timeout was reproduced.
- Broad cleanup verification passed with `rtk scripts/verify.sh` after the
  current action-context/dashboard/API cleanup slice. Live `/api/connectors`
  confirms GSC, GA4 and Merchant are configured, fresh and not missing
  credential names after the 2026-06-29T02:30Z refreshes. LinkedIn/Facebook
  remain optional missing-credential social connectors; Google Sheets remains
  disabled by scope.
- Live UAT packet export is prepared for real marketer review and uses Polish
  operator snapshot fields instead of raw `decision_type`, `status`,
  route-check or URL-contract keys. This prepares the required UAT step but
  does not count as completed UAT.
- Durable UAT handoff lives at
  `docs/handoffs/2026-06-29-marketer-uat-ready.md`. Goal 001 still needs a
  filled real marketer UAT result or explicit owner defer before completion can
  be claimed.
- Completion proof is machine-guarded by
  `scripts/goal_001_completion_check.py`. Without `--uat-result` or
  `--owner-defer`, the expected status is `blocked_missing_uat_proof`.
- Daily context-pack connector status uses API-owned Polish status and
  freshness labels, includes the latest successful read time where available,
  and no longer exposes empty freshness labels or `status configured`
  summaries to Codex skills.
- Connector status objects hydrate Polish `status_label` values at the shared
  backend schema boundary, and Treści diagnostics expose API-owned
  `live_data_status_label` for GSC/WordPress readiness.
- Metric facts hydrate Polish `metric_label` values at the shared backend
  schema boundary, and live contract smoke now prevents empty or raw snake_case
  metric labels from returning in metric fact contracts.
- Compact context-pack metric facts use those labels and no longer expose raw
  metric names or vendor dimension enums when Polish operator labels exist.
- Metric dimension value labels preserve useful free-text query/source/page
  context where safe instead of over-condensing everything to a placeholder.
- Google Ads campaign rows hydrate Polish campaign status and channel labels at
  the shared backend schema boundary, and live contract smoke now prevents empty
  or raw visible `*_label` fields in checked API payloads.
- Current proof artifacts live in `.local-lab/proof/`; detailed implementation
  history lives in git commits, not in this file.

## Active Findings

Use these as the next work queue. Do not start future product layers until these
are resolved or explicitly deferred.

1. Keep `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and this file short and
   aligned.
2. Continue raw fallback cleanup in active API/helper modules. Any new visible
   raw fallback must be fixed at typed API/schema/view-model source.
3. Continue typed contract/vendor-enum label registries outside the already
   cleaned Ads campaign status/channel path so unknown read contracts and vendor
   enums do not fall back to raw snake_case or English values in marketer-facing
   copy.
4. Continue moving repeated metric, dimension, source, blocker and evidence
   naming into API/domain labels. Pure numeric formatting can stay in UI.
   Latest done slice: compact daily context-pack metric facts now consume
   `MetricFact.metric_label`, `dimension_labels` and `dimension_value_labels`
   instead of raw metric keys or vendor dimension enums, while preserving useful
   free-text query/source/page values where safe. Compact skill active-action
   contexts now also use typed preview cards and Polish blocker labels instead
   of raw payload bodies, payload key lists or raw apply-blocker keys.
5. Dashboard still needs focused cleanup for any newly found content/ads
   payload-derived panels. Active actions with operator preview payloads now
   have typed-preview-card coverage. Action validation errors for Ads, GA4 and
   Localo now return Polish operator copy from source validators, with focused
   regression coverage for forbidden technical fragments.
6. Remaining active `replace("_", " ")` scan hits are Merchant attribute-key
   normalizers used for equality matching, not visible operator labels.
7. Continue checking compacted context-packs after dashboard/API cleanup. Daily
   and content-strategist context packs have focused tests, and
   `scripts/context_pack_language_guard.py` now guards live compact skill
   contexts across the core skill set in both `verify.sh` and the pre-demo
   gate.
8. Continue focused browser audits when touched routes change or a new visible
   copy risk is found. The latest expanded audit across core routes/action
   details is clean; any future long blocker/review list must be condensed at
   API/domain source, not trimmed in React.
9. Real marketer UAT is still required for usefulness claims unless explicitly
   deferred by the owner. Use
   `docs/handoffs/2026-06-29-marketer-uat-ready.md` as the current handoff.
   Guard command:
   `rtk uv run python scripts/goal_001_completion_check.py --format markdown`.

## Execution Policy

- Use `rtk` before every shell command.
- Use `scripts/local_stack.sh start|status|logs|restart|stop` for the local
  WILQ API/dashboard runtime; do not hand-roll detached API or dashboard
  processes.
- Inspect existing implementation before editing.
- Prefer small verified slices and conventional commits.
- Use subagents for parallel read-only audits or disjoint write scopes.
- Do not let multiple workers edit the same files without explicit ownership.
- After each slice:
  - run focused tests,
  - capture browser/API proof when a marketer route changes,
  - update only current recovery facts,
  - commit and push a coherent green slice.

## Verification

Focused checks:

- Docs-only: `rtk git diff --check`.
- API/schema/action: focused `rtk uv run pytest ...`.
- Dashboard: touched route test plus `rtk pnpm --dir apps/dashboard typecheck`.
- Skill changes: deterministic smoke and targeted eval.
- Marketer copy: `rtk uv run python scripts/marketer_language_guard.py`.
- Browser: `agent-browser` proof for touched marketer routes.

Broad checks:

- `rtk scripts/verify.sh` before cross-surface completion claims.

## Completion Definition

Goal 001 is complete when:

- Active docs agree on the corrected product model and cleaned language.
- Active product paths no longer depend on dev-site migration semantics.
- Primary marketer surfaces no longer show forbidden technical jargon.
- UI translators/string replacement cleanup helpers are removed or proven
  out-of-scope internal utilities.
- Deprecated active fields and compatibility aliases are removed where direct
  migration is feasible.
- Focused API/dashboard/skill checks pass for all touched slices.
- Browser proof verifies touched marketer routes.
- Remaining historical mentions are archived or explicitly tracked as removal
  debt.
- Real marketer UAT is captured or explicitly deferred by the owner.

The final WILQ Marketing Operating System remains a later goal. It still
requires ContentPreflight, sales brief, claim ledger, sprawdzenie przez
człowieka, WordPress draft handoff, measurement loop, workspace profiles,
knowledge lifecycle and safe execution gates.
