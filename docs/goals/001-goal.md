## 0. Live progress and recovery contract

Canonical active goal/progress file: `docs/goals/001-goal.md`.

Every Codex session working on WILQ must read this file first after context loss,
conversation compaction, restart, branch switch or any confusing handoff. Do not
reconstruct the goal from chat memory when this file is available.

This file must be updated continuously while Goal 001 is open:

* Before starting a non-trivial slice, make sure the continuation ledger states
  the intended product outcome, touched API/dashboard/skill surfaces, expected
  proof commands and known blockers.
* After completing and committing a slice, move shipped work into the completed
  checkpoint/foundation list and replace stale next tasks with the next real
  blocker.
* If context may run out, leave enough progress detail here for a fresh Codex
  session to resume without reading old chat logs.
* Never mark Goal 001 complete from vibes, green narrow tests or scaffolded
  contracts. Completion requires current evidence that the actual marketer-facing
  product works.

Final Goal 001 product acceptance:

* Tomorrow's Ekologus marketer can open the local dashboard and/or Codex
  Desktop/CLI and see one connected WILQ operating system, not disconnected
  prompt packs, placeholder routes or static reports.
* Codex skills, dashboard, hooks, workflows, expert rules, opportunities,
  actions, metrics and evidence must all use the same WILQ API contracts.
* Real vendor metrics and source facts must be shown where connectors are live.
  Where OAuth, API access, quota, permissions or unsupported writes block live
  data, the API, dashboard and skills must say that explicitly in Polish without
  inventing values.
* Every marketing recommendation must include source connectors, evidence IDs,
  metric facts or explicit missing-evidence blockers, a human diagnosis, risk,
  and the next safe ActionObject path.
* The intended product shape and scope from `docs/infra/001.md` remains binding:
  Ads, GSC/SEO, GA4, Merchant, Ahrefs, Localo, WordPress/content, social,
  knowledge, Codex runs and audited API actions are one operating system.

Required marketer-proof gates:

* Real metric audit: collect and show current source facts for pages, products,
  campaigns, queries, landing pages, feed/product state and connector freshness
  wherever credentials/API access allow it. Do not use fixture/seed data as
  proof of marketer usefulness.
* Real pages/products proof: WordPress and Merchant/Product-related surfaces
  must show actual inventory, freshness and evidence IDs before Content Planner
  or product/feed recommendations are considered useful.
* Non-interactive Codex proof: run `codex exec` evals for every upgraded WILQ
  skill against live WILQ API context. Evals must prove API use, Polish output
  with Polish diacritics, evidence IDs/source connectors, ActionObject
  validation behavior and no invented metrics.
* Dashboard proof: Playwright/browser proof must show that the marketer can see
  the same real metrics, evidence, blockers and action candidates in the
  dashboard, not only in Codex output.
* API consistency proof: the dashboard, Codex context packs, skill eval outputs,
  opportunities and actions must all reference the same evidence IDs and source
  connectors for the same recommendation.
* Human usefulness proof: a final walkthrough must answer concrete marketer
  questions: what burns budget, what can gain traffic, what content/product
  work is next, what social/local move is blocked or ready, and what can be
  safely prepared through an ActionObject.

Zrealizuj wszystkie zadania krok po kroku.

Stwórz repo przy pomocy 'gh' w 'korneliuszburian' (mój github nickname) -> prywatne, skonfiguruj .gitignore i wszystkie najważniejsze elementy, następnie idź do przodu.

````md
## -1. Skill and MCP creation policy

This goal must use official Codex skill and MCP primitives from the beginning.

Execution clarification from 2026-06-17:

```txt
This section is policy, not permission to scaffold skills before the API exists.
Create or update WILQ skills only after the WILQ API endpoints, context-pack
contract, connector status contract, and action validation path that a skill
will call are implemented and testable. Until then, keep `.agents/skills/` as
a placeholder and record the skill creation policy in AGENTS.md and
docs/architecture/codex-runtime.md.
```

When creating, updating, reviewing or refactoring any Codex skill, agents must use `$skill-creator` as the preferred workflow helper. Do not hand-roll large skills from scratch when `$skill-creator` can scaffold, structure, split or improve the skill.

`$skill-creator` must be used especially when a skill needs:

- a precise `SKILL.md`,
- task trigger descriptions,
- progressive-disclosure instructions,
- `references/` files,
- helper scripts under `scripts/`,
- output schemas,
- reusable workflow checklists,
- domain-specific examples,
- safety rules,
- validation commands,
- handoff notes.

Skills must follow the official Codex skill model:

```txt
.agents/skills/<skill-name>/
  SKILL.md
  references/
  scripts/
  assets/       # only when genuinely useful
````

Skill rules:

* Keep `SKILL.md` short, sharp and trigger-oriented.
* Put long domain knowledge in `references/`.
* Put executable helper logic in `scripts/`.
* Put schemas in `references/schemas/` or a shared schema package.
* Never put secrets into skills.
* Never make skills the only place where business logic lives.
* Every WILQ skill must call WILQ API for live/product data.
* Every WILQ skill must refuse to invent marketing metrics.
* Every WILQ skill must return source/evidence/action IDs where applicable.
* Every WILQ skill must declare which API endpoints it is allowed to use.
* Every WILQ skill must define its output contract.
* Every WILQ skill must include at least one smoke-test command or validation path.

Required first skill creation flow:

```txt
1. Use $skill-creator to design the skill skeleton.
2. Review generated SKILL.md for scope creep.
3. Move long instructions into references/.
4. Add scripts/ only when they call WILQ API or perform deterministic validation.
5. Add schema/output contract.
6. Add safety notes:
   - no invented metrics,
   - no secret printing,
   - no disconnected recommendations,
   - no write action without ActionObject validation.
7. Add smoke test.
8. Register skill in AGENTS.md and docs/architecture/codex-runtime.md.
```

Required skills created or scaffolded during Goal 001:

```txt
wilq-daily-command
wilq-ads-doctor
wilq-gsc-content-doctor
wilq-ahrefs-gap-finder
wilq-localo-operator
wilq-content-strategist
wilq-social-publisher
wilq-campaign-builder
wilq-custom-segments
wilq-demand-gen-operator
wilq-ga4-analyst
wilq-merchant-feed-operator
```

For Goal 001, only `wilq-daily-command` must be fully wired to WILQ API. Other skills may be production-shaped stubs, but they must be created with correct structure, trigger logic, allowed endpoints, evidence requirements and output contracts.

---

## -0. Official MCP policy

Use official OpenAI Codex MCP documentation and official OpenAI docs as the source of truth for MCP configuration and integration.

MCP is allowed and expected, but MCP is not the brain of the product.

Product rule:

```txt
WILQ API is the system brain.
MCP servers are adapters/tool surfaces.
Codex skills are operator workflows.
Dashboard is the human command center.
```

MCP integration rules:

* Use MCP only when it gives Codex controlled access to tools, documentation or external systems.
* Prefer official MCP servers and official documentation when available.
* Do not build unofficial MCP glue before checking official OpenAI Codex MCP docs.
* Do not put core business logic only in MCP server descriptions.
* Do not let MCP tool descriptions replace typed WILQ API contracts.
* Do not expose secrets through MCP tools, logs, prompts or tool descriptions.
* Every MCP server used by this repo must be documented in `docs/architecture/codex-runtime.md`.
* Every MCP server must have:

  * purpose,
  * config location,
  * auth model,
  * allowed tools,
  * denied/dangerous tools,
  * expected use by skills,
  * security notes,
  * fallback path if unavailable.
* If a WILQ API endpoint is exposed to Codex through MCP later, the REST/OpenAPI contract remains canonical.
* MCP tools must not bypass ActionObject validation for write actions.
* MCP tools must not bypass audit logging.
* MCP tools must not return raw secrets or credential values.

Required MCP-related deliverables for Goal 001:

```txt
docs/architecture/mcp-policy.md
docs/architecture/codex-runtime.md
.codex/mcp-notes.md
AGENTS.md section: MCP and tool-use policy
```

`docs/architecture/mcp-policy.md` must explain:

```txt
- what MCP is used for,
- what MCP is not used for,
- why WILQ API remains canonical,
- how skills may call MCP tools,
- how MCP connects to Localo/OpenAI docs/future connector tooling,
- how MCP tools are audited,
- how MCP tool descriptions must be written,
- how to avoid prompt injection and excessive agency through MCP.
```

When Codex needs current documentation during implementation, prefer:

```txt
1. official OpenAI Codex docs,
2. official OpenAI MCP docs,
3. official vendor API docs,
4. local `docs/research/source-registry.md`,
5. local skill `references/`.
```

Do not rely on random blog posts for MCP or skill behavior unless the official docs are insufficient and the source is explicitly marked as secondary.

---

## -0A. MCP/server description quality rule

MCP tool descriptions must be treated as product-critical contracts.

Every MCP tool description created for WILQ must be:

* accurate,
* complete,
* concise,
* parameter-specific,
* explicit about side effects,
* explicit about required auth,
* explicit about read/write behavior,
* explicit about whether it can mutate external systems,
* explicit about failure modes,
* explicit about returned evidence/action IDs.

Do not create vague MCP tool descriptions such as:

```txt
"Does Google Ads stuff."
"Gets marketing data."
"Updates campaign."
```

Use precise descriptions such as:

```txt
"Fetches Google Ads search terms for a configured customer and date range. Read-only. Returns search term metrics, campaign/ad group identifiers, evidence IDs and freshness metadata. Does not mutate Google Ads."
```

Reason:

Tool descriptions influence tool selection and agent behavior. Bad MCP descriptions create wrong tool calls, unsafe behavior and unreliable workflows. This project must treat MCP descriptions like API contracts, not comments.

````

Dorzuciłbym też krótką zasadę do `AGENTS.md`, najlepiej w sekcji `Codex skills and hooks rules`:

```md
## Skill creation rules

