# Goal 001 Handoff — WILQ Marketing Operating System Core

Status: in progress, foundation verified. Goal 001 is not complete yet.

## What was built

- Private GitHub repo target was created: `korneliuszburian/wilq-seo`.
- `docs/goals/001-goal.md` was created from the active goal.
- Root `AGENTS.md` now defines WILQ product philosophy, API-first rules, evidence rules, MCP rules, skill creation timing, security rules, quality gates and forbidden behavior.
- FastAPI WILQ API spine exists with health, system status, connectors, connector refresh runs, dashboard command center, opportunities, actions, expert rules, knowledge, Codex context/runs and workflows endpoints.
- Pydantic schemas exist for connectors, connector refresh runs, evidence, metrics, opportunities, actions, audit events, Codex runs and knowledge cards.
- Connector registry includes Google Ads, GSC, GA4, Merchant Center, Google Sheets, Ahrefs, Localo, WordPress, LinkedIn, Facebook and OpenAI/Codex.
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
- Google Ads, Google Search Console, GA4, Google Merchant Center, Google Sheets, Ahrefs and both WordPress sites have first read-only `vendor_read` adapters that persist aggregate metrics/inventory only.
- Opportunities are now derived from connector readiness evidence plus playbook/expert-rule mappings, not fixed demo opportunity rows.
- Workflow, model runtime, credential runtime, MCP, quality, security and source-registry docs exist.
- Codex hooks exist for SessionStart and Stop; they fail open and restrict API URL targets to local/allowed hosts.
- `.agents/skills/` intentionally contains only `.gitkeep`.

## Skill status

Skills were intentionally not created yet. The goal files now include an execution clarification:

```txt
Skill policy first, skill folders later.
Create WILQ skills only after the API endpoints, context-pack contract,
connector status contract and action validation path they call are implemented
and testable.
```

The first skill is still deferred. When the API/context-pack/action validation
contracts are stable enough to smoke test from a skill, create
`wilq-daily-command` with `$skill-creator`.

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
- `pip-audit`: no known vulnerabilities found.
- `detect-secrets`: no findings in scoped source scan.

## What failed or remains limited

- Semgrep is not installed, so `scripts/security.sh` reports `Skipping semgrep: command unavailable.`
- FastAPI/Starlette emits a TestClient deprecation warning about `httpx`; tests still pass.
- Goal 001 is not complete because skills are deferred by policy, several vendor-read connector adapters are still blocked/not implemented, and opportunity generation mostly uses connector-status/refresh evidence rather than vendor performance metrics.
- Live Google Ads `vendor_read` reaches Google's OAuth token endpoint from repo-local `.env`, but the current refresh-token tuple returns `400 invalid_grant`; generate a fresh `adwords`-scoped refresh token before expecting campaign metrics.
- API has a local-only guard but no production authentication. Do not expose it beyond localhost or a trusted tunnel before adding auth.

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
- `.agents/skills/` is intentionally empty except `.gitkeep`.

## Dashboard status

Dashboard is React/TypeScript with TanStack Query and Zod runtime parsing. It builds and tests successfully. It uses seed API state labeled as non-real, not final Ekologus metrics.

## API status

API is runnable through:

```bash
uv run uvicorn apps.api.wilq_api.main:app --reload
```

FastAPI OpenAPI docs are available when the API runs. Codex runs, workflow runs, connector refresh runs and audit events persist to local SQLite state. Knowledge cards are compiled deterministically from machine-readable playbooks. Evidence records are generated from local connector readiness state and connector refresh-run state. Opportunities are derived from readiness/refresh evidence plus playbook/expert-rule mappings; Google Ads can now persist aggregate read-only vendor metrics when credentials and API access allow it, Merchant Center can persist aggregate product status and issue counts when service-account access allows it, Google Sheets can persist aggregate review-surface metadata when service-account access allows it, Ahrefs can persist aggregate Site Explorer domain rating/rank metadata when token and target config allow it, and WordPress vendor reads can persist aggregate post/page inventory when site credentials allow it.

## Next recommended goal

Goal 002 — Google Ads Connector and Ads Doctor

Before Goal 002, keep skills as policy unless the current API context-pack and validation endpoints are stable enough for a real skill smoke test. If they are, create `wilq-daily-command` with `$skill-creator`.
