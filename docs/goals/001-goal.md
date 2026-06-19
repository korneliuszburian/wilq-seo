# Goal 001 - WILQ Marketing OS Active Goal

Last updated: 2026-06-19 12:48 Europe/Warsaw.

This is the only active goal file. Keep it short and current. Do not append a
chronological work log here. When a task is done, move it to the short completed
foundation list or remove it from the active queue. Git history is the detailed
archive.

## Recovery Contract

Every Codex session working on WILQ must read these files first:

1. `AGENTS.md` - operating rules, secrets policy, local paths and gotchas.
2. `docs/goals/001-goal.md` - current active goal and queue.
3. `docs/architecture/bdos-class-wilq-operating-system.md` - product bar.
4. `docs/infra/001.md` - original product scope.
5. `docs/architecture/codex-runtime.md` - skills, hooks, MCP and Codex evals.
6. `docs/audits/001-output.md` - fresh 2026-06-18 audit and next-slice critique.

Keep this file updated when connector readiness, live data status, blockers,
verification state or next tasks change.

## Product Bar

WILQ is an API-first marketing operating system for Ekologus, operated by a
Polish marketer through dashboard + Codex Desktop/CLI + WILQ skills.

WILQ is not:

- a connector dashboard,
- a prompt pack,
- a static report generator,
- a list of readiness cards,
- a place for invented marketing metrics.

The expected loop is:

1. Connector reads collect source facts.
2. WILQ normalizes facts into evidence IDs and metric facts.
3. Knowledge cards and expert rules map facts to diagnosis.
4. Opportunities and ActionObjects describe safe next moves.
5. Dashboard and Codex skills show the same evidence/action state.
6. Writes stay `dry_run -> preview -> confirm -> audit`.

Every marketer-facing response must be in Polish with Polish diacritics. Stable
API IDs, connector IDs, evidence IDs, enum values and endpoint paths remain in
their original form.

Skills are thin operator workflows over WILQ API. Do not put product decision
logic, dedupe rules, edge-case fixes or dashboard cleanup logic into skill
references. If a skill needs a smarter decision, implement the typed
API/schema/view-model first and make the skill consume that field.

## Delivery Expectation

Do not claim "better than BDOS" as done until the data/action contracts prove
it. A strong Ekologus demo can be delivered before the full product is complete:
dashboard decisions, WILQ API evidence, Polish Codex skills, ActionObject
safety, eval ledger and visible blocked claims. Ads now has a derived KPI read
contract for CTR/CPC/conversion rate/CPA/ROAS as calculations from campaign
facts, but full BDOS-class parity still requires optimizer contracts such as
account currency/profit-margin interpretation, budget pacing, recommendations,
change history, Keyword Planner enrichment, forecast or audience-size checks,
payload previews, apply safety and audit paths, plus real Localo
ranking/GBP/competitor/review read contracts. Missing contracts must be shown as
blockers, not hidden with prompt language.

## Research And Knowledge Contract

WILQ must be built from a source-backed marketing knowledge loop, not from loose
prompt intuition. The canonical source map is:

```txt
docs/research/wilq-marketing-source-map.md
```

Every serious Ads, SEO, Merchant, GA4, Ahrefs, Localo, WordPress or social
slice must follow this path:

1. Pick sources from the source map or add better current sources first.
2. Condense the source into a knowledge card, expert rule, schema contract or
   skill reference.
3. Bind the rule to required WILQ evidence fields and blocked claims.
4. Expose the result through the WILQ API before dashboard or skill polish.
5. Prove with dashboard/browser checks and `codex exec` that Polish prompts
   produce evidence-backed Polish outputs.

Research methods to preserve:

- ReAct-style loop: reason about the marketer task, call WILQ API/tooling, then
  answer from observed evidence.
- Self-RAG-style critique: retrieve only relevant evidence, check whether it is
  sufficient, then block unsupported recommendations.
- RAGAS/RAG-eval-style gates: context relevance, faithfulness to evidence,
  answer usefulness and no hallucinated metrics.
- Official platform docs first for APIs and constraints; practitioner sources
  only after the official contract is understood.
- BDOS-class product bar: diagnostics, safe actions, dry-run/preview/confirm,
  mutation/audit history, expert knowledge and multi-surface operation.

## Current Runtime Truth

Local dashboard:

```bash
http://127.0.0.1:5173/command-center
```

Local API:

```bash
http://127.0.0.1:8000/api/health
```

Use `uv run ...` for Python/WILQ commands. Do not use global `python`.

Current connector truth:

- `google_ads`: credentials are configured and live campaign-level
  `vendor_read` works after the 2026-06-18 OAuth + MCC/child-account fix.
  `596-895-8639 Agencja Proud Media` is the MCC/login customer. `Ekologus NOWY`
  is the child metrics customer. Do not call Ads an OAuth blocker unless a fresh
  read proves that. Google Ads now has live campaign rows, search-term rows,
  a derived KPI read contract for CTR/CPC/conversion rate/CPA/ROAS, a
  prepare-only custom segment candidate contract and a prepare-only negative
  keyword safety review contract. CPA/ROAS are allowed only as calculations from
  campaign facts; profitability, wasted-budget, negative keyword apply, audience
  size, budget scaling and campaign-performance claims still need explicit
  read/safety/apply contracts.
- `google_merchant_center`: live product/feed facts exist and support a review
  queue. Merchant diagnostics now distinguishes report occurrences from unique
  affected products: `/merchant` labels them as `Zgłoszenia`/`kontekst`, not
  `Affected`, and aggregate `product_count`/`issue_count` may fallback to latest
  refresh summary when issue-level metric facts are the only stored facts.
  Latest Merchant regression fix: live issue clusters can disappear when the
  Merchant metric fact read limit is too low, because newer aggregate facts push
  issue-level rows out of the window. The fix raises that limit and makes the
  Merchant skill smoke fail if live diagnostics has issues but no
  `issue_clusters`.
- `google_search_console`: query/page facts exist and support content decisions.
  Tactical/content reads now preserve complete latest metric groups per
  `(connector, evidence, dimensions)`, so query/page cards do not show false
  `impressions=0` when the same evidence group has real impressions. Latest
  GSC/content regression fix: newer aggregate GSC refresh rows can push older
  but still useful query/page facts outside a generic 300-row read window. The
  tactical/content selectors now preserve a larger GSC window for query/page
  evidence, and `wilq-gsc-content-doctor` smoke fails if query/page metric
  facts exist but `content_diagnostics.decision_queue` is empty.
- `google_analytics_4`: landing/source/campaign facts exist and
  `/api/ga4/diagnostics.decision_queue` now feeds both dashboard `/ga4` and
  `wilq-ga4-analyst`. Current live decisions are traffic-quality review; ROAS,
  revenue, conversion-drop, attribution verdict and tracking-fixed claims stay
  blocked unless conversion/cost/read contracts exist. Command Center must keep
  GA4 as `blocked` while those interpretation contracts are missing, even when
  live GA4 behavior facts exist; `ready` would imply a complete marketer
  decision and causes confusion.
- `wordpress_ekologus` and `wordpress_sklep`: inventory context exists and must
  protect against duplicate content.
- `ahrefs`: aggregate authority/rank facts exist; deeper gap workflows still
  need richer evidence.
- `localo`: MCP Server URL, OAuth Client ID/Organization ID, OAuth Client
  Secret/Create Token and local OAuth access token are configured. On
  2026-06-18, `refresh_localo_af3a75e8659e` completed a live API-triggered
  Localo MCP initialize with `mcp_initialize_status=200`, checked
  `LOCALO_ACCESS_TOKEN` and redacted the token value. No local ranking/GBP
  claim is allowed yet until WILQ API exposes Localo evidence beyond the
  OAuth/initialize probe.
- `linkedin` and `facebook`: publishing is permission-gated. Drafting can be
  prepare-only and evidence-backed; publishing cannot be claimed.
- `google_sheets`: intentionally not needed for current scope.

Known important local paths are documented in `AGENTS.md`; do not print secret
values.

## Completed Foundation

Do not rebuild these from scratch:

- Private repo, `.gitignore`, AGENTS rules, architecture docs and quality gates.
- WILQ API spine, typed schemas, connector registry, evidence registry,
  opportunities, expert rules, knowledge compiler and ActionObjects.
- Local `.env` credential runtime and redaction rules.
- SQLite local state, DuckDB metric store, Typer CLI and manual job scheduler.
- 12 repo-local WILQ skills under `.agents/skills`.
- Baseline non-interactive Codex eval harness and deterministic skill smokes.
- API-backed dashboard shell using typed frontend boundaries.
- Command Center, Merchant, Content Planner, GA4, Ads Doctor and Localo route
  surfaces.
- Google Ads OAuth helper and successful live campaign metric read.
- Real-browser Playwright smoke in `scripts/verify.sh`.
- Merchant route/API clarification for feed issues: issue clusters show report
  occurrences and context, while product-level sample IDs/titles remain blocked
  until the Merchant read contract exposes them.
- Merchant route operator cleanup: `/merchant` now shows the feed review task,
  issue clusters, translated blocked claims, ActionObject validation and
  `Dowody i ograniczenia Merchant` instead of duplicate diagnostic sections or
  English technical copy.
- Content Planner route operator cleanup: `/content-planner` now renders
  typed content decisions from `content_diagnostics.decision_queue`, blocks GA4
  tracking gaps as non-content tasks, groups GSC/WordPress decisions per URL
  and avoids false zero metrics when evidence is missing.
- GA4 route operator cleanup: `/api/ga4/diagnostics` now exposes a typed
  `decision_queue` with `fix_measurement`, `review_landing_mapping` and
  `review_traffic_quality` decisions. Dashboard `/ga4` renders this as the
  primary marketer view, keeps evidence/action IDs, and no longer shows raw
  English diagnostic section titles such as `GA4: landing/source/campaign
  behavior`, `GA4: tracking/conversion readiness` or `Analytics Safety Gate`.
- Ads Doctor route operator cleanup: `/api/ads/diagnostics` now exposes a typed
  `decision_queue` with campaign review, search-term review, custom segment
  candidate review and blocked write path decisions. Dashboard `/ads-doctor`
  renders those decisions first, keeps evidence/action traceability, translates
  status/blocked claims to Polish and no longer shows raw `Read contract Ads`,
  `Search terms read-only`, `Campaign activity read contract`, `Evidence`,
  `configured`, `READY`, `payload preview` or stale OAuth blocker copy when
  live Ads data exists.
- Localo route operator cleanup: `/api/localo/diagnostics` now exposes a typed
  access/readiness contract with missing Localo visibility contracts and blocked
  claims. Dashboard `/localo` renders `Status Localo / MCP access`,
  `Co marketer ma wiedzieć o Localo`, `Dowody i ograniczenia Localo` and a
  Localo/GBP safety gate instead of the generic tactical queue, `Metric facts`,
  `24 Taktyki` counters or stale `Dokończ Localo access` copy when MCP
  initialize already works.
