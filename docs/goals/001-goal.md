# Goal 001 - WILQ Marketing OS Active Goal

Last updated: 2026-06-18.

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
  read proves that.
- `google_merchant_center`: live product/feed facts exist and support a review
  queue.
- `google_search_console`: query/page facts exist and support content decisions.
- `google_analytics_4`: landing/source/campaign facts exist, but ROAS/revenue
  and conversion-drop claims are blocked unless conversion evidence exists.
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

## Active Product Problems

These are the current reasons Goal 001 is not complete:

1. **Dashboard still contains stale/sloppy states in places.**
   It must not show `ready` and stale OAuth blocker language for the same
   connector. Google Ads live state should show live review, not OAuth repair.

2. **Command Center still over-exposes developer-ish internals.**
   Evidence IDs and ActionObjects are required, but the marketer needs a clear
   "what to do now and why" hierarchy. Raw connector/status/readiness cards must
   not masquerade as marketing insight.

   Hard block: first-screen Command Center must not render readiness-only cards
   such as `connector_configured=true`, `Connector ... ready for ... refresh`,
   `No performance metrics have been collected`, or `Run a read-only refresh`.
   Those belong in lower diagnostic/settings surfaces unless converted into a
   real decision, blocker or action.

3. **Ads Doctor is only partially useful.**
   Campaign-level facts exist, but search terms, recommendations, quality,
   budget pacing, impression share, CPA/ROAS and negative keyword workflows need
   explicit read contracts before WILQ can claim BDOS-class Ads value.

4. **Codex skill usefulness is not proven end-to-end.**
   Skills have contracts and smokes, but Goal 001 still needs a clean
   plug-and-play Codex session proving Polish prompts -> WILQ API calls -> same
   evidence IDs as dashboard -> useful next actions.

5. **Knowledge condensation is not fully proven.**
   Playbooks and knowledge cards exist, but we must prove they influence skill
   outputs and content/Ads decisions instead of sitting beside the product.
   Goal 001 must show at least one source-backed chain:
   source -> knowledge card/rule -> API view model -> dashboard card ->
   non-interactive Codex skill output.

6. **Localo and social remain limited-evidence surfaces.**
   Localo access is no longer an OAuth blocker, but local ranking/GBP/competitor
   insight remains blocked until a concrete Localo read contract exists. Social
   publishing remains permission-gated; drafting can be prepare-only and
   evidence-backed.

7. **Full verification after the latest changes is still pending.**
   Focused API/dashboard/skill checks passed after the 2026-06-18 Localo and
   brief-dedupe fixes, but full `scripts/verify.sh` must pass before commit.

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
- Content: "GSC query/page + WordPress inventory suggests refresh/create/block;
  do not promise ranking or lead uplift."
- GA4: "Landing/source/campaign traffic quality looks weak; review tracking and
  message match; do not claim ROAS/revenue."
- Ads: "Campaign metric facts exist; review live campaign activity; search-term
  waste remains blocked until search-term read contract exists."
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
- 2026-06-18 follow-up: fourth real non-interactive Codex eval passed for
  `wilq-gsc-content-doctor`:
  `.local-lab/evals/codex-skill/20260618T101550Z/wilq-gsc-content-doctor/result.json`.
  It proves `pl-PL`, Polish diacritics, `api_used=true`,
  GSC/WordPress evidence IDs, `content_diagnostics.live_data_available=true`,
  `query_page_count=10`, `matched_inventory_count=0` and
  `act_prepare_content_refresh_queue` as the safe pending-validation content
  queue path. Remaining quality gap: future GSC evals should assert concrete
  query/page candidates with `refresh`, `merge`, `create` or `block` decisions.
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

- `wilq-content-strategist`: passed non-interactive Codex eval at
  `.local-lab/evals/codex-skill/20260618T093647Z/wilq-content-strategist/result.json`.
  Safe, API-backed, but future eval must force concrete
  `refresh`/`merge`/`create`/`block` decisions.
