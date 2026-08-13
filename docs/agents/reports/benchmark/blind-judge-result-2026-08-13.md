# Blind LLM-judge — wynik re-benchmarku (po domknięciu luki głębi)

Rola dokumentu: `current state` wyniku ślepej oceny przed/po. Nie jest publikacją
ani aprobatą człowieka.

## Werdykt

Blind judge (Codex SOL-ULTRA, read-only) na nowych rewizjach bez etykiet: **generated
preferowany na 4 z 5 stron** (cel wymagał ≥3).

| Strona | Judge preferował | Wynik |
|---|---|---|
| BDO | **generated (b)** | wygrana |
| Szkolenia | **generated (b)** | wygrana |
| Doradztwo | **generated (b)** | wygrana |
| Opracowania | **generated (b)** | wygrana |
| Pomiary | current (a) | przegrana |

Mapowanie: `text_a` = current WordPress, `text_b` = generated WILQ. Sędzia nie znał
mapowania (blind), a jego uzasadnienia opisują cechy treści, nie pochodzenie.

## Wyniki liczbowe (9 wymiarów × 2 teksty, skala 1–5)

Pełne wyniki: `blind-judge-result-2026-08-13.json`.

| Strona | Σ A (current) | Σ B (generated) |
|---|---|---|
| BDO | 28 | 40 |
| Szkolenia | 27 | 30 |
| Doradztwo | 34 | 42 |
| Opracowania | 30 | 31 |
| Pomiary | 39 | 35 |

Uzasadnienia sędziego (wybrane): BDO — „B jasno prowadzi przez obowiązki, terminy i
sankcje do kontaktu, podczas gdy A jest chaotyczny i oparty na wygasłych terminach z
2020 roku"; Doradztwo — „B konkretnie rozróżnia doradztwo od outsourcingu, opisuje
zakresy i dane wejściowe oraz prowadzi do jasnego kontaktu".

## Metryki deterministyczne (przed/po)

| Strona | Słowa cur→gen | Sekcje cur→gen | GSC cur→gen |
|---|---|---|---|
| BDO | 541→694 (+153) | 7→8 | 5.3%→10.5% |
| Szkolenia | 1473→512 (−961) | 0→7 | 6.2%→9.4% |
| Doradztwo | 365→814 (+449) | 0→11 | 5.9%→8.8% |
| Opracowania | 1519→770 (−749) | 0→9 | 25.0%→0.0% |
| Pomiary | 371→556 (+185) | 0→6 | 0.0%→75.0% |

## Co domknęło lukę

1. **Wiedza (source facts):** 4 karty usługowe z 1→6 faktów (Q42) rozszerzone do 30–49
   atomowych faktów per karta (procesy, zakresy, terminy, normy, adresaci), w tym 39
   nowych dla szkoleń i opracowań w tym cyklu (commit `b1f0a4d3`).
2. **Capacity BDO:** pre-save weryfikacja assertionów przed generacją
   (`regulatory_preflight_failed`), odmiana fleksyjna `bdo_full_name`, budżet assurance
   900→2400 s, grounding z sanityzacją meta-sformułowań i deduplikacją, oraz naprzemienna
   pętla assurance↔readability. BDO przechodzi teraz 9/9 semantic i trafia do sędziego.
3. **Regeneracja:** wszystkie 5 stron z nowymi planami (`regenerate_after_review` +
   `operator_hint`) i semantic review 9/9.

## Czego to NIE dowodzi

- Żadna treść nie jest opublikowana; brak wyników UAT Wilku ani pomiaru CTR/konwersji.
- Blind judge to opinia modelu, nie realny odbiorca. Pomiary nadal wypadają słabiej od
  current (sędzia wolał konkret metod/substancji current) — to jawna pozostała luka.
- Opracowania: GSC query coverage spadło 25%→0% (nowy plan nie pokrywa fraz GSC).

## Pliki

- `docs/agents/reports/benchmark/content-benchmark-2026-08-13.json` — deterministyczny.
- `docs/agents/reports/benchmark/llm-judge-input.json` — ślepe wejście sędziego.
- `docs/agents/reports/benchmark/blind-judge-result-2026-08-13.json` — wyniki sędziego.
- Poprzedni stan: `blind-judge-result-2026-08-12.md` (current 5/5).