- Metric store grouped batch reads for tactical/content surfaces: latest
  query/page groups keep clicks, impressions, CTR and position together instead
  of truncating by connector row count.

## Active Product Problems

These are the current reasons Goal 001 is not complete:

1. **Dashboard route audit must stay enforced, not restarted.**
   Command Center, `/actions`, `/opportunities` and `/merchant` have been
   cleaned up for the current stale Ads/Localo/readiness issues and technical
   wording. `/content-planner` has also been cleaned up around its typed
   content decision queue. `/ga4` has been cleaned up around its typed GA4
   decision queue. `/ads-doctor` has been cleaned up around its typed Ads
   decision queue. `/localo` has been cleaned up around
   `/api/localo/diagnostics`. Remaining route work is now regression control:
   every touched route must preserve the decision-first hierarchy, Polish
   operator copy, Codex bridge, evidence IDs and blocked claims. Do not
   reintroduce generic registries, readiness-only cards, stale blocker copy or
   raw metric dumps as first-screen marketer insight.

2. **Command Center and supporting registries must stay separated.**
   Evidence IDs and ActionObjects are required, but the marketer needs a clear
   "what to do now and why" hierarchy. Raw connector/status/readiness cards and
   opportunity/action registries must not masquerade as marketing insight.

   Hard block: first-screen Command Center must not render readiness-only cards
   such as `connector_configured=true`, `Connector ... ready for ... refresh`,
   `No performance metrics have been collected`, or `Run a read-only refresh`.
   Those belong in lower diagnostic/settings surfaces unless converted into a
   real decision, blocker or action.

   Fresh audit correction: canonical `DailyDecision` is the primary Command
   Center model. `operator_brief`, `action_plan`, `marketing_brief`,
   diagnostics, `/api/actions` and `/api/opportunities` are supporting
   surfaces, not competing first-screen decision queues.

3. **Ads Doctor is useful for read-only review, but not yet a full optimizer.**
   Campaign-level activity, search-term facts, custom segment candidates and
   the latest negative keyword safety review queue now have explicit
   read/decision contracts. The negative keyword queue is prepare-only safety
   review, not a waste verdict or apply path. Recommendations, quality scoring,
   budget pacing, impression share, derived CPA/ROAS, keyword/match context,
   full 90-day safety history, Keyword Planner enrichment,
   forecast/audience-size contracts and apply previews still need explicit
   read/safety/ActionObject contracts before WILQ can claim BDOS-class Ads
   optimization value.

4. **Codex skill usefulness is not fully proven end-to-end.**
   Skills have contracts and smokes, and `wilq-daily-command` now has a
   strengthened usefulness guardrail plus a fresh non-interactive eval pass.
   `wilq-content-strategist`, `wilq-ads-doctor` and
   `wilq-custom-segments` also have strict usefulness passes after their
   matching API contracts. `wilq-ga4-analyst` has now been repaired against
   `/api/ga4/diagnostics.decision_queue` and passed a fresh strict
   non-interactive eval on 2026-06-19. `wilq-localo-operator` should consume
   `/api/localo/diagnostics` for access/readiness and must continue blocking
   ranking/GBP/competitor claims until actual Localo visibility facts exist.
   Goal 001 still needs the same strict usefulness pass across the remaining
   high-value skills and a clean plug-and-play Codex session proving Polish
   prompts -> WILQ API calls -> same evidence IDs as dashboard -> useful next
   actions.

5. **Knowledge condensation is not fully proven.**
   Playbooks and knowledge cards exist, but we must prove they influence skill
   outputs and content/Ads decisions instead of sitting beside the product.
   Goal 001 must show at least one source-backed chain:
   source -> knowledge card/rule -> API view model -> dashboard card ->
   non-interactive Codex skill output.

   Current local slice moves this in the right direction for content:
   `content_diagnostics.decision_queue` is typed API state, not skill-reference
   logic. The follow-up daily context-pack slice also moved metric fact reads
   into batched/read-only API storage paths instead of skill-reference patches.

6. **Localo and social remain limited-evidence surfaces.**
   Localo access/readiness has a typed API surface in `/api/localo/diagnostics`.
   It proves MCP initialize/access state and names missing contracts, but local
   ranking/GBP/competitor/review insight remains blocked until a concrete Localo
   visibility read contract exists. Fresh `wilq-localo-operator` eval passed on
   2026-06-19 and proves this exact state: access is ready, local visibility
   insight is blocked. Social publishing remains permission-gated; drafting can
   be prepare-only and evidence-backed.

7. **Full verification after the latest changes passed.**
   `scripts/verify.sh` passed after the 2026-06-19 Localo diagnostics route
   cleanup: backend API contracts `100 passed`, dashboard route tests
   `13 passed`, Playwright e2e `9 passed` and dashboard production build
   passed. Keep this file current after every future slice.

## What WILQ Must Give The Marketer

For every meaningful screen or skill response, WILQ should answer:

- **Co widzę?** Real facts, source connector, freshness and evidence IDs.
- **Co to znaczy?** Diagnosis in Polish, with blocked claims named explicitly.
- **Co zrobić teraz?** One or more safe next actions, preferably ActionObjects.
- **Czego nie wolno twierdzić?** Missing evidence, unsupported metrics, blocked
  writes or permission gaps.
- **Jak sprawdzić?** Link/ID to evidence, action validation or dashboard route.

Examples of real value:

- Merchant: "15 product/feed issues require review; validate
  `act_review_merchant_feed_issues`; do not promise approval recovery."
- Content: "GSC + inventory WordPress suggests refresh/create/block decisions;
  do not promise ranking or lead uplift."
- GA4: "Landing/source/campaign traffic quality looks weak; review tracking and
  message match; do not claim ROAS/revenue."
- Ads: "Campaign and search-term metric facts exist, including conversion
  counts/value; review live activity and prepare safety review candidates, but
  keep profitability, wasted budget, budget scaling, negative keyword apply and
  recommendation/apply claims blocked until currency, margin, pacing,
  match-context, safety and ActionObject apply contracts exist."
- Localo: "MCP access działa (`mcp_initialize_status=200`), ale lokalna
  widoczność nie może być analizowana, dopóki WILQ API nie zbierze konkretnych
  Localo ranking/GBP/competitor facts poza initialize probe."

If a dashboard section only says "connector configured" without converting that
into a decision or blocker, it is not yet useful to the marketer.

## Plug-And-Play Acceptance Gate

Before Goal 001 can be closed, run a clean session that proves WILQ is useful
out of the box:

1. Start WILQ API and dashboard.
2. Open a fresh Codex session with repo skills available.
3. Use Polish marketer prompts:
   - `Pokaż 3 najważniejsze decyzje marketingowe na dziś dla Ekologus.`
   - `Co w Ads mogę uczciwie powiedzieć na podstawie obecnego evidence?`
   - `Którą treść odświeżyć albo stworzyć i czego nie wolno obiecywać?`
   - `Czy Merchant ma problem z produktami/feedem i jaki ActionObject sprawdzić?`
   - `Czy Localo daje już ranking/GBP insight czy nadal blocker?`
4. For each prompt compare:
   - plain Codex without WILQ skill/API context,
   - Codex using the matching WILQ skill,
   - dashboard/API view for the same evidence.
5. Pass only if the skill response:
   - is in Polish,
   - calls WILQ API or honestly reports a blocker,
   - includes source connectors and evidence IDs,
   - does not invent metrics,
   - gives a next safe action,
   - matches dashboard/API evidence for the same claim.

This gate answers the real question: can Codex + WILQ API + WILQ skills do more
for the marketer than plain Codex/manual panel work?

## MCP Decision

Do not build a WILQ MCP server just because MCP exists.

Current position:

- WILQ REST API is canonical.
- Repo skills call REST/context-pack.
- MCP servers are adapters, not the product brain.
- Localo exposes external MCP/OAuth and remains an adapter source.

A WILQ MCP server is justified only if plug-and-play testing proves that Codex
tool ergonomics or reliability are materially worse through REST/skills than
through a thin MCP surface. If built, it must wrap WILQ API and must not bypass
evidence IDs, ActionObject validation, audit logging or redaction.

## Active Queue

This is the current executable goal. Work through it in order and update this
section whenever a step is completed, blocked or replaced by a better-proven
next step.

### Audit-Derived Goal Stack

Source of truth for this stack:

```txt
docs/audits/001-output.md
```

The audit confirms the architecture direction is right: FastAPI/WILQ API is the
brain, typed schemas and evidence IDs are the product contract, and dashboard
plus Codex skills must consume the same API state. The audit also confirms the
current weakness: WILQ still sometimes presents system readiness as marketer
insight and several skills pass because they block safely, not because they
produce high-value decisions.

Work in this order:

1. **Done: content decision queue and Content Planner route cleanup.**
   `content_diagnostics.decision_queue` must remain typed API state, not skill
   reference logic. It must support `refresh_or_merge`,
   `merge_create_after_inventory_check`, `inventory_check_before_create` and
   `block_as_tracking_not_content`, with evidence IDs, source connectors,
   ActionObject IDs and blocked claims. This was committed as
   `2e0b0dc feat(content): expose content decision queue`.
   Follow-up route cleanup on 2026-06-19 made `/content-planner` render this
   decision queue as the primary marketer view, grouped duplicated GSC queries
   per URL, blocked GA4 tracking gaps as non-content work and removed stale
   labels such as `Query/page`, `WP match`, `exact_url`, `payload preview` and
   false `impressions=0` / `ctr=0` for missing evidence.

