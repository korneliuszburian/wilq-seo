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

## Follow-up: source-fact grounding (Q40/Q41, 2026-08-13)

W odpowiedzi na finding "generated jest płytszy" dodano:
- Q40: initial draft dostaje `approved_source_facts_by_section` — model ma konkretne fakty per sekcja od początku.
- Q41: repair-turn też dostaje source facts dla naprawianych sekcji.

### Pomiar (strona: oferta/pomiary-i-analizy)

| Wersja | Sekcja 01 (słowa) | Sekcja 03 (słowa) | Semantic review |
|---|---|---|---|
| rev1 (initial, bez Q40) | 86 | 80 | 9/9 reviewable |
| rev2 (Q40 initial + repair sec01) | 90 | 80 | needs_changes (2: search_intent FAQ + long_sentence sec02) |
| rev3 (repair sec03) | 90 | **44** | needs_changes (4: specificity, search_intent, long_sentence, answer_directness) |

### Ustalenia (uczciwe)

1. **Q40 pogłębia initial draft** — sekcja 01 dostała konkret (pomiary emisji/hałasu/próbek, plan remediacji), specificity/completeness strong.
2. **Q41 (repair per sekcja) destabilizuje** — model naprawia jedną sekcję, przenosząc treść i psując inne (rev3 uciął sekcję 03 do 44 słów). Repair jest dobry do usuwania wad, nie do budowania głębi.
3. **BDO (regulatory) nie przechodzi świeżej generacji z Q40** — nowy plan ma 9 sekcji ze scalonymi wymaganiami; model gubi dokładną frazę `bdo_full_name`. To capacity limit przy danym planie, nie błąd promptu. (Fix regulatory-exclusion nie zmienił tego.)
4. **Query coverage deterministycznie bez zmian** (14%→14%) — dostępne source facts pokrywają inne frazy niż zapytania GSC; brakuje faktów dopasowanych do zapytań.

### Wniosek

Source-fact grounding (Q40) jest właściwym kierunkiem i realnie pogłębia initial draft. Jednak **pipeline nie osiągnął jeszcze głębi existing WordPress content** — blind judge nadal wolał current (5/5), a repair-turn nie jest narzędziem do budowania głębi. Zamknięcie luki wymaga: (a) bogatszych source facts dopasowanych do zapytań GSC, (b) initial-draft-only pogłębiania (bez repair na głębię), (c) re-benchmarku z blind judge.

## Root cause luki głębi (potwierdzony z danych, 2026-08-13)

Mierzalny powód, dla którego blind judge wolał current WordPress:

| Strona | Merytoryczne source facts w wiedzy WILQ | Current WordPress |
|---|---|---|
| BDO | 11 | 804 słów, 12 sekcji |
| Szkolenia | 1 | 1625 słów, 12 sekcji |
| Doradztwo | 1 | 426 słów, 12 sekcji |
| Opracowania | 1 | 2001 słów, 12 sekcji |
| Pomiary | 1 | 430 słów, 12 sekcji |

4 z 5 stron usługowych mają tylko **1 merytoryczny source fact** (np. "oferta obejmuje X, Y, Z").
Model nie może wygenerować konkretnej, głębokiej treści z 1 ogólnego faktu — może jedynie
rozwinąć ogólniki. Świeża generacja doradztwa z Q40 dała 9/9 semantic (short ale strong),
ale tylko 148 słów vs 426 current — semantic review nie nagradza głębi.

**Wniosek:** luka głębi jest luką WIEDZY (source facts), nie promptu. Zamknięcie wymaga
wzbogacenia knowledge base o szczegółowe fakty per usługa (zakresy, procesy, normy, ceny,
obowiązki) — to osobny program danych, wykraczający poza prompt/pipeline. Bez tego generowana
treść pozostanie strukturalnie lepsza, ale merytorycznie płytsza niż existing content.
