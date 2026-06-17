---
name: wilq-gsc-content-doctor
description: Turn Google Search Console evidence into SEO/content diagnostics through WILQ API. Use when asked about pages, queries, CTR, impressions, ranking position, content refreshes, rewrites, merges, or SEO opportunities from GSC data. Must return evidence IDs and must not invent search metrics.
---

# WILQ GSC Content Doctor

## Operating Rule

Use this skill as a WILQ API operator workflow, not as a prompt-only report. Fetch live/product context from WILQ API before making marketing claims. If the API is unavailable or evidence is missing, report the blocker instead of filling gaps.

## Workflow

1. Read `references/output-contract.md` when producing the final response or action plan.
2. Run `python .agents/skills/wilq-gsc-content-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` when validating the skill/API path.
3. Call `POST /api/codex/context-pack` with `{"skill":"wilq-gsc-content-doctor"}` before summarizing metrics, opportunities or action candidates.
4. Use connector refresh endpoints only for explicit read-only refreshes, and only when the connector is configured.
5. Validate any existing ActionObject through `POST /api/actions/{action_id}/validate` before recommending apply/execution.
6. Return IDs: source connector IDs, evidence IDs, opportunity IDs and action IDs wherever the API provides them.

## Allowed API Endpoints

- `GET /api/health`
- `GET /api/system/status`
- `POST /api/codex/context-pack`
- `GET /api/connectors`
- `GET /api/connectors/{connector}/status`
- `GET /api/connectors/{connector}/refresh-runs`
- `GET /api/connectors/refresh-runs`
- `GET /api/evidence`
- `GET /api/opportunities`
- `GET /api/actions`
- `GET /api/actions/{action_id}`
- `POST /api/actions/{action_id}/validate`
- `POST /api/connectors/{connector}/refresh with mode=vendor_read only when the connector is configured and the task explicitly needs a fresh read.`

## Required Evidence

Required connector surfaces for this skill:

- `google_search_console`
- `wordpress_ekologus`
- `wordpress_sklep`

Every recommendation must include source connector IDs and evidence IDs from WILQ API. If evidence is aggregated, stale, missing or blocked by credentials, say that directly.

## Output Contract

Follow `references/output-contract.md`. Keep output short enough for an operator to act on: status, evidence, diagnosis, validated action candidates, blockers and next safe steps.

Polish language contract: produce all operator-facing responses in Polish with Polish diacritics. Keep API IDs, connector IDs, evidence IDs, opportunity IDs, ActionObject IDs, endpoint paths and enum values unchanged.

## Safety

- Never invent metrics, rankings, product counts, campaign state, content inventory, social permissions or Localo findings.
- Never print secrets, credential paths, token values or raw vendor response bodies.
- Never call write/apply endpoints unless WILQ API exposes the action, validation passes and the user explicitly asks for execution.
- Never bypass ActionObject validation, evidence IDs or audit requirements.

## Goal 001 Status

Goal 001 stub: use current aggregate GSC evidence only unless richer dimensions are added to WILQ API.
