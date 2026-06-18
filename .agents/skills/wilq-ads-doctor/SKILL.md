---
name: wilq-ads-doctor
description: Inspect Google Ads diagnostics through WILQ API evidence and action contracts. Use when asked about wasted spend, search terms, campaign quality, negative keywords, quality score, ad strength, recommendations, or Ads action validation for Ekologus. Must not invent Ads metrics or bypass ActionObject validation.
---

# WILQ Ads Doctor

## Operating Rule

Use this skill as a WILQ API operator workflow, not as a prompt-only report. Fetch live/product context from WILQ API before making marketing claims. If the API is unavailable or evidence is missing, report the blocker instead of filling gaps.

## Workflow

1. Read `references/output-contract.md` when producing the final response or action plan.
2. Run `python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` when validating the skill/API path.
3. Call `GET /api/ads/diagnostics` before diagnosing Google Ads readiness, wasted spend, search terms, campaign quality, recommendations or negative keywords.
4. Call `POST /api/codex/context-pack` with `{"skill":"wilq-ads-doctor"}` and confirm `ads_diagnostics` matches the Ads diagnostics endpoint.
5. Use connector refresh endpoints only for explicit read-only refreshes, and only when the connector is configured.
6. Validate any existing ActionObject through `POST /api/actions/{action_id}/validate` before recommending apply/execution.
7. Return IDs: source connector IDs, evidence IDs, opportunity IDs and action IDs wherever the API provides them.

## Allowed API Endpoints

- `GET /api/health`
- `GET /api/system/status`
- `POST /api/codex/context-pack`
- `GET /api/ads/diagnostics`
- `GET /api/marketing/brief`
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

- `google_ads`

Every recommendation must include source connector IDs and evidence IDs from WILQ API. If `/api/ads/diagnostics` reports `live_data_available=false`, return an OAuth/API blocker and blocked claims instead of diagnosing spend, CPA, ROAS, search terms or negative keywords.

## Output Contract

Follow `references/output-contract.md`. Keep output short enough for an operator to act on: status, evidence, diagnosis, validated action candidates, blockers and next safe steps.

Polish language contract: produce all operator-facing responses in Polish with Polish diacritics. Keep API IDs, connector IDs, evidence IDs, opportunity IDs, ActionObject IDs, endpoint paths and enum values unchanged.

## Safety

- Never invent metrics, rankings, product counts, campaign state, content inventory, social permissions or Localo findings.
- Never print secrets, credential paths, token values or raw vendor response bodies.
- Never call write/apply endpoints unless WILQ API exposes the action, validation passes and the user explicitly asks for execution.
- Never bypass ActionObject validation, evidence IDs or audit requirements.

## Goal 001 Status

Goal 001 status: `/api/ads/diagnostics` is the canonical Ads Doctor view model. Google Ads OAuth currently returns the redacted blocker `oauth_error=deleted_client`, so live campaign/search-term/recommendation metrics are still unavailable until a fresh working `adwords` token is installed.
