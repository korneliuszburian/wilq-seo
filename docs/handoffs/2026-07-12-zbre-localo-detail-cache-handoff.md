# Handoff: `zbre` Localo action-detail cold cache — 2026-07-12

## Decyzja

`get_action()` używa teraz kopii istniejącego prewarmed registry cache, jeśli
żądany ActionObject znajduje się w aktywnym cache. Po wybraniu kopii service
zawsze wykonuje `_with_persisted_validation_state` oraz `_with_review_gate` z
bieżącymi audit/mutation records. Cache nie jest źródłem zgody na zapis i nie
omija evidence/freshness/safety loop; brak akcji w cache zachowuje poprzedni
fallback registry build.

## Dowód produktu

- Przed zmianą: pierwszy Localo detail po managed restart przekroczył 60 s;
  retry po rozgrzaniu HTTP 200 w 13.241167 s.
- Po zmianie: pierwszy cold `GET /api/actions/act_review_localo_visibility_facts`
  po pełnym restarcie HTTP 200 w `0.013299 s`.
- Odpowiedź zachowuje 10 metryk, evidence
  `ev_refresh_refresh_localo_30cd98463f06`, preview `zapis zmian zablokowany`
  i `apply_allowed=false`.
- Browser first viewport: decyzja `Widoczność lokalna do sprawdzenia`, blocker
  `Zapis zablokowany`, CTA i technical disclosure:
  `.local-lab/proof/continuation-2026-07-12/localo-cold-fixed-live.png`
  oraz `localo-cold-fixed-live.txt`.
- Nie wykonano review/confirm/impact/apply POST ani vendor write.

## Weryfikacja

- `tests/actions/test_action_list_cache.py` i `tests/actions/test_metric_utils.py`:
  5 passed; test sprawdza kopię cache i brak ponownego seedowania.
- Ruff, mypy, complexity i `git diff --check`: zielone; znany frozen-file
  budget `service.py` jest jedynym raportowanym wyjątkiem.
- Managed API/dashboard ready; health `ok`; lista `/api/actions` pozostaje
  21 akcji i 0 write-capable.

## Beads

- `wilq-seo-zbre` zamknięty po cold SLA proof.
- `wilq-seo-jnra` pozostaje `in_progress` dla kolejnych niezależnych seamów.
- `wilq-seo-c9h9.11` pozostaje zamknięty; zbre nie zmienia listowego contractu.

## Commit

Implementacja i handoff: `abc63034` (`perf: reuse cached action details`).
