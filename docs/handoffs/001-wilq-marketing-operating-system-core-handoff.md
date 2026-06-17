# Goal 001 Handoff — WILQ Marketing Operating System Core

Status: in progress, foundation verified. Goal 001 is not complete yet.

## What was built

- Private GitHub repo target was created: `korneliuszburian/wilq-seo`.
- `docs/goals/001-goal.md` was created from the active goal.
- Root `AGENTS.md` now defines WILQ product philosophy, API-first rules, evidence rules, MCP rules, skill creation timing, security rules, quality gates and forbidden behavior.
- FastAPI WILQ API spine exists with health, system status, connectors, connector refresh runs, dashboard command center, opportunities, actions, expert rules, knowledge, Codex context/runs and workflows endpoints.
- Pydantic schemas exist for connectors, connector refresh runs, evidence, metrics, opportunities, actions, audit events, Codex runs and knowledge cards.
- Connector registry includes Google Ads, GSC, GA4, Merchant Center, Ahrefs, Localo, WordPress, LinkedIn, Facebook and OpenAI/Codex. Google Sheets remains documented as an optional disabled collaboration/export surface, not a required evidence source.
- Action validation now checks evidence, connector, mode, risk and payload action type.
- React/TanStack Query dashboard shell exists with required operating routes, route tests, API-backed cards, detail panels, payload preview and audit section.
- Shared Zod schema package exists and the dashboard API client parses API responses at runtime.
- Expert YAML foundations exist for Ads, SEO, content, local, social, GA4 and merchant/feed rules.
- Expert rules are loaded through typed Pydantic contracts and exposed at `/api/expert/rules`, `/api/expert/rule-summaries` and `/api/expert/capabilities`.
- Codex context packs include expert rule summaries and Ads capability definitions so future skills can use API-provided rule contracts.
- Dashboard operating routes render expert-rule cards from `/api/expert/rules` through shared Zod validation.
- Local SQLite state persists Codex runs, workflow runs, connector refresh runs and audit events through `wilq/storage/local_state.py`.
- Workflow run APIs exist at `/api/workflows/{workflow_id}/runs` and `/api/workflow-runs`.
- Dashboard workflow routes render persisted workflow-run state through shared Zod validation.
- Machine-readable marketing playbooks exist in `wilq/knowledge/playbooks/marketing_playbooks.yaml`.
- `wilq/knowledge/compilers/playbook_compiler.py` compiles playbooks into lineage-preserving `KnowledgeCard` records.
- Knowledge APIs expose playbooks, compiled cards and deterministic condensation results.
- Dashboard knowledge routes render compiled cards and playbooks through shared Zod validation.
- Evidence registry APIs expose connector-status evidence without secret values.
- Connector refresh APIs create durable `status_probe` and read-only `vendor_read` runs with redacted evidence IDs and no invented vendor metrics.
- Google Ads, Google Search Console, GA4, Google Merchant Center, Ahrefs and both WordPress sites have first read-only `vendor_read` adapters that persist aggregate metrics/inventory only. Google Sheets has a read adapter but is disabled by current product scope.
- Opportunities are now derived from connector readiness evidence plus playbook/expert-rule mappings, not fixed demo opportunity rows.
- Workflow, model runtime, credential runtime, MCP, quality, security and source-registry docs exist.
- Codex hooks exist for SessionStart and Stop; they fail open and restrict API URL targets to local/allowed hosts.
- `.agents/skills/` now contains the Goal 001 WILQ operator skills. `wilq-daily-command` is wired to WILQ API; the remaining skills are production-shaped stubs with references, scripts, endpoint contracts, evidence requirements and output contracts.

## Skill status

Goal 001 skills have been created with `$skill-creator` under `.agents/skills/`.

