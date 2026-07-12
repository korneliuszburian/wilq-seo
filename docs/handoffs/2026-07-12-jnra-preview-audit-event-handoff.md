# Handoff: `jnra` preview audit event owner — 2026-07-12

## Decyzja

`preview_action` nie składa już lokalnie `AuditEvent` dla dry-run. Nowy
`audit_store.build_preview_audit_event` jest właścicielem event ID, typu,
operator label, aktora, summary i evidence IDs; service pozostaje właścicielem
liczenia preview items, blockerów i statusu.

## Dowody

- `tests/actions/test_audit_store_contracts.py`: nowy test potwierdza
  `action_preview_generated`, label, actor, summary i evidence lineage.
- `tests/actions/test_action_preview_contracts.py`: 25 focused audit/preview
  testów przechodzi; `mutation_allowed=false` i audit projection pozostają
  niezmienione.
- Ruff, mypy i `git diff --check` przechodzą; brak nowych endpointów, payloadów,
  vendor writes, credentiali lub zmian UI.
- Po poprzednim managed restart API było `ok`, WordPress readiness pozostaje
  `ready_to_request_apply=false` i `vendor_write_possible=false`; ten slice nie
  zmienia runtime route.

## Beads

- `wilq-seo-jnra` pozostaje P0 `in_progress`; komentarz z dowodami dodany.
- Brak nowego Beada: to kolejny potwierdzony audit owner seam w aktywnym `jnra`.

## Następny slice

Reaudyt confirm/impact audit event assembly; wybrać jeden seam tylko jeśli
zachowuje dokładny event type, blocker copy i evidence, a test dowodzi dry-run
oraz safety.

## Pozostałe blokery

- Queue nadal `blocked`: 1 actionable przy wymaganych 3.
- Goal 005 nadal wymaga realnego Wilku UAT albo jawnego owner defer.
