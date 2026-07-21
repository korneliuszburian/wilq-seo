# Dashboard State

Last updated: 2026-07-21

This is the living state file for WILQ dashboard work. Read it before changing
any dashboard route, dashboard API view-model, dashboard copy, dashboard test or
dashboard screenshot task.

Do not treat this file as a historical audit. Replace rows when the state
changes. Historical roasts, screenshots and Beads may explain why a decision was
made, but this file is the current operating map.

## Rules

- One screen is useful only when a non-technical marketer can answer in 30
  seconds: what happened, why it matters, what proof exists, what is blocked and
  what to do next.
- Scores from WILQ's own deterministic evals or Codex self-review are not
  objective proof. They are smoke signals. Real readiness needs current API
  state, rendered screenshot and ideally a neutral second opinion.
- Do not create a new endpoint if an existing API surface already exposes the
  needed facts. First check the `API source` column and `apps/dashboard/src/lib/api.ts`.
- Do not keep returning to a screen that is already good enough unless a current
  screenshot or API change proves it regressed.
- Technical IDs, payloads, contracts, raw ActionObject details, evidence IDs and
  schema mechanics stay below the fold unless they directly explain a blocker.
- Dev/staging WordPress is not canonical SEO evidence. Production/public
  `ekologus.pl` and `sklep.ekologus.pl` are evidence and inventory sources;
  `ekologus.dev.proudsite.pl` is the safe workspace for draft/ACF/page-building
  work when access exists.

## Current Priority

Live fixed point (2026-07-21): BDO has a persisted full v2 revision
`content_revision_19eb47b728954d319fdaae40dda52adc` with 6 sections, 3 FAQ
items, 2 CTA blocks and one internal link. After explicit vendor-write
authority, the canonical ActionObject chain completed preview → review →
confirm → impact → apply and created exactly one new WordPress draft,
`post_id=1279`, with `status=draft`, title `BDO – co musi wiedzieć
przedsiębiorca?` and 601 words on the dev target. Readback confirmed the
draft. `publish_allowed=false` and `destructive_update_allowed=false` remain
true in the execution boundary; meta fields stay `review_required` because
the WordPress SEO/ACF mapping is not confirmed. This is a real draft proof,
not publication, UAT or a 10/10 claim.

The apply boundary now reconstructs the proposal by the immutable revision's
exact planning digest instead of rebuilding today's planner and accidentally
selecting a newer stale proposal. Missing or mismatched bindings still fail
before any vendor call. The generic action payload distinguishes forbidden
outputs (publish/update/delete) from an unavailable adapter, so draft-only
apply can pass readiness without weakening those safety boundaries.

The snapshot route uses the same revision-bound proposal lookup. After a
current inventory digest changes, a marketer still sees the reviewed draft's
`Szkic na devie` step and section navigator rather than being sent back to
`Zakres i cel`; current-plan drift is shown as lineage context, not as loss of
the exact reviewable revision. Browser proof is retained at
`.local-lab/proof/dashboard-content-workflow/2026-07-21/bdo-after-draft-apply-fixed-point.png`.
The marketer hero now derives its WordPress status from the active operator
step instead of the stale queue label; a ready exact revision reads
`WordPress · gotowy szkic na devie`. Desktop and mobile proof for this copy is
at `.local-lab/proof/dashboard-content-workflow/2026-07-21/bdo-status-copy-fixed.png`
and `bdo-status-copy-fixed-mobile.png`; the mobile viewport has no horizontal
overflow.
The same browser session can switch the active page from BDO to the exact
outsourcing work item through the API-owned selector; after the detail read
settles it shows the outsourcing service, its exact metrics and the same
`Szkic na devie` handoff state. Proof:
`.local-lab/proof/dashboard-content-workflow/2026-07-21/outsourcing-selection-after-bdo.png`.
The handoff context check allows a generated v2 section map to rewrite/merge
the baseline while retaining exact planning/service/package bindings; v1 keeps
the stricter section identity check. Deterministic review is `needs_changes`
only for the source-brief signal, so this is a usable dev demo, not production
approval or a 10/10 content claim.

The dev target projection was tightened on the same fixed point: when the dev
REST profile has no page with the selected public path, the dashboard now shows
`Cel dev · brak exact celu` and does not borrow the first unrelated ACF page.
The existing dev profile remains available as a target selector, while
`Szkic na devie` continues to mean the separate revision-bound draft action.
Focused target proof is 3/3, dashboard typecheck passes, and live desktop/mobile
browser proof shows no horizontal overflow.

The scope step distinguishes an accepted page/service decision from an
unresolved source brief: `źródła briefu wymagają review` is not a request to
map sections manually or select the service again. The distinction is exposed
by the API-owned operator-step label and a focused journey falsifier.
Recommended service candidates are now display-only until the marketer
explicitly chooses one; a prior choice is restored only when the API marks
`service_selection_confirmed=true`.

The second exact pilot is also now a real draft proof. For
`content_work_item_content_decision_https___www_ekologus_pl_oferta_doradztwo_i_outsourcing_ekologiczny`, proposal v7
(`content_planning_proposal_3d3fd007acbb4a75b468cb623a4ed1f8`) and revision v2
`content_revision_40a81d365e294d9e9ffcdd6e71da8eb3` were bound to planning
digest `dcd0db9d5254685fc1e3c7ccadf2a30c7dea285182975887241afd16355bb43d`.
The exact ActionObject chain completed and created WordPress `post_id=1280`;
independent readback confirmed `status=draft`, title `Doradztwo i outsourcing
ekologiczny dla firm` and 542 words. The dashboard now shows `Szkic na devie`
and the selected section navigator for this case as well:
`.local-lab/proof/dashboard-content-workflow/2026-07-21/outsourcing-after-draft-apply.png`.
The write remains draft-only (`publish_allowed=false`,
`destructive_update_allowed=false`), and meta mapping is still an explicit
human review blocker. Semantic review storage remains inactive, so neither
pilot is presented as a semantic PASS, publication or marketer UAT.

