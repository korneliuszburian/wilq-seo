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

Data: 2026-06-25

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

- `PLAN.md` remains the canonical self-contained ExecPlan and `/goal` reset
  prompt for the current Ekologus demo. `PLANS.md` is now the broader living
  ExecPlan for moving from the review-first demo cockpit toward the final
  ClientWorkspace-ready WILQ Marketing Operating System. Keep this file as the
  short recovery ledger only.
- Naming is now explicit: WILQ is the system/product, Wilku is the human
  marketer/operator persona, and Ekologus is the first depth-first
  workspace/client.
- Solid Ekologus demo gate passed on 2026-06-24 with
  `scripts/pre_demo_gate.sh --core-skills`: managed stack status, API health,
  live contract smoke, shared live schemas, dashboard route smoke 13/13 and
  sequential core skill smokes. This proves contract/demo readiness, not real
  marketer UAT or full BDOS/apply readiness.
- The same core pre-demo gate passed again after the mapping review handoff
  slice. Proof:
  `.local-lab/proof/pre-demo-gate-after-mapping-review-handoff.txt`.
- The core pre-demo gate passed again after messy-prompt eval hardening and
  runtime proofs. Proof:
  `.local-lab/proof/pre-demo-gate-after-messy-evals.txt`. Coverage: stack
  status, API health, live contract smoke, shared live schemas, dashboard route
  smoke 13/13 and sequential core skill smokes.
- Core demo path is currently usable in simulated/browser proof:
  Command Center -> Merchant -> Content Planner -> Ads Doctor -> GA4. Action
  copy and core navigation were hardened; Ads Doctor has the marketer-facing
  "Najpierw sprawdź w Ads" strip. Proof is in `PLAN.md` and `.local-lab/proof/`.
- Content workflow is the strongest proof point. It now has typed source/target
  context, inventory/canonical/duplicate gates, audited mapping and
  draft-readiness reviews, blocked staging handoff preview, review-only
  `act_prepare_wordpress_staging_draft`, blocked
  `post_publication_measurement_plan_v1`, and a read-only
  `target_site_migration_map` rendered in Content Planner as
  "Mapa migracji do review".
- Content workflow now also exposes concrete
  `target_site_mapping_review_inputs` for the marketer: candidate IDs, source
  URLs, candidate target URLs, allowed outcomes, checked-item templates, review
  notes prompt and blocked outputs. Live proof:
  `.local-lab/proof/content-mapping-review-input/live-mapping-review-input-summary.json`.
  This turns the mapping blocker into exact human input needed, but still does
  not unlock staging, publish, ranking/lead uplift or content-success claims.
- Mapping review inputs now also carry a typed review handoff:
  `review_action_id`, `review_endpoint` and `review_payload_template`.
  Content Planner renders this as "Review: zapisz review mapowania przez
  ActionObject" plus payload item count, without raw action IDs on the first
  screen. Live/browser proof:
  `.local-lab/proof/content-mapping-review-handoff/`.
- `scripts/export_content_mapping_review_packet.py` now exports the live
  mapping review packet as JSON or Markdown for the marketer/operator. Proof:
  `.local-lab/proof/content-mapping-review-packet/`. This is review-only:
  mapping still requires human input and does not unlock staging, publish or
  uplift claims.
- `scripts/export_marketer_uat_packet.py` now exports a live, read-only UAT
  packet for Command Center -> Merchant -> Content Planner -> Ads Doctor ->
  GA4. Proof: `.local-lab/proof/marketer-uat-packet/`. This prepares the real
  marketer session and records pass/fail fields, but is not itself marketer UAT.
- `scripts/record_marketer_uat_result.py` now validates a filled UAT result,
  rejects placeholders and turns marketer fail/confusion/new tasks into
  classified task candidates. Focused proof:
  `rtk uv run pytest tests/test_marketer_uat_packet.py tests/test_marketer_uat_result.py -q`.
