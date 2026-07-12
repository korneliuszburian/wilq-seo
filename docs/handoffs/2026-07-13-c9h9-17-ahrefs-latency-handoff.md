# Handoff — 2026-07-13: Ahrefs diagnostics latency

## Domknięty slice

`wilq-seo-c9h9.17` usuwał prawdziwy koszt CPU, nie przykrywał go cache'em.
`AhrefsCrossSourceMatcher` w `wilq/content/planning/ahrefs_overlap.py` kompiluje
immutable rekordy GSC i publicznego WordPressa raz dla batcha. Planner używa
matchera dla wszystkich luk; dotychczasowa funkcja
`assess_ahrefs_cross_source_overlap()` pozostaje kompatybilnym adapterem dla
pojedynczego wywołania.

Nie zmieniono routera, schematu, evidence/freshness, ActionObjectów ani reguł
`exact`/`weak`/`missing`. Nie dodano response cache, więc po refreshu nie ma
ryzyka podania starego snapshotu.

## Root cause i proof

- Przed naprawą realne `GET /api/ahrefs/diagnostics` trwały 14.654183 s,
  15.872616 s, 17.760386 s i do 25.637534 s.
- Bez baz danych isolated builder na aktualnych danych zrobił 93 mln wywołań i
  46.961183 s CPU: 338 luk przebudowywało rekordy GSC/WordPress dla każdego
  candidate'a.
- Po zmianie isolated builder z profilingiem trwa 2.198553 s; bez profilerowego
  narzutu batch na aktualnych 338 luk trwał 0.710046 s.
- Po managed restarcie trzy odczyty HTTP: 1.354044 s, 1.351506 s, 1.212189 s.
- Kontrakt live pozostał: `manual_required`, 6 kandydatów, 0 exact GSC, 0 exact
  WordPress i 0 akcji; evidence/source semantics nie zmieniono.
- Browser proof: `.local-lab/proof/c9h9-17-ahrefs-latency/ahrefs-desktop-fast.png`.

## Weryfikacja

- Focused tests Ahrefs/tactical/source contracts: 16 passed.
- Ruff i mypy dla zmienionych modułów przechodzą.
- `audit_complexity.py --changed` nie ma frozen-growth ani budget violations.
- `fallow:audit` nie znajduje problemów w pięciu zmienionych plikach.

## Następny seam

Nie podłączaj matchera do `wilq/briefing/tactical_queue.py` wprost. Próbna
zmiana ujawniła monolit 1400 LOC przy budżecie 800. `wilq-seo-c9h9.18` ma
wydzielić tylko Ahrefs tactical branch do typed modułu, zachowując manual/weak
bez ActionObjectu. Nie używaj globalnego wyjątku complexity ani response cache'a
jako obejścia.
