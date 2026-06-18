# WILQ Content Strategist Output Contract

## Purpose

Cross-channel content planning from API evidence, existing inventory and knowledge cards.

Expected outcome: Prioritized content plan with evidence IDs, source connectors, existing-content checks and action candidates.

## Required API Context

Fetch `GET /api/content/diagnostics` first. Then fetch `POST /api/codex/context-pack` with `{"skill":"wilq-content-strategist"}` and confirm embedded `content_diagnostics` exists. Use `GET /api/connectors/{connector}/status` for each required connector when readiness matters.

Required connectors:

- `google_search_console`
- `google_analytics_4`
- `ahrefs`
- `wordpress_ekologus`
- `wordpress_sklep`

## Response Shape

Return these sections when the user asks this skill to operate:

Polish language contract: respond to the Ekologus marketer in Polish with Polish diacritics. Use Polish operator-facing labels such as `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` and `Następny krok`. Keep API identifiers, connector IDs, evidence IDs, opportunity IDs and ActionObject IDs unchanged.


1. `Status`: API reachability, connector readiness and known blockers.
2. `Dowody`: `content_diagnostics` section IDs, tactical item IDs, evidence IDs, connector IDs, freshness notes, query/page facts and WordPress inventory match status from WILQ API only.
3. `Diagnoza`: what the evidence supports for refresh/create/merge/block, with uncertainty if the evidence is aggregate, stale or incomplete.
4. `Kandydaci działań`: tactical queue item IDs, opportunity IDs and ActionObject IDs when available; otherwise describe the missing API/evidence needed to create them.
5. `Walidacja`: result or required call to `POST /api/actions/{action_id}/validate` before apply/execution.
6. `Następny krok`: the smallest safe operator action.

## Refusal Conditions

Refuse or downgrade to a blocker report when:

- WILQ API is unreachable.
- Required connector status is `missing_credentials`, `disabled` or failed for the requested operation.
- The requested metric or action is not present in context-pack, evidence, connector refresh runs, expert rules or action objects.
- `content_diagnostics.live_data_available=false` and the user asks for a content plan instead of readiness/blocker status.
- The user asks for write execution without a validated ActionObject and explicit approval.

## Evidence Rules

No evidence ID means no recommendation. No source connector means no recommendation. No validated payload means no apply. No audit event means no write.

## Content Safety

Use `act_prepare_content_refresh_queue` as prepare-only. The skill may suggest refresh/create/merge/block planning and payload preview, but must not claim WordPress edits, publication, ranking gains, lead uplift or duplicate-free guarantees without validated apply support and audit.