2. **Active local slice: Command Center as canonical `DailyDecision`.**
   Introduce one first-screen decision model instead of competing
   `operator_brief`, `action_plan`, `marketing_brief`, diagnostics and action
   fragments. A `DailyDecision` must include:
   `co_widzimy`, `dlaczego_to_ma_znaczenie`, `bezpieczny_next_step`,
   `blocked_claims`, `evidence_ids`, `source_connectors`, `action_ids`,
   `skill_id`, `codex_prompt` and `route`.

   Current local status: `DailyDecision` schema and
   `/api/dashboard/command-center.daily_decisions` are implemented. Dashboard
   Command Center now renders one `Dzisiejsze decyzje marketera` board instead
   of duplicating the same intent as `Dzisiejszy panel operatora` plus
   `Plan działań marketera`. Full connector blocker cards were removed from
   `/command-center`; a compact `Źródła i ograniczenia` footer links to
   `/settings` for diagnostic credential/status details. `wilq-daily-command`
   smoke validates the field and its context-pack trace. Focused API/shared
   schema/dashboard checks and Playwright Command Center/demo proof pass after
   this cleanup. Full `scripts/verify.sh` passed on 2026-06-18 for the current
   checkout: backend API contracts 97 passed, dashboard route tests 12 passed,
   Playwright e2e 8 passed and dashboard production build passed.

   Follow-up completed on 2026-06-19: `/actions` starts from
   `ActionObjecty do przeglądu` and related evidence instead of generic
   registry dumps. `/api/actions` no longer resurrects
   `act_configure_google_ads_env` after a later Ads `status_probe` when a live
   Ads `vendor_read` exists. `/opportunities` is explicitly a supporting
   registry with Polish labels and no old readiness/inventory copy. Browser
   proof with `agent-browser` found no stale Ads OAuth action, no generic
   registry dump on `/actions`, and no old readiness phrases on
   `/opportunities`. Focused Playwright e2e passed: `9 passed`.

   Follow-up completed on 2026-06-19: `/ga4` now consumes a typed
   `Ga4DecisionItem` queue from `/api/ga4/diagnostics.decision_queue` and shows
   marketer-facing decisions instead of raw `landing/source/campaign behavior`
   diagnostic sections. Browser proof found no stale phrases:
   `payload preview`, `read-only`, `Evidence`, `READY`, `configured`,
   `WP match`, `WP missing`, `landing/source/campaign`,
   `Analytics Safety Gate`, `Tracking readiness`, `conversion-like`,
   `tracking-gap checklist` or `metric_facts`. Full `scripts/verify.sh` passed
   after this slice with backend API contracts `98 passed`, dashboard route
   tests `13 passed`, Playwright e2e `9 passed` and dashboard production build
   passed.

   Follow-up completed on 2026-06-19: `/localo` now consumes
   `/api/localo/diagnostics` instead of the generic workflow/tactical surface.
   The route shows MCP access/readiness, missing visibility contracts and
   blocked Localo/GBP claims. It does not show `Local Visibility Focus`,
   `Taktyki z WILQ API`, `Metric facts`, `24 Taktyki` or stale
   `Dokończ Localo access` copy when access is already proven. Focused backend
   contract tests and dashboard route tests pass for this slice. Full
   `scripts/verify.sh` passed after this slice with backend API contracts
   `100 passed`, dashboard route tests `13 passed`, Playwright e2e `9 passed`
   and dashboard production build passed.

3. **Slice 2: performance budget and scoped runtime.**
   Command Center summary target: under 1s local and about 80-120 KB when
   feasible. Non-daily skill context-pack target: under 2s and under 200 KB.
   Full context-pack is a debug mode, not default runtime. Measure before and
   after; do not hide performance issues with random frontend memoization.

4. **Slice 3: Merchant issue-level triage.**
   Convert Merchant from `products/issues` summary into issue clusters by
   `issue_type`, `affected_attribute`, `country`, `reporting_context`, impact,
   sample products if available, evidence IDs and
   `act_review_merchant_feed_issues`. This is the strongest current demo win.

   Current status: typed `MerchantIssueCluster` exists in Python and
   shared frontend schemas. `/api/merchant/diagnostics` now returns
   `issue_clusters`, `act_review_merchant_feed_issues` carries the same cluster
   payload, and dashboard `/merchant` renders clusters as the primary review
   queue. Full `scripts/verify.sh` passed for this slice on 2026-06-18. The
   current Merchant API read contract still does not return sample product IDs
   or product titles; the UI must state that limit honestly.

   Latest Merchant follow-up after overnight context handoff: latest live check found a
   regression where `issue_count=15` but `issue_clusters=[]` because
   `MERCHANT_METRIC_FACT_LIMIT=240` was too low for the current DuckDB history.
   The fix raises the limit to `2000` and strengthens
   `wilq-merchant-feed-operator` smoke to fail on live issue data without
   clusters. Proof so far: `/api/merchant/diagnostics` on `:8015` returns
   `issue_cluster_count=11`; the Merchant smoke passes; non-interactive
   `wilq-merchant-feed-operator` eval passed at
   `.local-lab/evals/codex-skill/20260619T073915Z/wilq-merchant-feed-operator/result.json`
   with `operator_usefulness_score=5`, `act_review_merchant_feed_issues` and
   blocked feed/product mutation claims. Focused ruff/mypy/API tests passed.
   Full `scripts/verify.sh` passed after updating the stale Merchant demo e2e
   assertion: backend API contracts `102 passed`, dashboard route tests
   `13 passed`, Playwright e2e `9 passed`, skill API smoke passed and dashboard
   production build passed.

5. **Slice 4: Content/GSC/GA4/WordPress URL normalizer.**
   Normalize host, path, slash, sitemap, post/page type and GA4 landing path to
   full WordPress URL. The goal is reliable `refresh/merge/create/block`
   decisions and no duplicate content suggestions. GA4 `(not set)` remains a
   tracking issue, not a content task.

   Current local status: tactical queue now reads enough WordPress inventory
   rows from DuckDB to avoid false `missing` caused by large sitemap inventories.
   GSC full URLs and GA4 landing paths expose normalized path keys, match
   confidence and matched WordPress URL in typed API fields. Direct checkout
   proof shows BDO, Zielony Ład and remediacja GSC URLs as `found exact_url`,
   and GA4 landing paths as `found path_fallback`. Full `scripts/verify.sh`
   passed for this slice on 2026-06-18.

   Latest follow-up on 2026-06-19: content/tactical GSC selection now preserves
   older dimensioned query/page evidence even when newer aggregate GSC refreshes
   exist. Live proof on `:8016` after the fix:
   `query_page_count=10`, `matched_inventory_count=10`, `decision_count=4`
   with decisions for homepage, BDO, Zielony Ład and remediacja. Regression test
   `test_content_diagnostics_preserves_gsc_query_page_after_newer_aggregate_runs`
   seeds newer aggregate GSC runs and fails if the older query/page group is
   lost again.

6. **Slice 5: Ads Doctor read contracts.**
   Keep Ads as live campaign-level review until WILQ has explicit read
   contracts for search terms, conversions, campaign budget/spend/clicks,
   recommendations, change history, safety checks and blocked-claim matrix. Do
   not call it a money-leak optimizer until those facts exist.

   Current local status: `/api/ads/diagnostics.campaign_read_contract` is typed
   and live. It groups Google Ads metric facts into campaign rows with
   `campaign_id`, `campaign_name`, `clicks`, `impressions`, `cost_micros`,
   `conversions`, `conversion_value`, evidence IDs and blocked claims.

   Current local status: `/api/ads/diagnostics.search_terms_read_contract` is
   now typed too. Google Ads `vendor_read` queries `search_term_view` in read
   mode and stores `search_term_clicks`, `search_term_impressions`,
   `search_term_cost_micros`, `search_term_conversions` and
   `search_term_conversion_value` metric facts with campaign/ad group/search
   term dimensions. Live read `refresh_google_ads_c2f62ee2b43a` completed on
   2026-06-18 with 18 campaign rows, 50 search term rows, campaign
   `conversions=2.0`, campaign `conversion_value=2.0`, search-term
   `search_term_conversions=0.0` and
   `search_term_conversion_value=0.0`. This unlocks honest campaign/search-term
   review with conversion context, not automatic waste or negative keyword
   claims.

   Current local status: `/api/ads/diagnostics.decision_queue` is typed and
   dashboard `/ads-doctor` renders it as the primary marketer view:
   `ads_review_campaign_activity`, `ads_review_search_terms`,
   `ads_prepare_custom_segments_from_search_terms` and
   `ads_block_write_actions_without_actionobject`. Browser proof on 2026-06-19
   found no stale visible `Read contract Ads`, `Search terms read-only`,
   `Campaign activity read contract`, `Search terms read contract`,
   `Google Ads: campaign activity rows`, `Google Ads: search terms read-only rows`,
   `Evidence`, `configured`, `READY`, `payload preview`, `write/apply` or
   `WILQ ma read-only Google Ads evidence`.

   Current local status: `/api/ads/diagnostics.custom_segments_read_contract`
   is typed and ready when Google Ads search-term evidence exists. It exposes
   1 prepare-only candidate for campaign `Kompendium PPWR`, real
   `source_terms`, evidence `ev_refresh_refresh_google_ads_c2f62ee2b43a`,
   missing contracts `keyword_planner_enrichment`,
   `forecast_or_audience_size`, `custom_segment_payload_preview`, and
   ActionObject `act_prepare_custom_segments_from_search_terms`. Dashboard
   `/ads-doctor` renders these candidates; the skill `wilq-custom-segments`
   consumes the same contract.

   Fresh correction: Ads diagnostics now selects the latest Google Ads
   `vendor_read` as the evidence-bearing refresh. A later `status_probe` cannot
   downgrade live Ads state into stale OAuth blocker language. While live Ads
   data is available, `/api/marketing/brief`,
   `/api/ads/diagnostics.action_ids` and the scoped `wilq-ads-doctor`
   context-pack no longer promote `act_configure_google_ads_env`.

   Fresh skill proof: `wilq-ads-doctor` passed non-interactive Codex eval at
   `.local-lab/evals/codex-skill/20260618T191243Z/wilq-ads-doctor/result.json`.
   The output is Polish, uses WILQ API, cites
   `ev_connector_google_ads_status` and
   `ev_refresh_refresh_google_ads_c2f62ee2b43a`, shows 18 campaign read-only
   rows and 50 search-term rows, and blocks CPA/ROAS profitability verdicts,
   search-term waste, wasted budget and negative keywords until missing
   interpretation/read/safety/ActionObject contracts exist.

   Fresh negative keyword safety proof: `wilq-ads-doctor` passed a new
   non-interactive Codex eval after `negative_keywords_read_contract` and
   `act_prepare_negative_keyword_review_queue` were added:
   `.local-lab/evals/codex-skill/20260619T065511Z/wilq-ads-doctor/result.json`.
   The output is Polish, uses WILQ API, cites
   `ev_connector_google_ads_status` and
   `ev_refresh_refresh_google_ads_c2f62ee2b43a`, returns
   `negative_keywords_read_contract.status=ready`, `candidate_count=7`, one
   prepare-only ActionObject and blocked apply/waste/CPA/ROAS claims.

   Fresh manual usefulness proof: a 2026-06-19 `wilq-ads-doctor` run over live
   Ads evidence produced a useful Polish triage: 18 campaigns, 50 search-term
   rows, top campaign/search-term observations, and valid prepare-only
   ActionObjects `act_prepare_negative_keyword_review_queue` plus
   `act_prepare_custom_segments_from_search_terms`. This is recorded in
   `docs/evals/skill-eval-ledger.md`. It still blocks profitability, wasted
   budget, negative keyword apply, budget scaling and recommendation/apply
   claims until match context, full 90-day safety, payload preview, currency or
   margin interpretation, pacing, recommendations, change history and
   impression share exist.
   action candidate `act_prepare_negative_keyword_review_queue`, usefulness
   score 5 and no safety findings. It blocks `negative keyword apply`,
   search-term waste, wasted budget, CPA and ROAS without
   `90_day_safety_check`, payload preview and validated ActionObject.

   Fresh skill proof: `wilq-custom-segments` passed non-interactive Codex eval
   at
   `.local-lab/evals/codex-skill/20260619T035937Z/wilq-custom-segments/result.json`.
   The output is Polish, uses WILQ API, cites
   `ev_refresh_refresh_google_ads_c2f62ee2b43a`,
   `ev_connector_google_ads_status` and
   `ev_connector_google_search_console_status`, returns 1 recommendation and
   1 action candidate, validates
   `act_prepare_custom_segments_from_search_terms`, and blocks `audience size`,
   `ROAS`, `conversion uplift`, `targeting applied` and
   `campaign performance`.

   Latest follow-up: `/api/ads/diagnostics.negative_keywords_read_contract`
   and `act_prepare_negative_keyword_review_queue` are implemented. The
   contract builds review-only candidates from
   `search_term_*` facts with activity and zero conversions/value in current
   evidence. It requires `apply_allowed=false`, `destructive=false`, evidence
   IDs and `90_day_safety_check`. It blocks `negative keyword apply`,
   `search-term waste`, `conversion loss`, CPA and ROAS.

   Still missing for BDOS-class Ads value: recommendations, change history,
   budget pacing, impression share, keyword/match context, full 90-day safety
   history, Keyword Planner enrichment, forecast/audience-size contract, custom
   segment payload preview, margin/currency interpretation and all Ads apply
   previews. Full `scripts/verify.sh` passed after the custom
   segments slice on 2026-06-19: backend API contracts `100 passed`, dashboard
   route tests `13 passed`, Playwright e2e `9 passed` and dashboard production
   build passed. For the negative keyword safety slice, focused
   ruff/mypy/backend tests/dashboard tests/shared-schema typecheck passed, and
   full `scripts/verify.sh` passed with backend API contracts `102 passed`,
   dashboard route tests `13 passed`, Playwright e2e `9 passed`, skill API
   smoke passed and dashboard production build passed.

