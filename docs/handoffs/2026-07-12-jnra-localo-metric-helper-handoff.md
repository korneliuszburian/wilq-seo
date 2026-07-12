# Handoff: `jnra` Localo metric snapshot helper — 2026-07-12

## Decyzja

Przeniosłem `_metric_snapshot_preview_rows_for_keys` z `wilq/actions/service.py`
do istniejącego `wilq/actions/localo/visibility_preview.py`. Helper filtruje
tylko nazwane metryki Localo i zachowuje formatowanie procentów/liczb; service
pozostaje fasadą. Nie zmieniono endpointu, payloadu ani safety loop.

## Dowód produktu

- Live API: `act_review_localo_visibility_facts` HTTP 200, `mode=prepare`,
  connector `localo`, 1 evidence ID i karta `localo_visibility_review`.
- Karta pokazuje agregaty widoczności/reviews, brakujące kontrakty i blocked
  twierdzenia o GBP/konkurencji; zapis pozostaje zablokowany.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/localo-metric-helper-live.png`.

## Weryfikacja

- Localo action preview oraz source diagnostics tests: passed.
- Ruff i mypy dla `visibility_preview.py`, `service.py` i testów: passed.
- Complexity changed audit: jeden znany frozen `service.py` budget finding;
  Localo module mieści się w budżecie.
- `git diff --check`: passed.
- Managed stack po restarcie: API/dashboard ready; health `ok`.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; helper seam jest bounded.
- `wilq-seo-r564` nadal blokuje kolejkę contentu: 1 actionable przy minimum 3.
- Następny turn wybierze kolejny potwierdzony seam po świeżym runtime/complexity
  checku; nie wraca do ukończonych Localo/content rendererów.

## Commit

Commit implementacji i docs zostanie dopisany po pushu.