The semantic schema fixed point now normalizes every Pydantic object property
to the Codex app-server's required-property contract. On an isolated copy of
the local SQLite/DuckDB pair (not the main state), the exact BDO revision
produced a persisted advisory review with all 9 dimensions and 3 findings
(2 medium, 1 low); readback returned `ready` with the same revision digest.
The same isolated run for outsourcing also returned 9 dimensions and 3
findings (1 high, 2 medium) with exact-digest readback. Those findings remain
instructions for selected-section child revisions, not approval.
The proof is `.local-lab/proof/semantic-review/2026-07-21/bdo-temp-storage-proof.json`.
This proves the model/store seam, not main-state activation or semantic PASS;
the maintenance-window gate remains open.

Selected inventory snapshots now rebuild the compact candidate inventory from
the fresh selected binding instead of reusing a stale diagnostics queue row.
This keeps the marketer's section count, ACF/the_content status and headings
aligned with the preflight read when a WordPress page changes between queue
load and workflow open.

The journey context now uses the full snapshot's fresh WordPress section count
for its visible “Pomiar i struktura” card before consulting the compact queue
projection. This prevents a stale queue count (for example, 1) from
contradicting the exact selected-page inventory (for example, 7 headings) on
the same screen. The fallback remains available only when preflight has no
numeric count.
The same card now keeps a confirmed structure in the fact tone even when GA4 is
missing; the missing exact GA4 read remains a separate blocker below instead of
making a known WordPress structure look untrusted.

Fresh fixed-point proof (2026-07-21) is retained at
`.local-lab/proof/dashboard-content-workflow/2026-07-21/bdo-section-count-metric-fixed.png`.
The focused helper (2 tests) and dashboard typecheck pass. The bounded
second-opinion checker is valid at
`/home/krn/coding/krn/second-opinion-review/wilq-seo/check/2026-07-20-fresh-inventory-count-QWGNTz/`;
its medium findings are classified as evidence gaps caused by omitted source
excerpts, not as demonstrated product defects.
The follow-up tone fixed point has a valid checker at
`/home/krn/coding/krn/second-opinion-review/wilq-seo/check/2026-07-20-structure-vs-ga4-tone-6Xdy5D/`;
all findings are LOW confirmations/evidence gaps and no product defect was
proven.

The review step now translates the storage activation blocker into marketer
language: automatic checking is temporarily unavailable, while reading the
exact text, checking sources and recording a human decision remain available.
The maintenance/storage detail is kept as the safe next technical step rather
than exposed as the primary button label.
The bounded checker for this copy is valid at
`/home/krn/coding/krn/second-opinion-review/wilq-seo/check/2026-07-20-semantic-review-blocker-copy-v3-JfkeDr/`;
its medium/low items are evidence gaps from omitted JSX excerpts, not proven
product defects.

The five-step task map now uses a compact five-column layout on mobile rather
than forcing 144px cards into a clipped horizontal strip. All five stages are
visible at 390px, with full status retained in the accessible labels; desktop
keeps the expanded labels and status text.
The mobile fixed point's checker is valid at
`/home/krn/coding/krn/second-opinion-review/wilq-seo/check/2026-07-20-mobile-task-map-lWVzsh/`;
its LOW items are coverage suggestions only. No product defect or UAT claim is
made from the 390px proof.
The section-navigation copy fixed point has a valid checker at
`/home/krn/coding/krn/second-opinion-review/wilq-seo/check/2026-07-20-section-navigation-copy-BWf4x3/`;
all findings are LOW confirmations or optional coverage follow-ups.

On 2026-07-21 the task-map status labels were made readable at the current
desktop width: step titles and statuses now wrap instead of being silently
truncated. Live proof is in
`.local-lab/proof/dashboard-content-workflow/2026-07-21/task-map-desktop-fixed-full.png`;
the 390px viewport remains free of horizontal overflow.

Section navigation in the text/review stages is explicitly labelled
“Przejdź do sekcji z planu” or “Przejdź do sekcji strony”. It is a navigation
control, not a manual mapping input; the generated section map remains owned by
the API.

Bring one content working surface to a genuinely useful state before spreading
work across the whole dashboard.

Target: `/content-workflow`.

The writing workbench now labels its source from API status at render time:
`ACF/flexible content`, `the_content (główna treść WordPress)` or
`niepotwierdzone`. The marketer-facing heading is neutral (“Plan treści i
mapowanie”); it must not imply ACF sections for a page whose inventory came
from the main WordPress content or a review-required rendered fallback.

Performance check (2026-07-18): the selected inventory queue no longer performs
a synchronous WordPress material read. On a managed-stack restart its first
read returned in 1.08s, then 0.50s/0.18s on subsequent reads; the background
inventory prewarm owns the cold catalog build. The selected queue exposes the
page and its material-read state, while the full snapshot still performs the
exact read-only WordPress/ACF/the_content read independently. The first
viewport must not claim material readiness until that snapshot confirms it.
Earlier measurements after the first optimization and managed-stack restart
were 4.26s for queue and 7.08s for snapshot. `inventory_decision_for_work_item`
now reuses its current
catalog instead of rebuilding the 601-row inventory during material read. The
selected loading state renders candidate title, reason, source count and safe
next step while the snapshot is pending, but the snapshot remains an active P0
optimization target. Secondary authoring/enrichment/activation reads must stay
independent of the first marketer viewport; no GET may invoke Codex or a vendor
write.

`/content-workflow` is the primary "Treści i SEO" marketer workspace. Its
snapshot owns one five-step journey: `scope → section_map → draft → review →
dev_draft`. Every step carries typed phase/readiness, open/submit permissions,
a blocker and the next safe step; React no longer parses Polish status copy.
`section_map` is an API-generated projection of the current plan, inventory and
evidence lineage. It is displayed for transparency but is not a second human
approval gate; while the plan is being generated the current step stays on
`scope`, and once the projection exists the journey advances directly to
`draft`. The operator reviews scope and the resulting exact revision.
Marketer mode renders one compact page/service/decision context, the task map
and exactly one selected workspace. The former queue/action/proof wall mounts
only after an explicit switch to `Audyt techniczny`.
Wybór work itemu jest własnością zwalidowanego URL-a: zmiana historii lub
routera po zamontowaniu widoku przełącza kandydaturę i snapshot bez zachowania
starego lokalnego wyboru React.
Główny selektor pokazuje kolejkę kandydatów; pozostały pełny inventory
WordPress jest dostępny przez rozwijaną wyszukiwarkę tytułu/adresu z limitem
30 wyników, zamiast renderować setki opcji naraz.