Use `$skill-creator` for new skills and major skill updates. Skills must be small operator workflows over WILQ API, not prompt dumps. Long knowledge goes to `references/`, deterministic helpers go to `scripts/`, and every skill must define trigger, allowed endpoints, evidence requirements, output contract, safety rules and smoke test.

## MCP rules

Use official OpenAI Codex MCP docs before configuring or implementing MCP. MCP servers are adapters, not the product brain. WILQ API remains canonical. MCP tools must not bypass ActionObject validation, audit logging, secret redaction or evidence requirements.
````

To jest akurat ważne, bo inaczej Codex zrobi nam po czasie “skille” jako wielkie markdownowe potwory, a MCP jako losowy worek narzędzi. `$skill-creator` + oficjalny MCP policy blokują ten rozjazd od pierwszego dnia.

[1]: https://developers.openai.com/codex/use-cases/reusable-codex-skills?utm_source=chatgpt.com "Save workflows as skills | Codex use cases"
[2]: https://developers.openai.com/codex/mcp?utm_source=chatgpt.com "Model Context Protocol – Codex"

# Goal 001 — WILQ Marketing Operating System for Ekologus

Status: in progress, foundation verified; Goal 001 is not complete yet.
Owner: Lead Architect / Codex Lead
Primary executor: Codex Desktop/CLI
Primary user: WILQ, marketer
Client scope: Ekologus only
Target repository file: `docs/goals/001-goal.md`

---

## Current checkpoint — 2026-06-17

Canonical goal state:

* `docs/goals/001-goal.md` is the only goal file to keep in the repository.
* The duplicate numbered goal file was identical and was removed.
* Existing repo instructions, handoff docs and source registry references point to `docs/goals/001-goal.md`.

Already committed to `origin/main`:

* `d300bc3 feat(skills): add WILQ operator skill contracts`
* `4e31126 feat(evals): add Codex skill eval harness`
* `e4cd4c4 test(dashboard): add real browser API smoke`
* `e5daad2 docs(goals): refresh continuation queue`
* `6c2c54d docs(goals): clarify marketing operating scope`
* `0a15bb4 docs(goals): add live progress recovery contract`
* `23a3260 docs(goals): define marketer proof gates`

Verified foundation already present:

* WILQ FastAPI spine, dashboard shell, connector registry, action model, expert rules, knowledge compiler, local SQLite state, hooks, docs and handoff exist.
* 12 WILQ operator skills live under `.agents/skills/wilq-*`.
* `scripts/codex_skill_eval.sh` uses `codex exec` non-interactive mode with schema output.
* 12/12 Goal 001 skills passed the baseline non-interactive Codex eval with `api_used=true`, `language=pl-PL`, Polish diacritics and JSON schema validation.
* WILQ API is reachable locally; current connector summary is 12 total connectors, 9 configured and 2 missing credentials.

Current implementation slice completed and verified in this checkpoint:

* DuckDB-backed metric store for redacted connector refresh metric facts.
* `/api/metrics` and `/api/metrics/status` API endpoints.
* Typer local operator CLI exposed as `uv run wilq`.
* Tests covering metric persistence, metric API and CLI secret redaction.
* Python packaging now installs the project as editable through hatchling so the `wilq` console script is available through `uv run wilq`.
* APScheduler-backed local job definitions, manual job run API/CLI, and redacted persisted job-run state for connector refresh orchestration.
* Playwright real-browser dashboard/API smoke wired into `scripts/verify.sh` using system Google Chrome.

Current implementation slice completed and verified after `23a3260`:

* Product outcome: move Command Center away from generic connector/status filler toward the first ActionObject-centered operating surface for a Polish marketer.
* Touched files:
  * `packages/shared-schemas/src/index.ts`
  * `apps/dashboard/src/lib/api.ts`
  * `apps/dashboard/src/routes/App.tsx`
  * `apps/dashboard/src/routes/App.test.tsx`
  * `apps/dashboard/e2e/dashboard-api.spec.ts`
* Implemented:
  * typed frontend access for `/api/metrics` and `/api/metrics/status`;
  * Polish Command Center sections for priorities, money leaks, traffic wins, content rewrite/create, local visibility, social queue, ActionObject candidates, local metric facts and connector blockers;
  * readiness-only cards explicitly say they are not performance recommendations until `vendor_read` evidence exists;
  * Playwright smoke expectations updated for the new operating-surface headings.
* Verified:
  * `GOMAXPROCS=1 pnpm --filter @wilq/dashboard exec vitest run --pool forks --poolOptions.forks.singleFork --maxWorkers=1 --minWorkers=1` passed: 8/8 tests.
  * `pnpm --filter @wilq/dashboard lint` passed after Playwright test-result race was cleared.
  * `pnpm --filter @wilq/dashboard typecheck` passed.
  * `GOMAXPROCS=1 pnpm --filter @wilq/dashboard test:e2e` passed: 3/3 tests, when API and Vite were pre-started on `127.0.0.1:8875` and `127.0.0.1:5373`.
  * `GOMAXPROCS=1 scripts/verify.sh` passed end-to-end after this slice, including lint, typecheck, 48 backend tests, frontend unit tests, security checks, API smoke, skill smoke, Playwright e2e 3/3 and dashboard production build.
* Runtime cleanup performed during this slice:
  * stale `agent-browser`/headless Chrome/Codex/MCP/dev-server processes were removed;
  * old supersearch/Qdrant/crawl/redis containers were stopped;
  * WordPress/Sawaryn Docker containers on `80/443/3306` were intentionally left running;
  * WILQ standard dev ports were then restarted for operator work: API on `http://127.0.0.1:8000` and dashboard on `http://127.0.0.1:5173`.
* Committed and pushed:
  * `159d783 feat(dashboard): add marketer command center surface`
* If resuming after context loss: do not reimplement or recommit this slice. Verify the current worktree first, then continue with the Google Ads data slice.

Current implementation slice completed after `7a5ced6`:

* Product outcome: make the Google Ads blocker actionable and then turn live Ads data into the first real Ads Doctor proof surface. Do not claim Ads performance insight until WILQ has live Google Ads evidence IDs and metric facts.
* Initial proof:
  * `uv run wilq connectors refresh google_ads --mode vendor_read --reason "Goal 001 Google Ads data slice current-state proof"` reached Google's OAuth token endpoint with all required credential names present.
  * The refresh failed as a redacted WILQ connector run: `refresh_google_ads_46316753e85f`.
  * Evidence IDs recorded by the API: `ev_connector_google_ads_status`, `ev_refresh_refresh_google_ads_46316753e85f`.
  * External call was attempted; vendor data was not collected; metric summary was empty.
  * Before this slice, exposed failure text was only `Google Ads OAuth token refresh HTTP 400.`
* Implemented:
  * Google Ads HTTP failures now parse and expose only safe OAuth/API labels such as `oauth_error=invalid_grant`, `api_status=PERMISSION_DENIED` and numeric `api_code`.
  * Raw `error_description`, `message`, vendor response bodies, credential values, token prefixes, client IDs and credential JSON bodies remain excluded from connector summaries/errors.
  * A Google Ads connector test proves `invalid_grant` is exposed while raw OAuth detail, refresh token and client secret are not leaked.
* Verified:
  * `uv run ruff check wilq/connectors/google_ads/client.py tests/test_api_contracts.py` passed.
  * `uv run mypy wilq/connectors/google_ads/client.py` passed.
  * `uv run pytest tests/test_api_contracts.py -q` passed: 44/44 tests.
  * `uv run wilq connectors refresh google_ads --mode vendor_read --reason "Goal 001 Google Ads sanitized OAuth diagnostic proof"` created redacted run `refresh_google_ads_9e5da536ca71`.
  * The live refresh exposed `Google Ads OAuth token refresh HTTP 400 (oauth_error=invalid_grant).`, attempted the external OAuth call, collected no vendor data and stored no metrics.
* Current blocker after diagnostics:
  * The local Google Ads credential tuple is present, but the refresh token is invalid for the `adwords` scope. The next human/API setup action is to generate or update a fresh `adwords`-scoped refresh token in the local `.env`; Codex must not claim live Ads metrics until the next `google_ads vendor_read` succeeds.
  * If the token is updated, immediately rerun `uv run wilq connectors refresh google_ads --mode vendor_read --reason "Goal 001 Google Ads live data proof"` and then continue to live Ads evidence/Ads Doctor usefulness.
* Committed and pushed:
  * `7db8b91 fix(connectors): expose sanitized google ads oauth errors`

Current implementation slice completed after `7db8b91`:

* Product outcome: make the Google Ads OAuth repair flow operator-safe, repo-local and repeatable, so the user does not need to manually inspect or paste credential values.
* Implemented:
  * `uv run wilq google-ads oauth-url` generates a Google Ads consent URL from the repo-local credential source using `https://www.googleapis.com/auth/adwords`, `access_type=offline` and `prompt=consent`.
  * `uv run wilq google-ads oauth-exchange --redirect-url '<final localhost URL>' --write-env` exchanges the OAuth code and writes `GOOGLE_ADS_REFRESH_TOKEN` into the local `.env` without printing the token.
  * The helper uses the same WILQ credential runtime as the connector; `.env` remains the primary local private credential source.
* Verified so far:
  * `uv run ruff check wilq/connectors/google_ads/oauth.py wilq/cli.py tests/test_google_ads_oauth_cli.py` passed.
  * `uv run mypy wilq/connectors/google_ads/oauth.py wilq/cli.py` passed.
  * `uv run pytest tests/test_google_ads_oauth_cli.py tests/test_metric_store_and_cli.py -q` passed: 8/8 tests.
  * `uv run wilq google-ads oauth-url --client-secret-file /home/krn/.local/wilq/client_secret_504856024095-0r6gpqoln9u6uvv474rqmeifk2urqgb7.apps.googleusercontent.com.json | jq '{scope, redirect_uri, secrets_redacted, client_secret_file_used, has_authorization_url: has("authorization_url")}'` confirmed the real local OAuth client JSON can generate an `adwords` consent URL without printing the URL/client ID in the transcript.