7. **Later P2/P3 data contracts.**
   Localo has access/readiness diagnostics, but still needs rankings, GBP
   visibility, competitors, reviews and local tasks before local SEO claims.
   Ahrefs needs competitor pages/backlink/content-gap records before gap claims.
   Custom Segments have real source terms and a prepare-only ActionObject, but
   still need Keyword Planner enrichment, forecast/audience-size and payload
   preview before any apply path. Campaign Builder needs campaign
   ActionObjects and payload preview contracts. Demand Gen needs
   creative/asset/landing-quality diagnostics. Social publishing stays explicit
   workflow only.

8. **Skill repair track: thin workflows after API contracts.**
   Skill repair is not done. It is also not the last cosmetic step. It runs
   immediately after the API/view-model contract for a workflow exists. The
   order is:
   - `wilq-daily-command` after canonical `DailyDecision`;
   - `wilq-merchant-feed-operator` after Merchant issue-level triage;
   - `wilq-content-strategist` and `wilq-gsc-content-doctor` after
     `content_diagnostics.decision_queue` and URL normalization. Fresh
     `wilq-gsc-content-doctor` eval passed on 2026-06-19 after the GSC
     query/page preservation fix:
     `.local-lab/evals/codex-skill/20260619T083631Z/wilq-gsc-content-doctor/result.json`;
   - done for `wilq-ga4-analyst` after GA4 decision queue repair; keep rerunning
     when conversion/cost/read contracts, tracking validation or richer
     landing/source/campaign classifiers are added;
   - done for `wilq-ads-doctor` after campaign table,
     search terms/conversions and blocked-claim matrix; keep rerunning when
     recommendations, change history, budget pacing, impression share, derived
     CPA/ROAS or negative keyword apply contracts are added. Fresh rerun after
     negative keyword safety review contract passed on 2026-06-19;
   - `wilq-localo-operator` after `/api/localo/diagnostics` for
     access/readiness and again after real ranking/GBP/competitor/review facts
     exist. Fresh access-ready blocker eval passed on 2026-06-19:
     `.local-lab/evals/codex-skill/20260619T072709Z/wilq-localo-operator/result.json`;
   - done for `wilq-custom-segments` after
     `ads_diagnostics.custom_segments_read_contract` and
     `act_prepare_custom_segments_from_search_terms`; keep rerunning when
     Keyword Planner enrichment, forecast/audience-size or payload preview
     contracts are added;
   - `wilq-ahrefs-gap-finder`, `wilq-campaign-builder`,
     `wilq-demand-gen-operator` and `wilq-social-publisher` only after their
     required read contracts or ActionObjects exist.

   Repair means:
   - `SKILL.md` has clean trigger intent, allowed endpoints, evidence
     requirements, blocked claims and output contract;
   - references contain durable domain guidance only, not product bug fixes,
     dedupe rules or dashboard cleanup patches;
   - deterministic smoke validates the API contract;
   - `scripts/codex_skill_eval.sh --skill <skill>` proves Polish output,
     WILQ API usage, evidence IDs, source connectors, ActionObject safety and
     a useful marketer decision for that workflow.

Stop doing, per audit:

- Do not treat `configured`, `ready for refresh`, or `connector_configured=true`
  as marketer insight.
- Do not promote LinkedIn/Facebook/social draft actions in daily flow unless
  the operator explicitly asks for social.
- Do not develop skills ahead of read contracts. Better prompts cannot replace
  missing API evidence.
- Do not load the full context-pack as default skill runtime.
- Do not put product decision repairs, dedupe rules or edge-case classifiers in
  skill references. Move them to typed API/schema/view-model contracts first.
- Do not call Ads Doctor a CPA/ROAS/search-term/wasted-budget optimizer until
  those read contracts exist.

Demo acceptance from the audit:

- First screen shows 3-5 marketer decisions, not system status.
- Every decision has evidence IDs, source connectors, blocked claims, route,
  ActionObject where applicable and a Polish Codex prompt for the matching
  skill.
- Dashboard and the matching skill return the same evidence/action IDs for the
  same marketer question.
- Skills are evaluated for usefulness, not only schema pass:
  Daily, Merchant, GA4, Content/GSC and Ads must each prove a concrete,
  evidence-backed Polish operator answer.

### 0. Preflight Truth

Goal: start from current runtime truth, not chat memory.

Tasks:

- Read `AGENTS.md`, this file, `docs/infra/001.md`,
  `docs/architecture/bdos-class-wilq-operating-system.md`,
  `docs/research/wilq-marketing-source-map.md` and
  `docs/goals/002-system-audit-and-usefulness-goal.md`.
- Check `git status --branch --short`.
- Check API and dashboard routes:
  - `http://127.0.0.1:8000/api/health`
  - `http://127.0.0.1:5173/command-center`
- Measure command-center API latency and payload size.

Pass criteria:

- current blockers are written here,
- no old Ads OAuth blocker is treated as current unless fresh API evidence says
  so,
- no credential value or secret path content is printed.

### 1. Command Center Anti-Slop Cleanup

Goal: first-screen Command Center must be useful to a Polish marketer.

Active slice handoff:

```txt
docs/handoffs/dashboard-audit-active-slice.md
docs/handoffs/command-center-second-opinion-brief.md
```

Keep this file updated while auditing dashboard routes. It contains current
agent-browser proof paths, confirmed broken/outdated surfaces and the next
implementation queue. If context is lost, resume from that handoff before
editing more dashboard code.

Current product correction:

- Stop treating Command Center as a place to display every available metric.
- Command Center must become a decision cockpit for the Polish marketer.
- Each top-level item must explain:
  - `co widzę`,
  - `co to znaczy`,
  - `co zrobić teraz`,
  - `czego nie wolno twierdzić`,
  - `jak Codex może pomóc`.
- Raw metric facts, query/page rows, GA4 landing/source rows and Merchant issue
  rows belong in dedicated diagnostic routes unless condensed into one decision.
- Codex skills are the operating layer: from a Command Center decision, the
  marketer should be able to run a matching WILQ skill that calls WILQ API,
  returns Polish evidence-backed output, prepares safe briefs/drafts/action
  previews, and blocks unsupported claims.
- Skill trigger descriptions must be written for real marketer intent, not for
  internal connector names. Example prompts that must route naturally:
  `pokaż przestrzeń do polepszenia adsów w Ekologus`,
  `znajdź ostatnie kampanie i ich efekty`,
  `które treści odświeżyć najpierw`,
  `czy feed produktowy jest OK`,
  `sprawdź jakość ruchu z GA4`,
  `jak poprawić lokalną widoczność`.
- Command Center action cards must expose the Codex bridge explicitly:
  `skill_id`, Polish `codex_prompt`, `codex_context_endpoint`,
  `expected_codex_output`, evidence IDs, ActionObject IDs and blocked claims.
  Without this bridge, the dashboard is only a data UI and Codex is not an
  operating layer.
- Before broad UI changes continue, use the second-opinion brief to validate
  the information architecture and next slices.

Tasks:

- Audit `/command-center` top-to-bottom with browser proof after the page
  settles. Current proof:
  `.local-lab/proof/dashboard-audit/text/command-center-final-slice.txt`.
- Remove, rewrite or demote readiness-only cards:
  - `connector_configured=true`,
  - `Connector ... ready for ... refresh`,
  - `No performance metrics have been collected`,
  - `Run a read-only refresh`,
  - social/local/connector debug cards that do not create a decision.
- Keep evidence IDs, ActionObjects and blockers, but present them as decisions:
  `co widzę`, `co to znaczy`, `co zrobić teraz`, `czego nie wolno twierdzić`,
  `jak Codex może pomóc`.
- Fix duplicate React keys and any UI warnings observed in browser console.
- Keep dashboard labels in Polish with Polish diacritics.
- Preserve the 2026-06-18 cleanup: `Dzisiejszy panel operatora` is only a
  compact status/header; detailed decision cards live only in
  `Plan działań marketera`.
- Preserve the 2026-06-18 cleanup: Command Center must not show
  `Demo dla marketera`, visible `PRIORITY N`, GA4 `(not set)` tactical cards,
  Localo OAuth probe/debug metric facts, `Freshness: unknown - Credential
  presence only`, `connector_configured`, or `Run a read-only`.
- Preserve the 2026-06-18 Localo correction: Command Center and `/localo` must
  say "access działa, brak ranking/GBP facts", not "dokończ access", after a
  completed Localo MCP initialize proof.
- Preserve the 2026-06-18 brief dedupe: `/api/marketing/brief` and generated
  ActionObjects must show the latest metric fact per
  `(source_connector, metric_name, dimensions)` and must not repeat the same
  aggregate metrics from older refresh runs.
