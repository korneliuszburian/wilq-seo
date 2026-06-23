# WILQ Progress Ledger

Aktualizuj ten plik przy istotnym postępie, zmianie blockerów albo wyniku
testu skilla. To ma być krótki recovery ledger, nie pełny changelog.

Pełne archiwa:

- `docs/progress/archive/2026-06-19-progress-ledger.md`
- `docs/progress/archive/2026-06-23-progress-ledger.md`

## Maintenance Rule

- Trzymaj tutaj aktualny stan, ostatnie 3-5 slice'ów, aktywne luki i następny
  krok.
- Nie dopisuj setek linii historii. Starsze wpisy przenoś do
  `docs/progress/archive/`.
- Git, goal i dedykowane ledgery są źródłem długiej historii. Ten plik ma
  pomagać po utracie contextu.

## Current Readout

Data: 2026-06-23

Stan produktu:

- Goal 001 nadal aktywny: `docs/goals/001-goal.md`.
- WILQ API jest system brain. Dashboard i Codex skills mają korzystać z tych
  samych kontraktów API, evidence IDs, ActionObject IDs i source connectors.
- Lokalny stack prowadź przez `scripts/local_stack.sh start|stop|restart|status|logs`.
  Kanoniczne URL-e: API `http://127.0.0.1:8000`, dashboard
  `http://127.0.0.1:5173/command-center`.
- Operator-facing output ma być po polsku z polskimi znakami.
- Nie wolno naprawiać błędów reasoning przez dopisywanie edge-case'ów do skill
  references. Naprawa ma iść przez typed API state, knowledge cards, expert
  rules, context-packi, evale i dashboard.
- Ekologus jest depth-first reference client. Docelowy kierunek produktu to
  agency/multi-client, ale multi-client abstraction dopiero po tym, jak Ekologus
  działa głęboko na realnych danych i ActionObjectach.

## Last Done

1. `wilq-ga4-analyst` decision-sample eval, 2026-06-23.
   GA4 smoke now exposes compact `decision_samples` with `active_users`,
   `sessions`, `engagement_rate` and landing/source/campaign dimensions, so
   non-interactive Codex can cite real GA4 decision metrics instead of only
   decision IDs. Eval passed at
   `.local-lab/evals/codex-skill/20260623T141114Z/wilq-ga4-analyst/result.json`.
   Result: `pl-PL`, `api_used=true`, evidence count `12`,
   `operator_usefulness_score=4`, no safety findings, validated
   `act_review_ga4_tracking_quality`. The live queue has
   `fix_measurement` and `review_traffic_quality`; `review_landing_mapping`
   remains absent, so Codex must not infer landing quality from GA4 rows alone.

2. `wilq-ads-doctor` current API proof, 2026-06-23.
   Non-interactive Codex eval passed against the current WILQ API:
   `.local-lab/evals/codex-skill/20260623T130149Z/wilq-ads-doctor/result.json`.
   Result: `pl-PL`, `api_used=true`, evidence count `3`,
   `operator_usefulness_score=5`, no safety findings, and validated
   `act_prepare_ads_campaign_review_queue`,
   `act_prepare_google_ads_recommendation_review_queue`,
   `act_prepare_custom_segments_from_search_terms` and
   `act_prepare_negative_keyword_review_queue`. A first run failed on a scoped
   context-pack byte-budget reading (`210127` bytes); direct remeasure was about
   `188143` bytes and rerun passed. If it repeats, fix API context-pack
   compaction/budget stability, not skill references.

3. Merchant diagnostics decision contract, 2026-06-23.
   `/api/merchant/diagnostics` ma typed pola eliminujące błąd interpretacji z
   live-run `wilq-merchant-feed-operator`: `freshness_assessment`,
   `unknowns`, `operator_summary.decision_source=decision_queue`,
   `drilldown_source=issue_clusters`, `count_semantics=reported_issue_occurrences`
   oraz `issue_cluster_ids` na decyzjach. Live API po restartcie stacka:
   Merchant read jest `stale`, około `133.3h`, `requires_refresh=true`.
   `/merchant` pokazuje `dane do odświeżenia` i `Czego nie wiemy z Merchant API`.
   Proof: Merchant API contract tests, Merchant dashboard route test, Python
   ruff/mypy, dashboard lint/typecheck, shared-schemas typecheck, browser proof
   `.local-lab/proof/dashboard/merchant-freshness-unknowns.txt`.

4. Ads Doctor drilldown/API copy cleanup, 2026-06-23.
   Commit `92febad fix(dashboard): polish ads doctor drilldowns` oczyścił dolne
   sekcje Ads Doctor i Custom Segments z najbardziej mylącego mieszanego copy.
   Keep enum names, endpoint names, field IDs, blocked-claim keys and Google API
   resource names unchanged; marketer-facing summaries/titles/next steps should
   stay Polish.

5. Command Center and Ads first-flow copy cleanup, 2026-06-23.
   Command Center first-screen daily decision cards compose concise Polish
   marketer copy from typed API fields and metric tiles. Ads Doctor first flow
   shows review-only Ads decisions instead of raw API slang and hides raw
   `ev_*`/`act_*` from the first decision path.

## Active Gaps

- Full BDOS-class Ads optimizer is not done. Current Ads has campaign/search
  term/recommendation/budget/impression-share/change-history/business-context
  review contracts, but still blocks unsupported claims such as wasted budget,
  profitability, budget scaling, recommendation apply, CPA/ROAS verdicts and
  incrementality without stronger business/target/human confirmation contracts.
- Merchant item-by-item work is not done. WILQ has aggregate issue clusters and
  decision queue, but not product IDs/titles/SKU. Add a product-level read
  contract before claiming specific product fixes.
- Localo access works at OAuth/MCP initialize level, but WILQ still must expose
  real Localo ranking/GBP/competitor evidence before local SEO recommendations.
- Skill evals prove API usage, Polish and evidence shape, but still need stricter
  “quality of decision” assertions for each skill.
- `docs/goals/001-goal.md` is still too long. Keep it canonical for now, but
  future cleanup should preserve active requirements and archive old history.

## Next Best Queue

1. Run the next high-value Codex skill eval against current API contracts and
   record whether it produces real decisions, not only schema-valid output.
   Recommended next skill: `wilq-merchant-feed-operator` rerun after product
   level read, or `wilq-gsc-content-doctor` if the next demo focuses on SEO.
2. If an eval exposes reasoning gaps, fix typed API/dashboard contracts first,
   not skill references.
3. Add Merchant product-level read contract only if the current demo needs
   product IDs/SKU; otherwise keep Merchant as safe aggregate review.
4. Keep focused verification. Use full `scripts/verify.sh` only for final
   handoff or broad cross-surface changes.