The current reviewer estimate is 7.5/10 for the operator workflow, real text
quality remains unscored and exact-version handoff safety remains 8/10. The
review step can now persist an advisory assessment of nine dimensions for the
exact full-document digest. Findings point to stable section IDs; after a human
`needs_changes` decision the writing step highlights those sections, but Wilku
still chooses which ones to send through the existing child-revision seam. It
does not expose a prompt box, approve the child or touch WordPress. Synthetic
proof is not evidence of final text quality.

Read-only Ahrefs and `wordpress_sklep` refreshes on 2026-07-16 restored source
freshness. The selected outsourcing fixed point now has a real persisted v2
revision after dynamic canonical WordPress REST resolution; it includes page
assets, 4 sections, 3 FAQ items, 2 CTA blocks and one internal link, with
`publish_ready=false`. The dynamic planning read builds an exact input digest
for the selected inventory item and binds the service, current public material,
GSC lineage and approved redacted source-material IDs. It does not call Codex or
create a proposal table on GET. The live queue currently exposes 51 candidates
and 50 actionable candidates. When a marketer opens a URL directly, the
lightweight selected-page response is merged with the full queue catalog in the
browser, so the picker never collapses to one preselected page. WILQ must still
not invent topics outside inventory. The remaining semantic-review storage gate is
`storage_activation_required`; it is a maintenance-window concern, not a reason
to pretend that a pre-publication measurement window already exists.
After bounding the first structured plan to 12 sections, 8 FAQ items, 4 CTA
blocks and 4 conditional hypotheses, prior synthetic/knowledge-bound runs
produced unreviewed proposals, but the current managed API no longer exposes
those as the active fixed point. After the app-server provider fix, both exact
pilot reads return `ready` with distinct proposals and `publish_ready=false`;
the plans are generated but still unapproved. The
remaining eight manifest materials stay `import_pending`. A fresh BDO retry
returned `generating` immediately and later failed without partial state. The
2026-07-18 BDO regeneration replaced the stale prior input with digest
`4b6065acaceab7443fa030155a3725a50fd9b5af7cae687f8d59a06e1144f08`; its
old scope and section-map decisions are intentionally not reused. The second exact pilot now resolves the offer URL to
`ekologus_service_environmental_consulting_outsourcing` with source fact
`ekologus_public_consulting_outsourcing_offer_2026_07_01`, even when the page
copy also mentions BDO. Exact canonical URL matching is ranked ahead of broad
copy-term overlap, with a focused regression.
Planning POST is API-owned and non-blocking: it persists an exact queued job
and returns `generating` in tens of milliseconds; the background task builds
the heavy snapshot and Codex turn. GET remains model-free and polls only while
that exact job is active. The current provider disconnect is surfaced as a
typed retry blocker with runtime trace; WILQ writes no partial proposal.
When the last attempt is `failed`, the marketer-facing panel now says
`Spróbuj ponownie` instead of implying a first generation and keeps the exact
runtime run ID in the technical disclosure for support/debugging.
Repeated POST for that exact digest returns `idempotent` immediately; a
mismatched digest returns HTTP 409 `stale_input` before any model call.
Queued jobs older than the 15-minute runtime window are exposed as a typed
retry blocker; the next identical POST atomically replaces the stale queued
row and schedules one fresh background attempt. Concurrent identical POSTs
share the same queued row, so only one returns `queued` and the others read
`generating` without duplicating the Codex turn.
The selected inventory queue now uses a bounded material read for the chosen
URL and fast connector-freshness projection; it does not build the full
diagnostics/action registry. A 30-second URL+evidence cache prevents repeated
WordPress requests on reload, while a changed evidence ID forces a new read.
Managed proof: first selected queue about 2.50s, subsequent reads 0.17–0.19s;
the browser shows the selected material before a deliberately delayed queue
response. The live `the_content`/ACF read remains review-required when it came
from rendered HTML.
The entry screen also reads the API-owned knowledge readiness contract before
planning. A failed readiness fetch is an explicit degraded blocker, loading is
visibly separate from ready, and an empty `next_step` cannot leave the
marketer without a safe action. Local state remains `import_pending` (7 of 15
materials imported), so this is a truthful gate, not generation approval.
The selected-workflow decision disclosure also shows the API-provided source
connector labels and freshness state for displayed metrics. It does not derive
new metrics, infer trends, or claim that a source is applicable when planning
marks it missing or not applicable.

The stale-source action in `/content-workflow` is deliberately page-scoped:
`Sprawdź stronę ponownie` calls the existing bounded inventory-material read for
the selected public URL and invalidates only the content workflow. It does not
launch the global WordPress REST/sitemap refresh, which remains available from
the system source controls. This keeps a marketer's selected-page recovery
bounded even when the full connector inventory takes minutes.

UX audit baseline captured 2026-07-20 for the current marketer surface:
`docs/review-packets/2026-07-20-ux-audit-input/second-opinion/` contains
verified 1440×900 and 390×844 first-view screenshots plus full-page captures for
both BDO and outsourcing. `prompt.md` is the independent second-opinion brief;
the screenshots are baseline evidence, not a claim that the current UI is
finished.
Fixed point `b5c28415` has 202 dashboard tests and typecheck passing. The
independent checker emitted no findings but had source-transport evidence gaps,
so it is not recorded as PASS.
Service Profile is approved-current for the BDO card used by this proof, while
other cards retain their own lifecycle statuses. Exact-page GSC queries remain
visible in scope, while
shared refresh-level evidence no longer pretends that every query supports every
section. The same intent-aware mapper now assigns a query only when one planned
section uniquely answers its intent; ambiguous or uncovered demand remains
`page_only`. Typed `section_mapping_status` distinguishes current
`intent_relevance`, readable legacy `lexical_relevance`, and `page_only`. Live
proof for both pilots shows BDO applicability queries only in the applicability
section, exact general consulting queries only in the general service section,
exact Śląsk demand in the locality section, and unmatched qualifiers—including
Ruda Śląska or unsupported cities—as page-level evidence.
Generated plan scope now also shows its internal-link count. Planning input v3
allows only link directions that resolve to an exact current public WordPress
inventory fact under the same evidence set; the model schema cannot introduce a
different URL. The persisted full-document link keeps placement and lineage in
page preview and the WordPress renderer, while missing inventory remains an
honest zero-link input.
Stateful proof is under
`.local-lab/proof/dashboard-content-workflow/2026-07-15T11-50-52-058Z/`.
The server-side Codex app-server path uses the existing ChatGPT login and full
API-owned model input to create an unreviewed child revision without approval or
vendor write. Browser proof for the new step is under
`.local-lab/proof/dashboard-content-workflow/2026-07-15T19-06-55-670Z/`.
`wilq-seo-r564.14` retired the legacy public Structured Outputs/API-key runtime,
including the additional `draft-variants` leak. OpenAPI now has four bounded,
review-gated content-model entrypoints: dynamic `planning-proposals`, exact
`initial-draft`, exact revision `semantic-review` and exact revision
`codex-proposal`; browser snapshots remain readiness-only and no path can
approve content or write to a vendor.

