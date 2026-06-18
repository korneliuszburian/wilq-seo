# WILQ Merchant Feed Operator Output Contract

## Purpose

Merchant Center product status, feed issue and product visibility triage.

Expected outcome: Feed issue summary and product action candidates with Merchant evidence IDs and validation blockers.

## Required API Context

Fetch `GET /api/merchant/diagnostics` before producing Merchant/feed analysis. Then fetch `POST /api/codex/context-pack` with `{"skill":"wilq-merchant-feed-operator"}` and use the embedded `merchant_diagnostics` object as a consistency check. Use `GET /api/connectors/{connector}/status` for each required connector when readiness matters.

Required connectors:

- `google_merchant_center`

## Response Shape

Return these sections when the user asks this skill to operate:

Polish language contract: respond to the Ekologus marketer in Polish with Polish diacritics. Use Polish operator-facing labels such as `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` and `Następny krok`. Keep API identifiers, connector IDs, evidence IDs, opportunity IDs and ActionObject IDs unchanged.


1. `Status`: API reachability, connector readiness and known blockers.
2. `Dowody`: Merchant diagnostics section IDs, evidence IDs, connector IDs, latest refresh state, issue dimensions, freshness notes and metric summaries from WILQ API only.
3. `Diagnoza`: what `/api/merchant/diagnostics` supports, with uncertainty if the evidence is aggregate, stale, incomplete or blocked by permissions.
4. `Kandydaci działań`: opportunity IDs and ActionObject IDs when available; otherwise describe the missing API/evidence needed to create them.
5. `Walidacja`: result or required call to `POST /api/actions/{action_id}/validate` before apply/execution.
6. `Następny krok`: the smallest safe operator action.

## Refusal Conditions

Refuse or downgrade to a blocker report when:

- WILQ API is unreachable.
- Required connector status is `missing_credentials`, `disabled` or failed for the requested operation.
- `/api/merchant/diagnostics` returns `live_data_available=false` and the user asks for feed issue actions, approval state, product visibility or product fixes.
- The requested metric or action is not present in context-pack, evidence, connector refresh runs, expert rules or action objects.
- The user asks for write execution without a validated ActionObject and explicit approval.

## Merchant Safety

Use `act_review_merchant_feed_issues` only as a prepare/review candidate unless WILQ API exposes a validated apply-mode Merchant action. Do not claim that an approval was restored, a product was fixed, revenue recovered, or the primary feed changed without an audit event.

## Evidence Rules

No evidence ID means no recommendation. No source connector means no recommendation. No validated payload means no apply. No audit event means no write.
