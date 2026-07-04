# WILQ Posty społecznościowe Kontrakt odpowiedzi

## Cel

Gotowość publikacji LinkedIn/Facebook i akcje do sprawdzenia oparte na dowodach.

Oczekiwany wynik: propozycje postów social z dowodami źródłowymi, stanem przeglądu i blokadami źródeł danych.

## Wymagany kontekst API

Pobierz `POST /api/codex/context-pack` z
`{"skill":"wilq-social-publisher"}` przed analizą marketingową. Skillowy
pakiet kontekstu musi zawierać `social_draft_context`; traktuj go jako kontrakt
szkicu, a nie promptowy generator postów. Pobierz też
`GET /api/social/history-inventory`, gdy mówisz o historii postów albo ryzyku
powtórek. Publiczne `discovery_seeds` pokazuj jako punkt startowy zbierania
metadanych, nie jako gotową historię postów. Użyj
`GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy
gotowość ma znaczenie.

Wymagane źródła danych:

- `linkedin`
- `facebook`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Można zrobić teraz`, `Pakiet do review`, `Wariant LinkedIn`, `Wariant Facebook`, `Historia do sprawdzenia`, `Decyzja po review`, `Dowód`, `Zablokowane`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.

W tekście dla operatora unikaj artefaktowego skrótu łączącego "tylko" z
"do sprawdzenia". Pisz normalniej: `do ręcznego przeglądu`, `bez publikacji`,
`wymaga review` albo `przed publikacją trzeba uzupełnić ...`.


1. `Można zrobić teraz`: przygotować szkic do ręcznego review, nie publikację.
2. `Pakiet do review`: temat, główna teza, CTA do ręcznego sprawdzenia i źródło inspiracji z WILQ.
3. `Wariant LinkedIn`: 2-4 zdania szkicu albo kierunku posta, bardziej ekspercko i bez obietnic efektu.
4. `Wariant Facebook`: 2-4 zdania szkicu albo kierunku posta, prostszym językiem i bez obietnic efektu.
5. `Historia do sprawdzenia`: powiedz normalnie, że nie wiemy jeszcze, czy podobny post już był na LinkedIn/Facebooku; nie wolno pisać, że temat jest nowy ani bezpieczny do powtórzenia.
6. `Decyzja po review`: co może się stać po sprawdzeniu historii i twierdzeń: zaakceptować szkic do ręcznego przygotowania, przerobić CTA, zablokować temat albo poczekać na historię social.
7. `Dowód`: `social_draft_context`, `source_inputs`, identyfikatory dowodów, identyfikatory źródeł danych, notatki o świeżości i podsumowania metryk wyłącznie z WILQ API. Surowe pola techniczne trzymaj tutaj albo w notes, nie jako główną kopię.
8. `Zablokowane`: publikacja, opublikowanie posta, wzrost skuteczności social, brak powtórzeń historycznych postów, zwrot z reklam i przychód.
9. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
10. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- Pakiet kontekstu skilla nie zawiera `social_draft_context`.
- `historical_social_inventory_status` ma wartość `missing`; wtedy nie wolno twierdzić, że temat nie powiela wcześniejszych postów LinkedIn/Facebook.
- `social_history_inventory.status` ma wartość `missing`; wtedy pokaż wymagane metadata-only pola historii (`channel`, `published_at`, `topic`, `service`, `claim`, `cta`, `format`, `post_url_or_id`, `source_evidence_id`) i nie używaj raw treści postów jako wymogu. Jeśli `discovery_seeds` zawiera publiczne adresy LinkedIn/Facebook, nazwij je tylko punktami startowymi discovery.
- Użytkownik prosi o zapis zmian bez akcji do sprawdzenia w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji do sprawdzenia w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.