Architecture proof (2026-07-15):

- The API/store keeps append-only revisions with a server-owned number,
  `base_revision_id`, content digest and full draft-package digest.
- The dashboard saves and restores the exact version after reload. A stale-base
  conflict preserves local edits instead of overwriting newer work.
- Review renders the exact revision content and evidence. Approval requires
  explicit confirmation that both were checked.
- A changed package, canonical URL or evidence set invalidates review and
  rebases the editor onto the current context.
- `dev_draft` receives its action ID and immutable revision binding from the
  API. The dashboard carries that binding through preview, review, confirm,
  impact and apply; it never rebuilds the binding from editable React state.
- Only the active ActionObject stage expands. Ordered same-binding audit events
  support resume; newer bindings, failed stages and typed apply conflicts reset
  or stop later progress without retry.
- The Codex browser proof intercepts the exact proposal POST, exercises pending
  and result states at 1440×900 and 390×844, and proves zero WordPress requests
  plus no horizontal overflow. The older ActionObject proof separately keeps
  WordPress apply synthetic and draft-only.
- Dynamic planning v3 uses one versioned input digest covering the exact page,
  confirmed service, one exact WordPress inventory record, verified internal-link
  candidates, knowledge, source facts and metrics. Its compact summary exposes ten unique
  source assessments with landing tiers and per-connector freshness. Only
  `used` lineage reaches model-authorized evidence; stale or blocked inputs
  return a typed blocker before stale-digest handling. GET is read-only and
  model-free; POST is idempotent, persists the proposal with its exact
  CodexRun, and has no fallback.
- Ads demand now uses the clicked expanded landing from the same 30-day
  search-term row as clicks, impressions, cost, conversions and conversion
  value. The dashboard distinguishes exact, stale, blocked and unmapped Ads;
  stale rows remain diagnostic but are excluded from model-authorized input.
  Raw landing URLs are not returned or persisted by this contract.
## Surface State

Readiness is a product/usefulness estimate, not a test pass rate.