- Preserve the 2026-06-18 brief scope cleanup: `/api/marketing/brief` is a
  marketer decision brief, not a connector inventory. Optional social/missing
  credential items such as LinkedIn/Facebook and disabled Sheets must not show
  as global blockers in `what_blocks_us`; social draft ActionObjects may exist
  in `/api/actions`, but they must not be promoted into brief
  `safe_next_actions` until social becomes an active marketer workflow.
- Preserve the 2026-06-18 skill eval ledger: real skill prompt runs and their
  usefulness findings belong in `docs/evals/skill-eval-ledger.md`; latest
  runtime/progress/performance state belongs in `docs/PROGRESS.md`.
- Preserve the 2026-06-18 context-pack performance finding:
  `/api/codex/context-pack` measured about 9.15s and 940 KB for
  `wilq-content-strategist`, mostly because it embeds broad state including
  hundreds of evidence summaries and multiple diagnostics. The next runtime
  optimization should be skill-scoped context packs, not random frontend
  memoization.
- 2026-06-18 follow-up: `wilq-content-strategist` now receives a skill-scoped
  context-pack by default. Local proof after API restart: full pre-scope pack
  about 8.106s / 940864 bytes; scoped content pack about 2.679s / 154334 bytes.
  Smoke still passes with `content_live=True`, `query_page_count=10`,
  action IDs `act_review_ga4_tracking_quality` and
  `act_prepare_content_refresh_queue`.
- 2026-06-18 follow-up: deterministic smoke suite passed for 12/12 WILQ skills
  after scoped context-pack changes. Summary artifact:
  `.local-lab/evals/skill-smoke-summary-20260618T093210Z.jsonl`. This proves
  API contract health, not final `codex exec` usefulness; non-interactive
  Codex evals are still required.
- 2026-06-18 follow-up: first real non-interactive Codex eval passed for
  `wilq-content-strategist`:
  `.local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`, evidence IDs,
  source connectors and `act_prepare_content_refresh_queue` as a safe candidate.
  Remaining quality gap: this eval is still too broad and must evolve to assert
  concrete content decisions (`refresh`, `merge/create-after-inventory-check`,
  `block`) rather than only schema-safe recommendations.
- 2026-06-18 follow-up: second real non-interactive Codex eval passed for
  `wilq-merchant-feed-operator`:
  `.local-lab/evals/codex-skill/20260618T094236Z/wilq-merchant-feed-operator/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`,
  `google_merchant_center` evidence IDs, live Merchant facts
  (`product_count=10900`, `issue_count=15`) and
  `act_review_merchant_feed_issues` as the safe pending-validation review path.
  Remaining quality gap: future Merchant evals should assert issue-level
  clustering and explicit ActionObject validation proof.
- 2026-06-18 follow-up: third real non-interactive Codex eval passed for
  `wilq-ga4-analyst`:
  `.local-lab/evals/codex-skill/20260618T101220Z/wilq-ga4-analyst/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`,
  `google_analytics_4` evidence IDs and
  `act_review_ga4_tracking_quality` as the safe pending-validation review path.
  It correctly blocks ROAS/revenue/conversion claims without stronger evidence.
  Remaining quality gap: future GA4 evals should assert ranked
  landing/source/campaign diagnostic items and explicit ActionObject validation
  proof.
- 2026-06-19 follow-up: `wilq-ga4-analyst` now consumes
  `/api/ga4/diagnostics.decision_queue` as the primary decision source. Fresh
  runtime proof after API restart showed `live_data_available=true`,
  `landing_group_count=10`, `decision_count=6` and
  `act_review_ga4_tracking_quality`. Fresh non-interactive Codex eval passed:
  `.local-lab/evals/codex-skill/20260619T032712Z/wilq-ga4-analyst/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`, GA4 evidence IDs,
  `review_traffic_quality` decisions, pending validation for
  `act_review_ga4_tracking_quality`, and blocked ROAS/revenue/conversion/
  attribution/tracking-fixed claims. Remaining gap: no current evidence
  exercises `fix_measurement` or `review_landing_mapping`, and ActionObject
  validation is still pending.
- 2026-06-18 follow-up: fourth real non-interactive Codex eval passed for
  `wilq-gsc-content-doctor`:
  `.local-lab/evals/codex-skill/20260618T101550Z/wilq-gsc-content-doctor/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`,
  GSC/WordPress evidence IDs, `content_diagnostics.live_data_available=true`,
  `query_page_count=10`, `matched_inventory_count=0` and
  `act_prepare_content_refresh_queue` as the safe pending-validation content
  queue path. Remaining quality gap: future GSC evals should assert concrete
  query/page candidates with `refresh`, `merge`, `create` or `block` decisions.
- 2026-06-18 follow-up: `wilq-daily-command` was hardened after Command Center
  and brief cleanup. Deterministic smoke now fails if daily context loses core
  ActionObjects or reintroduces social draft actions. Fresh non-interactive
  Codex eval passed:
  `.local-lab/evals/codex-skill/20260618T112920Z/wilq-daily-command/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`, 14 evidence IDs, core
  ActionObject candidates only, no safety findings and
  `operator_usefulness_score=5`.
- 2026-06-18 active local slice: `content_diagnostics.decision_queue` moved
  content classification into typed WILQ API. Fresh eval passed at
  `.local-lab/evals/codex-skill/20260618T114810Z/wilq-content-strategist/result.json`.
  It uses API decisions `inventory_check_before_create`,
  `merge_create_after_inventory_check` and `block_as_tracking_not_content`.
  The follow-up route cleanup is documented in `docs/PROGRESS.md`; resume route
  audit on `/ga4`, `/ads-doctor` and `/localo`.
- Performance direction: follow TanStack/React guidance by avoiding client
  waterfalls and duplicated data models. Do not patch this with random
  `useMemo`; next performance slice should build a lightweight daily-decision
  view model or short-lived materialized cache for the first screen.

Pass criteria:

- `agent-browser` or Playwright proof shows no readiness slop on the first
  screen,
- marketer sees concrete daily decisions and tactical work, not connector
  inventory,
- dashboard unit/e2e tests assert the slop is absent.
- `/api/dashboard/command-center` remains materially faster than the previous
  6-7s baseline. Latest proof after parallel diagnostics:
  1.95-2.32s live-server response time.
- Latest proof after Localo + brief cleanup:
  - `http://127.0.0.1:8000/api/dashboard/command-center` returns
    `daily_localo_readiness.status=ready`, title
    `Localo: MCP access działa, brak jeszcze ranking/GBP facts`, and
    `plan_localo_access_ready_wait_for_visibility_facts`.
  - `http://127.0.0.1:8000/api/marketing/brief` has
    `duplicates_found=False` for item-local metric facts.
  - Latest live proof for `/api/marketing/brief` after restart:
    `what_we_know=6`, `what_blocks_us=0`, `safe_next_actions=3`,
    `recommended_focus=2`, duplicate item IDs `0`, duplicate metric facts `0`.
    Core brief actions are only:
    `act_review_merchant_feed_issues`,
    `act_review_ga4_tracking_quality`,
    `act_prepare_content_refresh_queue`.

### 2. Source-To-Product Condensation

Goal: prove that research sources shape WILQ behavior, not only docs.

Tasks:

- Pick one high-value chain from `docs/research/wilq-marketing-source-map.md`.
  Preferred first chain:
  Google Ads or GSC/content because these matter most to the marketer demo.
- Encode the source-backed rule in the right product layer:
  - expert YAML / knowledge card,
  - schema/API view model,
  - dashboard card,
  - skill reference or prompt contract.
- Define required evidence fields and blocked claims.
- Use official docs first, then practitioner/academic sources only where they
  add operating value.

Pass criteria:

- one visible dashboard decision can be traced:
  source -> knowledge/rule -> API -> dashboard -> skill/eval,
- no rule exists only as prompt prose,
- blocked claims are explicit.

### 3. API And Skill Integration Proof

Goal: prove Codex + WILQ API + skills are better than plain Codex.

Tasks:

- Run real `codex exec` or Codex CLI/Desktop prompts against the local WILQ API.
- Use Polish prompts:
  - `Pokaż 3 najważniejsze decyzje marketingowe na dziś dla Ekologus.`
  - `Co w Ads mogę uczciwie powiedzieć na podstawie obecnego evidence?`
  - `Którą treść odświeżyć albo stworzyć i czego nie wolno obiecywać?`
  - `Czy Merchant ma problem z produktami/feedem i jaki ActionObject sprawdzić?`
  - `Czy Localo daje już ranking/GBP insight czy nadal blocker?`
- Compare plain Codex answer vs WILQ-skill/API answer vs dashboard/API state.

Pass criteria:

- WILQ answer is in Polish,
- WILQ answer uses API or reports blocker,
- WILQ answer includes evidence IDs/source connectors,
- WILQ answer avoids invented metrics,
- WILQ answer gives a safe next action,
- WILQ answer matches dashboard/API for the same claim.

Current eval progress:

- `wilq-daily-command`: strengthened and re-evaluated at
  `.local-lab/evals/codex-skill/20260618T112920Z/wilq-daily-command/result.json`.
  Strong daily pass: Merchant, Content and GA4 core action candidates only;
  Localo/social are not promoted without explicit evidence/workflow.
- `wilq-content-strategist`: passed non-interactive Codex eval at
  `.local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json`.
  Safe, API-backed, but future eval must force concrete
  `refresh`/`merge`/`create`/`block` decisions.
- `wilq-merchant-feed-operator`: passed at
  `.local-lab/evals/codex-skill/20260618T094236Z/wilq-merchant-feed-operator/result.json`.
  Strong Merchant pass with `product_count=10900`, `issue_count=15` and
  `act_review_merchant_feed_issues`.
- `wilq-ga4-analyst`: strict decision_queue pass at
  `.local-lab/evals/codex-skill/20260619T032712Z/wilq-ga4-analyst/result.json`.
  The skill uses `/api/ga4/diagnostics.decision_queue`, returns
  `review_traffic_quality` decisions with GA4 evidence IDs, carries
  `act_review_ga4_tracking_quality` as pending validation, and blocks
  ROAS/revenue/conversion/attribution/tracking-fixed claims.
- `wilq-gsc-content-doctor`: passed at
  `.local-lab/evals/codex-skill/20260618T101550Z/wilq-gsc-content-doctor/result.json`.
  Safe GSC/content pass; future eval must force concrete query/page decisions.
- `wilq-ads-doctor`: passed at
  `.local-lab/evals/codex-skill/20260618T102132Z/wilq-ads-doctor/result.json`.
  Important correction: Ads is currently live campaign review, not OAuth repair.
  The skill may use campaign and search-term evidence from `google_ads`, plus
  read-only derived KPI rows. It must still block profitability, wasted budget,
  negative keyword apply, budget scaling and recommendation/apply claims until
  WILQ exposes stronger interpretation, safety and apply contracts.
