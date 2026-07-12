# Handoff: `jnra` impact-check audit event owner — 2026-07-12

## Decyzja

`impact_check_action` deleguje konstrukcję `AuditEvent` do
`wilq/actions/audit_store.py` (`build_impact_check_audit_event`). Service
pozostaje właścicielem statusu `checked`/`blocked`, porównywanych okien,
metryk, source connectors, blockerów oraz unii evidence IDs; store składa
event metadata i zachowuje explicit measurement lineage.

## Dowody

- `tests/actions/test_audit_store_contracts.py`: test event ID/type/label, actor,
  summary i wieloelementowe evidence IDs.
- `tests/actions/test_action_review_contracts.py`,
  `tests/actions/test_action_preview_contracts.py`: 40 focused testów przechodzi.
- Ruff, mypy i `git diff --check` przechodzą.
- Managed API smoke: health `ok`, readiness pozostaje
  `ready_to_request_apply=false`, `vendor_write_possible=false`; brak nowych
  endpointów, payloadów, credentiali lub vendor writes.
- Przywrócono wymagany compatibility facade `_action_audit_event_label` dla
  `context_compaction`; nie usunięto publicznej granicy używanej przez API.

## Beads

- `wilq-seo-jnra` pozostaje P0 `in_progress`; komentarz z dowodami dodany.
- Nie utworzono nowego Beada — seam należy do aktywnego Action Service splitu.

## Następny slice

Reaudyt pozostałego `mutation_readiness_action` i lokalnych response-builderów;
nie przenosić kolejnych prostych wrapperów bez dowodu, że owner boundary
poprawia bezpieczeństwo albo utrzymanie.

## Pozostałe blokery

- Content queue: `blocked`, 1 actionable przy minimum 3; brak sztucznego tematu.
- Connector summary: 12 total, 9 configured, 2 missing credentials; część źródeł
  stale/unknown, więc metryki nie są dowodem bieżących wyników.
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer.