- `wilq-merchant-feed-operator`: passed at
  `.local-lab/evals/codex-skill/20260618T094236Z/wilq-merchant-feed-operator/result.json`.
  Strong Merchant pass with `product_count=10900`, `issue_count=15` and
  `act_review_merchant_feed_issues`.
- `wilq-ga4-analyst`: passed at
  `.local-lab/evals/codex-skill/20260618T101220Z/wilq-ga4-analyst/result.json`.
  Safe GA4 pass; blocks ROAS/revenue/conversion claims without stronger
  evidence.
- `wilq-gsc-content-doctor`: passed at
  `.local-lab/evals/codex-skill/20260618T101550Z/wilq-gsc-content-doctor/result.json`.
  Safe GSC/content pass; future eval must force concrete query/page decisions.
- `wilq-ads-doctor`: passed at
  `.local-lab/evals/codex-skill/20260618T102132Z/wilq-ads-doctor/result.json`.
  Important correction: Ads is currently live campaign review, not OAuth repair.
  The skill may use campaign-level evidence from `google_ads`, but must block
  `search terms`, `CPA`, `ROAS` and `wasted budget` until WILQ exposes stronger
  evidence/read contracts.
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

1. **Remove remaining Command Center readiness slop.**
   First-screen `/command-center` must stop rendering connector readiness as
   marketing insight. Keep real metric facts, tactical queue, ActionObjects and
   honest blockers.

2. **Clean remaining stale Ads/Localo/social state in product surfaces.**
   Ensure Command Center, Ads Doctor, marketing brief, action plan and skill
   text no longer show OAuth repair when live Ads data exists, and no Localo
   surface says "dokończ access" after `mcp_initialize_status=200`. Keep direct
   `/actions/act_configure_google_ads_env` available for troubleshooting only.

3. **Continue API surface audit from `/api/actions` and `/api/dashboard/command-center`.**
   `/api/marketing/brief` has been narrowed and deduped for the current slice.
   Continue by removing or demoting any ActionObject/Command Center item that
   repeats the same intent in multiple sections without adding a new decision,
   validation path or Codex bridge.

4. **Run focused verification.**
   Required:
   ```bash
   uv run ruff check wilq/actions/service.py wilq/briefing/command_center.py wilq/briefing/marketing_brief.py tests/test_api_contracts.py
   uv run mypy wilq/actions/service.py wilq/briefing/command_center.py wilq/briefing/marketing_brief.py
   uv run pytest tests/test_api_contracts.py::test_command_center_exposes_polish_operator_brief tests/test_api_contracts.py::test_command_center_treats_localo_mcp_initialize_as_access_ready tests/test_api_contracts.py::test_codex_context_pack_embeds_marketing_brief_contract -q
   pnpm --filter @wilq/dashboard lint
   pnpm --filter @wilq/dashboard typecheck
   pnpm --filter @wilq/dashboard test -- --run App.test.tsx
   ```

5. **Audit Command Center top-to-bottom.**
   Use the running dashboard and `agent-browser` after the page settles. Remove,
   rewrite or demote every visible section that cannot answer:
   `co widzę`, `co to znaczy`, `co zrobić teraz`, `czego nie wolno twierdzić`,
   and `jak Codex może pomóc`.

6. **Run full verification.**
   Required before commit:
   ```bash
   scripts/verify.sh
   ```

7. **Run a real Codex/API proof.**
   Use `codex exec` or Codex Desktop/CLI against the local WILQ API. Plain
   static prompt evaluation is not enough. The proof must show API use, Polish
   output, evidence IDs, source connectors, blocked claims and safe next actions.
   First proof exists for `wilq-content-strategist`; continue with the remaining
   skills and strengthen eval cases to score usefulness, not only schema pass.

8. **Run full product gate.**
   ```bash
   scripts/verify.sh
   ```

9. **Commit semantically and push.**
   Use Conventional Commits only. Do not commit `.env`, `.local-lab`, test
   traces or secrets.

10. **Run plug-and-play Codex acceptance session.**
   Add only the final result and any active blockers back into this file.

## Latest Focused Verification

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
backend API contracts: 90 passed
dashboard route tests: 12 passed
Playwright e2e: 8 passed
dashboard production build: passed
```
