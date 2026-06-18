# WILQ Ads Doctor Output Contract

## Purpose

Google Ads diagnostics, campaign quality, search terms, negative keyword and review-safe Ads action candidates.

Expected outcome: Evidence-backed Ads findings with action candidates that remain pending until validated by WILQ API.

Product inspiration: treat BDOS.ai as an Ads operating-system reference for the operator experience, and the official Google Ads MCP server as the reference MCP adapter pattern for read-only account discovery, GAQL/reporting exploration and documentation-assisted diagnostics. WILQ API remains canonical for evidence IDs, opportunity IDs, action validation and audit.

## Required API Context

Fetch `GET /api/ads/diagnostics` before producing Ads analysis. Then fetch `POST /api/codex/context-pack` with `{"skill":"wilq-ads-doctor"}` and use the embedded `ads_diagnostics` object as a consistency check, including `blocked_handoff`. Use `GET /api/connectors/{connector}/status` for each required connector when readiness matters.

Required connectors:

- `google_ads`

## Response Shape

Return these sections when the user asks this skill to operate:

Polish language contract: respond to the Ekologus marketer in Polish with Polish diacritics. Use Polish operator-facing labels such as `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` and `Następny krok`. Keep API identifiers, connector IDs, evidence IDs, opportunity IDs and ActionObject IDs unchanged.


1. `Status`: API reachability, connector readiness, `blocked_handoff.status` and known blockers.
2. `Dowody`: Ads diagnostics section IDs, evidence IDs, connector IDs, latest refresh status, freshness notes and metric summaries from WILQ API only.
3. `Diagnoza`: what `/api/ads/diagnostics` supports, with uncertainty if the evidence is aggregate, stale, incomplete or blocked by OAuth.
4. `Kandydaci działań`: opportunity IDs and ActionObject IDs when available; otherwise describe the missing API/evidence needed to create them.
5. `Walidacja`: result or required call to `POST /api/actions/{action_id}/validate` before apply/execution.
6. `Następny krok`: the smallest safe operator action.

## Refusal Conditions

Refuse or downgrade to a blocker report when:

- WILQ API is unreachable.
- Required connector status is `missing_credentials`, `disabled` or failed for the requested operation.
- `/api/ads/diagnostics` returns `live_data_available=false` and the user asks for spend, CPA, ROAS, search terms, negative keywords, campaign scaling or budget changes.
- The requested metric or action is not present in context-pack, evidence, connector refresh runs, expert rules or action objects.
- The user asks for write execution without a validated ActionObject and explicit approval.

## Evidence Rules

No evidence ID means no recommendation. No source connector means no recommendation. No validated payload means no apply. No audit event means no write.

## MCP Boundary

If a Google Ads MCP server is available later, use it only as a read-only adapter unless WILQ has a validated write ActionObject for the requested operation. MCP tool output must be converted into WILQ evidence or refresh-run state before it becomes a recommendation.
