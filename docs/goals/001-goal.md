# Goal 001 - WILQ Clean Product Semantics And Marketer Cockpit

Status: active

Date: 2026-06-25

## Objective

Clean WILQ's active product semantics and marketer-facing surfaces before
building the next product layer.

WILQ must become a clean API-first Marketing Operating System for Ekologus,
with reusable core architecture prepared for future client workspaces.

## Identity

- WILQ = system/product.
- Wilku = human marketer/operator persona.
- Ekologus = first depth-first workspace/client.
- `ekologus.pl` = public canonical content home.
- `sklep.ekologus.pl` = product/shop source where relevant.
- Dev preview host = optional design/staging preview only when explicitly
  configured by the owner.

## Current Correction

The previous plan over-weighted the dev host and created migration/mapping
language that does not match the real product model.

Required correction:

- Do not treat the dev host as a content source, final URL, canonical URL,
  migration target or default blocker.
- Do not preserve stale dev-preview or migration-era content fields as
  compatibility strategy.
- Migrate touched active consumers directly to:
  `source_public_url`, `final_canonical_url`, `intended_final_url`,
  nullable `preview_url`.
- Existing Ekologus content is preserve-first.
- Redesign does not imply rewrite.

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
- No React string replacement as product cleanup.
- No route-local translators, legacy label dictionaries or hardcoded copy
  patchers.
- Dirty marketer-facing copy must be fixed in typed API/schema/view-model/domain
  source.
- Local runtime must be started, checked and recovered through
  `scripts/local_stack.sh start|status|restart|logs`, not ad hoc detached API
  or dashboard processes.

## Marketer-Facing Language

Use plain Polish.

Allowed visible language examples:

- akcja do sprawdzenia
- sprawdzenie w WILQ
- podgląd zmian
- zapis zmian
- zatwierdzenie zmian
- blokada
- dowody
- źródła danych
- co zrobić dalej
- czego nie wolno obiecać

Forbidden visible language examples:

- kandydat zmiany
- payload
- legacy English preview wording
- raw technical execution wording
- wykonanie zmian
- tylko do sprawdzenia
- legacy dev-preview placement wording
- migration-map wording
- mapping-review wording

Internal type names may remain only where renaming would require a separate
schema/API migration and the name is not exposed to the marketer.

## Workstreams

### A. Recovery And Audit

Tasks:

- Run `rtk git status --branch --short`.
- Run recent logs and repo searches listed in `PLAN.md`.
- Classify every stale hit as active behavior, stale fixture, obsolete artifact,
  archive-only history, safe internal technical type or owner blocker.

Done when:

- Current `PLAN.md`, this file and `docs/PROGRESS.md` describe the same active
  direction.

### B. Active Contract Cleanup

Tasks:

- Remove stale dev-preview/migration fields from active content diagnostics,
  action previews, context packs, skill smokes and tests.
- Ensure the dev URL cannot become final canonical URL.
- Ensure dev/design preview is not required for preserve/refresh/merge.
- Remove old technical language from domain/action summaries.
- Add focused tests and skill smoke checks for removed fields and terms.

Done when:

- Active API/skill/dashboard paths no longer expose stale content fields or
  forbidden marketer-facing terms.

Latest slice:

- GA4 readiness labels now come from the WILQ API/shared schema, not from
  route-local read-contract mapping. `/ga4` renders condensed API metric tiles
  and hides raw GA4 metric fact names from decision cards; browser proof found
  no `landing page`, `Landing:`, `message match`, `key events`,
  `ecommerce_purchases`, `engagement`, raw action ID, `payload` or
  `ActionObject` hits in the rendered GA4 text.
- Dashboard status chips now expose readable separators in text/browser output.
  Browser proof across Command Center, Merchant, Content Planner, Ads Doctor,
  GA4, Localo and Ahrefs found no collapsed status strings like `brakuje
  dostępudane` or `gotoweniskie`.
- Custom Segments and Keyword Planner wording now uses API-owned Polish labels
  and source summaries for preview member type, review gates, blocked promises
  and blocked Keyword Planner access. Browser proof for
  `/ads-doctor/custom-segments` is stored under
  `.local-lab/proof/20260627-custom-segments-api-labels/browser/`.
