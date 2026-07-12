# Handoff: `jnra` content brief preview renderer — 2026-07-12

## Decyzja

Wydzieliłem `_content_brief_preview_card` oraz contentowe etykiety URL/metryk
z `wilq/actions/service.py` do nowego, wąskiego
`wilq/actions/content_preview.py`. Service zachowuje dispatcher i przekazuje
callbacks do typed rows, list oraz safety labels. Nie zmieniono endpointu,
payloadu ani ścieżki WordPress write.

## Dowód produktu

- Live API: `GET /api/actions/act_prepare_content_refresh_queue` zwrócił HTTP
  200, `mode=prepare`, connector `wordpress_ekologus`, 3 evidence IDs i trzy
  karty `content_brief_review`.
- Karty pokazują temat, tryb, publiczny URL, decyzje i blokadę zapisu; claimy
  wzrostu i publikacja pozostają review-gated.
- Browser proof desktop first viewport:
  `.local-lab/proof/continuation-2026-07-12/content-brief-preview-live.png`.

## Weryfikacja

- Content knowledge, content workflow API i action preview tests: passed.
- Ruff i mypy dla `content_preview.py`, `content_refresh.py` i `service.py`:
  passed.
- Complexity changed audit: jeden znany finding frozen `service.py`; nowy
  moduł mieści się w lokalnym budżecie.
- `git diff --check`: passed.
- Managed stack po restarcie: API/dashboard ready; health `ok`.

## Beads i następny krok

- `wilq-seo-jnra` pozostaje `in_progress`; seam jest bounded i bez duplikatu.
- `wilq-seo-r564` nadal blokuje się na kolejce contentu: 1 actionable z
  minimum 3, mimo świeżych danych.
- Następny turn wybiera kolejny istniejący action/preview seam po świeżym
  complexity i runtime checku.

## Commit

Commit implementacji i docs: `e3bba902` (`refactor: extract content brief
preview`), wypchnięty na `origin/main`.
