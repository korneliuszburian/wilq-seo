# WILQ Progress Ledger

Aktualizuj ten plik przy istotnym postępie, zmianie blockerów albo wyniku
testu skilla. To ma być krótki recovery ledger, nie pełny changelog.

Pełne archiwa:

- `docs/progress/archive/2026-06-19-progress-ledger.md`
- `docs/progress/archive/2026-06-23-progress-ledger.md`

## Maintenance Rule

- Trzymaj tutaj aktualny stan, ostatnie 3-5 ważnych faktów, aktywne luki i
  następny krok.
- Nie dopisuj setek linii historii. Starsze wpisy przenoś do
  `docs/progress/archive/`.
- Przed dopisaniem nowych zadań usuń albo zastąp rzeczy outdated/done, jeżeli
  nie zmieniają następnej decyzji operatora. Ten plik ma zostać najmniejszym
  użytecznym recovery ledgerem.
- Git, goal i dedykowane ledgery są źródłem długiej historii. Ten plik ma
  pomagać po utracie contextu.

## Current Readout

Data: 2026-06-24

Stan produktu:

- Active goal: `docs/goals/001-goal.md`.
- WILQ API is the system brain. Dashboard and Codex skills must use the same
  typed WILQ API contracts, evidence IDs, ActionObject IDs and source
  connectors.
- Local stack: `scripts/local_stack.sh start|stop|restart|status|logs`.
  Canonical URLs: API `http://127.0.0.1:8000`, dashboard
  `http://127.0.0.1:5173/command-center`.
- Operator-facing output must be Polish with Polish diacritics.
- Do not fix reasoning/product behavior by adding edge-case workaround prose to
  skill references. Fix typed API/schema/view-model/eval contracts first.
- Ekologus is the depth-first reference client. Multi-client/agency scale comes
  after Ekologus works deeply.

## Latest Important Facts

- `PLAN.md` is the canonical self-contained overnight plan and `/goal` reset
  prompt. Keep this file short and current.
- Solid Ekologus demo gate passed on 2026-06-24:
  `scripts/pre_demo_gate.sh --core-skills` completed managed stack status, API
  health, live contract smoke, shared live schemas, dashboard route smoke 13/13
  and sequential core skill smokes. This is contract/demo readiness, not
  marketer UAT or full BDOS/apply proof.
- Content Planner now exposes source/target context and
  `inventory_gate_status`, `canonical_gate_status`, `duplicate_gate_status`,
  `content_gate_summary`. Browser proof:
  `.local-lab/proof/dashboard/content-target-gate/content-planner-gates.txt`.
- Content Planner operator summary now exposes the live target-site mapping
  truth for `ekologus.dev.proudsite.pl`: current live top decisions have 4
  old-to-new candidate URLs with `target_site_migration_status=needs_review`;
  this is a migration-review queue, not a completed migration map. Proof:
  `.local-lab/proof/dashboard/content-migration-map/api-summary.json` and
  `.local-lab/proof/dashboard/content-migration-map/content-planner-snapshot.txt`.
- `act_prepare_content_refresh_queue` now carries the same target-site migration
  candidate/status/summary into content brief previews, reviewed draft previews
  and the content-strategist context-pack. Current old-site candidates stay
  `needs_review`, so draft/staging remains blocked until mapping is confirmed.
  Proof:
  `.local-lab/proof/dashboard/content-action-migration/action-payload-summary.json`.
- Content diagnostics and `act_prepare_content_refresh_queue` now expose
  `target_site_review_requirements` for the new-site path: target inventory
  mapping, canonical review, duplicate/cannibalization check and human
  confirmation. Proof:
  `.local-lab/proof/dashboard/content-target-review-requirements/action-review-requirements.json`.
- Content decisions, content ActionObject previews, reviewed draft previews,
  dashboard cards and the content-strategist context-pack now expose target
  inventory details WILQ actually has (`content_type`, `status`,
  `inventory_source`, `modified_gmt`) plus missing fields such as
  `title_or_h1` and `canonical_url`. Focused API tests, dashboard tests and the
  content-strategist smoke passed after a managed stack restart.
