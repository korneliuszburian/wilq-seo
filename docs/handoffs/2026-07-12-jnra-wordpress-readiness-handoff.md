# Handoff — jnra WordPress readiness seam

Data: 2026-07-12 Europe/Warsaw

Baseline before the preview-card seam: `0e5917a2`; preview-card seam commit:
`0ae4eba0`; payload-preview assembly seam is committed and pushed as
`7b285df2`.

## Zrobione

`wilq/actions/wordpress_mutation_requirements.py` przejął dwa WordPress-specific
builders z `wilq/actions/service.py`:

- gotowość handoffu i paczki szkicu;
- gotowość targetu po Claim Ledger/review/dry-run.
- target projection readiness (candidate ID, canonical URL i operator label).

`service.py` pozostaje cieńszym orchestrator/facade i przekazuje callback do
istniejącego `_payload_preview_items`; target projection jest w
`wilq/actions/mutation_target.py`. Nie dodano endpointu, adaptera ani
możliwości write. Blocker codes, evidence, polskie labels i kolejność
`validate → preview → review → confirm → audit → adapter` pozostały bez zmian.
WordPress payload/handoff preview cards są teraz w
`wilq/actions/wordpress_preview.py`; dispatcher przekazuje jawne callbacks do
row/string/label helpers, bez importu service do modułu domenowego.
Składanie `wordpress_draft_payload_preview_v1` jest teraz osobno w
`wilq/actions/wordpress_payload_preview.py`; reguły treści i labels pozostają
w `content_refresh` przez jawny support mapping. To jest assembly seam, nie nowy
kontrakt i nie nowa możliwość zapisu.

## Weryfikacja

- Focused mutation-readiness, review, confirmation, preview, validation i Goal
  005 tests — zielone.
- Ruff, mypy i `git diff --check` — zielone.
- Focused content/action contracts po payload assembly seam — zielone; nowy
  moduł nie ma funkcji ponad lokalny budżet (pozostały tylko wcześniejsze
  findings w `content_refresh.py`).
- Complexity po pierwszych seamach: `service.py` 3 897 LOC; target projection
  obniżył go do 3 868 LOC, a preview-card seam do 3 782 LOC. Znany frozen-file budget jest
  udokumentowany, bez nowego zachowania w monolicie.
- Live po managed restart: API `ok`; 21 akcji; `vendor_write_possible=0`;
  `would_attempt_vendor_write=0`; WordPress apply contract ma
  `publication_allowed=false` i `destructive_allowed=false`.
- Browser action proof po restarcie: `.local-lab/proof/continuation-2026-07-12/`
  (`action-preview-cards.png` i `.txt`) pokazuje cztery typed WordPress cards,
  canonical/public URL rows, blocked claims i „zapis zmian zablokowany”.
- Aktualne runtime metrics po read-only refreshu: 99 906 metric facts,
  4 577 refresh runs.
- Live content queue: `fresh`, `requires_refresh=false`, 2 kandydatów, 1
  actionable, minimum 3; WordPress handoff pozostaje preview-only.

## Stan grafu

`wilq-seo-jnra` pozostaje `in_progress`; ten seam nie zamyka całego zadania.
`c9h9.4`, `c9h9.2` i `r564.3` są zamknięte. Parent `r564` pozostaje otwarty
przez candidate density: 2 kandydatów, 1 actionable, minimum 3.

## Następny krok

Po wypchnięciu tego payload assembly seam uruchom świeży complexity/runtime
review `service.py` i wybierz kolejny niedublujący się domain seam. Przed zmianą pobierz live WILQ API; po zmianie
uruchom focused tests, Ruff, mypy, complexity, API smoke, `git diff --check`,
commit i push na `origin/main`. Nie przywracaj direct WordPress write.