| Surface | Readiness | Current state | API source | Keep / useful | Main slop / blocker | Next move |
| --- | ---: | --- | --- | --- | --- | --- |
| `/command-center` | 70% | Daily priority, blockers and source freshness remain useful. Expired daily-check dependencies no longer make an operator wait for staggered Command Center/GA4/content rebuilds: one background prewarm starts and the existing typed blocker returns in `0.003 s`; full follow-up reads measured `0.018/0.020/0.018 s` with unchanged proof projection. Mobile keeps two blocker/claim details above the fold and exposes exact remaining counts with disclosure instead of silently truncating them. Fresh browser smoke passes 1/1 in 3.2 s. | Existing `GET /api/dashboard/command-center`, `GET /api/marketing/daily-check`, current read caches and `getCommandCenter()`; no new endpoint. | Daily queue, blocked claims, source freshness and honest in-progress state. | Still needs stronger routing into one concrete work item; prewarm never means source refresh or recommendation readiness. | Keep as cockpit; preserve explicit invalidation and typed blocker, then route into content workbench. |
| `/opportunities` | 50% | Useful as registry but overlaps with Command Center and Actions. | `GET /api/opportunities`, `getOpportunities()` | Opportunity list with evidence/action links. | Duplicates "Kolejka" mental model. | Eventually merge into one decision/action queue; avoid new UI work here now. |
| `/content-workflow` | 7.5/10 operator workflow; real text quality still unscored; 8/10 handoff safety | Primary five-step "Treści i SEO" journey carries one exact service and page from dynamic planning through full-document generation, exact advisory review, persisted positive or negative human decision and selected-section child revision. The immutable v2 document includes title/meta/H1/lead, stable sections, FAQ, CTA and internal links. Marketer mode renders the page; GSC and exact clicked-landing Ads metrics are decision inputs, while stale/blocked Ads remain explicitly excluded. Inventory-bound IDs now receive an API-owned queue candidate on demand, so “Rozpocznij workflow” opens the selected page instead of falling back to an empty/error state. WordPress dry-run preserves all page assets and marks SEO meta as explicit human-only until mapping is confirmed. | Existing queue/snapshot and planning seams plus exact `initial-draft`, revision-bound `semantic-review` GET/POST and existing `codex-proposal`, all through the same server-side Codex app-server. Review and terminal run persist atomically; model output never approves or creates an ActionObject. Human review exposes separate `recordable`, `recorded` and `wordpress_handoff_allowed` states. | Knowledge-bound live planning persists both pilot plans with seven redacted approved-material IDs plus current WordPress/GSC lineage. Synthetic approved-card/temp-SQLite proof still covers initial-draft/revision seams. Ads lineage requires a complete same-evidence five-metric batch and clicked landing digest. | The eight remaining manifest materials, rendered WordPress material review, real semantic storage activation (backup + maintenance window), desktop/mobile proof on current state and real Wilku UAT remain open. No live Ads vendor call or vendor write has been made. | Finish owner-review/import gates, then run current bounded desktop/mobile proof and exact full-draft generation; do not claim real text quality, live Ads proof or UAT. |
| `/content-inventory` | 45% | Inventory is now exposed inside `/content-workflow`: 601 read-only WordPress objects, searchable by URL/title/section, with material-source labels and dynamic REST/HTML readback. It is not a separate writing cockpit. | `GET /api/content/inventory/catalog`, `GET /api/content/inventory/material` and `POST /api/content/inventory/bind` read sanitized WordPress material; the dashboard separates recommendation queue from full inventory. | Marketer can see whether an address has content + structure, summary only, structure only, or URL only. Latest managed read refresh projected 113 material-ready, 7 structure-only and 481 URL-only objects; counts remain API-owned and freshness-bound. | Arbitrary inventory binding now exists, but service-card matching, exact analytics projection, knowledge coverage and generation readiness remain separate blockers. | Add typed service/knowledge/metrics readiness before allowing any inventory work item into planning and draft generation. |
| `/service-profile` | 55% | Useful for owner/claim review, not daily writing screen. Its selected-card policy is now projected into the existing content work-item snapshot. | `GET /api/content/service-profile` is the source assembly; `GET /api/content/work-items/{id}/snapshot` projects its compact typed context; no frontend join. | Services, claim policy, source status and review-required data. | Not enough approved-current production depth; can overwhelm writer. | Keep owner review here; preserve the compact work-item projection instead of duplicating a second content view. |
| `/knowledge` | 65% | Admin/review support surface now leads with real Ekologus source facts and the metadata-only manifest of 15 approved-corpus files; operational cards/playbooks are explicitly secondary and remain behind disclosure. The UI calls out `import_pending` instead of presenting the manifest as production knowledge. `list_workflows()` still uses only command-center decisions; the focused browser proof passes 1/1. | `GET /api/knowledge/source-facts`, `GET /api/knowledge/source-materials`, existing `GET /api/knowledge/cards`, `/api/knowledge/playbooks`, `/api/knowledge/operating-map` | Source lineage, generation eligibility and claim review. | The 15 files are metadata-only until controlled redacted excerpt/transcript import and owner review; live source freshness remains separate from cache latency. | Extend the existing private-source review seam for redacted excerpts; never copy raw private material into prompts or mark `import_pending` text as eligible. |
| `/actions` | 75% | Safe action queue renders from a cached/prewarmed existing list seam; after managed restart HTTP reads measured `0.082513 s` and `0.021151 s`. First decision card remains useful while mutation readiness is pending and explicitly keeps write blocked; operation labels wrap without overlap. | `GET /api/actions`, existing action validate/preview/review/confirm/impact endpoints; `list_actions_cached()` lifecycle seam | Review/preview/confirm/audit flow; evidence IDs remain in list response. | Full dashboard-api smoke now asserts current queue, blocker and lifecycle copy; mutation readiness remains separately review-gated. | `c9h9.11` and stale assertion work in `c9h9.8` are closed; do not restore registry IA. |
| `/actions/:id` | 70% | Decision-first detail answers what to do, why, write status, evidence and next safe step. Existing-draft action now has typed current/proposed/blocked preview. Fresh full-page and first-viewport screenshots exist locally. | `GET /api/actions/{id}`, `GET /api/actions/{id}/mutation-readiness`, preview/validate/review/confirm endpoints | Polish decision hero, explicit blocked write, typed preview card, evidence summary; raw payload/audit stay in disclosure. Focused Vitest and Playwright pass. | One below-fold readiness sentence still uses technical `apply-capable ActionObject`; queue performance is separate. | Keep pattern; copy-tune below-fold term later, never bypass safety. |
| `/ads-doctor` | 75% | Existing summary remains evidence-first and cached. Negative-keyword review now emits preview/action only for an exact term + campaign + ad-group match with 90-day evidence; a 30-day-only candidate stays visible as `needs_90_day_review` without a fake action. Live proof has 5 matched review-only previews, all `apply=false`; current browser heading first paint is `1.432 s`. | Existing `GET /api/ads/diagnostics?view=summary`, `build_ads_diagnostics_summary_cached()` and ActionObject validator; no new endpoint. | Fresh Ads data, campaign rows, decisions and safe review actions; no writes or unsupported claims. | Ads conclusions still depend on current source freshness; 90-day evidence permits review, never automatic exclusion or waste/ROAS claims. | Preserve exact 90-day matching, cache invalidation and blocked claims. |
| `/ads-doctor/search-terms` | 10% | Hidden technical placeholder parked behind `/ads-doctor`; the real Ads screen no longer links its primary "Review Ads" row into this route. | Ads diagnostics contracts exist; no standalone marketer queue yet. | Needed later for BDOS-like Ads value. | Not real queue yet. | Keep hidden. Build only after API-owned search-term queue exists. |
| `/ads-doctor/custom-segments` | 65% | Experimental review-only drilldown now consumes existing `GET /api/ads/diagnostics?view=summary`; typed candidate/forecast/keyword-planner fields, evidence and blockers remain available without the full Ads payload. Focused Playwright passes 1/1 in 4.4 s. | Existing Ads summary view; no new endpoint. | Safety model and source-term contract exist; audience size, ROAS and writes remain blocked. | Live Ads freshness can still be stale; the route remains review-only. | `c9h9.10` and stale assertion work in `c9h9.8` are closed; keep summary projection narrow and review-only. |
| `/ads-doctor/demand-gen` | 35% | Experimental readiness surface. | `GET /api/demand-gen/diagnostics` | Good blocker posture. | No campaign/creative depth yet. | Keep hidden/technical. |
| `/ads-doctor/scaling` | 5% | Hidden technical placeholder with safe route back to `/ads-doctor`. | none beyond Ads diagnostics. | None for marketer now. | Empty promise. | Keep parked until strategy, budget and measurement contracts exist. |
| `/ads-doctor/seasonality` | 5% | Hidden technical placeholder with safe route back to `/ads-doctor`. | none beyond Ads diagnostics. | None for marketer now. | Empty promise. | Keep parked until period-comparison contracts exist. |
| `/ads-doctor/recommendations` | 5% | Hidden technical placeholder with safe route back to `/ads-doctor`. | none beyond Ads diagnostics. | None for marketer now. | Empty promise. | Keep parked until API-owned recommendations review queue exists. |
| `/merchant` | 70% | First decision now renders before heavy detail on desktop and mobile: product topic, stale freshness, blocker, next safe step and source status. Managed runtime prewarms a 15 s cached diagnostics view; first HTTP read after restart measured 0.004860 s and second 0.007203 s. | Existing `GET /api/merchant/diagnostics`, `getMerchantDiagnostics()`; cache/clear seam in the existing builder, no new endpoint. | Feed/product issue queue, product blockers, freshness, Polish safe CTA to Sources, evidence summary. | Startup prewarm is now part of managed runtime; live Merchant data is still stale and must not be treated as current. Full detail remains below the first decision. | `c9h9.13` closed; preserve cache invalidation on write/refresh paths. |
| `/ga4` | 60% | GA4 now separates metric-column availability, non-zero conversion observations and verified key-event configuration. Current local evidence has 275 conversion-like facts but zero observed non-zero values and no configuration proof, so the API returns `review_required` with one blocker instead of false `ready`. | `GET /api/ga4/diagnostics`, `getGa4Diagnostics()` and the shared `Ga4ConversionReadinessContract`. | Traffic-quality analysis remains useful while conversion, revenue and profitability conclusions stay blocked. | Key-event configuration provenance, GA4 settlement/data-quality state and exact GSC/WordPress landing alignment remain open. | Keep the honest blocker; next add source-quality and cross-source identity contracts before a real landing pilot. |
| `/localo` | 50% | Useful drilldown for local visibility readiness. | `GET /api/localo/diagnostics`, `getLocaloDiagnostics()` | Local blockers and evidence. | Not enough ranking/GBP depth for bold claims. | Park. |
| `/ahrefs` | 7/10 | SEO signal drilldown with an API-owned manual-only cross-check state. Above the card gallery, the first decision region says that 6 topics require manual GSC/WordPress review, has zero exact confirmations and zero queue actions, and distinguishes `gotowe` data from a brief-ready decision. The live diagnostics now responds within budget: 1.354044 s, 1.351506 s and 1.212189 s after managed restart. | `GET /api/ahrefs/diagnostics`, `getAhrefsDiagnostics()` and the shared `ContentAhrefsCandidateRow` schema; the route renders `gap_read_contract` directly. `AhrefsCrossSourceMatcher` compiles GSC/WordPress records once per planner batch; no response cache was added. | Gap/authority signals, current freshness, exact/weak/missing source lineage, evidence summary and one safe manual next step without raw IDs above details. Desktop/mobile proof is `.local-lab/proof/3bst7-ahrefs/`; fast desktop proof is `.local-lab/proof/c9h9-17-ahrefs-latency/`. | Ahrefs cannot drive publication or a content brief alone; the operator must still cross-check individual topics. Tactical queue still has a separate monolith seam before it can use the compiled matcher. | Keep it as input to `/content-workflow`. `3bst.7` and `c9h9.17` are closed. `c9h9.18` owns only typed extraction of the tactical Ahrefs branch; do not change matching rules, add an endpoint or create a direct action. |
| `/workflows` | 35% | Admin/audit surface. | `GET /api/workflows`, `GET /api/workflow-runs` | Runtime process visibility. | Not marketer route. | Keep secondary/admin. |
| `/settings` | 82% | Source health center has API-owned typed refresh state and now separates implemented read adapters, review-only actions and the one exact WordPress draft mutation adapter. Cards say explicitly whether a source is read-only, review-only, draft-only or disabled; `write=true` is no longer inferred from candidate actions. | Existing `GET /api/connectors` with typed `capabilities`, `refresh_state.automatic_refresh`, `POST /api/connectors/{id}/refresh`, `GET /api/connectors/refresh-runs/{run_id}` | Access/freshness, implemented adapter truth, missing source impact, explicit progress/result and policy-owned safe next step. Ads, Merchant, Localo and social proposals remain review-only; WordPress ekologus.pl alone exposes the draft-only adapter. | LinkedIn/Facebook have no read or publish adapter; Ahrefs and WordPress sklep expose no fictional action types. Credentials alone still do not prove useful vendor data. | Preserve API-owned capability truth and terminal invalidation; add vendor writes only through a separately implemented, validated ActionObject adapter. Browser proof remains historical until the next cross-route browser pass. |
| `/system` | 45% | Technical audit/admin. | connectors/workflows/runs plus system rows | Useful for dev/operator audit. | Not marketer mode. | Keep secondary. |
| `/social-publisher` | 25% | Hidden experimental review-only social drafts. | `POST /api/codex/context-pack`, `GET /api/social/history-inventory` | Review-only posture. | Needs historical social inventory before duplicate-free claims. | Park outside primary nav until social history and publish safety contracts exist. |
| `/google-sheets` | 15% | Hidden technical export placeholder. `/settings` shows "Eksport zablokowany" instead of linking operators into a fake workflow. | generic route; Sheets connector status | Export idea. | Not real workflow. | Keep hidden/technical until a safe export scope exists. |
| `/codex-runs` | 35% | Technical audit only. | system/codex run APIs if present | Debug value. | Not marketer value. | Keep technical. |
| `/security` | 40% | Technical safety view. | security/system route data | Shows guardrail status. | Not daily workflow. | Keep technical. |

