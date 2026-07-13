# Dashboard State

Last updated: 2026-07-13

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

Bring one content working surface to a genuinely useful state before spreading
work across the whole dashboard.

Target: `/content-workflow`.

`/content-workflow` is the primary "Treści i SEO" marketer workspace. The
current desktop render shows a concrete public page, public WordPress sections,
GSC signals, generic dev WordPress REST/ACF readback, editable draft text and a
typed current-vs-proposed preview. Direct create/live CTA is removed: the route
can only prepare a dry-run preview until canonical ActionObject apply exists.
The dev reader stays generic: it detects
flexible rows by `acf_fc_layout` and nested text candidates, never by a fixed
client-specific ACF key.

The current reviewer estimate is 6/10. Method: marketer/operator review of the
live snapshot, a 1440×900 render and a 390×844 render. Desktop and mobile now
answer page, public/dev context, decision direction, service/claim policy,
proof, blocker and dry-run next step without revealing IDs above the fold. The
typed service context correctly remains blocked until public-card review, so it
does not pretend that the writer is production-ready. Existing-draft duplication
remains closed by removing the direct live/create path; a real dev draft write
may return only through canonical ActionObject apply. The live queue currently
has 0 actionable items of the required 3 (2 candidates total) and must not
invent a third. `r564.5`,
`r564.6`, `r564.3`, `c9h9.4`, `/ahrefs` slice `3bst.7` and the Ahrefs latency
slice `c9h9.17` are closed. The current `/ahrefs` manual decision is above its
cards and diagnostics render within the operating budget; the next Ahrefs
maintenance seam is the separately tracked tactical-queue extraction `c9h9.18`,
not another React matching rule. The deleted legacy planner must not return.

