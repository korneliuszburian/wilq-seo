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

`/content-workflow` is the primary "Treści i SEO" marketer workspace. Its
snapshot owns one five-step journey: `scope → section_map → draft → review →
dev_draft`. Every step carries typed phase/readiness, open/submit permissions,
a blocker and the next safe step; React no longer parses Polish status copy.
Marketer mode renders one compact page/service/decision context, the task map
and exactly one selected workspace. The former queue/action/proof wall mounts
only after an explicit switch to `Audyt techniczny`.

The current reviewer estimate is 7/10. Method: marketer/operator plus content
strategist review of the live API snapshot and browser proof at 1440×900 and
390×844. In both viewports the first screen identifies the page, service,
decision, current step, blocker and safe next action; the page has no horizontal
overflow. Completed steps can be revisited without changing the API-owned
current marker or sending a write request. Live state honestly remains
`current_step_id=draft`: a generation contract and legacy package review do
not equal acceptance of exact text. `review` and `dev_draft` remain closed,
draft-only and fail-closed until immutable revision persistence and exact-version
human acceptance exist.

Read-only Ahrefs and `wordpress_sklep` refreshes on 2026-07-14 restored source
freshness. The queue still has only 1 actionable item from 2 candidates and
remains density-blocked; WILQ must not invent a third topic. Proof is under
`.local-lab/proof/dashboard-content-workflow/2026-07-14T02-17-53-121Z/`;
the latest E2E also captures current-step and completed-step revisit states.
The separate deterministic 390px five-tab contract proof is under
`.local-lab/proof/dashboard-content-workflow/2026-07-14T02-33-15-013Z/`; it
expands only the typed draft sections and is not presented as live evidence.
The next product target is revision-bound content persistence, then a
server-side Codex app-server/SDK adapter using existing ChatGPT login—not an
API-key-only Agents SDK dependency.

Architecture proof (2026-07-14):

- `ContentWorkflowSurface` still delegates remote reads to
  `contentWorkflowQueries.ts`, but now branches explicitly between
  `ContentWorkflowMarketerJourney` and the technical audit. The nine technical
  panels are absent from marketer-mode DOM.
- `ContentWorkflowJourneyContext` owns the compact page/service/decision
  summary. `ContentWorkflowTaskMap` owns read-only selection and preserves the
  API `aria-current` marker when an earlier step is revisited.
- `ContentPageWorkbench` renders only the selected `scope`, `section_map`,
  `draft`, `review` or `dev_draft` workspace. Existing action builders and
  safety gates remain unchanged and available in technical audit.
- Shared Zod and Python contracts require the exact five-step order, unique IDs,
  exactly one current step matching `current_step_id` and explicit
  readiness/navigation fields. The dashboard maps them through
  `contentWorkflowRuntime.ts`; no `includes("zablok")` or index-based stage
  guessing remains.
- The editor labels its state `Niezapisany szkic roboczy`; it does not invent a
  revision number. Both dry-run CTAs expose marketer-safe pending, success,
  blocker or failure feedback while preserving `write_authorization=null`.
- Confirmed unreferenced duplicates `MobileContentTriage`,
  `MobileDecisionCard`, `ContentWorkbenchHeader` and
  `ContentPageIdentityCard` were deleted after repo-wide reference checks.
- No endpoint, vendor-write path, fallback runtime or Codex dependency was
  added in this slice.
## Surface State

Readiness is a product/usefulness estimate, not a test pass rate.

| Surface | Readiness | Current state | API source | Keep / useful | Main slop / blocker | Next move |
| --- | ---: | --- | --- | --- | --- | --- |
| `/command-center` | 70% | Good IA direction: daily priority, blockers and source freshness. Still too easy to become summary-of-everything. | `GET /api/dashboard/command-center`, `getCommandCenter()` | Daily queue, blocked claims, source freshness. | Needs stronger routing into one concrete work item. | Keep as cockpit; do not add more cards. Route into content workbench once content view is ready. |
| `/opportunities` | 50% | Useful as registry but overlaps with Command Center and Actions. | `GET /api/opportunities`, `getOpportunities()` | Opportunity list with evidence/action links. | Duplicates "Kolejka" mental model. | Eventually merge into one decision/action queue; avoid new UI work here now. |
| `/content-workflow` | 7/10 | Primary five-step "Treści i SEO" journey. Marketer mode shows compact page/service/decision context, five API-owned tasks and one selected workspace; technical panels require an explicit audit-mode switch. Live current step is `draft`, while completed `scope`/`section_map` remain revisitable without moving `aria-current` or issuing writes. Desktop 1440×900 and mobile 390×844 expose the blocker and safe next action in the first viewport with no page overflow. | Existing queue/snapshot, enrichment, authoring-profile, activation/readiness and action endpoints; snapshot adds typed `current_step_id` and five required operator steps. No new endpoint. Shared schema rejects missing/duplicate/mismatched current steps. | Wilku can identify the concrete page, service, decision and current task in seconds; only one work surface is mounted; dry-run and ActionObject safety remain unchanged; confirmed duplicate mobile/header components are deleted. | Exact text is still local editor state. Legacy package review/audit is not revision acceptance, so `review` and `dev_draft` remain blocked. Queue remains density-blocked at 1 actionable of 3 and Service Profile remains review-required. | Build immutable revision persistence with digest/base revision and exact-version acceptance; then add a server-side Codex app-server/SDK adapter. Do not restore the wall or add an API-key-only Agents SDK dependency. |
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