- Reviewed WordPress draft previews now expose `draft_generation_status` and
  `draft_blockers`: `needs_review` target mapping stays
  `blocked_pending_target_mapping`, so a review event cannot look like staging
  or publish readiness.
- Content brief previews now include publication-quality review fields:
  title/meta/schema directions, legal/factual review notes, brand voice notes,
  publication readiness and publication blockers. This improves the content
  handoff while keeping staging, publish and apply blocked.
- Duplicate/canonical gates now flow through content ActionObject brief
  previews, reviewed draft previews, dashboard draft cards and the
  content-strategist context-pack. Draft preview readiness remains blocked for
  canonical/duplicate review instead of implying publish or staging readiness.
- Reviewed WordPress draft previews now expose `content_draft_generation_v1`:
  allowed output kind, required gates, required draft elements and forbidden
  outputs. Current live candidates remain outline-only until gates pass.
- WordPress content inventory now captures safe page metadata when available:
  `title_or_h1` and `canonical_url` from REST/public sitemap HTML metadata,
  with short metadata timeout and no full HTML body persistence. These fields
  flow through content diagnostics, ActionObject previews, reviewed draft
  previews, dashboard cards, shared schemas and the content-strategist
  context-pack. Focused API/dashboard/shared-schema tests passed; smoke proof:
  `.local-lab/proof/content-target-metadata/content-strategist-smoke.json`.
- Live read-only proof: `refresh_wordpress_ekologus_357e83863713` completed
  after the connector change and the local metric store contains 116
  `content_object_seen` facts with `title_or_h1` or `canonical_url`. Active
  `/api/content/diagnostics` still reports
  `target_site_mapping_review_needed`, so the remaining blocker is old-to-new
  target mapping, not lack of inventory metadata support.
- Drift fix after runtime audit: `/api/content/diagnostics` now merges latest
  WordPress inventory facts into decision inventory context, matching the
  ActionObject preview path. After managed stack restart, live diagnostics show
  1 active content decision with inventory title/canonical while the overall
  mapping status remains `target_site_mapping_review_needed`.
- Content preview cards now show the old-to-new migration candidate URL and
  mapping status in the same target-site summary helper used by reviewed draft
  previews, so marketer review sees the proposed dev-site URL before staging.
- Fresh non-interactive skill eval proofs from 2026-06-24:
  content target-site boundary score 4
  `.local-lab/evals/codex-skill/20260624T125302Z/wilq-content-strategist/result.json`;
  Ads overclaim boundary score 5
  `.local-lab/evals/codex-skill/20260624T125820Z/wilq-ads-doctor/result.json`;
  Merchant occurrence semantics score 5
  `.local-lab/evals/codex-skill/20260624T132303Z/wilq-merchant-feed-operator/result.json`;
  GA4 measurement boundary score 5
  `.local-lab/evals/codex-skill/20260624T132845Z/wilq-ga4-analyst/result.json`;
  Localo read-only visibility score 5
  `.local-lab/evals/codex-skill/20260624T133326Z/wilq-localo-operator/result.json`.
- Current Localo truth: WILQ has read-only aggregate facts for local rankings,
  GBP, competitor visibility and reviews. Localo is not merely OAuth proof
  anymore, but local tasks, GBP write, write/apply automation and local
  visibility uplift remain blocked.
- Short marketer UAT script is ready at
  `docs/handoffs/2026-06-24-marketer-uat-script.md`; real marketer feedback is
  not collected yet.
- Dashboard action language hardening started: `/actions` now shows
  marketer-facing `Akcje`, `Akcje do walidacji`, `Otwórz akcję` and
  `Pokaż payload techniczny` while preserving technical route/API IDs. Proof:
  `.local-lab/proof/dashboard/action-labels/actions-route-snapshot.txt`.
- Core demo route language hardening continued: Content, Merchant and GA4
  first-screen links/cards now use `akcja/akcje` copy instead of marketer-facing
  `ActionObject` labels. Focused dashboard tests passed.