* Operator flow to unblock live Ads data:
  * Run `uv run wilq google-ads oauth-url --client-secret-file /home/krn/.local/wilq/client_secret_504856024095-0r6gpqoln9u6uvv474rqmeifk2urqgb7.apps.googleusercontent.com.json`.
  * Open `authorization_url` as `marketing@rekurencja.com` and approve Google Ads access.
  * Copy the final `http://127.0.0.1:8085/oauth2callback?...code=...` URL from the browser.
  * Run `uv run wilq google-ads oauth-exchange --client-secret-file /home/krn/.local/wilq/client_secret_504856024095-0r6gpqoln9u6uvv474rqmeifk2urqgb7.apps.googleusercontent.com.json --redirect-url '<copied URL>' --write-env`.
  * Run `uv run wilq connectors refresh google_ads --mode vendor_read --reason "Goal 001 Google Ads live data proof"`.
* Known limitation:
  * Project `Owner` can manage APIs/IAM/OAuth clients, but cannot bypass Google user-consent OAuth for `marketing@rekurencja.com`. A fresh user-approved `adwords` refresh token is still required before live Google Ads metrics can be collected.
* Committed and pushed:
  * `0190062 feat(cli): add google ads oauth repair helper`

Current active slice after `0190062`:

* Product outcome: finish Google Ads OAuth setup with `marketing@rekurencja.com`, then prove live Google Ads evidence through WILQ API before building Ads Doctor usefulness.
* Operator action required:
  * Use the helper flow above to approve Google Ads access and write a fresh local `GOOGLE_ADS_REFRESH_TOKEN` to `.env`.
* Codex action immediately after token repair:
  * Run `uv run wilq connectors refresh google_ads --mode vendor_read --reason "Goal 001 Google Ads live data proof"`.
  * If live data succeeds, persist the run/evidence IDs in this goal and move to Ads Doctor live metric/action-candidate implementation.
  * If it fails, record only sanitized HTTP/OAuth/API status labels and continue from the concrete blocker.

Known external/product blockers:

* Google Ads `vendor_read` reaches Google's OAuth token endpoint, but the current refresh-token tuple returns `400 invalid_grant` for `adwords`; treat this as an external OAuth/token issue.
* Localo and social vendor-read adapters are not fully live yet.
* Baseline Codex skill evals are still smoke-level proofs; richer evidence-ID scenarios are needed before claiming full marketing recommendation quality for every skill.
* The dashboard is still not a marketer-useful final dashboard. The active WIP improves Command Center, but most route-specific views still need real metric cards, diagnostic tables, decision queues and vendor-read evidence before WILQ can use them for daily marketing work.

## Continuation ledger for context loss

Use this section first after conversation compaction, resume, or a fresh Codex run. The current worktree is always authoritative; verify it before trusting this ledger.

Maintenance rule:

* Keep exactly one active goal file while Goal 001 is open: `docs/goals/001-goal.md`.
* When a task is completed and committed, move it into the completed foundation list or checkpoint summary.
* Do not leave stale "next" tasks that were already shipped; replace them with the next real blocker.
* Keep unfinished blockers visible until verified evidence proves them complete.
* Every new task should include the required product outcome, the API/dashboard/skill surfaces affected, expected proof commands and the known blocker state.
* Write task descriptions so a future agent can resume after context loss without reading old chat logs.

Completed foundation that should not be reimplemented:

* Repository, private GitHub setup, root instructions, source registry, architecture docs, quality scripts and handoff exist.
* WILQ API spine, typed schemas, connector registry, action model, expert rules, opportunities, evidence registry, knowledge compiler and local state exist.
* Access-pack/bootstrap handling and secret-redaction rules exist; `.env` remains local and git-ignored.
* DuckDB metric store, Typer CLI and APScheduler-backed manual job orchestration exist and are covered by tests.
* 12 WILQ operator skills exist under `.agents/skills`; baseline non-interactive Codex evals passed as smoke-level proofs.
* Dashboard routes exist and are API-backed through TanStack Query/Zod, but they are not yet marketer-useful final surfaces.
* Playwright real-browser dashboard/API smoke exists to prove browser route/API/CORS health and must stay in `scripts/verify.sh`.
* Goal recovery/acceptance gates are now explicit at the top of this file: keep this file current, prove real metrics/pages/products, prove Codex non-interactive behavior, prove dashboard/browser usefulness and preserve `docs/infra/001.md` scope.
* Command Center now exposes the first marketer-facing operating surface pattern: Polish decision sections, ActionObject candidates, local metric facts, connector blockers, evidence IDs and explicit readiness-only warnings.
* Command Center operating-surface slice was committed and pushed as `159d783 feat(dashboard): add marketer command center surface`.
* Google Ads OAuth diagnostics now expose sanitized HTTP/OAuth labels without leaking raw vendor response bodies or credential material.
* Google Ads OAuth repair helper now exists in the WILQ CLI and can write a fresh refresh token to local `.env` without printing it.

Product scope that must not be simplified away:

* WILQ is not an Ads-only tool and not a connector dashboard. The finished operating loop must cover Ads, GSC/SEO, GA4, Merchant, Ahrefs, Localo, WordPress/content inventory, LinkedIn/Facebook social publishing, knowledge cards, Codex runs and audited ActionObjects.
* The marketer-facing loop is: collect vendor evidence -> normalize metric facts and knowledge cards -> run expert rules -> create opportunities -> prepare validated action candidates -> show them in Command Center/dashboard -> let Codex skills operate on the same API evidence -> audit every write path.
* Command Center must eventually answer, in Polish, the actual daily questions: what burns budget, what can win traffic, what content to rewrite/create/merge, what local/social move is ready, which API action can be safely prepared, and which blocker prevents action.
* Ads Doctor is only the first vertical proof because Google Ads has the highest immediate business leverage. It must establish the reusable pattern for all other surfaces, not replace them.
* Content work is first-class: GSC query/page evidence, GA4 landing diagnostics, Ahrefs gaps, WordPress inventory, Merchant product context and knowledge cards must feed Content Planner and content/social ActionObjects.
* Social Publisher is first-class but permission-gated: LinkedIn/Facebook post candidates must use evidence-backed claims and remain prepare-only until permissions, validation and audit support are live.
* Localo/local visibility is first-class but connector-gated: local ranking/GBP recommendations must show explicit blockers until Localo evidence exists.

Current Codex skill/API truth:

* `wilq-daily-command` is the only Goal 001 skill described as functionally wired today; it must call `POST /api/codex/context-pack` before producing a daily brief.
* The other WILQ skills are production-shaped API operator contracts and smoke-tested against `/api/codex/context-pack`, but they are not yet proof of rich domain usefulness. Do not describe them as fully useful or complete until their domain API evidence, diagnostic endpoints, action candidates and targeted eval cases exist.
* Every skill upgrade must follow the same sequence: implement or expose the API evidence first, add diagnostic/action contracts second, then update the skill and non-interactive Codex eval. Do not move business logic into prompts to compensate for missing API data.

Unfinished blockers to keep carrying forward:

1. Google Ads OAuth: current refresh-token tuple returns `400 invalid_grant` for `adwords`; get a fresh scoped token before claiming live Ads metrics.
2. Ads Doctor usefulness: replace generic readiness cards with live Google Ads metrics, diagnostic tables, evidence IDs, action candidates and Polish marketer labels.
3. Dashboard usefulness across routes: every operating route needs real metric cards, diagnostic queues, freshness, evidence IDs and explicit blockers when data is unavailable.
4. Localo and social vendor reads: current adapters are not fully live; keep blockers honest instead of pretending publishing/local metrics exist.
5. Skill eval depth: baseline skill evals prove API use, Polish output and schema compliance, but not rich evidence-ID recommendation quality for every skill.
6. Opportunity quality: many opportunities still come from connector readiness/refresh evidence rather than vendor performance data.
7. Runtime hardening: API is local-only but has no production authentication; do not expose beyond localhost/trusted tunnel.

Next implementation queue:

1. Google Ads OAuth setup/data slice: run the helper flow with `marketing@rekurencja.com`; once the local `.env` has a fresh `adwords`-scoped refresh token, prove a live `google_ads vendor_read` returns sanitized campaign/search-term/recommendation evidence, metric facts and evidence IDs.
2. Ads Doctor usefulness slice: turn `/ads-doctor` from a generic API-backed route into the first genuinely useful Polish marketer surface with live spend/waste/search-term/recommendation/quality diagnostics, evidence IDs, freshness and action candidates.
3. Content Planner usefulness slice: expose a real content decision queue from GSC, GA4, Ahrefs, WordPress inventory, Merchant/product context and knowledge cards: refresh, merge, create, avoid-duplicate, social adaptation and evidence-backed briefs.
4. Skill/eval upgrade slice: upgrade `wilq-ads-doctor`, `wilq-campaign-builder`, `wilq-custom-segments`, `wilq-demand-gen-operator`, `wilq-gsc-content-doctor`, `wilq-content-strategist`, `wilq-ahrefs-gap-finder`, `wilq-localo-operator` and `wilq-social-publisher` only after their WILQ API endpoints expose the evidence they need; evals must prove no invented metrics and Polish output.
5. After Ads Doctor and Content Planner are useful, promote the same metric-view/action-candidate pattern to GA4, Merchant, Ahrefs, Localo and social surfaces.

Goal 002 draft acceptance notes:

* Product outcome: WILQ can open Ads Doctor and immediately see which Google Ads work matters, why it matters, what evidence supports it and what safe action can be prepared next.
* API surfaces: connector refresh runs, metric facts, evidence registry, opportunities, actions, Ads capability definitions and context packs must all describe the same Ads truth.
* Dashboard surfaces: `/ads-doctor`, `/ads-doctor/search-terms`, `/ads-doctor/custom-segments`, `/ads-doctor/demand-gen`, `/ads-doctor/recommendations`, `/actions/:id`.
* Skill surfaces: `wilq-ads-doctor`, `wilq-campaign-builder`, `wilq-custom-segments`, `wilq-demand-gen-operator`.
* Proof commands: `uv run wilq connectors refresh google_ads --mode vendor_read`, targeted Ads tests, `pnpm --filter @wilq/dashboard test:e2e`, `scripts/quality.sh`, `scripts/security.sh`, `scripts/verify.sh`, and targeted Codex skill evals once live Ads evidence exists.
* Blocker language: if OAuth, API quota, account access or unsupported Ads write capability blocks a metric/action, the API, dashboard and skills must all say that explicitly without printing credential values.

---

## 0. Goal command

Use this document as the first durable goal for the repository.

Recommended Codex invocation:

```txt
/goal Read docs/goals/001-goal.md and execute Goal 001 exactly. Spawn the requested subagents first, wait for their findings, merge their handoffs into one implementation plan, then implement the smallest production-shaped foundation that satisfies the stop condition. Do not build static artifacts, reports, fake dashboards, or disconnected prompt packs. Dashboard, API, Codex skills, hooks, expert rules, action objects, tests, and AGENTS.md must be designed as one system.
```

---

## 1. Objective

Build the initial production-shaped foundation of **WILQ Marketing Operating System**, a local API-first marketing command center for Ekologus.

This is the first goal in the repository, so treat it as the foundational system architecture goal, not as a temporary prototype.

The system must connect:

* dynamic marketing dashboard,
* local WILQ API,
* connector registry,
* full API connector boundaries,
* expert marketing rules,
* action object model,
* knowledge compiler foundation,
* Codex Desktop/CLI runtime,
* Codex skills,
* Codex hooks,
* subagent workflow,
* useful quality gates,
* repository-level `AGENTS.md`.

The product is not a generic BI dashboard, static report generator, prompt pack, or artifact factory. It is a **marketing operating system** that turns real marketing data into decisions and executable actions.

---

## 2. Product thesis

WILQ should be able to start the day in Codex Desktop/CLI or the dashboard and immediately see:

1. What is wasting money in Google Ads.
2. What can generate more SEO traffic from GSC data.
3. Which Ads search terms should become SEO/content/landing opportunities.
4. Which content already exists and must not be duplicated.
5. Which content should be rewritten, merged, refreshed, created, or published.
6. What should be posted on LinkedIn/Facebook.
7. What needs attention in Localo / local visibility / Google Business Profile.
8. What can be executed through real APIs.
9. What Codex did, which data it used, and what action objects it produced.

The system must make raw metrics usable for a marketer:

```txt
metric → diagnosis → evidence → recommended action → API payload → execution/audit
```

The core rule:

```txt
No evidence ID → no recommendation.
No source connector → no recommendation.
No validated payload → no apply.
No audit event → no write.
No WILQ API call → Codex must not invent metrics.
```

---

## 3. Non-negotiable philosophy

### 3.1 Final-product-first

Do not frame this repository as a disposable MVP, demo, fake POC, or static proof.

Build production-shaped foundations from the first commit:

* clear contracts,
* typed schemas,
* connector boundaries,
* action model,
* audit trail,
* quality gates,
* Codex runtime integration,
* dashboard that consumes the same API as Codex skills.

### 3.2 No artifact-driven development

Do not create a culture of “generate artifact and move on”.

Forbidden as product direction:

* static HTML reports,
* generated mock dashboards detached from real API,
* one-off markdown dumps replacing system behavior,
* screenshots as proof of architecture,
* fake final behavior,
* prompt-only workflows without code contracts,
* snapshot reports as the main product surface.

Allowed as technical infrastructure:

* local operational state,
* freshness metadata,
* event logs,
* audit logs,
* local cache for expensive APIs,
* reproducible fixtures for tests,
* handoff documents after verified implementation.

Do not confuse operational memory/cache with “snapshot product”. The UI must present freshness and source state, not static report artifacts.

### 3.3 API-first

The WILQ API is the source of truth.

Dashboard must call WILQ API.
Codex skills must call WILQ API.
Hooks must call WILQ API.
Action execution must go through WILQ API.
Expert rules must be consumable by WILQ API.

Do not let the dashboard, Codex skills, and connector scripts become three separate products.

### 3.4 Codex as operator, not metric source

Codex may reason, plan, inspect, write code, and generate marketer-facing text. Codex must not invent metrics, evidence, campaign state, GSC results, Ahrefs findings, Localo rankings, WordPress content inventory, or social performance.

For marketing recommendations, Codex must fetch a context pack from WILQ API.

### 3.5 Use real API capability from the beginning

Design for real read/write APIs from the first goal.

Do not block the architecture on missing credentials. If credentials are missing, expose honest connector status and exact missing env/config, but keep the connector boundary production-shaped.

Write actions are allowed, but must be represented as action objects with validation, risk, payload, evidence, and audit.

---

## 4. Confirmed external source anchors

Use the following source anchors when implementing docs, references, rules, and connector boundaries.

### 4.1 Codex / agent workflow anchors

* OpenAI Codex `/goal`: durable objective, long-running work, clear success condition, validation loop.
* OpenAI Codex Skills: repo-scoped `.agents/skills`, `SKILL.md`, optional `scripts/`, `references/`, `assets/`, progressive disclosure.
* OpenAI Codex Hooks: deterministic lifecycle scripts for SessionStart, Stop, tool-use validation, logging, guardrails.
* OpenAI Codex Subagents: parallel specialized agents for complex tasks; spawn explicitly; consolidate handoffs.
* Codex non-interactive mode: `codex exec`, JSONL output, schema output, CI/smoke usage.
* AGENTS.md open format: repository-level agent instructions, setup commands, tests, code style, security, conventions.
* Academic/industry anchor: AGENTS.md can improve coding-agent efficiency and reduce runtime/token consumption.

### 4.2 Marketing API anchors

* Google Ads API:

  * mutate operations and temporary resource names,
  * recommendations and optimization score,
  * search terms,
  * campaigns,
  * ad groups,
  * keywords,
  * negative keywords,
  * responsive search ads,
  * assets,
  * quality score diagnostics.
* Google Search Console API:

  * Search Analytics query endpoint,
  * clicks,
  * impressions,
  * CTR,
  * position,
  * query/page/date/device dimensions.
* Ahrefs API v3:

  * Site Explorer,
  * Keywords Explorer,
  * Site Audit,
  * Rank Tracker,
  * SERP Overview,
  * Batch Analysis,
  * Brand Radar,
  * social/media endpoints where available.
* Localo API/MCP:

  * local rankings,
  * local visibility,
  * Google Business Profile visibility,
  * competitor comparison,
  * reviews/tasks/posts where available.
* WordPress REST API:

  * read/write posts,
  * read/write pages,
  * metadata,
  * content inventory for `ekologus.pl` and `sklep.ekologus.pl`.
* LinkedIn Posts API:

  * organization publishing requires correct roles and permissions.
* Facebook Pages API:

  * page post creation, publishing, updating where permissions allow.

### 4.3 Academic and evaluation anchors

Use these as early architecture constraints, not as late research decorations:

* RAG: external non-parametric memory improves factuality and updateability compared to relying only on model parameters.
* Lost in the Middle: long-context models may underuse information placed in the middle; do not rely on giant prompts as a knowledge strategy.
* Self-RAG: retrieval and critique/self-reflection patterns improve factuality and controllability.
* RAGAS: retrieval and generation quality must be evaluated with retrieval relevance, faithfulness, context precision, and answer quality.
* Ad text strength / CTR prediction research: ad text quality can be evaluated using CTR prediction and semantic similarity to stronger ads; do not treat ad copy generation as pure creative writing.
* Type-checking research: type systems and static checks are part of code comprehension and defect prevention; use TypeScript and Python typing from the beginning.

---

## 5. Final technology stack

### 5.1 Backend

Use:

* Python 3.12+
* FastAPI
* Pydantic v2
* SQLModel or SQLAlchemy
* SQLite for operational state
* DuckDB for analytical metric store
* httpx for HTTP connector calls
* Typer for local CLI
* APScheduler or a minimal job abstraction for connector refresh orchestration
* optional Redis later only if real background workload requires it

Backend responsibilities:

* API spine,
* connector registry,
* credential/config status,
* metric normalization,
* expert rule evaluation,
* opportunity generation,
* action object validation,
* action execution,
* audit events,
* Codex context packs,
* knowledge card management.

### 5.2 Frontend

Use:

* Vite
* React
* TypeScript
* TanStack Query
* TanStack Router
* TanStack Table
* Tailwind
* Radix/shadcn-style components
* Recharts or equivalent lightweight charts
* Zod for runtime validation at frontend boundaries

Frontend responsibilities:

* command center,
* connector status,
* opportunities,
* actions,
* Ads Doctor,
* SEO/GSC Doctor,
* Ahrefs Lab,
* Localo Operator,
* Content Planner,
* Content Inventory,
* Social Publisher,
* Knowledge Base,
* Codex Runs,
* Settings.

### 5.3 Codex runtime

Use:

* root `AGENTS.md`,
* `.codex/hooks.json`,
* `.codex/agents/` for custom subagent definitions,
* `.agents/skills/` for repo-scoped skills,
* `codex exec` smoke tests,
* JSON schema validation for Codex outputs,
* WILQ API context packs.

Codex must work as an operator for the WILQ API, not as a disconnected chatbot.

### 5.4 Quality tooling

Adopt quality tooling from the first goal.

Python:

* `ruff check`
* `ruff format --check`
* `mypy`
* `pytest`
* `pytest-cov` where useful
* `bandit`
* `pip-audit`
* `semgrep`
* `detect-secrets` or equivalent secret scanning
* `pre-commit`

