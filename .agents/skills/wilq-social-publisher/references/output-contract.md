# WILQ Posty społecznościowe Kontrakt odpowiedzi

## Cel

Gotowość publikacji LinkedIn/Facebook i akcje do sprawdzenia oparte na dowodach.

Oczekiwany wynik: propozycje postów social z dowodami źródłowymi, stanem przeglądu i blokadami źródeł danych.

## Wymagany kontekst API

Pobierz `POST /api/codex/context-pack` z
`{"skill":"wilq-social-publisher"}` przed analizą marketingową. Skillowy
pakiet kontekstu musi zawierać `social_draft_context`; traktuj go jako kontrakt
szkicu, a nie promptowy generator postów. Użyj
`GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy
gotowość ma znaczenie.

Wymagane źródła danych:

- `linkedin`
- `facebook`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Status`: zasięg API, gotowość źródeł danych i znane blokady.
2. `Dowody`: `social_draft_context`, `source_inputs`, identyfikatory dowodów, identyfikatory źródeł danych, notatki o świeżości i podsumowania metryk wyłącznie z WILQ API.
3. `Diagnoza`: co wspierają dowody, z niepewnością gdy dowody są zagregowane, stare albo niepełne.
4. `Akcje do sprawdzenia`: użyj `social_draft_context.source_inputs`, `draft_action_ids`, `draft_constraints`, `missing_publish_access`, `historical_social_inventory_status`, `duplicate_risk_status`, `social_history_inventory` i identyfikatory akcji, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
5. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- Pakiet kontekstu skilla nie zawiera `social_draft_context`.
- `historical_social_inventory_status` ma wartość `missing`; wtedy nie wolno twierdzić, że temat nie powiela wcześniejszych postów LinkedIn/Facebook.
- `social_history_inventory.status` ma wartość `missing`; wtedy pokaż wymagane metadata-only pola historii (`channel`, `published_at`, `topic`, `service`, `claim`, `cta`, `format`, `post_url_or_id`, `source_evidence_id`) i nie używaj raw treści postów jako wymogu.
- Użytkownik prosi o zapis zmian bez akcji do sprawdzenia w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji do sprawdzenia w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.
