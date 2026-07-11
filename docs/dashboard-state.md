# Dashboard State

Last updated: 2026-07-10

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

The current manual usefulness score is 5/10. Method: one reviewer checked the
ten first-screen questions in this file against live API data, a 1440×900
render, a 390×844 render and the content Playwright proof. Desktop answers page,
public/dev context, decision direction and dry-run next step. It fails current
freshness, cold-load speed and mobile first-viewport CTA. Existing-draft
duplication is now closed by removing the direct live/create path; the action
detail also renders a typed current/proposed/blocked preview. A real dev draft
write may return only through canonical ActionObject apply. Do not restore a
direct adapter or describe prior draft creation as current write readiness.
Next work is canonical dev-only apply (`c9h9.4`), then mobile UX (`r564.3`). The deleted legacy planner
must not return.

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
| `/content-workflow` | 6/10 | Primary "Treści i SEO" workspace. Live queue is blocked at 0 of 2 actionable candidates (minimum 3). Queue and selected snapshot carry typed freshness; stale GSC/public WordPress evidence blocks the homepage with a refresh-first next step. Queue-owned first card now renders before snapshot/enrichment, API prewarm keeps cold queue under 5 s, and mobile has a compact decision card before heavy detail. | Existing queue, snapshot, enrichment, authoring-profile, activation/readiness and action endpoints in `api.ts`; no new endpoint is needed. Direct execution is dry-run only; React forces `mode=dry_run` and null authorization. | Concrete public page selection; public/dev role split; freshness/source blocker above fold; evidence lineage; queue decision and safe next step before subordinate reads; mobile decision/blocker/safe CTA; no duplicate-create/direct-live CTA; publish/destructive false. | Full browser proof for a fresh non-blocked candidate still depends on external source refresh; live stale queue remains the honest blocker. | Finish external proof for `r564.3`, then keep cold-route Beads behind the content surface; do not restore the removed live path. |
| `/content-inventory` | 20% | Hidden technical placeholder. Inventory remains an input to `/content-workflow`, not a separate writing cockpit. | currently generic/compact route; check `surfaceRegistry.ts` before adding code | Concept is needed inside content workbench. | Not a real marketer view yet. | Do not build separate cockpit; expose inventory inside content workbench. |
| `/service-profile` | 55% | Useful for owner/claim review, not daily writing screen. | `GET /api/content/service-profile`, `getContentServiceProfile()` | Services, claim policy, source status, review-required data. | Not enough approved-current production depth; can overwhelm writer. | Feed allowed/blocked claims into content workbench, not as primary task screen. |
| `/knowledge` | 45% | Admin/review support surface with current "Wiedza" IA. | `GET /api/knowledge/cards`, `/api/knowledge/playbooks`, `/api/knowledge/operating-map` | Source lineage and claim review. | Cold concurrent map/cards/playbooks makes operating-map take 51.6 s; `c9h9.12`. Lineage is not production-ready content by itself. | Keep admin; fix shared cold build/progressive loading before more UI. |
| `/actions` | 75% | Safe action queue renders from a cached/prewarmed existing list seam; after managed restart HTTP reads measured `0.082513 s` and `0.021151 s`. First decision card remains useful while mutation readiness is pending and explicitly keeps write blocked; operation labels wrap without overlap. | `GET /api/actions`, existing action validate/preview/review/confirm/impact endpoints; `list_actions_cached()` lifecycle seam | Review/preview/confirm/audit flow; evidence IDs remain in list response. | Legacy cold `/actions` E2E still asserts removed registry IA and belongs to `c9h9.8`; current list/detail browser proof passes. | `c9h9.11` closed; fix only the stale behavior assertion in `c9h9.8`, without restoring old IA. |
| `/actions/:id` | 70% | Decision-first detail answers what to do, why, write status, evidence and next safe step. Existing-draft action now has typed current/proposed/blocked preview. Fresh full-page and first-viewport screenshots exist locally. | `GET /api/actions/{id}`, `GET /api/actions/{id}/mutation-readiness`, preview/validate/review/confirm endpoints | Polish decision hero, explicit blocked write, typed preview card, evidence summary; raw payload/audit stay in disclosure. Focused Vitest and Playwright pass. | One below-fold readiness sentence still uses technical `apply-capable ActionObject`; queue performance is separate. | Keep pattern; copy-tune below-fold term later, never bypass safety. |
| `/ads-doctor` | 75% | Existing `GET /api/ads/diagnostics?view=summary` now has 15 s read-through cache; cold/warm HTTP after restart measured `1.426757 s` / `0.016956 s`. Shared schema accepts the API-owned summary and route has safe lazy/data-loading shells while actions continue loading. Full proof shows 5 decisions, freshness, evidence and blocked ROAS/revenue claims. Focused current Playwright passes 1/1 with measured heading first paint `1.853 s`. | Existing summary view + `build_ads_diagnostics_summary_cached()`; no new endpoint. | Fresh Ads data, campaign rows, decisions, action IDs; no writes or unsupported claims. | Legacy `dashboard-api.spec.ts` Ads expectations belong to `c9h9.8`; live Ads data remains stale and requires refresh before performance claims. | `c9h9.9` closed; preserve cache invalidation and blocked claims while `c9h9.8` is rebaselined. |
| `/ads-doctor/search-terms` | 10% | Hidden technical placeholder parked behind `/ads-doctor`; the real Ads screen no longer links its primary "Review Ads" row into this route. | Ads diagnostics contracts exist; no standalone marketer queue yet. | Needed later for BDOS-like Ads value. | Not real queue yet. | Keep hidden. Build only after API-owned search-term queue exists. |
| `/ads-doctor/custom-segments` | 25% | Experimental review-only drilldown. | It currently calls full `GET /api/ads/diagnostics`; existing view boundary can be extended. | Safety model and source-term contract exist. | Focused cold E2E exceeds 30 s; `c9h9.10`. | Keep hidden; later use a narrow existing diagnostics view, not full Ads payload. |
| `/ads-doctor/demand-gen` | 35% | Experimental readiness surface. | `GET /api/demand-gen/diagnostics` | Good blocker posture. | No campaign/creative depth yet. | Keep hidden/technical. |
| `/ads-doctor/scaling` | 5% | Hidden technical placeholder with safe route back to `/ads-doctor`. | none beyond Ads diagnostics. | None for marketer now. | Empty promise. | Keep parked until strategy, budget and measurement contracts exist. |
| `/ads-doctor/seasonality` | 5% | Hidden technical placeholder with safe route back to `/ads-doctor`. | none beyond Ads diagnostics. | None for marketer now. | Empty promise. | Keep parked until period-comparison contracts exist. |
| `/ads-doctor/recommendations` | 5% | Hidden technical placeholder with safe route back to `/ads-doctor`. | none beyond Ads diagnostics. | None for marketer now. | Empty promise. | Keep parked until API-owned recommendations review queue exists. |
| `/merchant` | 70% | First decision now renders before heavy detail on desktop and mobile: product topic, stale freshness, blocker, next safe step and source status. Managed runtime prewarms a 15 s cached diagnostics view; first HTTP read after restart measured 0.004860 s and second 0.007203 s. | Existing `GET /api/merchant/diagnostics`, `getMerchantDiagnostics()`; cache/clear seam in the existing builder, no new endpoint. | Feed/product issue queue, product blockers, freshness, Polish safe CTA to Sources, evidence summary. | Startup prewarm is now part of managed runtime; live Merchant data is still stale and must not be treated as current. Full detail remains below the first decision. | `c9h9.13` closed; preserve cache invalidation on write/refresh paths. |
| `/ga4` | 55% | Useful for separating measurement problems from traffic quality. | `GET /api/ga4/diagnostics`, `getGa4Diagnostics()` | Measurement blocker language. | Can still read technical; should feed Ads/content decisions. | Use as supporting signal, not target right now. |
| `/localo` | 50% | Useful drilldown for local visibility readiness. | `GET /api/localo/diagnostics`, `getLocaloDiagnostics()` | Local blockers and evidence. | Not enough ranking/GBP depth for bold claims. | Park. |
| `/ahrefs` | 45% | Useful as SEO signal drilldown, not standalone decision center. | `GET /api/ahrefs/diagnostics`, `getAhrefsDiagnostics()` | Gap/authority signals. | Ahrefs cannot drive publication alone. | Feed into content workbench with GSC/WP cross-check. |
| `/workflows` | 35% | Admin/audit surface. | `GET /api/workflows`, `GET /api/workflow-runs` | Runtime process visibility. | Not marketer route. | Keep secondary/admin. |
| `/settings` | 65% | Source health center now has stale-source read-only refresh buttons. | `GET /api/connectors`, `POST /api/connectors/{id}/refresh` | Access/freshness, missing source impact, refresh action. | Needs queued/running/partial job state later. | Good enough for now; do not polish until content target needs source state. |
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
