# WILQ Daily Command Output Contract

## Purpose

Daily command-center triage across connectors, evidence, opportunities, actions, expert rules and knowledge cards.

Expected outcome: A concise operating brief with source connector status, evidence IDs, opportunity IDs, action IDs, blockers and next safe steps.

## Required API Context

Fetch `GET /api/dashboard/command-center` before producing marketing analysis.
This is the canonical first-screen operator view model used by dashboard and
Codex skills.

Then fetch `GET /api/marketing/brief` for supporting daily sections and metric
summaries.

Then fetch `POST /api/codex/context-pack` with
`{"skill":"wilq-daily-command"}` for wider context: connector status,
refresh runs, evidence summaries, opportunities, ActionObjects, expert rules
and knowledge cards. The embedded `command_center` in the context pack must
match `GET /api/dashboard/command-center` for `operator_brief`,
`primary_next_step`, blocker count, tactical item count and action IDs. The
embedded `marketing_brief` in the context pack must match
`GET /api/marketing/brief` for language, section IDs, blocker count,
recommendation count, evidence IDs and action IDs.

Use `GET /api/connectors/{connector}/status` for each required connector when
readiness matters.

Required connectors:

- `google_ads`
- `google_search_console`
- `google_analytics_4`
- `google_merchant_center`
- `ahrefs`
- `localo`
- `wordpress_ekologus`
- `wordpress_sklep`

## Response Shape

Return these sections when the user asks this skill to operate:

Polish language contract: respond to the Ekologus marketer in Polish with Polish diacritics. Use Polish operator-facing labels such as `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` and `Następny krok`. Keep API identifiers, connector IDs, evidence IDs, opportunity IDs and ActionObject IDs unchanged.


1. `Status`: API reachability, connector readiness, `CommandCenter.operator_brief` status and known blockers.
2. `Dowody`: evidence IDs, connector IDs, freshness notes and metric summaries from `CommandCenter`/`MarketingBrief`/WILQ API only.
3. `Diagnoza`: what the operator brief supports, with uncertainty if the evidence is aggregate, stale or incomplete.
4. `Kandydaci działań`: `operator_brief.action_ids`, opportunity IDs and ActionObject IDs when available; otherwise describe the missing API/evidence needed to create them.
5. `Walidacja`: result or required call to `POST /api/actions/{action_id}/validate` before apply/execution.
6. `Następny krok`: the smallest safe operator action.

## Refusal Conditions

Refuse or downgrade to a blocker report when:

- WILQ API is unreachable.
- Required connector status is `missing_credentials`, `disabled` or failed for the requested operation.
- The requested metric or action is not present in context-pack, evidence, connector refresh runs, expert rules or action objects.
- The user asks for write execution without a validated ActionObject and explicit approval.

## Evidence Rules

No evidence ID means no recommendation. No source connector means no recommendation. No validated payload means no apply. No audit event means no write.