- `wilq-localo-operator`: passed at
  `.local-lab/evals/codex-skill/20260618T102743Z/wilq-localo-operator/result.json`.
  Important correction: Localo is currently access-ready, not missing
  `LOCALO_ACCESS_TOKEN`; however, the skill must still block ranking, GBP,
  competitor and local visibility uplift claims until WILQ exposes Localo facts
  beyond MCP initialize/access readiness.
- `wilq-daily-command`: passed at
  `.local-lab/evals/codex-skill/20260618T103758Z/wilq-daily-command/result.json`.
  This proves the top-level Polish daily loop across Command Center,
  MarketingBrief and context-pack: Merchant first, then Content/GA4/Ads/Localo
  with evidence IDs and safe next actions. Cleanup still needed:
  LinkedIn/Facebook draft ActionObjects can leak into daily action candidates
  from the wider `marketing_brief.action_ids`; daily primary actions should stay
  focused on core marketer decisions unless social is explicitly requested.
- `wilq-campaign-builder`: passed at
  `.local-lab/evals/codex-skill/20260618T104154Z/wilq-campaign-builder/result.json`.
  This is a safety/blocker pass, not campaign creation proof. It confirms
  Ads/GA4/GSC evidence access, then blocks campaign candidate and payload
  preview because WILQ lacks a campaign-specific ActionObject, keyword/asset
  evidence, budget facts and validated campaign payload contract.
- `wilq-custom-segments`: passed at
  `.local-lab/evals/codex-skill/20260618T104644Z/wilq-custom-segments/result.json`.
  This is an anti-hallucination pass. It blocks audience/custom segment
  candidates because WILQ currently has aggregate Ads/GSC facts, but not real
  source terms/search terms/query evidence with lineage.
- `wilq-demand-gen-operator`: passed at
  `.local-lab/evals/codex-skill/20260618T105005Z/wilq-demand-gen-operator/result.json`.
  This is a guardrail pass with low usefulness (`operator_usefulness_score=3`).
  It correctly blocks Demand Gen recommendations because WILQ has aggregate
  Ads/GA4/Merchant readiness only, not asset, creative, landing-quality,
  migration diagnostics or a Demand Gen-specific ActionObject.
- `wilq-ahrefs-gap-finder`: passed at
  `.local-lab/evals/codex-skill/20260618T105335Z/wilq-ahrefs-gap-finder/result.json`.
  This is a guardrail pass with low usefulness (`operator_usefulness_score=3`).
  It correctly blocks backlink/competitor/content gap claims because WILQ has
  aggregate Ahrefs authority metrics plus GSC/WordPress context, but no concrete
  Ahrefs gap records.
- `wilq-social-publisher`: passed at
  `.local-lab/evals/codex-skill/20260618T105649Z/wilq-social-publisher/result.json`.
  This is a strong safety pass. It exposes LinkedIn/Facebook draft ActionObjects
  but blocks publishing and draft claims because social credentials and
  ActionObject validation are missing.

Current eval coverage: 12/12 WILQ skills have recorded non-interactive Codex
evals, and GA4 has a fresh strict decision_queue rerun. This proves API
integration and guardrails, not Goal 001 completion. The next product work must
convert eval findings into fixes: Localo facts, Ahrefs gap records,
source-term/custom-segment evidence, campaign ActionObjects, Demand Gen
diagnostics and the final plug-and-play Codex acceptance session.

### 4. Performance Slice

Goal: Command Center must feel usable, not wait ~15 seconds for avoidable work.

Tasks:

- Measure:
  - `/api/dashboard/command-center`,
  - `/api/marketing/tactical-queue`,
  - `/api/metrics?limit=80`,
  - dashboard first meaningful render.
- Identify whether bottleneck is backend joins, payload size, duplicate frontend
  fetches, rendering volume or dev-server overhead.
- Prefer small fixes:
  - remove unused first-screen fetches,
  - lazy-load secondary panels,
  - truncate long evidence lists,
  - cache expensive view-model joins,
  - avoid broad refactors until measured.

Pass criteria:

- before/after timing is recorded here,
- first-screen work is reduced or a precise blocker remains,
- no performance fix removes required evidence/action traceability.

Current slice result:

- Implemented scoped default context-pack for
  `POST /api/codex/context-pack {"skill":"wilq-daily-command"}`.
- Default daily context now includes `command_center`, `marketing_brief`, core
  daily ActionObjects, relevant connector status, relevant evidence summaries,
  knowledge cards, expert rules and expert capabilities.
- Default daily context no longer embeds `tactical_queue`, Ads/Merchant/Content
  or GA4 diagnostics. Full context remains available through
  `{"skill":"wilq-daily-command","full_context":true}`.
- Baseline from the old `:8000` runtime before this slice:
  - command-center: `5.937s`, `30521 bytes`;
  - marketing brief: `1.648s`, `46310 bytes`;
  - daily context-pack: `15.030s`, `996121 bytes`;
  - daily full context-pack: `11.734s`, `996121 bytes`.
- Fresh `:8011` runtime proof after this slice:
  - default daily context-pack: `2.888s`, `160053 bytes`;
  - repeated default daily context-pack: `2.985s`, `160053 bytes`;
  - repeated default daily context-pack: `2.959s`, `160053 bytes`;
  - full daily context-pack: `6.465s`, `998704 bytes`;
  - marketing brief: `0.541s`, `46072 bytes`;
  - command-center: `2.424s`, `30521 bytes`;
  - repeated command-center: `2.094s`, `30521 bytes`;
  - repeated command-center: `2.102s`, `30521 bytes`.
- Metric store read paths now use batch DuckDB reads and read-only DuckDB
  connections when the DB file already exists. This removes the conflicting
  lock failure observed when local profiling and the running `:8000` API read
  `.local-lab/state/wilq.duckdb` at the same time.
- Current follow-up adds a shared `DailyRuntime` for daily Codex context:
  `command_center`, `marketing_brief` and core daily ActionObjects are built
  from one connector/action/refresh snapshot and cached for a short TTL.
  `WILQ_DAILY_RUNTIME_CACHE_SECONDS` controls the TTL, default `2`; tests
  disable the cache. The cache is invalidated after connector refresh and
  action validation/apply paths.
- Fresh helper API proof on `:8011` after this follow-up:
  - default daily context: `3.047s` cold, then `0.467s`, `0.544s`, `0.470s`
    warm within TTL;
  - payload size stayed `160478 bytes`;
  - `/api/dashboard/command-center`: `2.034s`, `2.029s`, `2.396s`;
  - `/api/marketing/brief`: `0.618s`, `0.608s`, `0.588s`.
- Focused proof passed:
  ```bash
  uv run ruff check apps/api/wilq_api/main.py wilq/briefing/command_center.py wilq/briefing/daily_runtime.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
  uv run mypy apps/api/wilq_api/main.py wilq/briefing/command_center.py wilq/briefing/daily_runtime.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
  uv run pytest tests/test_api_contracts.py -q -k 'daily_runtime_reuses_preloaded_daily_inputs or codex_context_pack_embeds_marketing_brief_contract or command_center_exposes_polish_operator_brief or daily_context_pack_excludes_social_draft_action_objects or codex_context_pack_contains_no_metric_invention_instruction or codex_context_pack_includes_expert_rule_summaries'
  uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8011
  ```
- Full proof passed:
  ```bash
  scripts/verify.sh
  ```

Completed follow-up on 2026-06-19, pushed as
`35d8be3 perf(api): share daily runtime endpoints`:

- Public dashboard endpoints are being moved onto the same `DailyRuntime`
  cache:
  - `GET /api/dashboard/command-center` ->
    `build_daily_runtime().command_center`;
  - `GET /api/marketing/brief` ->
    `build_daily_runtime().marketing_brief`.
- This is the next real bottleneck after scoping daily Codex context-pack:
  Command Center, Marketing Brief and Codex daily context should share one
  daily view-model in the API process instead of rebuilding overlapping daily
  state through separate endpoint paths.
- Changed files were:
  - `apps/api/wilq_api/main.py`,
  - `tests/test_api_contracts.py`,
  - `docs/CONTEXT.md`,
  - `docs/PROGRESS.md`,
  - `docs/goals/001-goal.md`.
- Added/updated tests:
  - `test_command_center_endpoint_uses_daily_runtime_cache`,
  - `test_marketing_brief_endpoint_uses_daily_runtime_cache`.
- Focused checks passed after adding both endpoint regression tests:
  ```bash
  uv run ruff check apps/api/wilq_api/main.py tests/test_api_contracts.py
  uv run mypy apps/api/wilq_api/main.py tests/test_api_contracts.py
  uv run pytest tests/test_api_contracts.py -q -k 'command_center_endpoint_uses_daily_runtime_cache or marketing_brief_endpoint_uses_daily_runtime_cache or daily_runtime_reuses_preloaded_daily_inputs or codex_context_pack_embeds_marketing_brief_contract or marketing_brief_aggregates_metric_facts_and_blockers'
  ```
- Result: ruff passed, mypy passed, pytest 5 selected tests passed.
- Broader route/API proof also passed:
  ```bash
  uv run pytest tests/test_api_contracts.py -q -k 'command_center or marketing_brief or daily_runtime or context_pack'
  pnpm --filter @wilq/dashboard typecheck
  pnpm --filter @wilq/dashboard test -- --run App.test.tsx
  ```
- Result: backend selected tests 17 passed, dashboard typecheck passed,
  dashboard route tests 13 passed.
- Full proof passed:
  ```bash
  scripts/verify.sh
  ```
- Result: backend API contracts 102 passed, dashboard route tests 13 passed,
  Playwright e2e 9 passed, skill API smoke passed and dashboard production
  build passed.
- Non-blocking warning: Vite reports the main JS chunk is above 500 KB. This is
  now a known future performance issue, not a blocker for this API runtime
  slice.

Remaining blocker:

- Payload size, DuckDB read stability and warm daily Codex context are much
  better, but cold runtime is not done. The remaining cost is inside Command
  Center diagnostics/tactical joins and should be reduced by the next product
  slices: Merchant issue-level triage, URL normalization and slimmer
  `DailyDecision` data. Do not hide this in skill references.

Completed 2026-06-19 follow-up, pushed as
`ad17223 perf(api): slim command center runtime`:

- `build_command_center_response()` and `build_command_center_brief()` now
  accept preloaded `tactical_queue` and `actions`, so DailyRuntime can build
  Command Center without refetching action/tactical state.
- Command Center no longer builds full Content Diagnostics, GA4 Diagnostics and
  Merchant Diagnostics just to render first-screen daily cards. Content and GA4
  summaries are derived from the already-built tactical queue; Merchant summary
  reads `google_merchant_center` metric facts directly and keeps full issue
  clustering on `/merchant`.
