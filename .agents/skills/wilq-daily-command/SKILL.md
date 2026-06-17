---
name: wilq-daily-command
description: Run the daily WILQ operating brief from WILQ API context. Use when starting a marketing work session, checking today's connector readiness, listing top opportunities, summarizing available actions, or preparing the next evidence-backed operator steps for Ekologus. Must call WILQ API and must not invent metrics.
---

# WILQ Daily Command

## Operating Rule

Use this skill as a WILQ API operator workflow, not as a prompt-only report. Fetch live/product context from WILQ API before making marketing claims. If the API is unavailable or evidence is missing, report the blocker instead of filling gaps.

## Workflow

1. Read `references/output-contract.md` when producing the final response or action plan.
2. Run `uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000` when validating the skill/API path.
3. Call `GET /api/marketing/brief` first. This is the canonical daily operator view model for Polish marketer output.
4. Call `POST /api/codex/context-pack` with `{"skill":"wilq-daily-command"}` to get wider evidence, opportunities, actions, expert rules and knowledge cards.
5. The `marketing_brief` embedded in the context pack must agree with `GET /api/marketing/brief` on `language`, section IDs, blocker count, recommendation count, evidence IDs and action IDs.
6. Use connector refresh endpoints only for explicit read-only refreshes, and only when the connector is configured.
7. Validate any existing ActionObject through `POST /api/actions/{action_id}/validate` before recommending apply/execution.
8. Return IDs: source connector IDs, evidence IDs, opportunity IDs and action IDs wherever the API provides them.

## Allowed API Endpoints

- `GET /api/health`
- `GET /api/system/status`
- `GET /api/marketing/brief`
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
- `POST /api/connectors/{connector}/refresh with mode=vendor_read for explicitly requested read-only refreshes.`
- `GET /api/knowledge/cards`
- `GET /api/expert/rules`
- `GET /api/expert/capabilities`

## Required Evidence

Required connector surfaces for this skill:

- `google_ads`
- `google_search_console`
- `google_analytics_4`
- `google_merchant_center`
- `ahrefs`
- `localo`
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

This is fully wired in Goal 001 through `GET /api/marketing/brief` and `POST /api/codex/context-pack`. Use the smoke script before claiming the skill path works.
