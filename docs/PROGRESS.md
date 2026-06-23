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
- Skill eval schema/harness now requires `decision_quality`: actionable
  decision, safe next step, blocked-claims handling, workflow-specific
  interpretation and evidence-backed reasoning. Live proof:
  `.local-lab/evals/codex-skill/20260623T191904Z/wilq-daily-command/result.json`.
- Content/GSC inventory matching no longer marks current Ekologus URLs as
  missing when wide WordPress inventory pushes public sitemap URLs past the old
  slice boundary. Live HTTP proof after stack restart:
  `/api/content/diagnostics` returned `query_page_count=10` and
  `matched_inventory_count=10`.
- GA4 landing inventory matching preserves dimensioned landing facts even when
  aggregate GA4 facts are noisy. Live HTTP proof after stack restart:
  `/api/ga4/diagnostics` returned `landing_group_count=10`,
  `wordpress_match_count=6`; `(not set)` rows remain measurement blockers.
- Merchant decision queue now carries review-only `payload_preview` on concrete
  feed issue decisions, including sample product IDs/titles when available and
  blocked apply/API mutation state. Focused API contract tests pass for issue
  queue and grouped reporting contexts. Live HTTP proof after stack restart:
  `/api/merchant/diagnostics` decision queue entries expose
  `merchant_feed_issue_review_preview_v1`; apply/API mutation/destructive flags
  stay false.
- Localo diagnostics now expose live aggregate facts and typed
  `read_contract_statuses`. Live HTTP proof after managed stack restart:
  `live_data_available=true`, `visibility_fact_count=17`,
  `act_review_localo_visibility_facts` ready, `place_inventory`,
  `local_rankings` and `reviews` ready; `gbp_visibility`,
  `competitor_visibility` and `local_tasks` missing with explicit blocked
  claims. If Localo appears empty while metric store has facts, restart the
  managed stack before changing product logic.
- Skill hygiene now has a deterministic gate: `scripts/skill_hygiene_check.py`
  runs from `scripts/quality.sh`, blocks `Goal 001`/workaround/bugfix/outdated
  prose, English safety headings, English `with mode=vendor_read` endpoint notes
  English imperative workflow steps in WILQ skill docs and mixed-language
  `API identifiers` wording. WILQ `SKILL.md` and
  `references/output-contract.md` files now use Polish operator prose while
  preserving API IDs, endpoint paths and enum values.
- Live Ads blocker distinction: current `change_history_read_contract` is
  blocked because Google Ads returned zero change_event rows in the current
  window; current `keyword_planner_read_contract` is blocked by
  `authorizationError.DEVELOPER_TOKEN_NOT_APPROVED`, not by missing OAuth.
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

1. **Localo beyond aggregate read contracts**
   - Current Localo supports live place inventory, local rankings and reviews as
     typed aggregate read contracts.
   - Missing: GBP visibility, competitor visibility, local tasks, write/apply
     contracts and uplift claims.

2. **Skill/reference hygiene audit**
   - Obvious hygiene failures are now guarded by `scripts/skill_hygiene_check.py`.
   - Repeated output-contract language wording has been normalized across WILQ
     skills.
   - Remaining: deeper semantic review of references for product logic hidden in prose.
   - References should describe contracts and output shape only; product logic,
     workaround rules and bug fixes belong in API/schema/eval.

3. **Remaining Ads optimizer value**
   - Current Ads is review-only for many important paths.
   - Missing: approved/live Keyword Planner enrichment, forecast/audience size,
     change-history rows with pre/post performance windows, safe apply/audit
     contracts.

4. **Code quality where it affects velocity**
   - Avoid broad aesthetic refactors.
   - Extract large route modules only when they block product work, reviewability
     or focused verification.

## Next Best Queue

1. Continue with missing Localo GBP/competitor/local task read contracts, deeper
   semantic skill/reference audit or remaining Ads optimizer value based on live
   API/browser proof.