- Fully wired: `wilq-daily-command`, which calls WILQ API context-pack through `scripts/smoke_context_pack.py`.
- Production-shaped stubs: `wilq-ads-doctor`, `wilq-gsc-content-doctor`, `wilq-ahrefs-gap-finder`, `wilq-localo-operator`, `wilq-content-strategist`, `wilq-social-publisher`, `wilq-campaign-builder`, `wilq-custom-segments`, `wilq-demand-gen-operator`, `wilq-ga4-analyst`, `wilq-merchant-feed-operator`.
- Every skill has `SKILL.md`, `references/output-contract.md`, `scripts/`, `agents/openai.yaml`, allowed endpoints, evidence requirements, output contract and no-invented-metrics safety rules.

## Commands run

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev mypy .
pnpm install
pnpm --filter @wilq/dashboard typecheck
pnpm --filter @wilq/dashboard test
pnpm --filter @wilq/dashboard build
scripts/quality.sh
scripts/security.sh
scripts/verify.sh
scripts/access_pack_check.sh
scripts/access_pack_manifest.sh
python3 .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000
python3 .agents/skills/wilq-merchant-feed-operator/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
python3 .agents/skills/wilq-social-publisher/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
python3 .agents/skills/wilq-localo-operator/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000
scripts/codex_skill_eval.sh --all --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 scripts/codex_skill_eval.sh --skill wilq-demand-gen-operator --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 scripts/codex_skill_eval.sh --skill wilq-ga4-analyst --api-base http://127.0.0.1:8000
CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1 scripts/codex_skill_eval.sh --skill wilq-merchant-feed-operator --api-base http://127.0.0.1:8000
gh repo view korneliuszburian/wilq-seo --json nameWithOwner,isPrivate,url,defaultBranchRef
```

## What passed

- `scripts/quality.sh`: passed.
- `scripts/security.sh`: passed.
- `scripts/verify.sh`: passed.
- Backend tests: 41 passed.
- Dashboard tests: 8 passed.
- Dashboard build: passed.
- API smoke inside `scripts/verify.sh`: passed.
- Paid Ahrefs live `vendor_read` smoke passed on 2026-06-17: report date `2026-06-16`, `domain_rating=24.0`, `ahrefs_rank=6433882`, `target_source=repo_env`; token and target values were not returned.
- Google first-party local credentials now use `authorized_user` ADC for `marketing@rekurencja.com` through `GOOGLE_APPLICATION_CREDENTIALS=/home/krn/.config/gcloud/application_default_credentials.json`; service-account JSON remains only a fallback path.
- Merchant API and Analytics Data API are enabled in OAuth project `rekurencja-seo`, and Merchant account `5519957373` has registered GCP project number `433565033354` via `developerRegistration:registerGcp`.
- Live Google first-party smokes passed on 2026-06-17: Merchant `aggregateProductStatuses` returned `total_products=10916`, `disapproved_products=16`, `expiring_products=96`, `merchant_action_product_count=1919`; GSC Search Analytics returned `clicks=777`, `impressions=83288`, `average_position=12.2934`; GA4 Analytics Data API returned `active_users=1791`, `sessions=2316`, `screen_page_views=5863`, `event_count=26437`, `engagement_rate=0.502591`.
- Runtime note: after changing `.env` credentials, restart the API process before HTTP smoke checks. `.env` is loaded into process env at import/startup, and old server processes keep old credential values.
- Skill validation passed for all 12 Goal 001 skills through the `$skill-creator` quick validator.
- `wilq-daily-command` API smoke passed against `http://127.0.0.1:8000` with configured connectors, evidence summaries, opportunity IDs and action IDs returned from WILQ context-pack.
- Representative stub smokes passed for Merchant, Social and Localo operator skills. `scripts/verify.sh` now validates skill structure and runs all skill smoke scripts against a temporary local API server.
- Non-interactive Codex skill eval baseline passed for 12/12 Goal 001 skills on 2026-06-17. All final eval JSONs had `api_used=true`, `language=pl-PL`, Polish diacritics and schema validation pass through `docs/evals/schemas/wilq-skill-eval-result.schema.json`.
- Proof artifacts were written under `.local-lab/evals/codex-skill/`. Main full sweep: `.local-lab/evals/codex-skill/full-20260617T164313Z` produced 9 skill results before a global Codex transport error. Clean retries with `CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1` completed `wilq-demand-gen-operator`, `wilq-ga4-analyst` and `wilq-merchant-feed-operator`.
- `pip-audit`: no known vulnerabilities found.
- `detect-secrets`: no findings in scoped source scan.