- `agent-browser` marketer audit on 2026-06-25 captured real browser proof for
  Command Center, Merchant, Content Planner, Ads Doctor and GA4. Handoff:
  `docs/handoffs/2026-06-25-browser-marketer-audit.md`; proof:
  `.local-lab/proof/browser-marketer-audit-20260625/`. Main finding: Command
  Center is usable, GA4 is clearest, Merchant is useful but deep, Content is
  high-value but overloaded, Ads Doctor is too dense for unassisted demo.
- Fresh condensation browser audit on 2026-06-25 captured current API-backed
  route text/snapshots after starting the local stack. Handoff:
  `docs/handoffs/2026-06-25-condensation-browser-audit.md`; proof:
  `.local-lab/proof/condensation-browser-audit-20260625/`. Main finding:
  Command Center is the right start, GA4 is the reference condensation pattern,
  Merchant and Content need selected-first/detail-later structure, and Ads
  Doctor remains the biggest overload at 61,885 text chars and 54 headings.
- Ads Doctor now has the first implemented condensation slice: a live
  dashboard panel before the diagnostic wall that shows the primary Ads
  decision, why it matters, safe next action, evidence/source summary, blocked
  claims, missing inputs and measurement plan. Proof:
  `.local-lab/proof/ads-condensed-decision-panel-20260625/`. Focused checks:
  `rtk pnpm --dir apps/dashboard typecheck` and
  `rtk pnpm --filter @wilq/dashboard test -- AdsDoctorSurface`.
- Content Planner now has a selected-first "Dzisiejszy brief do review" panel.
  It condenses one content decision into current WILQ API metrics, H1/H2/FAQ/CTA
  direction, source evidence, target mapping state, blocked claims, missing
  inputs and measurement plan. It also states the domain rule explicitly:
  `ekologus.pl`/`sklep.ekologus.pl` are source-of-truth inventory, while
  `ekologus.dev.proudsite.pl` is preview/design context. Proof:
  `docs/handoffs/2026-06-25-content-selected-decision-panel.md` and
  `.local-lab/proof/content-selected-decision-panel-20260625/`.
- Merchant now has a selected-first "Problem feedu do sprawdzenia" panel before
  the full drilldown. It explains the first issue, count semantics
  (`reported_issue_occurrences` is not unique SKU count), safe validation step,
  evidence/source summary, blocked claims, missing inputs and measurement plan.
  First-screen copy avoids `ActionObject review`, `payload preview`, `feed
  write`, `approval` and `price-impact` phrasing. Proof:
  `docs/handoffs/2026-06-25-merchant-selected-decision-panel.md` and
  `.local-lab/proof/merchant-selected-decision-panel-20260625/`.
- Fresh 2026-06-24 adversarial skill evals exist for content, Ads, Merchant,
  GA4 and Localo. They prove overclaim blocking for target-site boundaries,
  CPA/ROAS/wasted budget, Merchant occurrence semantics, GA4 `(not set)` and
  Localo read-only visibility. Detailed artifact paths live in `PLAN.md`.
- Core demo eval cases now also include messy marketer prompts for Content,
  Ads, Merchant, GA4 and Localo, and `scripts/codex_skill_eval.sh` injects them
  into future `codex exec` eval prompts. Focused contract proof:
  `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q`.
- The first real messy-prompt runtime proof passed for
  `wilq-content-strategist`: artifact
  `.local-lab/evals/codex-skill/20260624T205857Z/wilq-content-strategist/result.json`,
  `operator_usefulness_score=5`, all decision-quality booleans true and
  staging/publish/uplift claims still blocked. This is not real marketer UAT.
- The Ads Doctor messy-prompt runtime proof also passed: artifact
  `.local-lab/evals/codex-skill/20260624T210410Z/wilq-ads-doctor/result.json`,
  `operator_usefulness_score=5`, four review ActionObjects validated and
  CPA/ROAS/wasted-budget/apply claims still blocked.
- The Merchant messy-prompt runtime proof passed: artifact
  `.local-lab/evals/codex-skill/20260624T210800Z/wilq-merchant-feed-operator/result.json`,
  `operator_usefulness_score=5`, `decision_queue` used as review scale,
  reported occurrences not treated as unique SKU count and feed/approval/
  revenue/price-impact claims still blocked.
