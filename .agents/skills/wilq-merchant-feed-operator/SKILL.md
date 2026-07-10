---
name: wilq-merchant-feed-operator
description: Analizuje dowody Merchant Center dla produktów i pliku produktowego Ekologus przez WILQ API i przygotowuje bezpieczną kolejkę sprawdzenia problemów pliku produktowego. Użyj, gdy marketer pyta "czy plik produktowy jest OK?", "które produkty mają problemy?", "co blokuje Shopping/PMax produkty?", "sprawdź odrzucone produkty", "przygotuj kolejkę przeglądu problemów pliku produktowego", albo pyta o diagnostykę Merchant, ryzyka widoczności produktów, poprawki pliku produktowego, typy problemów, atrybuty, dostępność, ceny, GTIN/obrazy lub zatwierdzenia produktów. Nie wolno zmieniać danych produktu bez akcji do sprawdzenia w WILQ i audytu.
---

# WILQ Merchant Center

## Zasada skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Czy plik produktowy Ekologus/sklep.ekologus.pl jest zdrowy?"
- "Pokaż problemy produktów w Merchant Center."
- "Co może blokować widoczność produktów w Shopping/PMax?"
- "Przygotuj bezpieczną kolejkę sprawdzenia problemów pliku produktowego."

</triggers>

## Workflow operatora

<workflow>

1. Wywołaj `GET /api/merchant/diagnostics` przed podsumowaniem zdrowia pliku produktowego/produktów, issue queue lub akcji do sprawdzenia produktowych.
2. Pobierz `POST /api/codex/context-pack` tylko gdy wąski endpoint nie wystarcza albo potrzebujesz kontekstu wielu powierzchni. Nie rób z tego obowiązkowego kroku.
3. Endpointów refresh źródeł danych używaj tylko do jawnych odczytów danych i tylko gdy źródło danych jest skonfigurowane.
4. Jeśli użytkownik prosi o zapis albo podgląd zmiany, użyj `POST /api/actions/{action_id}/validate`; w review-only odpowiedzi wystarczy wskazać action_id i bezpieczny następny krok.
5. W podstawowej odpowiedzi używaj polskich podsumowań dowodów i źródeł danych. Techniczne identyfikatory źródeł danych, dowodów, szans i akcji dodawaj tylko jako ślad techniczny, gdy API je udostępnia.
6. Dla pytań o aktualny stan pliku produktowego użyj `freshness_assessment`: `requires_refresh=true` albo `state=stale|missing|blocked` oznacza nieaktualne dane albo blokadę, chyba że użytkownik jawnie pozwala na odczyt danych źródła danych.
7. Finalną kolejkę pracy grupuj po `decision_queue`. `issue_clusters` traktuj jako drilldown raportowy; `product_count` przy `count_semantics=reported_issue_occurrences` nie jest liczbą unikalnych SKU ani produktów.
8. Nie wolno opisywać całej listy produktów na podstawie próbek ani liczby zgłoszeń jako liczby unikalnych SKU. Próbki pokazuj jako punkty do ręcznego sprawdzenia.

</workflow>

## API

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `POST /api/codex/context-pack`
- `GET /api/merchant/diagnostics`
- `GET /api/marketing/brief`
- `GET /api/marketing/tactical-queue`
- `GET /api/connectors`
- `GET /api/connectors/{connector}/status`
- `GET /api/connectors/{connector}/refresh-runs`
- `GET /api/connectors/refresh-runs`
- `GET /api/evidence`
- `GET /api/opportunities`
- `GET /api/actions`
- `GET /api/actions/{action_id}`
- `POST /api/actions/{action_id}/validate`
- `POST /api/connectors/{connector}/refresh` z `mode=vendor_read` tylko wtedy, gdy źródło danych jest skonfigurowane i zadanie jawnie wymaga świeżego odczytu danych.

</allowed_endpoints>

## Dowody

<evidence_requirements>

Wymagane powierzchnie źródeł danych dla tego skilla:

