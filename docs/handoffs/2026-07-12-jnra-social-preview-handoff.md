# Handoff — jnra social preview seam

Data: 2026-07-12 Europe/Warsaw

## Zrobione

`_social_draft_input_preview_cards` nie składa już kart w
`wilq/actions/service.py`. Renderer jest w istniejącym
`wilq/actions/social.py`; service przekazuje tylko callbacks do wspólnych
labels/rows/formatowania. Payload social, evidence IDs, Polish safety copy,
`prepare` mode i brak publikacji pozostają bez zmian.

## Weryfikacja

- Focused `tests/actions/test_action_object_contracts.py` social/preview — zielone.
- Ruff, mypy i `git diff --check` — zielone.
- Complexity: `service.py` 3 746 LOC; jedyny changed-code finding to znany
  frozen-file budget monolitu.
- Live po managed restart: API health `ok`; LinkedIn i Facebook mają po cztery
  `social_draft_input_review` cards, evidence IDs i tryb `prepare`; nie ma
  publish/write action.

## Stan grafu

`wilq-seo-jnra` pozostaje `in_progress`; WordPress payload preview seam jest
pushnięty jako `7b285df2`, a social preview seam jako `3895ca5a`.

## Następny krok

Po commicie uruchom ponowny complexity/runtime review i wybierz kolejny
niezakończony domain preview seam. Nie przywracaj direct social publish ani nie
omijaj ActionObject review/audit.