Frontend:

* `tsc --noEmit`
* `eslint`
* `vitest`
* `playwright` for minimal smoke/e2e once dashboard is runnable
* `zod` schema validation at API boundaries

Repository:

* `.editorconfig`
* `.gitignore`
* `.env.example`
* `.pre-commit-config.yaml`
* scripts for `quality`, `test`, `lint`, `typecheck`, `security`, `verify`
* docs for quality gates and local dev

Do not create quality theater. Every quality gate must catch realistic failure classes:

* invalid schemas,
* connector misconfiguration,
* missing evidence IDs,
* unsafe write action,
* secret leak,
* bad imports,
* type errors,
* broken dashboard route,
* broken API contract,
* Codex output not matching schema.

---

## 6. Required repository structure

Create or converge toward this structure:

```txt
.
├── AGENTS.md
├── README.md
├── .env.example
├── .gitignore
├── .editorconfig
├── .pre-commit-config.yaml
├── pyproject.toml
├── package.json
├── pnpm-workspace.yaml
├── docs/
│   ├── goals/
│   │   └── 001-goal.md
│   ├── architecture/
│   │   ├── system-overview.md
│   │   ├── action-model.md
│   │   ├── connector-registry.md
│   │   ├── dashboard-information-architecture.md
│   │   ├── codex-runtime.md
│   │   └── quality-gates.md
│   ├── research/
│   │   ├── source-registry.md
│   │   ├── ads-expert-sources.md
│   │   ├── retrieval-and-knowledge-patterns.md
│   │   └── code-quality-sources.md
│   └── handoffs/
├── apps/
│   ├── api/
│   └── dashboard/
├── packages/
│   └── shared-schemas/
├── wilq/
│   ├── actions/
│   ├── connectors/
│   ├── expert/
│   ├── knowledge/
│   ├── opportunities/
│   ├── codex/
│   └── storage/
├── .codex/
│   ├── hooks.json
│   └── agents/
├── .agents/
│   └── skills/
├── scripts/
└── tests/
```

If the repository already has a different structure, inspect it first and adapt surgically. Do not rewrite unrelated repo layout without cause.

---

## 7. Required `AGENTS.md`

Create a detailed root `AGENTS.md`.

It must include at least these sections:

```txt
# AGENTS.md

## Project identity
## Product philosophy
## Runtime model
## Architecture rules
## Evidence and metrics rules
## API-first rules
## Dashboard rules
## Codex skills and hooks rules
## Marketing expert rules
## Write action rules
## Knowledge compiler rules
## Quality gates
## Security rules
## Subagent workflow
## Development commands
## Testing instructions
## Stop conditions
## Forbidden behavior
```

### 7.1 AGENTS.md content requirements

The `AGENTS.md` must explicitly say:

* This repo builds WILQ Marketing Operating System for Ekologus.
* WILQ is the marketer.
* Codex Desktop/CLI is the primary operator runtime.
* Dashboard and Codex skills must use the same WILQ API.
* The project must not produce disconnected static artifacts.
* The project must not build static HTML reports.
* The project must not use mock/fake data as final behavior.
* The project must not let Codex invent metrics.
* Every marketing recommendation requires evidence IDs.
* Every write action requires validated action object and audit event.
* MCP servers are adapters, not the system brain.
* The WILQ API is the system brain.
* Expert rules must be structured and consumed by code.
* Tests must be useful and tied to real failure modes.
* Quality gates are mandatory from the first goal.
* Secrets must never be committed or printed.
* Missing credentials must be exposed honestly, not hidden.
* Agents must prefer surgical changes.
* Agents must explain assumptions before broad implementation.
* Agents must use subagents for large parallel analysis.
* Agents must merge subagent handoffs into one implementation plan before coding.
* Agents must leave a handoff document after goal completion.

### 7.2 AGENTS.md forbidden behavior

Include this exact forbidden behavior block:

```txt
## Forbidden behavior

Do not:
- Build static report artifacts instead of system behavior.
- Create one-off HTML dashboards.
- Treat screenshots as product progress.
- Hide missing connector credentials.
- Invent marketing metrics or source facts.
- Generate recommendations without evidence IDs.
- Generate API write payloads without validation.
- Execute destructive write actions without explicit action model support.
- Split dashboard logic from Codex skill logic.
- Put business logic only in prompts.
- Put connector logic only in skills.
- Add vector DB before the knowledge compiler and evidence model exist.
- Add multi-client abstraction before Ekologus works deeply.
- Add test theater unrelated to product risk.
- Refactor unrelated code.
- Commit secrets, tokens, credential dumps, or protected client data.
```

### 7.3 AGENTS.md working style

Include this exact working style block:

```txt
## Working style

Think before coding.
State assumptions.
Prefer small verified slices.
Use subagents for parallel investigation.
Merge findings before implementation.
Touch only files required by the goal.
Every changed line must trace to the goal.
Use structured schemas before prose.
Use real API boundaries before prompt cleverness.
Use dashboard/API/Codex as one product surface.
Validate before claiming done.
Leave durable docs and handoff.
```

---

## 8. API spine deliverables

Implement the initial WILQ API spine.

Required endpoints:

```txt
GET  /api/health
GET  /api/system/status
GET  /api/connectors
GET  /api/connectors/{connector}/status
POST /api/connectors/{connector}/refresh

GET  /api/dashboard/command-center

GET  /api/opportunities
GET  /api/opportunities/{id}
POST /api/opportunities/recompute

GET  /api/actions
GET  /api/actions/{id}
POST /api/actions/{id}/validate
POST /api/actions/{id}/apply

GET  /api/knowledge/cards
GET  /api/knowledge/search
POST /api/knowledge/condense

GET  /api/codex/context
POST /api/codex/context-pack
POST /api/codex/runs
GET  /api/codex/runs
```

The API must expose OpenAPI documentation through FastAPI.

---

## 9. Connector registry deliverables

Implement connector registry with these connectors:

```txt
google_ads
google_search_console
ahrefs
localo
wordpress_ekologus
wordpress_sklep
linkedin
facebook
```

Each connector must expose:

```txt
id
label
status
configured
missing_credentials
error
last_success_at
freshness
capabilities.read
capabilities.write
required_env
supported_actions
health_check
```

Statuses:

```txt
configured
missing_credentials
missing_dependency
unreachable
auth_error
rate_limited
error
disabled
```

Do not hide missing credentials. The dashboard must be able to show exactly what is missing without printing secret values.

---

## 10. Core schema deliverables

Implement typed schemas for:

```txt
ConnectorStatus
ConnectorCapability
Evidence
MetricFact
Opportunity
ActionObject
ActionValidationResult
ActionApplyResult
ActionMode
ActionRisk
CodexRun
KnowledgeCard
ServiceCard
ContentCard
KeywordClusterCard
CampaignCard
VoiceRule
SourceDocument
FreshnessState
AuditEvent
```

Required enums:

```txt
ActionMode:
- suggest
- prepare
- apply

ActionRisk:
- low
- medium
- high
- critical

OpportunityDomain:
- google_ads
- gsc_seo
- ahrefs
- localo
- wordpress
- social
- knowledge
- content
- codex
```

Schema hard rules:

* `Opportunity` requires at least one source connector.
* `Opportunity` requires at least one evidence ID.
* `Opportunity` requires plain-language diagnosis.
* `ActionObject` requires evidence IDs.
* `ActionObject` requires mode.
* `ActionObject` requires risk.
* `ActionObject` requires connector.
* `ActionObject` requires validation status before apply.
* `CodexRun` must record skill/hook/source where available.
* `KnowledgeCard` must record source lineage where available.

---

## 11. Action object model

Action objects are the core execution primitive.

Every action must contain:

```txt
id
title
domain
connector
mode
risk
status
evidence_ids
metrics
human_diagnosis
recommended_reason
payload
validation_status
created_by
created_at
updated_at
audit_events
```

Allowed statuses:

```txt
new
ready
needs_validation
validation_failed
ready_to_apply
applying
applied
failed
dismissed
blocked
```

Validation rules:

* `apply` must fail if evidence IDs are missing.
* `apply` must fail if connector is not configured.
* `apply` must fail if payload is invalid for connector/action type.
* `apply` must record audit event.
* high/critical risk must require explicit support in action model.
* destructive actions must be blocked until separately implemented.

This goal does not need to implement all real write operations, but the model must be production-shaped and not fake.

---

## 12. Expert rules foundation

Create structured expert rules under:

```txt
wilq/expert/
├── ads/
├── seo/
├── content/
├── local/
└── social/
```

Initial files:

```txt
wilq/expert/ads/principles.yaml
wilq/expert/ads/diagnostics.yaml
wilq/expert/ads/search_terms.yaml
wilq/expert/ads/negative_keywords.yaml
wilq/expert/ads/responsive_search_ads.yaml
wilq/expert/ads/quality_score.yaml
wilq/expert/ads/recommendations.yaml
wilq/expert/ads/landing_page_alignment.yaml

wilq/expert/seo/gsc_opportunities.yaml
wilq/expert/seo/query_page_matrix.yaml
wilq/expert/seo/content_decay.yaml
wilq/expert/seo/cannibalization.yaml

wilq/expert/content/voice_rules.yaml
wilq/expert/content/duplication_rules.yaml
wilq/expert/content/brief_rules.yaml
wilq/expert/content/social_limits.yaml

wilq/expert/local/local_visibility.yaml
wilq/expert/local/reviews.yaml

wilq/expert/social/linkedin_rules.yaml
wilq/expert/social/facebook_rules.yaml
```

Rules must be structured, versioned, and consumable by code. Do not make them prose-only prompt blobs.

Each rule file should support:

```txt
id
name
source_anchor
when_to_use
required_inputs
diagnostic_logic
recommended_actions
risk_notes
output_contract
```

