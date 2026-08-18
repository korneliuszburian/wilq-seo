# Independent review: Content Pipeline ledger — Stop authority Slice 1

Rola dokumentu: retained read-only code-review decision dla publikacji pięciu
slice'ów ledgeru. Nie jest approvalem implementacji ani dowodem produkcyjnym.

- Fixed point: `c4490cdf7c7fae470ec04ebd079892f8be382d8f`
- Data review: 2026-08-18
- Reviewer: `opencode/deepseek-v4-flash-free`, variant `max`
- Tryb: bezpośredni, autoryzowany przez ownera, `--pure --agent review`
- Scope: fizycznie odizolowany snapshot wyłącznie dozwolonych plików
- Consumer: publikacja tasków S1-S5 pod `wilq-seo-1oa.36`
- Decyzja po lokalnej disposition: `ACCEPT_FOR_SLICE_WORK`

## Werdykt i disposition

Reviewer zwrócił `NEEDS_REVISION` z trzema findingami. Lokalna weryfikacja
potwierdziła każdy z nich, ale nie wykazała sprzeczności architektury ani
brakującego prekursora. Wszystkie trzy są dokładniejszym wskazaniem testów już
wymaganych przez kontrakt S1 i zostały przyjęte jako `accept_and_fix`:

1. `tests/api_contracts/test_security_connector_contracts.py:304` — zastąpić
   test legalizujący publiczny zapis przez collision + malformed JSON, oba z
   top-level typed `410`, oraz dowodem braku mutacji runu i telemetryki.
2. `tests/test_codex_hooks.py:12` — dodać capture requestu dowodzący dokładnego
   bodyless POST do `/api/codex/telemetry/stop-events`; zachować non-blocking
   unavailable-API proof.
3. `tests/content/test_content_section_focus.py:194` i `:231` — skoordynować
   oczekiwania wersji i dodać exact migrację v4→v5 zachowującą istniejący
   `codex_runs` payload.

Pełny lokalny caller scan znalazł tylko produkcyjny POST z hooka Stop, deklarację
routera i test publicznego POST-u. Dashboard używa starej trasy wyłącznie przez
GET. Wewnętrzni writerzy używają bezpośrednio `save_codex_run` i nie wymagają
publicznego POST-u.

## Granica decyzji

Slice 1 pozostaje najmniejszą bezpieczną izolacją authority Stop. Publikowany
task S1 musi zawierać powyższe trzy korekty jako jawne acceptance criteria.
S2-S5 zachowują zatwierdzoną kolejność i własność zakresu; review nie przesuwa
retention, exact lookup, bounded readers ani reconciliation do S1.

Raport nie dowodzi poprawności przyszłej implementacji, auth sufficiency,
real-store migration, produkcyjnej gotowości, realnego UAT, commit/push/merge,
deploymentu ani vendor write.