## Content Workbench Target Model

## UX slice 2026-07-20

Pierwszy viewport `/content-workflow` został odchudzony: aktywna strona pozostaje
widoczna, pełna kolejka/inventory jest drugorzędnym disclosure, a wybór sekcji
nie pojawia się na etapach `scope` ani `section_map` (mapa jest automatyczna).
Kontekst pokazuje realne GSC/GA4/inventory w kartach oraz grupuje dane na Fakty,
Sygnały i Blokady. Proof desktop/mobile znajduje się w
`docs/review-packets/2026-07-20-ux-audit-input/second-opinion/` jako
`*-first-slice-live.png`.
Banner freshness jest renderowany tylko raz przez route shell; plan, tekst,
review i dev preview nie powielają już tego samego komunikatu.

## Production-ready visual slice 2026-07-20

Surface ma teraz responsive header dla `/content-workflow` (desktop sidebar,
mobile menu z hamburgerem), subtelny entrance/hover motion z obsługą
`prefers-reduced-motion`, kompaktowy hero strony/usługi i jeden dominujący
next-step hero. Tryb technical pozostaje dostępny jako progressive disclosure;
marketer nie ogląda źródeł ani freshness banneru przed decyzją. Live proof:
`docs/review-packets/2026-07-20-ux-audit-input/second-opinion/` pliki
`bdo-production-*`.

Stale planning approval jest teraz wyjaśniane językiem marketera: gdy API zwraca
`scope_current=false`, next-step hero mówi, że poprzednia decyzja jest
nieaktualna, podaje powód i prowadzi bezpośrednio do aktualnego formularza
zakresu. Znika niejasne „uzupełnij etap”. Proof:
`bdo-stale-scope-action.png`.

The first content screen should not be a gallery of cards. It should be a
working map for one selected content item or one prioritized queue.