---

## 13. Opportunity engine foundation

Implement the initial opportunity engine with these opportunity types:

```txt
google_ads_waste
google_ads_negative_keywords
google_ads_landing_mismatch
google_ads_recommendation_review
google_ads_quality_score_issue
gsc_ctr_opportunity
gsc_content_decay
gsc_cannibalization
gsc_near_top_opportunity
ahrefs_content_gap
ahrefs_competitor_gap
ahrefs_backlink_gap
localo_visibility_drop
wordpress_content_refresh
wordpress_duplicate_content_risk
social_post_candidate
content_brief_candidate
```

The engine may initially use deterministic fixture-like seed inputs only for tests, but product code must clearly separate:

```txt
real connector data
test fixtures
seed/demo dev data
```

Never present fixtures as real Ekologus state.

---

## 14. Dashboard deliverables

Create dynamic dashboard shell with these routes:

```txt
/command-center
/opportunities
/opportunities/:id
/actions
/actions/:id
/ads-doctor
/seo-gsc
/ahrefs
/localo
/content-planner
/content-inventory
/social-publisher
/knowledge
/codex-runs
/settings
```

Dashboard rules:

* Must be React/TypeScript, not static HTML.
* Must use API calls through TanStack Query.
* Must expose connector freshness/status.
* Must show command center as default route.
* Must show opportunity cards with raw metrics and human diagnosis.
* Must show action detail panel with evidence, payload, validation, risk, status.
* Must show missing connector credentials honestly.
* Must not include fake “final” metrics.
* Must not hardcode marketing insight text disconnected from API.

Dashboard usefulness acceptance:

* A route is not marketer-useful just because it renders.
* Each final operating route must show real API-backed metrics that help a Polish marketer decide what to do next.
* Ads views must show spend, waste, search terms, recommendation, quality, impression-share, scaling, custom-segment and Demand Gen readiness diagnostics when the connectors can provide them.
* SEO/GSC views must show query/page clicks, impressions, CTR, average position, decay, near-top opportunities and cannibalization evidence.
* GA4 views must show engagement, sessions, landing-page quality, source/medium quality and conversion/event availability.
* Merchant views must show product counts, disapprovals, expiring products, issue counts, feed/data-source state and product-ad readiness.
* Content, social and Localo views must show inventory, blockers, evidence IDs, freshness and action candidates instead of generic route filler.
* If live metrics are unavailable, the view must say exactly which connector, credential, OAuth scope, API enablement or vendor-read adapter is blocking them.

Initial Command Center sections:

```txt
Today’s Moves
Money Leaks
Traffic Wins
Content To Rewrite
Content To Create
Local Visibility Moves
Social Queue
Codex Operator Status
Connector Health
```

---

## 15. Codex runtime deliverables

Create:

```txt
.codex/hooks.json
.codex/agents/
.agents/skills/
wilq/codex/
```

### 15.1 Hooks

Implement or scaffold hooks for:

```txt
SessionStart
Stop
```

SessionStart behavior:

* check WILQ API health,
* show whether API is reachable,
* tell Codex to use WILQ API for all marketing metrics,
* warn if connectors are missing,
* do not print secrets.

Stop behavior:

* attempt to log run summary to `/api/codex/runs`,
* never fail the whole coding task if API is unreachable,
* avoid logging secrets or large private payloads.

### 15.2 Skills

Create skill folders:

```txt
.agents/skills/wilq-daily-command/
.agents/skills/wilq-ads-doctor/
.agents/skills/wilq-gsc-content-doctor/
.agents/skills/wilq-ahrefs-gap-finder/
.agents/skills/wilq-localo-operator/
.agents/skills/wilq-content-strategist/
.agents/skills/wilq-social-publisher/
.agents/skills/wilq-campaign-builder/
```

Each skill must include:

```txt
SKILL.md
references/
scripts/
```

For Goal 001, only `wilq-daily-command` must be functionally wired to WILQ API.

Other skills must have production-shaped stubs with:

* clear trigger description,
* what API endpoints they will call,
* what evidence they require,
* what output schema they must follow,
* explicit warning not to invent metrics.

### 15.3 Codex context pack

Implement:

```txt
POST /api/codex/context-pack
```

It must return:

```txt
current product rules
available connectors
connector status
top opportunities
active action objects
knowledge card summaries
strict instruction not to invent metrics
```

---

## 16. Knowledge compiler foundation

Create foundation for knowledge cards.

Required card types:

```txt
service_card
content_card
keyword_cluster_card
campaign_card
voice_rule
ads_pattern_card
negative_keyword_pattern_card
competitor_card
local_visibility_card
social_pattern_card
```

The knowledge system must preserve lineage:

```txt
source_type
source_id
source_url_or_path
extracted_at
confidence
last_seen_at
```

Knowledge compiler rule:

```txt
Do not stuff everything into long prompts.
Condense source material into canonical cards first.
Retrieve or expose compact context packs to Codex.
```

This is required because long context can hide relevant facts and because marketing recommendations must be explainable.

---

## 17. Source registry deliverables

Create:

```txt
docs/research/source-registry.md
docs/research/ads-expert-sources.md
docs/research/retrieval-and-knowledge-patterns.md
docs/research/code-quality-sources.md
```

These docs must record:

* source title,
* domain,
* why it matters,
* product decision affected,
* implementation location,
* last checked date.

Do not paste long copyrighted passages. Summarize and link.

At minimum include source anchors for:

```txt
OpenAI Codex /goal
OpenAI Codex Skills
OpenAI Codex Hooks
OpenAI Codex Subagents
OpenAI Codex non-interactive mode
AGENTS.md open format
AGENTS.md efficiency paper
Google Ads API mutate best practices
Google Ads Recommendations API
Google Ads Quality Score
Google Ads negative keywords
Google Ads responsive search ads
Google Search Console Search Analytics
Ahrefs API v3
Localo API/MCP integration
WordPress REST API
LinkedIn Posts API
Facebook Pages API
RAG paper
Lost in the Middle
Self-RAG
RAGAS
Ruff
mypy
pre-commit
Bandit
pip-audit
Semgrep
ESLint
TypeScript
Vitest
Playwright
Zod
TanStack Query
```

---

## 18. Quality gates deliverables

Create scripts:

```txt
scripts/quality.sh
scripts/test.sh
scripts/lint.sh
scripts/typecheck.sh
scripts/security.sh
scripts/verify.sh
```

Expected behavior:

```txt
scripts/lint.sh
- ruff check
- eslint where frontend exists

scripts/typecheck.sh
- mypy
- tsc --noEmit where frontend exists

scripts/test.sh
- pytest
- vitest where frontend exists

scripts/security.sh
- bandit
- pip-audit
- semgrep
- detect-secrets or equivalent if configured

scripts/quality.sh
- lint
- typecheck
- test

scripts/verify.sh
- quality
- security
- API smoke if runnable
- dashboard build if runnable
```

Quality gates should be strict enough to catch real issues but should not block progress on unrelated perfection.

If a tool cannot be configured immediately because the repo is empty, create the config and document exact next step.

---

## 19. Initial tests

Backend tests:

```txt
test_health_endpoint
test_connector_registry_contains_required_connectors
test_connector_status_does_not_expose_secret_values
test_opportunity_requires_source_connector
test_opportunity_requires_evidence_id
test_action_requires_evidence_id
test_action_apply_requires_validation
test_command_center_returns_valid_shape
test_codex_context_pack_contains_no_metric_invention_instruction
```

Frontend tests:

```txt
command center renders
connector status renders
opportunities route renders
action detail route renders
missing connector state renders
```

Codex tests:

```txt
codex context endpoint returns strict rules
sample Codex run validates against schema
wilq-daily-command script can fetch API context if API is running
```

Do not create tests that only prove mocks exist.

---

## 20. Subagent strategy

Before implementation, spawn subagents. Use them aggressively but with clear boundaries.

Required subagents:

```txt
Lead Architect Agent
API Kernel Agent
Connector Registry Agent
Google Ads Connector Agent
Ads Expert Rules Agent
GSC/SEO Agent
Ahrefs Agent
Localo Agent
WordPress Connector Agent
Social Publisher Agent
Knowledge Compiler Agent
Dashboard UX Agent
Frontend Implementation Agent
Codex Runtime Agent
Security & Safety Agent
QA/Eval Agent
Integration Orchestrator Agent
```

Each subagent must return:

```txt
findings
risks
files to create/change
contracts/schemas affected
validation checks
handoff to Lead Architect
```

Lead Architect must merge all handoffs into one implementation plan before coding.

Subagents must not independently create conflicting architecture.

---

## 21. Implementation order

Follow this order unless repo inspection proves a better path:

1. Inspect repository structure.
2. Create `docs/goals/001-goal.md`.
3. Create `AGENTS.md`.
4. Create base docs under `docs/architecture` and `docs/research`.
5. Create backend project skeleton.
6. Create core schemas.
7. Create connector registry.
8. Create API spine.
9. Create action model.
10. Create expert rules skeleton.
11. Create opportunity engine foundation.
12. Create dashboard skeleton.
13. Create Codex hooks and skills skeleton.
14. Wire `wilq-daily-command` to WILQ API.
15. Add quality tooling.
16. Add useful tests.
17. Run quality gates.
18. Create handoff.

---

## 22. Non-goals for Goal 001

Do not:

* implement every real connector fully,
* implement all Google Ads write operations,
* implement destructive API actions,
* implement multi-client architecture,
* implement vector DB,
* implement SaaS auth,
* implement full RAG,
* implement full social publishing flow,
* implement final UI polish,
* create static reports,
* create static HTML dashboards,
* create artifact-only deliverables,
* fake real Ekologus data,
* hide missing credentials.

Goal 001 is not a tiny MVP. It is the foundation of the final product. The non-goal is not “ambition”; the non-goal is uncontrolled scope that prevents the foundation from being correct.

