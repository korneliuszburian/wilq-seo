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

## Active Gaps

- Real marketer UAT has not been collected. Browser/smoke/eval proof does not
  prove that the marketer saves time or knows what to do without explanation.
- Content workflow still lacks confirmed old-to-new mapping against full
  dev-site inventory, staging handoff, publishing and post-publication
  measurement loop for `ekologus.dev.proudsite.pl`.
- Source contracts still block deeper claims: Ads optimizer/apply, Merchant
  feed repair/product ROAS/price impact, GA4 attribution/performance verdicts,
  Localo tasks/write/uplift and full BDOS/agency-grade automation.
- Dashboard still has marketer-facing technical language in some places,
  especially `ActionObjecty`, raw IDs and technical drilldowns. Change only
  with browser proof that it blocks demo comprehension.

## Next Best Queue

1. Run or defer the short marketer UAT script: Command Center -> Merchant ->
   Content Planner -> Ads Doctor -> GA4, then record whether the marketer knew
   what to do next and where they got confused.
2. If demo UX is the next priority, change one confirmed blocker at a time:
   likely nav label `ActionObjecty` -> marketer-friendly wording, or hide raw
   drilldown IDs behind technical details.
3. If content depth is next, continue from the existing source/target,
   duplicate/canonical and migration-candidate status toward confirmed dev-site
   inventory mapping and draft/staging handoff, without publish/apply claims.
4. Do not re-add ready/done surfaces as active tasks. If a completed area looks
   wrong, reopen it only with fresh API/browser proof and a focused failing
   check.