## What failed or remains limited

- Semgrep is not installed, so `scripts/security.sh` reports `Skipping semgrep: command unavailable.`
- FastAPI/Starlette emits a TestClient deprecation warning about `httpx`; tests still pass.
- Goal 001 is not complete because Localo/social vendor-read connector adapters are still blocked/not implemented, Google Ads OAuth still needs a fresh `adwords` refresh token, and opportunity generation mostly uses connector-status/refresh evidence rather than vendor performance metrics.
- Live Google Ads `vendor_read` reaches Google's OAuth token endpoint from repo-local `.env`, but the current refresh-token tuple returns `400 invalid_grant`; generate a fresh `adwords`-scoped refresh token before expecting campaign metrics.
- API has a local-only guard but no production authentication. Do not expose it beyond localhost or a trusted tunnel before adding auth.
- Baseline Codex skill evals are smoke-level proofs. Several skills correctly return `blocked=true` because current smoke scripts expose readiness/counts rather than concrete evidence IDs for final marketing recommendations. This is expected and safer than inventing metrics.
- `codex exec` with user-level config hit a global MCP/transport failure for `wilq-demand-gen-operator` (`wss://chatgpt.com/backend-api/codex/responses` returned `HTTP 404`). The same skill passed with `CODEX_SKILL_EVAL_IGNORE_USER_CONFIG=1`, so treat that failure as user config/transport noise, not a WILQ skill/API failure.

## Connector status

Credential runtime safe check:

```txt
repo_env_file_present=True
repo_env_key_count=42
access_pack_present=True
access_pack_env_file_present=True
access_pack_env_key_count=24
credential_file_count=3
manifest_file_count=7
secrets_redacted=true
```

Connector status is generated from local runtime source presence and does not print values.

## Quality gate status

Quality is green for the current foundation. Security is green with Semgrep skipped because the command is unavailable.

## Codex runtime status

- `AGENTS.md` exists.
- `.codex/hooks.json` exists.
- `.codex/mcp-notes.md` exists.
- `.codex/agents/` contains read-only agent notes.
- `.agents/skills/` contains 12 Goal 001 WILQ skills.

## Dashboard status

Dashboard is React/TypeScript with TanStack Query and Zod runtime parsing. It builds and tests successfully. It uses seed API state labeled as non-real, not final Ekologus metrics.

## API status

API is runnable through:

```bash
uv run uvicorn apps.api.wilq_api.main:app --reload
```

FastAPI OpenAPI docs are available when the API runs. Codex runs, workflow runs, connector refresh runs and audit events persist to local SQLite state. Knowledge cards are compiled deterministically from machine-readable playbooks. Evidence records are generated from local connector readiness state and connector refresh-run state. Opportunities are derived from readiness/refresh evidence plus playbook/expert-rule mappings; Google Ads can now persist aggregate read-only vendor metrics when credentials and API access allow it, Merchant Center can persist aggregate product status and issue counts when Google credentials and Merchant developer registration allow it, Ahrefs can persist aggregate Site Explorer domain rating/rank metadata when token and target config allow it, and WordPress vendor reads can persist aggregate post/page inventory when site credentials allow it. Google Sheets is disabled for current Ekologus scope and must not block connector readiness.

## Next recommended goal

Goal 002 — Google Ads Connector and Ads Doctor

Before Goal 002, expand only the skills whose underlying WILQ API endpoints are live enough to validate. Next strongest move is Google Ads OAuth refresh plus Ads Doctor live vendor metrics.
