# Dashboard State

Last updated: 2026-07-07

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

Target: `/content-planner` plus drilldown into `/content-workflow`.

Current completed slice: `/content-planner` first viewport now starts from a
real public WordPress page and real GSC/WP/Ahrefs/dev authoring facts instead
of a vague candidate count. `/content-workflow` now has one consolidated dev
draft panel above the old detailed mechanics: dev URL, draft write state, ACF
layout count, missing review/audit/handoff steps, admin/dev links, an
ActionObject authorization step, gated dev draft creation and persisted
activation-packet readback after draft creation. Keep the next slice focused on
current dev draft/ACF section editing, not on adding more top-level cards.

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
| `/content-planner` | 68% | First viewport now selects a confirmed public WordPress page before Ahrefs-only gaps. It shows real URL, title/H1, current public sections, GSC query metrics, Ahrefs as supporting signal, dev WordPress target and ACF layout readiness. Current local runtime has draft writes enabled for dev only (`publish_allowed=false`, `live_write_enabled=false`). Latest screenshot: `/tmp/wilq-content-planner-draft-enabled.png`. | `GET /api/content/diagnostics`, `GET /api/content/preflight`, `GET /api/content/wordpress/authoring-profile`, `getContentDiagnostics()`, `getContentPreflight()`, `getWordPressAuthoringProfile()` | Concrete page workbench: public URL, current sections, query group, source freshness, dev/admin links, blockers and next workflow action. | Current dev page/ACF row contents are not shown yet, and lower legacy panels still need trimming once the write/read loop exists. | Wire dev draft readiness/apply/readback: show existing dev draft or create draft package, then show editable section plan and ACF mapping against current dev state. |
| `/content-workflow` | 77% | Strongest content mechanic but still overloaded below the fold. Top now shows one selected content item with public URL/title/H1/sections, GSC reason, blockers, Claim Ledger summary and a consolidated dev draft WordPress panel. That panel can prepare ActionObject write authorization, create a gated dev WordPress draft, persist the execution result and read the real dev WordPress draft back through REST after reload. Local proof on 2026-07-07 created dev draft ID `1275`; the activation packet now returns `draft_readback.status=available`, title, `post_status=draft`, link, content summary and word count. Publish/destructive update stayed false. Latest screenshot: `/tmp/wilq-content-workflow-dev-draft-readback.png`. | `GET /api/content/work-items/queue`, `GET /api/content/work-items/{id}/snapshot`, `GET /api/content/wordpress/authoring-profile`, draft readiness/activation endpoints in `api.ts`, action preview/review/confirm endpoints, `POST /api/content/work-items/wordpress-draft-execution`, WordPress REST readback for created drafts | Step workflow, selected public page, dev draft state, ACF layout count, missing review/audit/handoff steps, dev/admin links, Claim Ledger, draft-only posture, ActionObject authorization, gated dev draft creation, persisted dev draft result and live dev draft readback. | Lower half is still too long and card-heavy. The readback currently summarizes post content and ACF field names/counts, but it does not yet show editable ACF row contents or a side-by-side section mapping against the dev page. The local dev draft proof used a Codex/local operator smoke review, not Wilku content approval. | Next: read current dev draft ACF rows/sections from `ekologus.dev.proudsite.pl`, show editable section/ACF mapping in the top workbench, then cut or collapse lower legacy panels into one active writing step. |
| `/content-inventory` | 20% | Placeholder/hidden inventory route. | currently generic/compact route; check `surfaceRegistry.ts` before adding code | Concept is needed. | Not a real marketer view yet. | Do not build separate cockpit; expose inventory inside content workbench. |
| `/service-profile` | 55% | Useful for owner/claim review, not daily writing screen. | `GET /api/content/service-profile`, `getContentServiceProfile()` | Services, claim policy, source status, review-required data. | Not enough approved-current production depth; can overwhelm writer. | Feed allowed/blocked claims into content workbench, not as primary task screen. |
| `/knowledge` | 45% | Admin/review support surface. | `GET /api/knowledge/cards`, `/api/knowledge/playbooks`, `/api/knowledge/operating-map` | Source lineage and claim review. | Lineage is not production-ready content by itself. | Keep as admin mode. Do not use as writing cockpit. |
| `/actions` | 55% | Safe action queue concept is good. | `GET /api/actions`, action validate/preview/review/confirm/impact endpoints | Review/preview/confirm/audit flow. | First-level language still partially technical. | Keep queue; improve individual action detail before expanding actions. |
| `/actions/:id` | 25% | Current single-action view is confusing. User explicitly reported not knowing what to do. | `GET /api/actions/{id}`, `GET /api/actions/{id}/mutation-readiness`, preview/validate/etc. | Underlying safety flow. | Too many conditions, blocked claims and raw mechanics above the decision. | P0 Bead exists: redesign into "what this checks, can it write, what proof, next click". |
| `/ads-doctor` | 35% | API has real data but route was observed stuck on loading in dev and is too heavy for first screen. | `GET /api/ads/diagnostics?view=summary`, `GET /api/actions` currently too heavy | Fresh Ads data, campaign rows, decisions, action IDs. | Loads/parses too much before first paint; not current priority after user switched to content. | Park. Later create lightweight Ads dashboard summary or trim route query. |
| `/ads-doctor/search-terms` | 10% | Placeholder. | Ads diagnostics contracts exist, route is hidden placeholder. | Needed later for BDOS-like Ads value. | Not real queue yet. | Do not show in primary nav. |
| `/ads-doctor/custom-segments` | 25% | Experimental drilldown. | `GET /api/ads/diagnostics`, custom segment contracts | Safety model exists. | Not daily marketer workflow. | Keep hidden until Ads work resumes. |
| `/ads-doctor/demand-gen` | 35% | Experimental readiness surface. | `GET /api/demand-gen/diagnostics` | Good blocker posture. | No campaign/creative depth yet. | Keep hidden/technical. |
| `/ads-doctor/scaling` | 5% | Placeholder. | none beyond Ads diagnostics. | None for marketer now. | Empty promise. | Hide/leave placeholder. |
| `/ads-doctor/seasonality` | 5% | Placeholder. | none beyond Ads diagnostics. | None for marketer now. | Empty promise. | Hide/leave placeholder. |
| `/ads-doctor/recommendations` | 5% | Placeholder. | none beyond Ads diagnostics. | None for marketer now. | Empty promise. | Hide/leave placeholder. |
| `/merchant` | 60% | Improved copy and stale-source refresh path. Better but still not enough product mapping. | `GET /api/merchant/diagnostics`, `getMerchantDiagnostics()` | Feed/product issue queue, product blockers, source freshness. | Some labels still abstract; needs product examples and Ads/GA4 product joins before revenue claims. | Park after copy improvements. Do not rework again until content target lands. |
| `/ga4` | 55% | Useful for separating measurement problems from traffic quality. | `GET /api/ga4/diagnostics`, `getGa4Diagnostics()` | Measurement blocker language. | Can still read technical; should feed Ads/content decisions. | Use as supporting signal, not target right now. |
| `/localo` | 50% | Useful drilldown for local visibility readiness. | `GET /api/localo/diagnostics`, `getLocaloDiagnostics()` | Local blockers and evidence. | Not enough ranking/GBP depth for bold claims. | Park. |
| `/ahrefs` | 45% | Useful as SEO signal drilldown, not standalone decision center. | `GET /api/ahrefs/diagnostics`, `getAhrefsDiagnostics()` | Gap/authority signals. | Ahrefs cannot drive publication alone. | Feed into content workbench with GSC/WP cross-check. |
| `/workflows` | 35% | Admin/audit surface. | `GET /api/workflows`, `GET /api/workflow-runs` | Runtime process visibility. | Not marketer route. | Keep secondary/admin. |
| `/settings` | 65% | Source health center now has stale-source read-only refresh buttons. | `GET /api/connectors`, `POST /api/connectors/{id}/refresh` | Access/freshness, missing source impact, refresh action. | Needs queued/running/partial job state later. | Good enough for now; do not polish until content target needs source state. |
| `/system` | 45% | Technical audit/admin. | connectors/workflows/runs plus system rows | Useful for dev/operator audit. | Not marketer mode. | Keep secondary. |
| `/social-publisher` | 25% | Experimental review-only social drafts. | `POST /api/codex/context-pack`, `GET /api/social/history-inventory` | Review-only posture. | Needs historical social inventory before duplicate-free claims. | Park. |
| `/google-sheets` | 15% | Placeholder/export readiness. | generic route; Sheets connector status | Export idea. | Not real workflow. | Keep hidden/technical. |
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