---

## 23. Validation commands

Run what exists. Add what is missing.

Minimum target commands:

```bash
scripts/lint.sh
scripts/typecheck.sh
scripts/test.sh
scripts/security.sh
scripts/quality.sh
scripts/verify.sh
```

Backend examples:

```bash
pytest
ruff check .
ruff format --check .
mypy .
bandit -r .
pip-audit
semgrep scan --config auto
```

Frontend examples:

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
npx playwright test
```

Codex examples:

```bash
codex exec --json "Use the wilq-daily-command skill to fetch WILQ API context and return the top available operational marketing actions. Do not invent metrics."
```

If Codex is unavailable in the environment, document that honestly and validate the scripts/schema manually.

---

## 24. Stop condition

Stop only when all are true:

* `docs/goals/001-goal.md` exists and contains this goal.
* Root `AGENTS.md` exists and contains the required working rules.
* Source registry docs exist.
* Architecture docs exist.
* API skeleton runs or has documented setup if dependencies are not installed.
* Core schemas exist and reject missing evidence/source fields.
* Connector registry exposes all required connectors honestly.
* API spine exposes required endpoints.
* Action object model exists.
* Expert rules foundation exists as structured files.
* Opportunity engine foundation exists.
* Dashboard skeleton renders planned routes or has a runnable frontend skeleton.
* Dashboard limitations are documented honestly; a rendered shell must not be described as a final marketer-useful dashboard until real metric views and diagnostic queues exist.
* Codex hooks exist.
* Skills folders exist.
* `wilq-daily-command` is wired to WILQ API if API can run.
* Quality scripts exist.
* Useful tests exist.
* Verification commands were run where possible.
* Failures are documented honestly.
* A handoff document exists under `docs/handoffs/`.

---

## 25. Handoff requirements

Create:

```txt
docs/handoffs/001-wilq-marketing-operating-system-core-handoff.md
```

The handoff must include:

```txt
what was built
what files changed
what commands were run
what passed
what failed
why failures remain
connector status
quality gate status
Codex runtime status
dashboard status
API status
next recommended goal
```

The next recommended goal should be named:

```txt
Goal 002 — Google Ads Connector and Ads Doctor
```

Do not create a huge backlog disguised as a handoff. Give the next highest-leverage goal.

## 25A. Access pack bootstrap requirements

Goal 001 must include first-class support for the Ekologus access pack.

Known access pack location:

```txt
/home/krn/ekologus-access-pack-20260617-120758
/home/krn/ekologus-access-pack-20260617-120758.tar.gz
```

Known access pack contents:

```txt
ekologus.env
README.md
MANIFEST.txt
source-notes/krn-ekologus-superior.env.raw
credentials/gcloud-application_default_credentials.json
credentials/krn-seo-google-ads-oauth-client.json
credentials/seo-command-center-google-ads-oauth-client.json
```

Known variable groups include:

```txt
Ahrefs
Google Search Console
Google Ads
GA4
WordPress staging
Google Sheets
OpenAI/Codex
Ekologus URLs
```

Required deliverables:

```txt
wilq/access_pack/
docs/architecture/access-pack-bootstrap.md
docs/security/credential-handling.md
scripts/access_pack_check.sh
scripts/access_pack_manifest.sh
```

Implementation requirements:

* Do not copy secrets into committed files.
* Do not print secret values.
* Do not commit raw `.env` files.
* Do not commit OAuth JSON files.
* Read only variable names and credential availability.
* Generate safe connector status from env presence.
* Generate `.env.example` from manifest keys without values.
* Expose missing credentials through connector status without values.
* Add redaction utilities before any connector logs are implemented.
* Add tests proving secret values are not exposed through connector status, logs, API responses, handoffs, or Codex context packs.

Access pack should become the source of initial connector configuration, not a loose manual setup note.

---

## 25B. Additional first-class connectors

Extend the required connector registry beyond the original list.

Required connectors for Goal 001:

```txt
google_ads
google_search_console
google_analytics_4
google_merchant_center
google_sheets
ahrefs
localo
wordpress_ekologus
wordpress_sklep
linkedin
facebook
openai_codex
```

Each connector must expose:

```txt
id
label
status
configured
missing_credentials
error
last_success_at
freshness
capabilities.read
capabilities.write
required_env
supported_actions
rate_limit_notes
cost_notes
risk_notes
health_check
```

Connector-specific notes:

```txt
google_analytics_4
- must support acquisition, engagement, conversion, landing page, source/medium, campaign and funnel diagnostics.
- must connect Ads/GSC outcomes to real site behavior.

google_merchant_center
- must support product/feed visibility, feed health, data sources, product diagnostics, product issue checks and future product ad workflows.
- required because sklep.ekologus.pl exists and product/shop ads were mentioned as a target.

google_sheets
- must support export/import workflows for marketer-friendly review, bulk edits, client summaries and structured handoff tables.
- Sheets is not the main system, only a collaboration/export surface.

