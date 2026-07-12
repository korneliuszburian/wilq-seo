# Handoff: `jnra` metric utility seam — 2026-07-12

## Decyzja

Trzy read-only helpery metryk zostały przeniesione z `wilq/actions/service.py`
do istniejącego `wilq/actions/metric_utils.py`:

- `latest_metric_facts_by_identity` deduplikuje po connectorze, nazwie i
  posortowanych wymiarach, zostawiając najnowsze `collected_at`;
- `metric_fact_sort_time` zachowuje pusty sort key dla braku daty;
- `facts_by_connector` zachowuje kolejność wejściową w grupach.

Service pozostaje orkiestratorem przez kompatybilne fasady. Nie zmieniono
endpointów, evidence/freshness, ActionObject safety loop ani żadnej ścieżki
vendor write.

## Dowód produktu

- `/api/actions` po managed restarcie: HTTP 200, 21 akcji, 0 write-capable.
- `act_record_ads_strategy_review`: HTTP 200, `mode=prepare`, 2 evidence IDs,
  `review_gate=kontrola WILQ poprawna`, `apply_allowed=false`, preview
  `zapis zmian zablokowany`.
- Browser first viewport zachowuje decyzję, blocker i CTA; technical details są
  za disclosure. Proof: `.local-lab/proof/continuation-2026-07-12/metric-utils-live.png`
  oraz `metric-utils-live.txt`.
- Nie wykonano review/confirm/impact/apply POST ani vendor write.

## Weryfikacja

- `tests/actions/test_metric_utils.py` i istniejące testy action metrics: 6
  passed.
- Ruff i mypy dla `metric_utils.py`, `service.py` i testów: zielone.
- Complexity: jedyne bieżące zgłoszenie to znany frozen-file budget
  `wilq/actions/service.py`; brak nowej funkcji ponad budżet.
- `git diff --check`, API health, managed dashboard i WILQ queue: zielone
  technicznie; content queue pozostaje uczciwie `blocked` przy 1 actionable z 3.

## Beads i zależności

- `wilq-seo-jnra` pozostaje `in_progress`; ten seam jest domknięty, a następny
  wybór wymaga świeżego przeglądu pozostałego orchestratora.
- `wilq-seo-c9h9.4` pozostaje zamknięty — nie wracamy do gotowej ścieżki
  WordPress apply.
- `r564` pozostaje zewnętrznie zablokowany przez `not_enough_actionable_candidates`;
  nie twórz sztucznego trzeciego tematu.

## Commit

Implementacja i handoff: `7f321c26` (`refactor: centralize metric action helpers`).