- Demand Gen readiness wording now uses API-owned Polish labels and source
  metrics for channel labels, review gates, missing-data labels and blocked
  promises. The `/ads-doctor/demand-gen` browser proof confirms no raw action
  IDs, raw read-contract keys, `DG rows`, `asset`, `payload` or `ActionObject`
  text on the marketer surface:
  `.local-lab/proof/20260627-demand-gen-api-labels/browser/demand-gen-body.txt`.
- GA4 expanded action preview now uses API-owned metric snapshot labels from
  the action payload and context pack. The expanded `/ga4` panel shows Polish
  metric labels such as `aktywni użytkownicy`, `zakupy e-commerce`,
  `zaangażowanie` and `zdarzenia kluczowe`, with no raw GA4 metric names in the
  marketer-facing scan. Proof:
  `.local-lab/proof/20260627-ga4-preview-snapshot-labels/`.
- Merchant decision labels, issue cluster labels, product-row problem labels
  and operator-summary source labels now come from the WILQ API/domain
  contract. The expanded `/merchant` browser scan found no active hits for raw
  Merchant vendor values or internal queue keys such as `landing_page_error`,
  `n:link`, `SHOPPING_ADS`, `MERCHANT_ACTION`, `decision_queue`,
  `issue_clusters` or `reported_issue_occurrences`. Proof:
  `.local-lab/proof/20260627-merchant-expanded-audit/merchant-expanded-final.txt`.
- Ahrefs decision type labels, allowed evidence labels, missing-data labels,
  review-gate labels, metric labels and gap-record labels now come from the
  WILQ API/shared schema. `/ahrefs` no longer uses React label dictionaries for
  active Ahrefs enum values, and browser proof found no `domain_rating=`,
  `ahrefs_rank=`, `status=completed`, `rows=`, `mode=subdomains`,
  `content_gap`, `organic_keyword_gap`, `top_page_gap`, `backlink_gap`,
  `competitor_page`, `Ahrefs Rank` or `DR` hits:
  `.local-lab/proof/20260627-ahrefs-api-labels/ahrefs-rendered-final.txt`.
- Content Planner active copy now says `plan treści` instead of visible
  `brief` wording. The cleanup was made in API/action source strings and the
  route copy, not through a route-local translator. After managed stack restart,
  API health, live contract smoke, content skill smoke and `/content-planner`
  browser proof pass; the rendered view has no `Brief`, `Przygotuj brief`,
  `Podgląd briefów`, `Pokaż briefy` or `Zapisz sprawdzenie briefu` hits:
  `.local-lab/proof/20260627-content-plan-language/content-planner-final.txt`.
- Action Detail content preview copy now matches the same language:
  `Plan treści do sprawdzenia` and `Cel planu treści`. The old headings are
  blocked by `scripts/marketer_language_guard.py`, and browser proof for
  `/actions/act_prepare_content_refresh_queue` confirms the new wording with
  no old `Brief treści do sprawdzenia`, `Cel briefu` or `Przygotuj brief` hits:
  `.local-lab/proof/20260627-action-detail-content-plan-language/action-detail-content.txt`.
- Generic operating route copy now avoids endpoint/type jargon in visible
  fallback descriptions. `BriefWorkflowSurface` configs no longer expose
  `/api/marketing/brief`, `MarketingBrief`, `spend` or `inventory`; focused
  tests cover the config, and browser proof for `/social-publisher` confirms
  no hits for those terms:
  `.local-lab/proof/20260627-brief-workflow-copy/social-publisher.txt`.
- GA4 and Merchant copy now avoids `mapowanie` as a visible operator label for
  conversion, landing-page and product-state checks. The API/domain source uses
  `powiązanie konwersji`, `sprawdź stronę wejścia` and `powiązane produkty`;
  focused tests and `scripts/marketer_language_guard.py` prevent regression.
  Live API and browser proof:
  `.local-lab/proof/20260627-mapping-language-cleanup/`.
