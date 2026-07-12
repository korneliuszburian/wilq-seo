# Handoff: `jnra` GA4 metric snapshot helper — 2026-07-12

## Decyzja

Przeniosłem `_metric_snapshot_preview_rows` i formatter z
`wilq/actions/service.py` do istniejącego `wilq/actions/ga4/tracking_preview.py`.
Helper filtruje nazwane metryki i zachowuje formatowanie procentów/liczb;
service pozostaje fasadą. Nie zmieniono endpointu, payloadu ani safety loop.

## Dowód produktu

- Live API: `act_review_ga4_tracking_quality` HTTP 200, `mode=prepare`,
  connector `google_analytics_4`, 1 evidence ID i karta
  `ga4_tracking_quality_review`.
- Karta pokazuje landing/source/campaign oraz metryki zaangażowania, a blokuje
  twierdzenia o konwersji, ROAS i przychodzie; zapis pozostaje zablokowany.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/ga4-metric-helper-live.png`.

## Weryfikacja

- GA4 action preview oraz source diagnostics tests: passed.
- Ruff i mypy dla `tracking_preview.py`, `service.py` i testów: passed.
- Complexity changed audit: jeden znany frozen `service.py` budget finding;
  GA4 module mieści się w budżecie.
- `git diff --check`: passed.
- Managed stack po restarcie: API/dashboard ready; health `ok`.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; helper seam jest bounded.
- `wilq-seo-r564` nadal blokuje kolejkę contentu: 1 actionable przy minimum 3.
- Następny turn wybierze kolejny potwierdzony seam po świeżym runtime/complexity
  checku; nie wraca do ukończonych Localo/GA4 helperów.

## Commit

Commit implementacji i docs zostanie dopisany po pushu.
