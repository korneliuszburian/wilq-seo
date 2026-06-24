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

- Full overnight execution map was added on 2026-06-24 in `PLAN.md`. Use it as
  the canonical self-contained plan for unattended continuation and `/goal`
  reset; keep this file as the short recovery ledger.
- Content target-site adversarial eval was verified through real
  non-interactive Codex on 2026-06-24. Proof:
  `.local-lab/evals/codex-skill/20260624T125302Z/wilq-content-strategist/result.json`.
  Result passed with `operator_usefulness_score=4`, API usage, Polish output,
  evidence IDs, source connectors, canonical/duplicate/target-context wording
  and blocked claims for `ekologus.dev.proudsite.pl source evidence`,
  WordPress publish, duplicate-free guarantee, ranking guarantee, lead uplift
  and revenue impact. This is guardrail proof, not marketer UAT.
- Ads overclaim adversarial eval was verified through real non-interactive
  Codex on 2026-06-24. Proof:
  `.local-lab/evals/codex-skill/20260624T125820Z/wilq-ads-doctor/result.json`.
  Result passed with `operator_usefulness_score=5`, live Google Ads evidence,
  four validated review-only ActionObjects and explicit blocks for CPA, ROAS,
  search-term waste, wasted budget, budget scaling, recommendation apply,
  targeting/apply and negative keyword apply. This proves Ads review guidance,
  not optimizer/apply readiness.
- Marketer demo walkthrough hardening completed on 2026-06-24. Live managed
  stack was ready, browser snapshots for `/command-center`, `/merchant`,
  `/content-planner`, `/ads-doctor`, `/ga4` and
  `/actions/act_prepare_content_refresh_queue` are saved under
  `.local-lab/proof/dashboard/marketer-demo-walkthrough/`. Ready findings:
  Command Center gives the narrow demo path, Merchant correctly separates
  reported issue occurrences from unique products/feed writes, Content Planner
  shows concrete GSC/WP-backed refresh/merge briefs, Ads blocks CPA/ROAS/
  wasted-budget/apply overclaims, and GA4 treats `(not set)` as measurement
  quality rather than campaign failure. Hardening fixed in this slice: Action
  detail no longer shows marketer-facing `Dry-run preview`, `Goal 001 live
  proof` or raw context-pack proof notes; it now renders Polish podgląd/review
  summaries while preserving audit event IDs. Focused proof: dashboard route
  tests 35 passed, dashboard typecheck passed, targeted Playwright action-detail
  smoke passed, `git diff --check` clean, and refreshed browser snapshot
  `actions__act_prepare_content_refresh_queue_after_copy_fix.txt` shows the new
  copy.
- Content decision target-context slice completed on 2026-06-24. Typed backend
  and shared schemas now expose `source_url`, `source_site_host`,
  `target_site_url`, `target_site_host` and
  `target_site_adaptation_status` on content decisions, and Content Planner
  cards show source/target context. Live `/api/content/diagnostics` after
  managed stack restart showed 4 content decisions with target context. Focused
  proof: content API pytest subset 2 passed, shared schema tests passed,
  dashboard typecheck passed, dashboard route-focused tests passed 35 tests and
  live API check passed.
- External second-opinion synthesis was captured on 2026-06-24 in
  `docs/audits/002-2026-06-24-second-opinion-synthesis.md`. Consensus: WILQ is
  a real API-first review cockpit and content-planning assistant, not a prompt
  pack, but it must not be overclaimed as full BDOS/optimizer/write automation.
  The highest-value direction remains one strong evidence-backed content
  workflow for Ekologus: source evidence -> target-site context -> inventory/
  canonical/duplicate check -> structured brief/draft plan -> review
  ActionObject -> later staging/publish/measurement loop.