- Dashboard action copy hardening is now browser-smoke verified on fresh test
  ports: `/actions` expects `Akcje do walidacji`, action lists say `akcje`,
  Action detail uses `Pokaż payload techniczny` instead of raw debug wording,
  and the API-backed demo path passed 14/14 e2e checks with
  `WILQ_E2E_API_PORT=8876 WILQ_E2E_DASHBOARD_PORT=5374 rtk pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts`.
- Content migration candidate truth is now explicit: content diagnostics,
  ActionObject previews, shared schemas and Content Planner cards expose
  `target_site_migration_candidate_inventory_status` plus summary text. Live
  `/api/content/diagnostics` shows top old-site candidates for Zielony Lad,
  BDO, operat wodnoprawny and remediacja as `missing_target_inventory`, so the
  remaining blocker is real old-to-new dev-site mapping before draft or staging
  work.
- `wilq-content-strategist` smoke coverage now requires the same migration
  candidate inventory status/summary fields in content brief previews. Fresh
  proof:
  `.local-lab/proof/content-target-metadata/content-strategist-smoke.json`.
- Simulated operator UAT walkthrough captured route proof under
  `.local-lab/proof/dashboard/marketer-uat-20260624/` and findings in
  `docs/handoffs/2026-06-24-operator-uat-findings.md`. Result: core path gives
  a real review/planning boost, with Content Planner and Merchant strongest,
  but real marketer UAT is still not collected.
- Command Center CTA blocker from the simulated UAT is fixed: daily decisions
  now link as `Otwórz Merchant`, `Otwórz Content Planner`, `Otwórz GA4` and
  `Otwórz Ads Doctor` instead of generic `Otwórz działanie`. Browser proof:
  `.local-lab/proof/dashboard/marketer-uat-20260624/01-command-center-after-cta.txt`.
- Global dashboard navigation now exposes the core demo workflow links
  `Merchant`, `Content`, `Ads Doctor` and `GA4` before registry/admin routes.
  Browser proof:
  `.local-lab/proof/dashboard/marketer-uat-20260624/01-command-center-after-nav.txt`.
- Pre-demo gate passed after the content migration inventory contract, content
  skill smoke hardening and dashboard UAT navigation/CTA fixes:
  `rtk scripts/pre_demo_gate.sh --core-skills`. Coverage included local stack
  status, API health, live contract smoke, shared schemas live contracts,
  dashboard API-backed route smoke 13/13 and core skill smokes.
- Content operator summary now aggregates old-to-new migration candidate
  inventory truth: live `/api/content/diagnostics` after stack restart reports
  `target_site_mapping_review_count=4`,
  `target_site_confirmed_candidate_inventory_count=0`,
  `target_site_missing_candidate_inventory_count=4` and
  `target_site_mapping_status=target_site_mapping_review_needed`. Browser
  proof:
  `.local-lab/proof/dashboard/content-migration-map/content-planner-candidate-counts.txt`.
- `wilq-content-strategist` smoke now validates the operator-summary migration
  candidate inventory counts against `decision_queue`, so the aggregate cannot
  drift from per-decision target inventory status. Fresh proof:
  `.local-lab/proof/content-target-metadata/content-strategist-smoke.json`.
- Content brief previews, reviewed WordPress draft previews, the
  content-strategist context-pack and Action detail cards now expose typed
  `intent`, so the content workflow no longer loses one of the explicit goal
  fields between API, dashboard and skill context. Browser proof:
  `.local-lab/proof/dashboard/content-intent/action-content-intent.txt`;
  smoke proof:
  `.local-lab/proof/content-target-metadata/content-strategist-smoke.json`.
