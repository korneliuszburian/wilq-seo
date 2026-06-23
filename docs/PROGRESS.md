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
- Git, goal i dedykowane ledgery są źródłem długiej historii. Ten plik ma
  pomagać po utracie contextu.

## Current Readout

Data: 2026-06-23

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

- Goal and progress were compacted on 2026-06-23 to remove ready/done task
  noise from active recovery docs. Historical proof remains in git history and
  `docs/progress/archive/`.
- Latest pushed slice: `41735b4 fix(dashboard): surface ads business guardrails`.
  `/actions/act_confirm_ads_target_guardrails` and
  `/actions/act_record_ads_strategy_review` render Ads business context,
  missing target ROAS/CPA, target env options, strategy gates, validations,
  blocked claims and blocked apply/API mutation state as Polish review cards.
- Skill coverage table: `docs/evals/skill-coverage-audit.md`. Current state:
  12/12 skills have non-interactive eval artifacts; base API/evidence/Polish
  output/safety checks are covered.
- Strong demo path today:
  `/command-center` -> `/merchant` -> `/content-planner` -> `/ads-doctor` ->
  optional `/ga4` and `/localo`.

## Active Gaps

1. **Decision-quality evals**
   - Current skill evals are too format-heavy.
   - Add explicit quality checks: actionable decision, safe next step, blocked
     claims handled, workflow-specific interpretation and evidence-backed
     reasoning.

2. **Merchant product-row depth**
   - Current Merchant review is useful, but still too aggregate in places.
   - Preserve freshness and queue semantics.
   - Add product IDs/titles/SKU-level previews where vendor/API allows.

3. **Content inventory matching**
   - GSC/GA4 can see URLs that WordPress inventory may mark missing.
   - Improve URL normalization, host aliases, trailing slash and post/page/sitemap
     matching before publish-ready content decisions.

4. **Localo beyond OAuth and aggregate facts**
   - Current Localo supports aggregate visibility/reviews review.
   - Rankings, GBP performance, competitors, local tasks, writes and uplift
     claims still require typed read/write contracts.

5. **Skill/reference hygiene audit**
   - Audit `.agents/skills/**/SKILL.md` and `references/*.md`.
   - References should describe contracts and output shape only.
   - Product logic, workaround rules and bug fixes belong in API/schema/eval.

6. **Remaining Ads optimizer value**
   - Current Ads is review-only for many important paths.
   - Missing: live Keyword Planner enrichment, forecast/audience size, stronger
     budget pacing, change-history impact context, safe apply/audit contracts.

7. **Code quality where it affects velocity**
   - Avoid broad aesthetic refactors.
   - Extract large route modules only when they block product work, reviewability
     or focused verification.

## Next Best Queue

1. Tighten Codex skill eval schema/harness with explicit `decision_quality`.
2. Run focused eval-contract tests and one targeted non-interactive skill eval if
   the schema/harness changes.
3. Update `docs/evals/skill-coverage-audit.md` with the new eval standard.
4. Commit/push.
5. Continue with Merchant product-row depth or content inventory matching based
   on live API/browser proof.