- Measured before this follow-up from local direct profiling:
  - `build_command_center_response()`: about `4.896s`;
  - `build_daily_runtime()`: about `6.600s`;
  - after removing Content/GA4 duplicate diagnostics:
    `build_command_center_response()` about `2.7-2.8s`;
  - after replacing Merchant Diagnostics in Command Center:
    `build_command_center_response()` about `1.685-2.073s`,
    `build_daily_runtime()` about `2.053-2.104s`.
- HTTP proof on fresh `:8016` after this follow-up:
  - cold `GET /api/dashboard/command-center`: `2.526s`, `26629 bytes`;
  - warm repeated Command Center within TTL: `0.011-0.012s`;
  - `POST /api/codex/context-pack {"skill":"wilq-daily-command"}`:
    `0.882-0.934s` while warm, `3.451s` after TTL expiry, `171000 bytes`.
- Full `scripts/verify.sh` passed after this follow-up:
  - backend API contracts: `103 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill API smoke and dashboard production build passed.
- This is useful progress, not final performance completion. The next
  bottleneck is the daily context-pack after cache expiry and any remaining
  route-level render cost in the dashboard. Keep evidence IDs, ActionObject IDs
  and blocked claims intact when optimizing.

Active 2026-06-19 follow-up:

- Daily Codex context-pack now reuses `DailyRuntime.refresh_runs` instead of
  calling `list_connector_refresh_runs()` again.
- Daily Codex context-pack now uses targeted `list_evidence_by_ids()` instead
  of scanning the full evidence registry. Metric-fact evidence can be fetched
  directly by evidence ID through DuckDB.
- Focused proof passed:
  ```bash
  uv run ruff check apps/api/wilq_api/main.py wilq/evidence/registry.py wilq/storage/metric_store.py wilq/briefing/daily_runtime.py tests/test_api_contracts.py
  uv run mypy apps/api/wilq_api/main.py wilq/evidence/registry.py wilq/storage/metric_store.py wilq/briefing/daily_runtime.py
  uv run pytest tests/test_api_contracts.py -q -k 'codex_context_pack_embeds_marketing_brief_contract or list_evidence_by_ids_returns_metric_fact_evidence_without_full_scan or daily_runtime_reuses_preloaded_daily_inputs or codex_context_pack_includes_compiled_knowledge_cards or daily_context_pack_excludes_social_draft_action_objects or command_center_endpoint_uses_daily_runtime_cache or marketing_brief_endpoint_uses_daily_runtime_cache'
  uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
  ```
- HTTP proof on local `:8000` after this follow-up:
  - `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` cold after
    TTL: `2.548s`, `171000 bytes`;
  - warm repeats: `0.273s` and `0.324s`, `171000 bytes`;
  - `GET /api/dashboard/command-center` after TTL: `2.009s`,
    `26629 bytes`;
  - warm Command Center: `0.008s`, `26629 bytes`.
- Full `scripts/verify.sh` passed after this follow-up:
  - backend API contracts: `106 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill structure smoke, skill API smoke and dashboard production
    build passed.
- This improves the known daily context-pack TTL spike, but does not close the
  full performance budget. Remaining future work: smaller dashboard JS chunk,
  lower cold DailyRuntime cost and richer value contracts rather than hidden
  frontend-only memoization.

Current hook-runtime fix:

- The Stop hook must never print plain text on stdout when Codex expects Stop
  hook JSON. The observed failure was:
  `Stop hook (failed): hook returned invalid stop hook JSON output`.
- `.codex/hooks/stop_log.py` now emits valid JSON with `continue=true` when it
  skips run logging because WILQ API is unreachable or because the configured
  API URL is unsupported. This keeps WILQ API unreachable as context, not as a
  hook failure.
- `.codex/hooks.json` must use `uv run python` from repo root, not global
  `python3`.
- Regression proof must cover unreachable local API and parse stdout as JSON.
- Full `scripts/verify.sh` passed after the hook fix:
  - backend API contracts: `105 passed`;
  - dashboard route tests: `13 passed`;
  - Playwright e2e: `9 passed`;
  - API smoke, skill smokes and dashboard production build passed.

### 5. Verification And Commit

Goal: finish with proof, not vibes.

Required focused checks after touched surfaces:

```bash
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run pytest tests/test_api_contracts.py -q
```

Required full gate:

```bash
scripts/verify.sh
```

Commit rules:

- Conventional Commits only.
- Do not commit `.env`, `.local-lab`, traces, screenshots, secrets or protected
  client data.
- Update this goal before commit with:
  - completed step,
  - proof commands,
  - remaining blockers,
  - next step.

## Immediate Next Tasks

1. **Preserve the cleaned marketer routes and move to value contracts.**
   Command Center, `/merchant`, `/content-planner`, `/ga4`, `/ads-doctor`,
   `/localo`, `/actions` and `/opportunities` have current decision-first
   cleanup proof. Do not restart those audits unless browser proof shows a
   regression. Next product work should add missing value contracts: Localo
   visibility facts, Ahrefs gap records, source-term/custom-segment evidence,
   campaign ActionObjects and Demand Gen diagnostics.

2. **Keep supporting registries out of first-screen decision flow.**
   `/actions` is now ActionObject review, and `/opportunities` is now a
   supporting registry. Do not reintroduce them as duplicated Command Center
   decision queues unless a typed API model adds a new, useful marketer
   decision.

3. **Improve route usefulness, not just wording.**
   For every route cleanup, prefer typed API/view-model changes over copy-only
   patches. If a card has only connector readiness, convert it into a real
   decision, honest blocker, ActionObject validation path or remove it from the
   marketer route.

4. **Run focused verification after every route slice.**
   Minimum:
   ```bash
   uv run ruff check <touched-python-files>
   uv run mypy <touched-python-files>
   uv run pytest tests/test_api_contracts.py -q -k '<relevant-tests>'
   pnpm --filter @wilq/dashboard lint
   pnpm --filter @wilq/dashboard typecheck
   pnpm --filter @wilq/dashboard test -- --run App.test.tsx
   WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts
   ```

5. **Run full verification before commit.**
   Required:
   ```bash
   scripts/verify.sh
   ```

6. **Run stricter Codex/API proof for the next high-value gap.**
   Use `codex exec` or Codex Desktop/CLI against the local WILQ API. Plain
   static prompt evaluation is not enough. The proof must show API use, Polish
   output, evidence IDs, source connectors, blocked claims and safe next actions.
   GA4 now has a strict decision_queue rerun. Continue with Localo after real
   visibility facts, or Ahrefs/custom-segments/campaign-builder after their API
   read/action contracts exist.

7. **Commit semantically and push.**
   Use Conventional Commits only. Do not commit `.env`, `.local-lab`, test
   traces or secrets.

8. **Run plug-and-play Codex acceptance session.**
   Add only the final result and any active blockers back into this file.

## Latest Focused Verification

Passed after the 2026-06-19 GA4 blocked-copy correction and manual
`wilq-ads-doctor` usefulness proof:

```bash
uv run ruff check wilq/briefing/command_center.py tests/test_api_contracts.py
uv run mypy wilq/briefing/command_center.py
uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief'
pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-demo-proof.spec.ts --workers=1
scripts/verify.sh
```

Result:

- Live `/api/dashboard/command-center` now exposes
  `decision_review_ga4_landing_quality` as `blocked`, with title
  `GA4: brak danych do oceny ruchu` and copy that frames `/ga4` as a missing
  contract diagnostic, not a ready performance recommendation.
- Manual `wilq-ads-doctor` proof is recorded in
  `docs/evals/skill-eval-ledger.md`: 18 campaigns, 50 search-term rows,
  Google Ads evidence IDs, valid prepare-only ActionObjects and blocked
  waste/profitability/apply claims.
- Focused checks passed: ruff, mypy, selected backend contract test and
  targeted Playwright demo proof.
- Full gate passed: backend API contracts `106 passed`, dashboard route tests
  `13 passed`, Playwright e2e `9 passed`, API smoke, skill structure smoke,
  skill API smoke and dashboard production build passed. Non-blocking warning:
  Vite main JS chunk remains above 500 KB.

Passed after the 2026-06-19 `wilq-ga4-analyst` decision_queue repair:

```bash
uv run ruff check wilq/briefing/ga4_diagnostics.py .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py
uv run mypy wilq/briefing/ga4_diagnostics.py .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py wilq/schemas.py
uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q -k 'ga4_diagnostics or route_specific'
uv run python .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 CODEX_SKILL_EVAL_TIMEOUT=300 scripts/codex_skill_eval.sh --skill wilq-ga4-analyst --api-base http://127.0.0.1:8000
scripts/verify.sh
```

Result:

- API runtime proof: `live_data_available=true`, `landing_group_count=10`,
  `decision_count=6`.
- Deterministic smoke: passed with `act_review_ga4_tracking_quality`, GA4
  evidence IDs and supported decision types.
- Non-interactive Codex eval: passed at
  `.local-lab/evals/codex-skill/20260619T032712Z/wilq-ga4-analyst/result.json`.
- Narrow backend checks: ruff passed, mypy passed, focused pytest `3 passed`.
- Full gate: backend API contracts `100 passed`, dashboard route tests
  `13 passed`, Playwright e2e `9 passed` and dashboard production build passed.

Passed after the 2026-06-19 Ads derived KPI + conservative GA4 Command Center
status slice:

```bash
uv run ruff check wilq/schemas.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py tests/test_api_contracts.py
uv run mypy wilq/schemas.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py
uv run pytest tests/test_api_contracts.py -q -k 'command_center_exposes_polish_operator_brief or ads_diagnostics_exposes_live_campaign_metric_facts'
pnpm --filter @wilq/shared-schemas typecheck
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
scripts/verify.sh
```

Result:

- Command Center GA4 remains `blocked` when live behavior facts exist but
  ROAS/revenue/conversion-drop/tracking-fixed interpretation contracts are
  missing.
- `/api/ads/diagnostics.derived_kpi_read_contract` exposes CTR/CPC/conversion
  rate/CPA/ROAS/value per conversion as calculated read-only KPI rows with
  evidence IDs and blocked profitability/waste/budget/apply claims.
- Live runtime proof on `:8000`: derived KPI status `ready`, `kpi_rows=18`,
  decision `ads_review_derived_kpis`.
- Full gate: backend API contracts `106 passed`, dashboard route tests
  `13 passed`, Playwright e2e `9 passed`, API smoke, skill structure smoke,
  skill API smoke and dashboard production build passed. Non-blocking warning:
  Vite main JS chunk remains above 500 KB.

Passed after the 2026-06-19 `/ads-doctor` decision route cleanup:

```bash
uv run ruff check wilq/briefing/ads_diagnostics.py wilq/schemas.py tests/test_api_contracts.py
uv run mypy wilq/briefing/ads_diagnostics.py wilq/schemas.py
uv run pytest tests/test_api_contracts.py -q -k 'ads_diagnostics'
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts dashboard-demo-proof.spec.ts
scripts/verify.sh
```