- `google_merchant_center`

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API. Merchant Diagnostics sections i tactical items traktuj jako główne źródło. Jeśli dowody są zagregowane, stare, niepełne albo zablokowane dostępem do źródła danych, powiedz to wprost.

Jeśli `/api/merchant/diagnostics` zwraca `unknowns`, `product_sample_readiness.status=blocked`, `product_performance_readiness.status=blocked` albo `price_impact_readiness.status=blocked`, odpowiedź musi mieć sekcję "Czego nie wiemy" i nie może udawać kolejki produkt-po-produkcie, zwrotu z reklam na poziomie produktu, wpływu ceny ani wpływu naprawy na przychód.

Przy `product_performance_readiness` i `price_impact_readiness` odróżniaj
`required_read_contracts` od `missing_read_contracts`. W widocznej odpowiedzi
dla operatora tłumacz braki na normalny polski, np. "brakuje danych
skuteczności produktu", "brakuje historii/zdarzenia zmiany ceny" albo
"brakuje okna porównania wyników produktu". Surowe wartości pól
`required_read_contracts`, `missing_read_contracts`, `product_performance_readiness`,
`price_impact_readiness`, `missing_read_contracts`, `required_read_contracts`,
`merchant_price_change_event_or_snapshot`,
`google_ads_shopping_product_performance` i
`google_ads_or_ga4_product_performance_window` zostaw tylko w technicznym
śladzie/debugu, jeśli są potrzebne do audytu. Nie używaj tych szczegółowych nazw w
`label_pl`, `blocked_reason`, `operator_next_step` ani widocznych
`action_candidates`; tam pisz po ludzku, czego brakuje i co to blokuje.
Dla debug-notatek przy brakującym kontrakcie można zachować wartości techniczne,
ale nie rób z nich głównej kopii dla marketera.

</evidence_requirements>

## Odpowiedź

<output>

Odpowiedź ma być krótka i użyteczna dla operatora: co sprawdzić pierwsze,
jak czytać liczby bez pułapki SKU, czego nie wiemy, jaka decyzja może paść po
review i co można pokazać marketerowi. Nie pokazuj szczegółowych nazw pól jako
głównej kopii dla marketera, jeśli można je opisać normalnym polskim.

Widocznie używaj tych sekcji:

- `Kolejność review`: najpierw najwyższe ryzyko lub największa grupa problemów z `decision_queue`, potem mapping Ads/product state, potem próbki produktów.
- `Liczby bez pułapki`: powiedz, czy liczby oznaczają zgłoszenia/wystąpienia problemów, próbki czy unikalne SKU. Jeśli unikalnych SKU nie ma, napisz to wprost.
- `Czego nie wiemy`: brakujące kontrakty, brak pełnej listy SKU, brak wpływu ceny, brak skuteczności produktu albo nieświeżość danych.
- `Decyzja po review`: co można zrobić po ręcznym sprawdzeniu: przygotować listę poprawek, poprosić o odświeżenie danych, eskalować strona wejścia error albo zostawić jako niskie ryzyko.
- `Brief dla marketera`: 3-5 zdań normalnym językiem: co WILQ widzi w Merchant, co sprawdzić pierwsze, czego nie wolno obiecać i jaki jest następny bezpieczny krok.

Język: wszystkie odpowiedzi dla operatora pisz po polsku z polskimi znakami. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans, identyfikatory akcji, ścieżki endpointów i wartości enumów zostaw bez zmian.

</output>

## Bezpieczeństwo

<safety_rules>

<!-- no-invented-metrics guardrail: do not invent metrics. -->
<!-- Polish language contract: operator-facing responses must be in Polish with Polish diacritics. -->

- Nie wymyślaj metryk, rankingów, liczby produktów, stanu kampanii, spisu treści, dostępów social ani ustaleń Localo.
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj endpointów zapisu zmian, chyba że WILQ API wystawia akcję, sprawdzenie w WILQ przechodzi i użytkownik jawnie prosi o zapis zmian.
- Nie omijaj sprawdzenia w WILQ, identyfikatorów dowodów ani wymagań audytu.
</safety_rules>
