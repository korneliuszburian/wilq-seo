# WILQ Plan kampanii Kontrakt odpowiedzi

## Cel

Planowanie kampanii i przygotowanie akcji do sprawdzenia z sprawdzeniem w WILQ.

Oczekiwany wynik: evidence-bound kolejka przeglądu istniejących kampanii z
identyfikatorami dowodów, landing/context, jawnymi brakami i niemutującym
podglądem zmian. To nie jest generator nowej struktury kampanii.

Obsługiwane pola wynikowe to wyłącznie te obecne w kontrakcie API:
`campaign_candidates`, `derived_kpis`, `budget_context`,
`budget_payload_preview`, `human_review_gates`, `target_context`,
`missing_read_contracts`, `blocked_claims`, `evidence_ids` i `action_ids`.
Brak osobnego, zatwierdzonego kontraktu oznacza blokadę dla keywords, ad groups,
assets, sitelinks, copy, targetowania, typu kampanii, budżetu docelowego,
prognozy lub claimu gotowości.

## Wymagany kontekst API

Pobierz `POST /api/codex/context-pack` z
`{"skill":"wilq-campaign-builder"}` przed analizą marketingową. Skillowy
pakiet kontekstu musi zawierać `ads_diagnostics` i `content_landing_context`; traktuj
je jako typed kontrakt odczytu danych, a nie promptowy brainstorm. Użyj
`GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy
gotowość ma znaczenie.

Wymagane źródła danych:

- `google_ads`
- `google_analytics_4`
- `google_search_console`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Plan kampanii`, `Podgląd bez zapisu`, `Co sprawdzić przed kampanią`, `Decyzja po review`, `Zablokowane obietnice`, `Brief dla marketera`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Przegląd kampanii`: istniejąca kampania/landing, usługa/temat i źródła danych, z których wynika kolejka review.
2. `Podgląd bez zapisu`: co można przygotować jako preview/review w WILQ, bez zapisu zmian.
3. `Co sprawdzić przed kampanią`: strona wejścia, intencja z GSC, jakość ruchu z GA4, istniejące kampanie/rekomendacje Ads i brakujące kontrakty.
4. `Decyzja po review`: po sprawdzeniu operator może przygotować podgląd, odłożyć kampanię, poprosić o landing/content review albo zablokować temat.
5. `Zablokowane obietnice`: skuteczność kampanii, wzrost konwersji, gwarancja pozycji, zmiana kampanii i zapis bez preview/review/zgody.
6. `Brief dla marketera`: 3-5 zdań bez technicznego żargonu: co WILQ może przygotować, z czego to wynika, czego nie wolno obiecać i jaki jest następny bezpieczny krok.
7. `Akcje do sprawdzenia`: użyj `content_landing_context.query_page_candidates`, `campaign_candidates` z podglądem zmian i identyfikatory akcji, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia. Nie dodawaj nieobsługiwanych keywords/assets/budżetów.
8. `Sprawdzenie w WILQ`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed zapisem zmian.
9. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- Pakiet kontekstu skilla nie zawiera `content_landing_context` albo `ads_diagnostics`.
- Użytkownik prosi o zapis zmian bez akcji do sprawdzenia w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak podglądu zmian sprawdzonego w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.