- Content diagnostics, `act_prepare_content_refresh_queue`, reviewed draft
  previews, dashboard cards and the content-strategist smoke contract now
  expose alternative `ekologus.dev.proudsite.pl` mapping candidates when the
  exact old-to-new URL is missing. Live proof found alternatives for BDO and
  remediacja while preserving `missing_target_inventory`, so this is manual
  mapping evidence, not migration confirmation or draft/staging readiness.
  Proof:
  `.local-lab/proof/content-target-alternatives/live-content-alternatives.json`,
  `.local-lab/proof/content-target-alternatives/content-strategist-smoke.json`
  and
  `.local-lab/proof/dashboard/content-target-alternatives/content-planner-alternatives.txt`.
- Content mapping alternatives now produce typed mapping-review decisions in
  diagnostics, ActionObject previews, reviewed draft previews, dashboard cards
  and the content-strategist context-pack. Live proof after stack restart
  returned 4 decisions: BDO/remediacja as `review_alternative_candidates` and
  Zielony Lad/operat wodnoprawny as `manual_mapping_required`. This still does
  not confirm migration or unlock draft/staging/publish. Proof:
  `.local-lab/proof/content-mapping-review/live-mapping-review.json`,
  `.local-lab/proof/content-mapping-review/content-strategist-smoke.json` and
  `.local-lab/proof/dashboard/content-mapping-review/content-planner-mapping-review.txt`.
- `act_prepare_content_refresh_queue` now exposes
  `target_site_mapping_review_contract` with review-only allowed outcomes,
  required fields and blocked outputs. Live payload proof keeps
  `apply_allowed=false` and `api_mutation_ready=false`; content-strategist smoke
  now requires the contract. Proof:
  `.local-lab/proof/content-mapping-review/action-mapping-review-contract.json`
  and
  `.local-lab/proof/content-mapping-review/content-strategist-contract-smoke.json`.
- Target-site mapping review can now be recorded through the existing
  `/api/actions/act_prepare_content_refresh_queue/review` audit path. The
  selected target URL is stored in structured `AuditEvent.details`, the human
  summary masks the URL as `[stored in audit details]`, and reviewed draft
  previews surface the recorded outcome/selected URL while keeping
  `apply_allowed=false`, `api_mutation_ready=false` and draft blockers active.
  Proof:
  `.local-lab/proof/content-mapping-recording/live-review-recording.json` and
  `.local-lab/proof/dashboard/content-mapping-recording/action-detail-mapping-recording.txt`.

## Active Gaps

- Real marketer UAT has not been collected. Simulated operator UAT says the
  core path is useful, but it does not prove that the marketer saves time or
  knows what to do without explanation.
- Content workflow still lacks reviewed old-to-new mapping decisions, staging
  handoff, publishing and post-publication measurement loop for
  `ekologus.dev.proudsite.pl`. Exact missing candidates, alternative dev-site
  URLs and typed mapping-review decisions are now exposed; they do not confirm
  mapping or resolve draft/staging/publish readiness.
- Source contracts still block deeper claims: Ads optimizer/apply, Merchant
  feed repair/product ROAS/price impact, GA4 attribution/performance verdicts,
  Localo tasks/write/uplift and full BDOS/agency-grade automation.
- Dashboard may still have technical language in secondary routes, fixtures and
  deep drilldowns. The core demo route smoke no longer exposes the known
  `ActionObjecty`/raw-debug blocker; change remaining copy only with browser
  proof that it blocks demo comprehension.

## Next Best Queue

1. Run or defer the short marketer UAT script: Command Center -> Merchant ->
   Content Planner -> Ads Doctor -> GA4, then record whether the marketer knew
   what to do next and where they got confused.
2. If demo UX is the next priority, change one confirmed blocker at a time
   from browser/UAT evidence. Do not repeat the completed action-copy cleanup
   unless a fresh route proof finds a remaining marketer-facing leak.
3. If content depth is next, continue from the existing source/target,
   duplicate/canonical, ActionObject migration status, target-site review
   requirements, typed intent, alternative candidate URLs, mapping-review
   statuses, the review-only mapping contract and audited mapping record
   toward the next draft/staging readiness gate without publish/apply claims.
4. Do not re-add ready/done surfaces as active tasks. If a completed area looks
   wrong, reopen it only with fresh API/browser proof and a focused failing
   check.