Result:

- API focused pytest: passed.
- Dashboard lint/typecheck: passed.
- Dashboard route tests: 13 passed.
- Playwright e2e: 9 passed.
- `agent-browser` proof: `/ads-doctor` has decisions for campaign review,
  search-term review and blocked write path, with no visible stale
  `Read contract Ads`, `Search terms read-only`, `Campaign activity read contract`,
  `Search terms read contract`, `Google Ads: campaign activity rows`,
  `Google Ads: search terms read-only rows`, `Evidence`, `configured`, `READY`,
  `payload preview`, `write/apply` or stale read-only evidence copy.
- Full `scripts/verify.sh`: passed with backend API contracts `98 passed`,
  dashboard route tests `13 passed`, Playwright e2e `9 passed` and dashboard
  production build passed.

Passed after the 2026-06-19 `/merchant` operator cleanup:

```bash
uv run ruff check wilq/briefing/merchant_diagnostics.py tests/test_api_contracts.py
uv run mypy wilq/briefing/merchant_diagnostics.py
uv run pytest tests/test_api_contracts.py -q -k 'merchant_diagnostics'
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts dashboard-demo-proof.spec.ts
scripts/verify.sh
```

Result:

- API focused pytest: passed.
- Dashboard lint/typecheck: passed.
- Dashboard route tests: 13 passed.
- Playwright e2e: 9 passed.
- `agent-browser` proof: `/merchant` has no visible `payload preview`,
  `review queue`, `read-only`, `feed/product`, `configured`, `Evidence`,
  `Feed Safety Gate`, `ActionObject focus`, duplicate old Merchant diagnostic headings,
  `automatic feed edit`, `approval restored`, `sample product IDs` or `READY`.
- Full `scripts/verify.sh`: passed with backend API contracts `98 passed`,
  dashboard route tests `13 passed`, Playwright e2e `9 passed` and dashboard
  production build passed.

Passed after the 2026-06-19 `/actions` + `/opportunities` cleanup:

```bash
uv run ruff check wilq/opportunities/engine.py wilq/actions/service.py tests/test_api_contracts.py
uv run mypy wilq/opportunities/engine.py wilq/actions/service.py
uv run pytest tests/test_api_contracts.py::test_ads_diagnostics_exposes_live_campaign_metric_facts -q
pnpm --filter @wilq/dashboard lint
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
WILQ_E2E_API_PORT=8000 WILQ_E2E_DASHBOARD_PORT=5173 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts
```

Result:

- API focused pytest: passed.
- Dashboard lint/typecheck: passed.
- Dashboard route tests: 13 passed.
- Playwright e2e: 9 passed.
- `agent-browser` proof: `/actions` has no generic registry dump or stale Ads
  OAuth repair action; `/opportunities` has no old readiness/English blocker
  phrases.
- Full `scripts/verify.sh`: passed after this slice with backend API contracts
  `98 passed`, dashboard route tests `13 passed`, Playwright e2e `9 passed`
  and dashboard production build passed.

Already passed after the current stale-state cleanup started:

```bash
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test -- --run App.test.tsx
uv run ruff check wilq/actions/service.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py wilq/briefing/marketing_brief.py
uv run mypy wilq/actions/service.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py wilq/briefing/marketing_brief.py
uv run pytest tests/test_api_contracts.py::test_command_center_exposes_polish_operator_brief tests/test_api_contracts.py::test_ads_diagnostics_exposes_live_campaign_metric_facts tests/test_api_contracts.py::test_google_ads_oauth_repair_action_is_explicit_and_redacted -q
```

Result:

- Dashboard typecheck: passed.
- Dashboard route tests: 12 passed.
- Backend ruff: passed.
- Backend mypy: passed.
- Focused backend API tests: 3 passed.
- Current-code sanity check: `daily_ads_status` is ready/live, Ads action plan
  is live review, Ads demo step is live campaign metrics, and active Ads repair
  action is filtered out when latest Ads refresh has live data.

Full `scripts/verify.sh` passed after the current cleanup:

```text
backend API contracts: 93 passed
dashboard route tests: 12 passed
Playwright e2e: 8 passed
dashboard production build: passed
```

Latest content decision queue verification:

- Focused ruff, mypy and API contract tests passed for
  `content_diagnostics.decision_queue`, redaction and skill smoke updates.
- Full `scripts/verify.sh` passed after adding clean-runtime core prepare
  ActionObjects and stabilizing `wilq-content-strategist` smoke.
- Clean runtime rule: core daily prepare ActionObjects may exist with connector
  evidence only, but content `decision_queue` must remain empty until real
  GSC/GA4/WordPress metric facts exist. Live runtime still requires concrete
  `inventory_check_before_create`, `merge_create_after_inventory_check` and
  `block_as_tracking_not_content` decisions.

Latest focused backend slice:

- Social draft ActionObjects remain available in `/api/actions` and explicit
  `wilq-social-publisher` context-pack.
- `GET /api/marketing/brief` top-level `action_ids` now contains only core
  daily actions:
  `act_review_merchant_feed_issues`,
  `act_review_ga4_tracking_quality`,
  `act_prepare_content_refresh_queue`.
- `POST /api/codex/context-pack {"skill":"wilq-daily-command"}` now exposes
  only those core daily `active_action_objects`.
- Proof:
  ```bash
  uv run ruff check apps/api/wilq_api/main.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
  uv run mypy apps/api/wilq_api/main.py wilq/briefing/marketing_brief.py
  uv run pytest tests/test_api_contracts.py -q -k 'marketing_brief_exposes_metric_backed_prepare_actions or codex_context_pack_embeds_marketing_brief_contract or daily_context_pack_excludes_social_draft_action_objects or social_context_pack_keeps_explicit_social_draft_action_objects or command_center_exposes_polish_operator_brief'
  uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
  ```

Latest Command Center cleanup:

- Localo is configured and access-ready, not an active OAuth/access blocker.
- Because WILQ still lacks concrete Localo ranking/GBP/competitor facts,
  access-ready Localo is no longer shown as a primary Command Center
  `operator_brief` card or action-plan item.
- Localo still appears as a primary Command Center card only when access is
  genuinely missing, because that is an actionable blocker.
- `/localo` and `wilq-localo-operator` remain the right surfaces for Localo
  access/readiness status until a real Localo visibility read contract exists.

Latest Marketing Brief cleanup:

- `GET /api/marketing/brief` now reads metric facts per connector instead of a
  single global DuckDB limit that was dominated by recent aggregate refreshes.
- Metric cards prefer dimensional business facts before aggregate facts, so the
  brief promotes useful GSC query/page, GA4 landing/source, Merchant issue and
  Ads campaign facts instead of stale-looking aggregates such as
  `active_products=12`, `sessions=30` or `clicks=3`.
- This does not change `/api/actions`; it only improves the evidence selected
  for the daily brief and Codex context.

Latest Command Center Codex bridge cleanup:

- Daily decision cards now visibly expose `Jak Codex może pomóc`, the matching
  `skill_id`, `codex_prompt`, `codex_context_endpoint` and
  `expected_codex_output`.
- The first-screen source footer uses Polish operator wording:
  `Źródła`, `Aktywne`, `Do naprawy`, `Otwórz ustawienia`.
- Focused proof passed:
  ```bash
  pnpm --filter @wilq/dashboard lint
  pnpm --filter @wilq/dashboard typecheck
  pnpm --filter @wilq/dashboard test -- --run App.test.tsx
  WILQ_E2E_API_PORT=<dynamic> WILQ_E2E_DASHBOARD_PORT=<dynamic> CI= pnpm --filter @wilq/dashboard exec playwright test apps/dashboard/e2e/dashboard-api.spec.ts --workers=1
  ```

Latest Command Center metric-decision cleanup:

- `DailyDecision` now exposes `metric_tiles` and Command Center renders them
  directly on the first-screen decision cards.
- Runtime proof after API restart:
  - Merchant decision: `produkty=10900`, `issues=15`, `blockery=0`;
  - Content decision: `query/page=10`, `WP match=15`, `blockery=0`;
  - GA4 decision: `landing groups=10`, `low engagement=0`, `WP match=5`;
  - Ads decision: `kampanie=18`, `search terms=50`, `blockery=1`.
- GA4 no longer claims `0 landing/source groups` when tactical queue already
  has landing/source/campaign groups; diagnostics falls back to tactical group
  count when section metric facts are empty.
- Merchant issue cluster IDs include reporting context and resolution, so issue
  clusters do not collide across `all_contexts`, `FREE_LISTINGS` and
  `SHOPPING_ADS`.
- `agent-browser` proof was run with local runtime dir:
  `XDG_RUNTIME_DIR=$PWD/.local-lab/xdg-runtime`.

Latest Ads/Localo stale-state cleanup:

- Live Ads diagnostics no longer overload `blocked_handoff` for "next step"
  messaging. `blocked_handoff` is now only for real access blockers; live Ads
  keeps write/apply limits in `ads_action_safety`, campaign/search-term read
  contracts and blocked claims.
- `wilq-ads-doctor` smoke now accepts both legal API states: live diagnostics
  with no OAuth handoff, or blocked diagnostics with a blocked handoff and
  ActionObject IDs.
- `/localo` no longer renders generic global tactical queue stats when there
  are no Localo tactical items. It keeps Localo access/readiness and blocks
  ranking/GBP/local-visibility claims until a real Localo read contract exists.
- Focused proof passed:
  - `uv run ruff check wilq/briefing/ads_diagnostics.py tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py`
  - `uv run mypy wilq/briefing/ads_diagnostics.py`
  - `uv run pytest tests/test_api_contracts.py tests/test_codex_skill_eval_cases.py -q`
  - `pnpm --filter @wilq/dashboard lint`
  - `pnpm --filter @wilq/dashboard typecheck`
  - `pnpm --filter @wilq/dashboard test -- --run App.test.tsx`
  - `WILQ_E2E_API_PORT=8875 WILQ_E2E_DASHBOARD_PORT=5373 pnpm --filter @wilq/dashboard test:e2e -- dashboard-api.spec.ts` -> `8 passed`
  - `scripts/verify.sh` -> backend API contracts `98 passed`, dashboard route
    tests `12 passed`, Playwright e2e `8 passed`, dashboard production build
    passed.

Important product note:

- The Codex bridge is necessary but not sufficient. It only connects a dashboard
  decision to a WILQ skill. It is not yet the marketer value by itself.
- The next useful slice must audit the primary dashboard routes
  `/ga4`, `/ads-doctor` and `/localo`, then
  replace technical inventory with real metric-backed decisions.
- Every route should preserve evidence/action traceability while making the
  marketer-facing hierarchy obvious: real metric, diagnosis, safe next action,
  blocked claims and matching Codex skill/prompt.