Recommended first viewport:

```text
Treści i SEO
Źródła: GSC fresh | WordPress public fresh | WordPress dev connected? | Ahrefs supporting

Najważniejsza praca teraz
URL / title / type / service
Current public status: existing page/post, last modified, canonical/source
Dev target: no draft / draft exists / ACF sections available
Decision: refresh / merge / create / block
Why: query group + GSC metrics + content gap + service fit
Next step: prepare brief / open workflow / open dev draft / block claim

Content map
Public page sections -> missing sections -> proposed dev sections
GSC query groups -> matching page sections
Ahrefs gaps -> supporting topics only
Claims -> allowed / review-required / blocked
```

Minimum useful data fields:

- URL, title, content type, environment (`public`, `shop`, `dev`),
- WordPress ID or safe label when available,
- current H1/H2/ACF section summary,
- GSC top query group with clicks/impressions/CTR/position/decay,
- Ahrefs gap label with volume/difficulty/competitor only as supporting proof,
- service fit and claim status,
- duplicate/canonical risk,
- recommended content decision,
- next safe action ID or workflow link.

If the API lacks these fields, add them to a content view-model first. Do not
invent them in React copy or skill instructions.

## API Reuse Map

Use these before adding endpoints:

- Daily cockpit: `GET /api/dashboard/command-center`
- Content diagnostics: `GET /api/content/diagnostics`
- Content preflight: `GET /api/content/preflight`
- Content queue: `GET /api/content/work-items/queue`
- Content work item snapshot/enrichment: see `getContentWorkItemSnapshot()` and
  `getContentWorkItemEnrichment()` in `apps/dashboard/src/lib/api.ts`
- Content revisions: `POST /api/content/work-items/{id}/draft-revisions`,
  `POST /api/content/work-items/{id}/draft-revisions/{revision_id}/review`
- WordPress authoring profile: `GET /api/content/wordpress/authoring-profile`
- WordPress draft readiness/activation packet: `getContentWordPressDraftWriteReadiness()`,
  `getContentWordPressDraftActivationPacket()`
- Knowledge/service profile: `GET /api/content/service-profile`,
  `GET /api/content/knowledge-cards`
- GSC/SEO content signals are currently inside content diagnostics/preflight.
- Ahrefs: `GET /api/ahrefs/diagnostics`
- Source health: `GET /api/connectors`,
  `POST /api/connectors/{connector}/refresh`
- Actions: `GET /api/actions`, `GET /api/actions/{id}`, validate/preview/review/confirm endpoints

## Second Opinion Packet Requirements

When asking for a neutral second opinion, include:

- product goal: WILQ as BDOS-class marketing OS for Ekologus, not generic SEO UI,
- current route URL and screenshot,
- API payload summary, not raw secrets or full payload dump,
- exact user persona: Polish marketer/content operator, non-technical,
- what task the user should complete in 30 seconds,
- what data is real, stale, missing, review-only or dev-only,
- what must remain blocked,
- current known weaknesses from this file,
- ask for a harsh review: keep, cut, hide, merge, missing data, first viewport rewrite.

Never ask second opinion to validate a self-score. Ask it to roast whether the
screen helps a marketer perform real work.

## 2026-07-20 — zakres bez zgadywania

Na kroku `Zakres` panel pokazuje teraz krótką instrukcję operatora: sprawdź
dopasowaną usługę, zaznacz potwierdzenie i zapisz decyzję. WILQ buduje mapę
sekcji automatycznie; marketer nie zatwierdza ręcznie ACF ani `the_content`.
Jeśli API zwróci jedną kartę usługi albo jedną rekomendowaną kartę, formularz
wybiera ją wstępnie, ale nadal wymaga jawnego potwierdzenia człowieka.

Na aktywnym kroku `Zakres` formularz decyzji jest renderowany przed technicznym
panelem generatora planu. Dzięki temu pierwszy ruch nie wymaga przewijania przez
page assets ani ślady źródeł. Stara decyzja otrzymuje etykietę `Poprzednia decyzja
dotyczy starszego zakresu`, gdy digest zakresu nie jest już bieżący. Nie pokazujemy
wtedy jednocześnie `zaakceptowano`, żeby marketer nie odczytał historycznej decyzji
jako gotowej do przejścia dalej; hero prowadzi do `Sprawdź aktualny zakres`.

Na realnym case `content_work_item_content_decision_https___www_ekologus_pl_oferta_doradztwo_i_outsourcing_ekologiczny`
sprawdzono ten stan w przeglądarce: usługa jest potwierdzona, ale zakres wymaga
ponownego sprawdzenia po zmianie digestu. Proof obrazu: `.local-lab/proof/dashboard-content-workflow/2026-07-21/outsourcing-stale-decision-copy.png`.

W planie podstawowy widok pokazuje tylko liczby wejściowe i statusy źródeł.
Dokładne fakty oraz porównania okresów są dostępne pod jednym rozwijanym
`Pokaż dokładne fakty i porównania metryk`, żeby marketer widział mięso bez
ściany technicznego payloadu.

Podgląd `Tekst` ma jawny status `wersja robocza`, licznik sekcji/FAQ i lokalną
nawigację po całej stronie. Marketer może czytać materiał jak finalną stronę,
a lineage i digest pozostają w rozwijanym panelu technicznym.

Plan nie przechodzi bramki jakości, jeśli exact portfolio zapytań jest dostępne,
ale żadna sekcja nie ma jawnego `query_terms`. Zapytania bez pewnego dopasowania
mogą pozostać `page_only`; całe portfolio nie może jednak zniknąć z mapy sekcji.

Na kroku `Review` operator dostaje tę samą krótką orientację: przeczytaj pełny
podgląd, uruchom advisory review jako listę uwag, a następnie zapisz własną
decyzję dla exact revision. Review semantyczne nie jest automatyczną akceptacją.

Selektor `Aktywna strona` obsługuje również strony spoza kolejki okazji. Wybór
pozycji z `Pełny inventory WordPress` przechodzi przez ten sam endpoint kolejki
i ten sam snapshot workflow; nie jest lokalnym wyjątkiem ani atrapą danych.

Projekcja inventory jawnie komunikuje też źródło struktury: gdy WILQ nie
wykryje ACF/flexible content, ale ma czytelny materiał WordPress, marketer
widzi, że sekcje planu wynikają z `the_content`. Brak ACF nie jest wtedy
udawany jako brak treści ani nie blokuje planowania.