- Solid Ekologus demo gate passed on 2026-06-24. `scripts/pre_demo_gate.sh`
  completed managed stack status, API health, live contract smoke, shared live
  schemas, dashboard API-backed route smoke 13/13 and sequential core WILQ skill
  smokes. Treat this as contract/demo readiness, not marketer UAT or proof of
  full BDOS/apply automation.
- Skill/reference/eval baseline is current-demo ready. `scripts/skill_hygiene_check.py`
  passed, manual semantic review of 12 `references/output-contract.md` files
  found contract/output guidance rather than workaround prose, and the eval
  harness requires `decision_quality`. Content strategist proof now includes
  `content_brief_preview_v1`, H1/H2/FAQ fields and non-interactive eval score 5.
  The content eval case now also guards the new-site boundary:
  `ekologus.dev.proudsite.pl` must be treated as target context, not source
  evidence, and publish/ranking/lead/revenue/duplicate-free claims stay blocked
  without validated write/apply evidence. Reopen this area only with a concrete
  skill that passes while making a bad or unsupported decision.

## Active Gaps

1. **Content workflow depth**
   - Must-have direction: old/current Ekologus evidence -> target context for
     `ekologus.dev.proudsite.pl` -> inventory/canonical/duplicate gate ->
     Polish brief or draft plan -> review ActionObject.
   - Current status: content decisions and ActionObject previews expose useful
     source/target and H1/H2/FAQ/CTA/source-fact fields, but full staging
     handoff, publishing and post-publication measurement remain deferred.
   - Verified now: live content diagnostics and non-interactive skill output
     satisfy the target-site boundary eval contract.
   - Next risk to test: duplicate/canonical gating for target-site content
     before draft/staging work.

2. **Marketer UAT and route usefulness**
   - Browser proof shows the narrow demo path is usable, but no real marketer
     UAT has yet proved that the screens save time or improve decisions.
   - Next audit should ask: can a marketer choose one content action, one
     Merchant blocker, one Ads review and one GA4 measurement issue without a
     developer explaining the UI?

3. **Source contracts still blocking deeper claims**
   - Ads: target CPA/ROAS, Keyword Planner approval/forecast, change-history
     impact and write/apply safety remain blockers for optimizer claims.
   - Merchant: product IDs/SKU, true unique-product rows, historical price
     changes and before/after performance windows remain blockers for product
     ROAS, price-impact, approval recovery and feed-repair claims.
   - GA4: conversion/revenue/attribution confidence remains a blocker for ROAS,
     profitability and funnel verdicts.
   - Localo: access/read evidence must not be treated as tasks, writes or uplift
     unless WILQ API exposes those contracts.

4. **Dashboard language and information hierarchy**
   - Fixed this slice: Action detail no longer leads with dry-run/proof-run
     wording.
   - Remaining hardening: primary nav still says `ActionObjecty`, some raw IDs
     and technical labels remain visible in drilldowns, and some route modules
     are large. Only change these with browser proof that they block demo
     comprehension.

5. **BDOS / agency-grade future**
   - Deferred until Ekologus works deeply: full Ads apply path, budget optimizer,
     Demand Gen automation, social publishing apply, Merchant feed writes,
     Localo write/uplift automation, multi-client permissions, production auth,
     deployment/monitoring and full external knowledge compiler.

## Next Best Queue

1. If continuing eval hardening, pick Merchant occurrences-not-unique-products,
   GA4 `(not set)` measurement blocker or Localo access-not-ranking. Ads
   no-CPA/ROAS overclaim proof is current.
2. If demo UX is the next priority, change only one confirmed blocker at a time:
   likely nav label `ActionObjecty` -> marketer-friendly wording, or hide raw
   drilldown IDs behind technical details.
3. If content depth is the next priority, add/verify a target-site duplicate/
   canonical gate for `ekologus.dev.proudsite.pl` before any draft/staging work.
4. Do not re-add ready/done surfaces as active tasks. If a completed area looks
   wrong, reopen it only with fresh API/browser proof and a focused failing
   check.
