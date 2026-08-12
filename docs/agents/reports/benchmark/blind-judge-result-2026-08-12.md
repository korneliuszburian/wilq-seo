# Blind LLM-judge — wynik benchmarku jakości treści

Rola dokumentu: `current state` wyniku ślepej oceny przed/po. Nie jest publikacją
ani aprobatą człowieka.

## Metoda

- Sędzia: Codex SOL-ULTRA (gpt-5.6-sol, read-only), na wejściu
  `docs/agents/reports/benchmark/llm-judge-input.json`.
- Pary `text_a`/`text_b` NIE były oznaczone (blind). Sędzia nie znał, które
  jest istniejącą stroną WordPress, a które rewizją WILQ.
- 9 wymiarów w skali 1–5 per tekst + ogólna preferencja per strona.

## Mapowanie (ustalone po ocenie)

- `text_a` = **current WordPress** (istniejąca treść)
- `text_b` = **generated WILQ** (rewizja pipeline'u)

## Wynik

| Strona | Blind judge preferował | Score A (current) | Score B (generated) |
|---|---|---|---|
| BDO | current | wyżej: kompletność/specyfika | niżej |
| Szkolenia | current | wyżej | niżej |
| Doradztwo | current | wyżej | niżej |
| Opracowania | current | wyżej | niżej |
| Pomiary | current | wyżej | niżej |

Wszystkie 5 stron: **current WordPress lepszy w ocenie ślepej** — głównie
kompletność (więcej szczegółów merytorycznych) i specyficzność. Generated WILQ
był chwalony za porządek, nawigację i klarowność CTA, ale "powtarza ogólniki"
i "pomija obszary usług".

## Porównanie z metrykami deterministycznymi

| Metryka | Current | Generated |
|---|---|---|
| Query coverage (GSC) | niższa (0–20%) | wyższa (7–67%) |
| Struktura sekcji | słaba/0 (spłaszczone) | 3–8 sekcji |
| Unikalność | — | 100% nowych |
| Notatki robocze | 0 | 1 (BDO) |

## Wniosek (uczciwy)

Pipeline deterministycznie dostarcza: strukturę, pokrycie zapytań, unikalność.
Jednak **jakość merytoryczna generowanej treści jest za płytka** — model pisze
bardziej ogólnikowo niż istniejąca strona. To jest realna luka do zamknięcia w
promptach/pipeline (więcej source facts per sekcja, głębsze rozwinięcie
merytoryczne), NIE stan do uznania za "najlepszy". To potwierdza decyzję
z research: `9/9 semantic review` nie jest dowodem jakości dla czytelnika.

## Nie dowodzi

- Żadna z tych treści nie jest opublikowana ani nie ma wyników użytkownika.
- Blind judge to opinia modelu, nie UAT Wilku ani pomiar CTR/konwersji.