Architecture proof (2026-07-13): `ContentWorkflowSurface` now delegates queue,
selected work item, enrichment and WordPress readiness queries to the typed
`contentWorkflowQueries.ts` seam. The route keeps state selection and
presentation orchestration; the seam owns React Query keys/enabled gates. The
page identity/decision card is now a separate presentational
`ContentPageIdentityCard.tsx` boundary; it receives typed display values and
renders the existing Service Profile projection without owning API logic. The
existing GSC/Ahrefs/brief column is now `ContentSignalColumn.tsx`; it renders
only the route's typed signal rows and does not rank or invent evidence.
The dev-only WordPress/ACF target column is now `ContentDevTargetColumn.tsx`; it
keeps explicit target selection and draft-only wording in a separate boundary
without adding a write path or client-specific ACF assumptions.
The public WordPress page/section column is now `ContentPublicPageColumn.tsx`;
it renders only the selected URL and section headings and does not infer SEO
decisions, canonical matches or evidence.
The shared marketer fact tile is now `ContentWorkflowFactTile.tsx`; it is a
presentation-only primitive used by existing panels and does not own metric
meaning or business rules.
The repeated safety card layout is now `ContentSafetyPanel.tsx`; its callers
continue to provide API-owned safety copy and blocked-claim meaning.
The three-use Claim Ledger list layout is now `ContentClaimList.tsx`; it renders
typed claim text, reasons and evidence IDs without classifying claim status.
Workflow action controls now render through `ContentWorkflowControlButton.tsx`;
disabled reasons and pending state remain supplied by the existing action
orchestration, so the component does not validate or mutate actions.
The full topic-enrichment panel is now `ContentOpportunityEnrichmentPanel.tsx`;
it renders the existing enrichment/measurement contract and blockers without
inferring service fit or replacing Service Profile decisions.
The Claim Ledger gate panel is now `ClaimLedgerGatePanel.tsx`; it preserves the
existing typed ledger filtering and evidence rendering while the route only
orchestrates its placement.
The blocked-candidate state is now `ContentWorkflowBlockedCandidate.tsx`; it
renders the existing queue freshness, blocker, safe next step and candidate
metrics without changing their API-owned meaning.
The quality-review panel is now `ContentQualityReviewPanel.tsx`; the route/API
still owns quality safety classification, while the component renders the
typed safety text, findings, dimensions and next step.
The revision-plan panel is now `ContentRevisionPlanPanel.tsx`; revision safety
classification remains in the route helper while the component renders typed
blockers, instructions and required evidence.
The ACF authoring preview is now `AcfPreviewPanel.tsx`; its recursive field
renderer is shared with the existing authoring readback while ACF safety text
continues to come from the route helper.
The structured draft preview is now `StructuredDraftPreviewPanel.tsx`; it
renders typed title, sections, evidence and human-review checklist while the
route retains safety classification.
The safety-panel composition is now `WorkflowSafetyPanels.tsx`; it receives
typed display text and child payloads, while route helpers remain the only
owners of safety classification.
The mobile decision surface is now `MobileContentTriage.tsx`; it renders the
API-owned candidate, blockers, freshness/evidence disclosure and review-only
CTA without inventing decision logic.
The workbench title and refresh controls are now `ContentWorkbenchHeader.tsx`;
they remain presentation-only and do not own route or decision semantics.
The public inventory card is now `ContentPublicInventoryPanel.tsx`; it renders
typed public title/URL/section state and the existing missing-inventory blocker
without moving canonical or SEO logic into React.
The compact mobile decision is now `MobileDecisionCard.tsx`; it renders typed
queue decision/blocker/freshness inputs and the review-only CTA without owning
recommendation logic.
The decision panel's publication blockers are now
`ContentWorkflowPublicationBlockers.tsx`; human-review, draft-only and
forbidden-claim copy remains a typed presentation boundary.
The decision panel's next-action card is now
`ContentWorkflowNextDecisionPanel.tsx`; it renders typed decision, proof,
claim-count and safe-next-step inputs without owning ranking logic.
The decision panel header is now `ContentWorkflowDecisionHeader.tsx`; it renders
typed topic, publication-blocked state and stepper inputs while route/model code
retains workflow semantics.
The decision panel's claim summary is now `ContentWorkflowClaimSummary.tsx`; it
renders typed claim counts and review/brief/WordPress links while claim-gate
semantics remain API/model-owned.
`docs/architecture/dashboard-react-standards.md` is the review contract.
The current Playwright proof also asserts the live marketer contract (decision,
public URL, current/signals/dev sections, safe draft-preview CTA and no
horizontal overflow) instead of historical freshness strings.

The target content workbench must show:

- current public WordPress pages/posts and their role,
- dev WordPress target state when available,
- current page sections/components/ACF blocks in marketer-readable language,
- GSC queries/pages and visible opportunity metrics,
- Ahrefs gaps as supporting signals, not standalone proof,
- service/claim status from WILQ knowledge,
- clear work decision: keep, refresh, merge, create, block,
- next action that can be handed to Codex or opened as a safe ActionObject,
- no generic "refresh ekologus" task without URL, page title, query group,
  current content, missing sections and reason.

## Surface State

Readiness is a product/usefulness estimate, not a test pass rate.

