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
- Active actions with operator preview payloads now have a focused guard that
  requires typed preview cards, so new preview payloads do not fall back to raw
  shape-derived rows.
- Expanded DOM audit across core marketer routes and action details is clean
  for old route names, stale content URL terms and technical action-model
  jargon outside technical drawers.
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
  boundary; fresh GSC, GA4 and Merchant reads on 2026-06-28 completed with
  vendor data collected.
- Current proof artifacts live in `.local-lab/proof/`; detailed implementation
  history lives in git commits, not in this file.

## Active Findings

Use these as the next work queue. Do not start future product layers until these
are resolved or explicitly deferred.

1. Keep `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and this file short and
   aligned.
2. Continue raw fallback cleanup in active API/helper modules. Any new visible
   raw fallback must be fixed at typed API/schema/view-model source.
3. Add typed contract/vendor-enum label registries outside the already-cleaned
   Ads diagnostics helper path so unknown read contracts and vendor enums do not
   fall back to raw snake_case or English values in marketer-facing copy.
4. Continue moving repeated metric, dimension, source, blocker and evidence
   naming into API/domain labels. Pure numeric formatting can stay in UI.
5. Dashboard still needs focused cleanup for any newly found content/ads
   payload-derived panels. Active actions with operator preview payloads now
   have typed-preview-card coverage.
6. Remaining active `replace("_", " ")` scan hits are Merchant attribute-key
   normalizers used for equality matching, not visible operator labels.
7. Continue checking compacted context-packs after dashboard/API cleanup. Daily
   and content-strategist context packs now have string-value guards; extend
   the same pattern when another skill context changes.
8. Continue focused browser audits when touched routes change or a new visible
   copy risk is found. The latest expanded audit across core routes/action
   details is clean; any future long blocker/review list must be condensed at
   API/domain source, not trimmed in React.
9. Real marketer UAT is still required for usefulness claims unless explicitly
   deferred by the owner.

## Execution Policy

- Use `rtk` before every shell command.
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