- Action and opportunity detail views now hide raw technical data until the
  operator opens a technical panel. The default surface shows readable action
  previews and API metric tiles; raw payload JSON, metric fact JSON and source
  references are no longer rendered up front. Focused tests cover opportunity
  detail metric summaries and action detail raw-JSON avoidance; browser proof:
  `.local-lab/proof/20260627-technical-details-hidden/`.
- Ads diagnostics source wording now uses Polish exclusion-review language for
  the negative keyword queue. The old `Akcje do sprawdzenia negative keywords`
  title and `search terms` compatibility labels are removed from active
  source; live API proof confirms no old English terms in the Ads diagnostics
  payload:
  `.local-lab/proof/20260627-ads-negative-keyword-language/`.
- Actions route content copy now uses `plan treści` consistently instead of
  old `podgląd briefu` wording. Active skill/eval terms were migrated to
  `podgląd planu treści`, and `scripts/marketer_language_guard.py` blocks the
  old phrases. Browser proof:
  `.local-lab/proof/20260627-actions-content-plan-language/actions.txt`.

### C. Dashboard Condensation

Tasks:

- Keep the core path:
  `/command-center -> /merchant -> /content-planner -> /ads-doctor -> /ga4`.
- Make each touched route selected-first:
  primary decision, why it matters, safe next step, blockers, evidence/source
  summary and measurement plan.
- Move raw traces to technical drawers.
- Verify with route tests, typecheck and `agent-browser`.

Done when:

- Wilku can understand the first screen without knowing internal models.

### D. Content Product Completion

Tasks:

- Add `ContentPreflight`: preserve, refresh, merge, create or block.
- Build Content Inventory v2 over real public content.
- Add duplicate/canonical/cannibalization checks.
- Add `ContentSalesBrief`.
- Add Claim Ledger.
- Require Human Review.
- Add draft-only WordPress handoff.
- Add post-publication measurement loop.

Done when:

- WILQ can safely answer whether to write, preserve, refresh, merge or block a
  content task before generating any draft.

### E. Workspace-Ready Core

Tasks:

- Add typed workspace/profile contracts:
  `ClientWorkspace`, `SiteProfile`, `BrandProfile`, `ServiceMap`,
  `ClaimPolicy`, `ConnectorProfile`, `MeasurementProfile`,
  `KnowledgeNamespace`.
- Move Ekologus-specific service, claim and tone rules out of reusable core.
- Do not build multi-client SaaS yet.

Done when:

- Ekologus still works deeply and core is ready for a future second workspace
  without prompt copy.

### F. Knowledge And Self-Improving Runtime

Tasks:

- Add source registry, freshness, confidence and lineage.
- Convert recurring corrections into rules, tests, eval cases or skill smokes.
- Store feedback from sprawdzenie przez człowieka and measured outcomes as knowledge.
- Keep progress docs pruned and current.

Done when:

- Repeated mistakes become durable checks instead of chat-only corrections.

## Verification

Focused checks:

- `rtk uv run pytest ...` for touched API/action/schema paths.
- `rtk pnpm --dir apps/dashboard test -- ...` for touched dashboard routes.
- `rtk pnpm --dir apps/dashboard typecheck`.
- Relevant skill smoke/eval when skill behavior changes.
- `agent-browser` proof for touched marketer routes.
- `rtk git diff --check`.

Broad checks:

- `rtk scripts/verify.sh` before cross-surface completion claims.

## Completion Definition

Goal 001 is complete when:

- Active docs agree on the corrected product model.
- Active product paths no longer depend on dev-site migration semantics.
- No marketer-facing primary surface shows forbidden technical jargon.
- UI translators/string replacement cleanup helpers are removed.
- Focused API/dashboard/skill checks pass.
- Browser proof verifies touched routes.
- Remaining historical mentions are archived or explicitly tracked as removal
  debt.

The final WILQ Marketing Operating System is not complete until preflight,
sales brief, claim ledger, sprawdzenie przez człowieka, WordPress draft handoff, measurement
loop, workspace profiles, knowledge lifecycle and safe execution are done.

## Current `/goal`

Use the `/goal` prompt embedded at the end of `PLAN.md`.
