# Handoff: `jnra` payload readiness preview parser — 2026-07-12

## Decyzja

Parser preview payloadów został przeniesiony z `wilq/actions/service.py` do
istniejącego `wilq/actions/payload_readiness.py`:

- `payload_preview_items` zachowuje kolejność specjalnych kluczy,
  `payload_preview` i fallback list z `apply_allowed`;
- `payload_preview_contract` wybiera jawny kontrakt payloadu, potem kontrakt
  pierwszego preview itemu.

Service zachowuje kompatybilne fasady. `apply_allowed`, `api_mutation_ready`,
preview i review gate nie dostały nowej logiki biznesowej ani nowej ścieżki
zapisu.

## Dowód produktu

- Po managed restarcie Localo detail HTTP 200 w `0.013621 s`: 10 metryk,
  evidence `ev_refresh_refresh_localo_30cd98463f06`, `apply_allowed=false`.
- Ads strategy detail HTTP 200 w `0.016223 s`: 2 evidence IDs,
  `apply_allowed=false`, preview `zapis zmian zablokowany`.
- `/api/actions` HTTP 200 w `0.017043 s`: 21 akcji, 0 write-capable.
- Browser first viewport zachowuje `Ocena strategii Ads do zapisania`,
  `Zapis zablokowany` i disclosure techniczny:
  `.local-lab/proof/continuation-2026-07-12/payload-readiness-live.png`
  oraz `payload-readiness-live.txt`.
- Nie wykonano review/confirm/impact/apply POST ani vendor write.

## Weryfikacja

- `tests/actions/test_payload_readiness.py`, cache i metric tests: 7 passed.
- Ruff, mypy, complexity i `git diff --check`: zielone; jedyny complexity
  finding to znany frozen-file budget `service.py`.
- API health, managed dashboard i live WILQ evidence: zielone.

## Beads

- `wilq-seo-jnra` pozostaje `in_progress`; payload parser seam jest domknięty.
- `wilq-seo-c9h9.4`, `c9h9.11` i `zbre` pozostają zamknięte.
- Kolejny seam wymaga świeżego odczytu pozostałego orchestratora; nie powtarzaj
  gotowych payload/readiness boundary.