- The GA4 messy-prompt runtime proof passed: artifact
  `.local-lab/evals/codex-skill/20260624T211123Z/wilq-ga4-analyst/result.json`,
  `operator_usefulness_score=5`, `(not set)` handled as `fix_measurement`, no
  campaign/landing blame from tracking gaps and ROAS/revenue/profitability
  claims still blocked.
- The Localo messy-prompt runtime proof passed: artifact
  `.local-lab/evals/codex-skill/20260624T211506Z/wilq-localo-operator/result.json`,
  `operator_usefulness_score=5`, Localo described as read-only visibility
  review and local tasks/GBP write/uplift claims still blocked.
- Content strategist eval hardening now requires the current
  `operator_summary.target_site_migration_map`, mapping-review gate markers and
  blocked staging/ranking outputs, so the eval cannot pass on generic
  target-context wording alone.
- Localo eval hardening now matches current live readiness: read-only place,
  rankings, GBP, competitor and review aggregates are allowed for review, while
  `local_tasks`, GBP write and local visibility uplift remain blocked.

## Active Gaps

- Real marketer UAT has not been collected. Simulated operator UAT says the
  core path is useful, but it does not prove that the marketer saves time or
  knows what to do without explanation.
- Content workflow now has a read-only old-to-new migration map and review
  input packet for the active decisions, but it still lacks confirmed human
  mapping for every row, publishing and real post-publication follow-up data for
  `ekologus.dev.proudsite.pl`. Mapping and draft-readiness review decisions can
  be recorded and audited; staging handoff and post-publication measurement now
  have blocked preview contracts, and Command Center exposes the review-only
  staging draft ActionObject, but this does not unlock draft/staging/publish,
  uplift or content-success readiness.
- Source contracts still block deeper claims: Ads optimizer/apply, Merchant
  feed repair/product ROAS/price impact, GA4 attribution/performance verdicts,
  Localo tasks/write/uplift and full BDOS/agency-grade automation.
- Shared action-focus/detail copy has been hardened in `/actions` and action
  detail panels: marketer-facing copy now says `Akcje do walidacji`,
  `podgląd zmian`, `Wykonanie` and `Dane techniczne akcji`, while raw data stays
  behind the technical toggle. Browser proof:
  `.local-lab/proof/action-copy-polish-20260625/actions.final3.text.txt`.
- Product-language hardening must not be implemented as component-local
  `replaceAll`, route-specific enum dictionaries or ad hoc label maps. If the
  dashboard exposes jargon, fix the typed API/view-model/shared label contract
  first; React routes should render that contract, not repair product meaning.
- Content Planner pure domain labels and metric formatting have been moved from
  `ContentDiagnosticSurface.tsx` into
  `apps/dashboard/src/lib/contentLabels.ts` with focused tests. This is a
  structural cleanup, not full UX completion: fresh browser proof still shows
  Content Planner jargon from API/backend summaries and composed detail rows,
  so the next correct fix is a typed Content condensation view-model/API
  contract.

## Next Best Queue

1. Run or defer the live marketer UAT packet from
   `.local-lab/proof/marketer-uat-packet/`: Command Center -> Merchant ->
   Content Planner -> Ads Doctor -> GA4, then record the filled result through
   `scripts/record_marketer_uat_result.py`.
2. Do not repeat completed first-screen condensation or shared action-copy
   hardening unless fresh browser proof finds a specific marketer-facing leak.
3. Do not patch marketer-facing leaks through UI-side string replacement or
   hardcoded route copy. Add a typed view-model/shared label contract and tests
   first.
4. For Content Planner, continue by adding a typed Content condensation
   view-model/API contract for visible decisions and blockers. Do not keep
   cleaning copied backend prose inside React.
5. Do not add new evals unless fresh route proof finds a specific
   marketer-facing leak.
6. If content depth is next, continue from the review handoff packet toward
   confirmed human mapping for every row, then audited draft-readiness. Do not
   unlock staging, publish or uplift claims without typed preview, human
   confirmation and audit.
5. Do not re-add ready/done surfaces as active tasks. If a completed area looks
   wrong, reopen it only with fresh API/browser proof and a focused failing
   check.