## 2026-07-21 — świeżość kontra jakość odczytu

Kolejka może mieć stan ogólny `dane treści świeże`, mimo że pojedynczy konektor
ma `partial`, `unverified` albo `settling`. W marketerowym widoku `/content-workflow`
nie chowamy już tej różnicy wyłącznie pod `Źródła i szczegóły`: pod grupami
`Fakty / Sygnały / Blokady` pojawia się jedna kondensowana linia `Źródła do
interpretacji`. Pokazuje tylko konektory wymagające ostrożności i kończy się
jasnym zastrzeżeniem, że jakość odczytu nie jest wynikiem kampanii.

Live WILQ proof 2026-07-21 dla BDO pokazał: GSC `odczyt częściowy`, WordPress,
GA4 i Ahrefs `jakość do sprawdzenia`; panel nadal poprawnie pokazał 181
wyświetleń, CTR 0,00% i 7 sekcji, bez dopisywania trendu. Focused proof:
`summarizeContentSourceQuality` (4/4) oraz screenshot
`.local-lab/proof/dashboard-content-workflow/2026-07-21/bdo-source-quality-caveat.png`.
Second-opinion checker `2026-07-20-source-quality-caveat-30CWhb` był ważny i
nie zgłosił findings; odnotował wyłącznie ograniczenie transportu cytacji oraz
human-only decyzję o naturalności polskiego wording.

## 2026-07-21 — kolejka używa bieżącego inventory struktury

Karta propozycji na ekranie bez wybranego work itemu nie może pokazywać starej
liczby sekcji z lekkiej projekcji kolejki, gdy pełny katalog WordPress ma świeży
rekord tego samego adresu pod innym `work_item_id`. `ContentCandidateQueuePanel`
wiąże teraz rekord po identyfikatorze albo znormalizowanej ścieżce URL i preferuje
`ContentInventoryCatalogItem.section_count`; fallbackiem pozostaje kolejka.

Live proof na `/content-workflow` zmienił BDO z nieopisanej projekcji `1 sekcji`
na jawne `12 nagłówków inventory WordPress`; po wybraniu strony workflow nadal
pokazuje 7 nagłówków bezpośredniego materiału REST. Rozbieżność jest teraz
opisana źródłem zamiast udawania, że oba liczniki oznaczają to samo. Nie zmienia
to decyzji ani nie tworzy nowego URL. Obraz:
`.local-lab/proof/dashboard-content-workflow/2026-07-21/queue-inventory-section-count.png`.

## 2026-07-21 — powody dopasowania usługi bez szumu z body

Service Profile nadal zwraca pełną, dynamiczną listę kandydatów i ich lineage.
W scope panelu nie wypisujemy jednak wszystkich fraz znalezionych w całym body
strony, bo stopka/nawigacja może wspominać inne obszary Ekologusa. UI pokazuje
dwie najmocniejsze exact frazy z API oraz liczbę słabszych dopasowań. Nie zmienia
to wybranej karty, rankingu ani kontraktu API.

Live outsourcing proof pokazuje `outsourcing ekologiczny` i `doradztwo
środowiskowe` jako główne dopasowania; `bdo`, `kobize` i `opakowani` nie są już
prezentowane jako równorzędny powód wyboru usługi. Screenshot:
`.local-lab/proof/dashboard-content-workflow/2026-07-21/outsourcing-service-reasons.png`.

## 2026-07-21 — główna akcja nie udaje gotowości przy blockerze

Hero workflow używa teraz typed blockera bieżącego kroku do nazwania akcji.
Jeśli review jest zablokowane, przycisk mówi `Sprawdź blokadę review`; jeśli
blokada dotyczy dev preview, mówi `Sprawdź blokadę dev preview`. Przy stanie
gotowym zachowane są krótkie akcje otwierające właściwy krok. To zmiana
prezentacji istniejącego kontraktu API: nie omija blokady i nie zmienia
uprawnień do WordPress.

Focused proof: `workflowStepActionLabel` (2/2) oraz dashboard typecheck.

W tym samym hero, gdy API zwraca blocker dla bieżącego kroku, instrukcja
pokazuje jego ludzki `label` i `reason`. Bez blockera pozostaje standardowa
instrukcja kroku. Dzięki temu marketer wie, co sprawdzić, bez odsłaniania
technicznego kodu i bez sugerowania akceptacji albo publikacji.

Focused proof: `workflowStepInstruction` (3/3) oraz dashboard typecheck.

## 2026-07-21 — jakość źródeł jest scoped do wybranej decyzji

Wybrany work item nie dziedziczy już quality states i caveatów wszystkich
connectorów z szerokiego diagnostics cache. Snapshot BDO ogranicza je do
WordPress Ekologus i GSC, bo tylko te źródła są w jego aktualnym lineage;
`WordPress sklep` nie pojawia się jako szum dla zwykłej strony. Pełny widok
diagnostics nadal może oceniać wszystkie konektory, ale ekran decyzji pokazuje
wyłącznie źródła relewantne dla tej strony.

Live proof 2026-07-21: snapshot BDO zwraca quality states
`google_search_console`, `wordpress_ekologus`, bez `wordpress_sklep`; browser
pokazuje `GSC: odczyt częściowy · WordPress: jakość do sprawdzenia`. Focused
proof: `test_stale_shop_wordpress_does_not_block_ordinary_content_freshness`
oraz testy API state/queue.

## 2026-07-21 — stale plan nie zeruje bazy wiedzy

Jeśli digest aktualnego zakresu lub planu jest nieaktualny, panel nadal pokazuje
lineage poprzedniej exact revision, ale nazywa go wprost `Zakres · lineage
poprzedniej wersji`. Fallback działa per pole: brakujące materiały albo karty
nie znikają tylko dlatego, że nowy proposal jest pusty; istniejące pola nowego
proposal pozostają nadrzędne. To nie odblokowuje starego planu i nie udaje, że
poprzednie źródła są aktualne.

Live BDO proof: panel równocześnie pokazuje `Plan wymaga aktualizacji` oraz
`7 materiałów Ekologusa · 4 kart`, bez raw IDs. Focused proof:
`planningSourceSummary` (current + stale lineage) i dashboard typecheck.
