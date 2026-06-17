# WILQ Social Publisher Output Contract

## Purpose

LinkedIn/Facebook publishing readiness and evidence-backed social action objects.

Expected outcome: Social post candidates with source evidence, review state and connector blockers.

## Required API Context

Fetch `POST /api/codex/context-pack` with `{"skill":"wilq-social-publisher"}` before producing marketing analysis. Use `GET /api/connectors/{connector}/status` for each required connector when readiness matters.

Required connectors:

- `linkedin`
- `facebook`

## Response Shape

Return these sections when the user asks this skill to operate:

Polish language contract: respond to the Ekologus marketer in Polish with Polish diacritics. Use Polish operator-facing labels such as `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` and `Następny krok`. Keep API identifiers, connector IDs, evidence IDs, opportunity IDs and ActionObject IDs unchanged.


1. `Status`: API reachability, connector readiness and known blockers.
2. `Dowody`: evidence IDs, connector IDs, freshness notes and metric summaries from WILQ API only.
3. `Diagnoza`: what the evidence supports, with uncertainty if the evidence is aggregate, stale or incomplete.
4. `Kandydaci działań`: opportunity IDs and ActionObject IDs when available; otherwise describe the missing API/evidence needed to create them.
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