openai_codex
- must expose runtime availability, codex exec availability, skill directory status, hook status and model/runtime notes.
```

Do not hide connectors just because credentials are missing. Missing connector state is product information.

---

## 25C. BDOS-inspired Google Ads capability pack

Add a dedicated product capability pack inspired by BDOS-class workflows, but implemented as our own WILQ API/action system.

Create:

```txt
docs/architecture/google-ads-capability-pack.md
wilq/expert/ads/capabilities.yaml
wilq/expert/ads/demand_gen.yaml
wilq/expert/ads/custom_segments.yaml
wilq/expert/ads/keyword_planner.yaml
wilq/expert/ads/impression_share.yaml
wilq/expert/ads/seasonality.yaml
wilq/expert/ads/scaling_candidates.yaml
wilq/expert/ads/experiments.yaml
```

Required capabilities:

```txt
ads_daily_check
ads_monthly_review
ads_changes_review
ads_search_terms_ngram
ads_negative_keywords
ads_keyword_research
ads_custom_segments
ads_create_custom_segments_from_search_terms
ads_demand_gen_migration_readiness
ads_demand_gen_campaign_builder
ads_audience_targeting
ads_scaling_candidates
ads_budget_cap_diagnostics
ads_impression_share_diagnostics
ads_holiday_impact_diagnostics
ads_seasonality_adjustments
ads_recommendations_review
ads_quality_score_diagnostics
ads_rsa_generation_and_validation
ads_campaign_builder
ads_pmax_channels
ads_pmax_asset_review
ads_merchant_review
ads_feed_optimize
ads_bucketing
ads_ga4_data_analyst
```

Capability rule:

```txt
Every Ads capability must map to:
- required connector inputs,
- required evidence,
- metrics,
- diagnosis logic,
- action object types,
- risk level,
- write capability,
- API limitations,
- validation checks.
```

Do not implement these as loose commands only. They must exist as capability definitions consumed by API, dashboard and skills.

---

## 25D. Demand Gen and Display-to-Demand-Gen migration readiness

Add Demand Gen as a first-class Google Ads module.

Create:

```txt
wilq/connectors/google_ads/demand_gen.py
wilq/opportunities/rules/demand_gen.py
wilq/expert/ads/demand_gen.yaml
docs/architecture/demand-gen-migration.md
```

Required diagnostics:

```txt
display_campaign_inventory
display_to_demand_gen_migration_candidates
demand_gen_asset_readiness
demand_gen_image_asset_requirements
demand_gen_video_asset_requirements
demand_gen_carousel_readiness
demand_gen_cta_variants
demand_gen_audience_targeting
demand_gen_google_ai_enhancements_status
demand_gen_budget_and_goal_alignment
```

Required actions:

```txt
prepare_demand_gen_migration_plan
prepare_demand_gen_campaign
prepare_demand_gen_ad_group
prepare_demand_gen_audience_targeting
prepare_demand_gen_creative_requirements
prepare_demand_gen_cta_test
apply_demand_gen_campaign_changes
```

Rules:

* Detect Display campaigns that need migration planning.
* Detect missing or weak creative assets.
* Detect whether audience targeting is configured correctly.
* Treat Google AI enhancements as explicit state; do not silently enable them.
* Expose campaign-readiness score in Dashboard.
* Add a Dashboard route or section under Ads Doctor for Demand Gen readiness.

---

## 25E. Custom segments from real search terms and Keyword Planner

Add a first-class workflow equivalent to:

```txt
create custom segments from real search terms
validate using Keyword Planner
add as targeting to Demand Gen / Display / Search where supported
```

Create:

```txt
wilq/expert/ads/custom_segments.yaml
wilq/expert/ads/keyword_planner.yaml
wilq/opportunities/rules/custom_segments.py
wilq/actions/google_ads/custom_segments.py
docs/architecture/custom-segments-from-search-terms.md
```

Required pipeline:

```txt
1. Pull real search terms from Google Ads.
2. Cluster and clean search terms.
3. Remove irrelevant, low-intent, brand-risk or duplicated terms.
4. Enrich with Keyword Planner ideas, historical metrics and forecasts.
5. Build candidate custom segment definitions.
6. Validate segment payload.
7. Create action object.
8. Apply custom audience / audience targeting where supported.
9. Log evidence and action history.
```

Required UI:

```txt
Ads Doctor → Custom Segments
- source search terms
- cleaned terms
- rejected terms
- Keyword Planner enrichment
- segment payload
- target campaign/ad group
- supported campaign types
- action status
```

Required skill:

```txt
.agents/skills/wilq-custom-segments/
```

This skill must never invent audience terms. It must use WILQ API evidence from Google Ads search terms, Keyword Planner and existing campaigns.

---

## 25F. GA4 behavior and conversion diagnostics

Add GA4 as a core diagnostic connector.

Create:

```txt
wilq/connectors/google_analytics_4/
wilq/expert/analytics/ga4_diagnostics.yaml
wilq/opportunities/rules/ga4.py
docs/architecture/ga4-diagnostics.md
```

Required diagnostics:

```txt
landing_page_engagement
source_medium_performance
campaign_traffic_quality
conversion_path_diagnostics
funnel_dropoff
engaged_sessions
event_and_conversion_availability
ads_click_to_site_behavior
seo_click_to_site_behavior
content_quality_from_behavior
```

Required action objects:

```txt
ga4_landing_page_issue
ga4_campaign_quality_issue
ga4_funnel_dropoff_issue
ga4_tracking_gap
ga4_conversion_mapping_gap
```

Rules:

* Ads/GSC clicks are not enough.
* The system must connect acquisition data to on-site behavior.
* If GA4 conversion/event setup is missing, expose it as a measurement issue, not as marketing failure.
* GA4 must enrich Ads Doctor, SEO/GSC Doctor, Content Planner and Command Center.

---

## 25G. Merchant Center, product feed and shop marketing

Because `sklep.ekologus.pl` exists, add Merchant Center and product/feed intelligence from the beginning.

Create:

```txt
wilq/connectors/google_merchant_center/
wilq/expert/merchant/feed_rules.yaml
wilq/expert/merchant/product_diagnostics.yaml
wilq/opportunities/rules/merchant.py
docs/architecture/merchant-center-and-feed.md
```

Required diagnostics:

```txt
merchant_account_status
merchant_product_inventory
feed_data_source_status
product_input_status
product_disapprovals
missing_required_product_fields
weak_product_titles
weak_product_descriptions
product_category_gaps
pmax_retail_readiness
shopping_ads_readiness
```

Required action objects:

```txt
merchant_feed_issue
merchant_product_title_rewrite
merchant_product_description_rewrite
merchant_product_attribute_gap
pmax_retail_readiness_gap
shopping_campaign_candidate
```

Required dashboard sections:

```txt
Merchant / Feed Health
Product Ads Readiness
Feed Optimization Queue
```

Product copy rules:

* Product titles and descriptions must be generated from product data, not imagined.
* Changes must preserve factual product attributes.
* Feed changes must be validated before apply.
* If Merchant Center is not linked to Google Ads, expose this as a blocking connector relationship issue.

---

## 25H. Google Sheets as collaboration and bulk-edit surface

Add Google Sheets integration as a secondary operator surface.

Create:

```txt
wilq/connectors/google_sheets/
wilq/actions/google_sheets/
docs/architecture/google-sheets-operator-surface.md
```

Supported use cases:

```txt
export_opportunities_to_sheet
export_ads_search_terms_to_sheet
export_negative_keyword_candidates
export_content_plan
export_social_calendar
export_product_feed_issues
import_reviewed_bulk_edits
append_client_summary_rows
```

Rules:

* Sheets is not the source of truth.
* WILQ API remains the source of truth.
* Sheets exports must include evidence IDs and action IDs.
* Sheets imports must validate action IDs before applying anything.
* Imported rows must not execute write actions without action validation.

---

## 25I. Workflow parallelism and multi-run orchestration

BDOS-style productivity depends on parallel workflows, not a single slow agent pass.

Add workflow orchestration foundations.

Create:

```txt
wilq/workflows/
wilq/workflows/registry.py
wilq/workflows/models.py
docs/architecture/workflow-orchestration.md
```

Required workflow primitives:

```txt
Workflow
WorkflowRun
WorkflowStep
WorkflowInput
WorkflowOutput
WorkflowStatus
WorkflowEvidence
WorkflowActionObject
```

Initial workflows:

```txt
daily_command
monthly_review
ads_daily_check
ads_monthly_review
ads_changes_review
ads_search_terms_ngram
ads_custom_segments
demand_gen_readiness
gsc_content_doctor
ahrefs_gap_finder
localo_visibility_review
merchant_feed_review
ga4_data_analyst
content_calendar_builder
social_publishing_queue
```

Workflow requirements:

* Workflows must run against WILQ API.
* Workflows must be visible in Dashboard.
* Codex skills may trigger workflows, but not own the workflow logic.
* Workflow runs must record evidence IDs, action IDs, connector status and errors.
* Parallel runs must not create conflicting action objects without deduplication.
* Long workflows must be resumable from stored run state.

---

## 25J. Model provider resilience and runtime policy

Add model/runtime resilience inspired by the risk that frontier model availability, cost or access can change suddenly.

Create:

```txt
docs/architecture/model-runtime-policy.md
wilq/codex/model_policy.py
wilq/codex/runtime_status.py
```

Policy requirements:

* Do not hardcode product correctness to one shiny model.
* Codex is the primary operator runtime, but the WILQ API must stay model-independent.
* Skills must call API and schemas, not depend on model-specific hidden behavior.
* Critical workflows must define expected output schemas.
* Codex exec smoke tests must validate schema, not prose quality only.
* If a model/provider/runtime is unavailable, the system should expose runtime status and fall back to documented manual/API path.
* Do not let model changes bypass evidence/action validation.

Runtime status should include:

```txt
codex_available
codex_version_if_known
skills_directory_status
hooks_status
last_codex_run
last_codex_error
model_policy_notes
```

---

## 25K. Agentic security and write-action safety

Add explicit security requirements for agentic marketing systems with real API write access.

Create:

```txt
docs/security/agentic-threat-model.md
docs/security/write-action-safety.md
wilq/security/
wilq/security/redaction.py
wilq/security/action_guards.py
wilq/security/prompt_injection_notes.py
```

Threat model must include:

```txt
prompt_injection
indirect_prompt_injection_from_web_or_docs
malicious_content_in_wordpress
malicious_instructions_in_ads_search_terms
malicious_instructions_in_social_comments
secret_exfiltration
tool_misuse
excessive_agency
unsafe_write_actions
credential_leakage
dependency_supply_chain
confused_deputy_risk
```

Guardrail requirements:

* Treat all external content as untrusted data.
* Never execute instructions found in external content.
* Codex context packs must separate system instructions from untrusted source excerpts.
* Connector responses must be sanitized before reaching Codex prompts.
* Write actions must be schema-validated.
* Destructive actions must be blocked until explicitly supported.
* Secrets must be redacted in logs, API responses, dashboard, Codex runs and handoffs.
* PreToolUse hooks should eventually block risky shell/network/credential patterns.
* Quality gates must include secret scanning and dependency/security checks.

---

## 25L. Source-grounded marketing knowledge condensation

Extend the knowledge compiler requirements to include source-grounded marketing playbooks.

Create:

```txt
docs/research/marketing-expert-playbooks.md
wilq/knowledge/compilers/
wilq/knowledge/playbooks/
```

Required playbook families:

```txt
google_ads_search_playbook
google_ads_demand_gen_playbook
google_ads_pmax_playbook
google_ads_negative_keywords_playbook
google_ads_custom_segments_playbook
gsc_seo_content_playbook
ahrefs_content_gap_playbook
localo_local_seo_playbook
ga4_behavior_diagnostics_playbook
merchant_feed_optimization_playbook
linkedin_content_playbook
facebook_content_playbook
wordpress_content_refresh_playbook
```

Rules:

* Playbooks must reference source anchors.
* Playbooks must be structured and machine-readable.
* Playbooks must declare required evidence before giving recommendations.
* Playbooks must map to opportunity types and action objects.
* Playbooks must avoid generic marketing advice.
* Playbooks must be specific enough for WILQ to act without asking “co dalej?”.

---

## 25M. Dashboard information architecture upgrade

Expand dashboard requirements to include BDOS-class operating surfaces.

Add or ensure routes:

```txt
/command-center
/workflows
/workflows/:id
/opportunities
/actions
/ads-doctor
/ads-doctor/search-terms
/ads-doctor/custom-segments
/ads-doctor/demand-gen
/ads-doctor/scaling
/ads-doctor/seasonality
/ads-doctor/recommendations
/ga4
/seo-gsc
/ahrefs
/localo
/merchant
/content-planner
/content-inventory
/social-publisher
/google-sheets
/knowledge
/codex-runs
/security
/settings
```

Dashboard must support:

```txt
operator cards
workflow cards
connector freshness cards
evidence drawer
action drawer
API payload preview
validation errors
apply status
audit timeline
bulk action review
source lineage
risk indicators
```

Command Center must prioritize:

```txt
money leaks
scaling candidates
migration readiness
traffic wins
content gaps
feed issues
local visibility drops
social opportunities
tracking gaps
connector failures
Codex workflow failures
```

---

## 25N. Expanded stop condition additions

Extend the Goal 001 stop condition with these additional checks:

* Access pack bootstrap is documented.
* Access pack checker exists and does not print secret values.
* Connector registry includes GA4, Merchant Center, Google Sheets and OpenAI/Codex.
* Source registry includes Demand Gen migration, custom audiences, Keyword Planner, seasonality, impression share, GA4 Data API, Merchant API, Google Sheets API, OWASP LLM, NIST AI RMF and model runtime policy sources.
* Ads capability pack exists as structured YAML/docs.
* Demand Gen readiness is represented in expert rules and dashboard route plan.
* Custom segments from search terms workflow is represented in expert rules, action types and skill plan.
* GA4 diagnostics are represented in connector registry and opportunity types.
* Merchant/feed diagnostics are represented in connector registry and opportunity types.
* Google Sheets is represented as collaboration/export surface, not source of truth.
* Workflow orchestration foundation exists or is documented with schemas.
* Agentic security threat model exists.
* Model runtime policy exists.
* Dashboard IA includes workflow, Demand Gen, custom segments, GA4, Merchant and security surfaces.

---

## 26. Final executor reminder

This repository exists to give WILQ real leverage.

Do not build pretty dashboards that do not decide.
Do not build AI prompts that do not call APIs.
Do not build metrics that do not become actions.
Do not build actions without evidence.
Do not build write operations without validation and audit.
Do not build static artifacts instead of an operating system.

Build the system spine first.
Then connect the strongest data source.
Then make Codex and dashboard operate the same truth.