| Surface | Readiness | Current state | API source | Keep / useful | Main slop / blocker | Next move |
| --- | ---: | --- | --- | --- | --- | --- |
| `/command-center` | 70% | Good IA direction: daily priority, blockers and source freshness. Still too easy to become summary-of-everything. | `GET /api/dashboard/command-center`, `getCommandCenter()` | Daily queue, blocked claims, source freshness. | Needs stronger routing into one concrete work item. | Keep as cockpit; do not add more cards. Route into content workbench once content view is ready. |
| `/opportunities` | 50% | Useful as registry but overlaps with Command Center and Actions. | `GET /api/opportunities`, `getOpportunities()` | Opportunity list with evidence/action links. | Duplicates "Kolejka" mental model. | Eventually merge into one decision/action queue; avoid new UI work here now. |
| `/content-workflow` | 6/10 | Primary "Treści i SEO" workspace. Live queue has 2 total candidates, 1 actionable, and requires a minimum of 3, while content freshness is now fresh after read-only refresh. Queue and selected snapshot carry typed freshness; selected snapshot also owns a compact per-item Service Profile decision: typed service binding, approval and policy for that card (full Claim Ledger stays separate), source/freshness/evidence, first blocker and safe next step. IDs remain in disclosure; mobile retains a compact decision card before heavy detail and has no horizontal page overflow at 390 px. Ahrefs supporting rows distinguish exact proof from weak manual similarity. | Existing queue and existing snapshot plus enrichment, authoring-profile, activation/readiness and action endpoints in `api.ts`; no new endpoint. Direct execution is dry-run only; React forces `mode=dry_run` and null authorization. | Concrete public page selection; public/dev role split; fresh source status; service/claim context next to current page; evidence lineage; queue decision and safe next step; no duplicate-create/direct-live CTA; publish/destructive false. | Service Profile is honestly review-blocked; live queue remains blocked at 1 of 3 and must not invent a third topic. Production-depth and final draft remain unavailable until human review. | `r564.5` and `r564.6` are closed. Preserve the snapshot-owned context and the closed mobile viewport `r564.3`; do not infer service from enrichment or restore a live path. |
| `/content-inventory` | 20% | Hidden technical placeholder. Inventory remains an input to `/content-workflow`, not a separate writing cockpit. | currently generic/compact route; check `surfaceRegistry.ts` before adding code | Concept is needed inside content workbench. | Not a real marketer view yet. | Do not build separate cockpit; expose inventory inside content workbench. |
| `/service-profile` | 55% | Useful for owner/claim review, not daily writing screen. Its selected-card policy is now projected into the existing content work-item snapshot. | `GET /api/content/service-profile` is the source assembly; `GET /api/content/work-items/{id}/snapshot` projects its compact typed context; no frontend join. | Services, claim policy, source status and review-required data. | Not enough approved-current production depth; can overwhelm writer. | Keep owner review here; preserve the compact work-item projection instead of duplicating a second content view. |
| `/knowledge` | 65% | Admin/review support surface with current "Wiedza" IA. Operating-map remains the only initial read; cards/playbooks defer until disclosure. `list_workflows()` now uses only command-center decisions; standalone map core is `4.878 s`. Managed runtime starts a non-blocking map prewarm after readiness; first/second warmed HTTP reads measured `0.003550 s` / `0.003175 s`. First decision/blockers render in the browser proof; focused current Playwright passes 1/1 in 2.7 s. | `GET /api/knowledge/cards`, `/api/knowledge/playbooks`, `/api/knowledge/operating-map`; `build_knowledge_operating_map_cached()` and existing disclosure controls | Source lineage and claim review. | Prewarm stability must be checked on subsequent restarts; live knowledge/source freshness remains separate from cache latency. | Keep prewarm fail-open and non-blocking; do not re-enable concurrent subordinate reads. |
| `/actions` | 75% | Safe action queue renders from a cached/prewarmed existing list seam; after managed restart HTTP reads measured `0.082513 s` and `0.021151 s`. First decision card remains useful while mutation readiness is pending and explicitly keeps write blocked; operation labels wrap without overlap. | `GET /api/actions`, existing action validate/preview/review/confirm/impact endpoints; `list_actions_cached()` lifecycle seam | Review/preview/confirm/audit flow; evidence IDs remain in list response. | Full dashboard-api smoke now asserts current queue, blocker and lifecycle copy; mutation readiness remains separately review-gated. | `c9h9.11` and stale assertion work in `c9h9.8` are closed; do not restore registry IA. |
| `/actions/:id` | 70% | Decision-first detail answers what to do, why, write status, evidence and next safe step. Existing-draft action now has typed current/proposed/blocked preview. Fresh full-page and first-viewport screenshots exist locally. | `GET /api/actions/{id}`, `GET /api/actions/{id}/mutation-readiness`, preview/validate/review/confirm endpoints | Polish decision hero, explicit blocked write, typed preview card, evidence summary; raw payload/audit stay in disclosure. Focused Vitest and Playwright pass. | One below-fold readiness sentence still uses technical `apply-capable ActionObject`; queue performance is separate. | Keep pattern; copy-tune below-fold term later, never bypass safety. |
| `/ads-doctor` | 75% | Existing `GET /api/ads/diagnostics?view=summary` now has 15 s read-through cache; cold/warm HTTP after restart measured `1.426757 s` / `0.016956 s`. Shared schema accepts the API-owned summary and route has safe lazy/data-loading shells while actions continue loading. Full proof shows 5 decisions, freshness, evidence and blocked ROAS/revenue claims. Focused current Playwright passes 1/1 with measured heading first paint `1.853 s`. | Existing summary view + `build_ads_diagnostics_summary_cached()`; no new endpoint. | Fresh Ads data, campaign rows, decisions, action IDs; no writes or unsupported claims. | Live Ads data remains stale and requires refresh before performance claims; full dashboard-api smoke now follows the current evidence-first route. | `c9h9.9` and stale assertion work in `c9h9.8` are closed; preserve cache invalidation and blocked claims. |
| `/ads-doctor/search-terms` | 10% | Hidden technical placeholder parked behind `/ads-doctor`; the real Ads screen no longer links its primary "Review Ads" row into this route. | Ads diagnostics contracts exist; no standalone marketer queue yet. | Needed later for BDOS-like Ads value. | Not real queue yet. | Keep hidden. Build only after API-owned search-term queue exists. |
| `/ads-doctor/custom-segments` | 65% | Experimental review-only drilldown now consumes existing `GET /api/ads/diagnostics?view=summary`; typed candidate/forecast/keyword-planner fields, evidence and blockers remain available without the full Ads payload. Focused Playwright passes 1/1 in 4.4 s. | Existing Ads summary view; no new endpoint. | Safety model and source-term contract exist; audience size, ROAS and writes remain blocked. | Live Ads freshness can still be stale; the route remains review-only. | `c9h9.10` and stale assertion work in `c9h9.8` are closed; keep summary projection narrow and review-only. |
| `/ads-doctor/demand-gen` | 35% | Experimental readiness surface. | `GET /api/demand-gen/diagnostics` | Good blocker posture. | No campaign/creative depth yet. | Keep hidden/technical. |
| `/ads-doctor/scaling` | 5% | Hidden technical placeholder with safe route back to `/ads-doctor`. | none beyond Ads diagnostics. | None for marketer now. | Empty promise. | Keep parked until strategy, budget and measurement contracts exist. |
| `/ads-doctor/seasonality` | 5% | Hidden technical placeholder with safe route back to `/ads-doctor`. | none beyond Ads diagnostics. | None for marketer now. | Empty promise. | Keep parked until period-comparison contracts exist. |
| `/ads-doctor/recommendations` | 5% | Hidden technical placeholder with safe route back to `/ads-doctor`. | none beyond Ads diagnostics. | None for marketer now. | Empty promise. | Keep parked until API-owned recommendations review queue exists. |
| `/merchant` | 70% | First decision now renders before heavy detail on desktop and mobile: product topic, stale freshness, blocker, next safe step and source status. Managed runtime prewarms a 15 s cached diagnostics view; first HTTP read after restart measured 0.004860 s and second 0.007203 s. | Existing `GET /api/merchant/diagnostics`, `getMerchantDiagnostics()`; cache/clear seam in the existing builder, no new endpoint. | Feed/product issue queue, product blockers, freshness, Polish safe CTA to Sources, evidence summary. | Startup prewarm is now part of managed runtime; live Merchant data is still stale and must not be treated as current. Full detail remains below the first decision. | `c9h9.13` closed; preserve cache invalidation on write/refresh paths. |
| `/ga4` | 55% | Useful for separating measurement problems from traffic quality. | `GET /api/ga4/diagnostics`, `getGa4Diagnostics()` | Measurement blocker language. | Can still read technical; should feed Ads/content decisions. | Use as supporting signal, not target right now. |
| `/localo` | 50% | Useful drilldown for local visibility readiness. | `GET /api/localo/diagnostics`, `getLocaloDiagnostics()` | Local blockers and evidence. | Not enough ranking/GBP depth for bold claims. | Park. |
| `/ahrefs` | 7/10 | SEO signal drilldown with an API-owned manual-only cross-check state. Above the card gallery, the first decision region says that 6 topics require manual GSC/WordPress review, has zero exact confirmations and zero queue actions, and distinguishes `gotowe` data from a brief-ready decision. The live diagnostics now responds within budget: 1.354044 s, 1.351506 s and 1.212189 s after managed restart. | `GET /api/ahrefs/diagnostics`, `getAhrefsDiagnostics()` and the shared `ContentAhrefsCandidateRow` schema; the route renders `gap_read_contract` directly. `AhrefsCrossSourceMatcher` compiles GSC/WordPress records once per planner batch; no response cache was added. | Gap/authority signals, current freshness, exact/weak/missing source lineage, evidence summary and one safe manual next step without raw IDs above details. Desktop/mobile proof is `.local-lab/proof/3bst7-ahrefs/`; fast desktop proof is `.local-lab/proof/c9h9-17-ahrefs-latency/`. | Ahrefs cannot drive publication or a content brief alone; the operator must still cross-check individual topics. Tactical queue still has a separate monolith seam before it can use the compiled matcher. | Keep it as input to `/content-workflow`. `3bst.7` and `c9h9.17` are closed. `c9h9.18` owns only typed extraction of the tactical Ahrefs branch; do not change matching rules, add an endpoint or create a direct action. |
| `/workflows` | 35% | Admin/audit surface. | `GET /api/workflows`, `GET /api/workflow-runs` | Runtime process visibility. | Not marketer route. | Keep secondary/admin. |
| `/settings` | 80% | Source health center has API-owned typed refresh state (`ready`, `stale`, `partial`, `failed`, `blocked`, `unknown`) and starts one async read-only refresh per connector identity only when `automatic_refresh.eligible=true`. Existing run polling and terminal invalidation update the source and API-indicated decision view-models. | Existing `GET /api/connectors` with `refresh_state.automatic_refresh`, `POST /api/connectors/{id}/refresh`, `GET /api/connectors/refresh-runs/{run_id}` | Access/freshness, missing source impact, explicit progress/result, policy-owned safe next step and no write path. Focused fixtures retain honest partial/failed copy with no automatic retry; a failed status read stays a non-confirmed blocker with retry. | LinkedIn/Facebook remain missing access; this correctly blocks social conclusions, not source refresh itself. | Preserve the API policy and terminal invalidation; do not add a React stale/cooldown rule or a second refresh endpoint. Browser proof `.local-lab/proof/continuation-2026-07-12/3gre-settings-terminal-{desktop,mobile}.png`. |
| `/system` | 45% | Technical audit/admin. | connectors/workflows/runs plus system rows | Useful for dev/operator audit. | Not marketer mode. | Keep secondary. |
| `/social-publisher` | 25% | Hidden experimental review-only social drafts. | `POST /api/codex/context-pack`, `GET /api/social/history-inventory` | Review-only posture. | Needs historical social inventory before duplicate-free claims. | Park outside primary nav until social history and publish safety contracts exist. |
| `/google-sheets` | 15% | Hidden technical export placeholder. `/settings` shows "Eksport zablokowany" instead of linking operators into a fake workflow. | generic route; Sheets connector status | Export idea. | Not real workflow. | Keep hidden/technical until a safe export scope exists. |
| `/codex-runs` | 35% | Technical audit only. | system/codex run APIs if present | Debug value. | Not marketer value. | Keep technical. |
| `/security` | 40% | Technical safety view. | security/system route data | Shows guardrail status. | Not daily workflow. | Keep technical. |

## Content Workbench Target Model

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
