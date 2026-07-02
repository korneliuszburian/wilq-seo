# WILQ Merchant Center Kontrakt odpowiedzi

## Cel

Przegląd Merchant Center dla stanu produktów, problemów pliku produktowego i widoczności produktów.

Oczekiwany wynik: podsumowanie problemów pliku produktowego i produktowe akcje do sprawdzenia z identyfikatorami dowodów Merchant oraz blokady sprawdzenia.

## Wymagany kontekst API

Pobierz `GET /api/merchant/diagnostics` przed analizą Merchant i pliku produktowego. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-merchant-feed-operator"}` i użyj osadzonego `merchant_diagnostics` jako consistency check. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `google_merchant_center`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Akcje do sprawdzenia`, `Sprawdzenie w WILQ` i `Następny krok`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Status`: zasięg API, gotowość źródeł danych, `freshness_assessment` i znane blokady. Jeśli `freshness_assessment.requires_refresh=true` albo `state=stale|missing|blocked`, oznacz wynik jako przegląd nieświeżych danych lub blokad zamiast aktualnego stanu produkcyjnego.
2. `Dowody`: Merchant diagnostics identyfikatorów sekcji, identyfikatory dowodów, identyfikatory źródeł danych, stan ostatniego odczytu, wymiary problemów, podsumowania metryk, gotowość próbek produktów, `product_performance_readiness` i `price_impact_readiness` wyłącznie z WILQ API.
3. `Kolejka review`: grupuj finalne rekomendacje po `decision_queue`. `issue_clusters` pokazuj tylko jako drilldown raportowania. Jeśli `count_semantics=reported_issue_occurrences`, wartości `product_count`, `issue_count`, `max zgłoszeń` i `raporty razem` opisuj jako wystąpienia/zgłoszenia problemu, nie jako unikalne produkty, SKU ani listę produktów do poprawy.
4. `Przykładowe produkty`: jeśli `product_sample_readiness.sample_products_available=true`, pokaż kilka `sample_product_ids` albo tytułów jako materiał do sprawdzenia. Nie traktuj próbek jako pełnej listy SKU ani zgody na zapis do pliku produktowego.
5. `Czego nie wiemy`: opisz `unknowns` z `/api/merchant/diagnostics`, szczególnie brak unikalnej liczby produktów, brak pełnego SKU workflow, brak próbek dla części klastrów, `product_performance_readiness.status=blocked` albo `price_impact_readiness.status=blocked`.
   Cytuj `missing_read_contracts` jako faktycznie brakujące kontrakty, a
   `required_read_contracts` tylko jako pełną listę wymagań. Nie łącz tych list
   w jeden "brak", bo WILQ może mieć część wymagań już spełnioną. Jeśli
   `missing_read_contracts` jest dostępne, wypisz jego wartości literalnie jako
   faktyczny brak.
6. `Diagnoza`: co `/api/merchant/diagnostics` wspiera, z niepewnością jeśli dowody są zagregowane, nieświeże, niepełne albo zablokowane uprawnieniami.
7. `Akcje do sprawdzenia`: identyfikatory szans i identyfikatory akcji, gdy są dostępne; w przeciwnym razie opisz brakujące dane źródłowe albo dowody potrzebne do ich utworzenia.
8. `Sprawdzenie w WILQ`: pokaż różnicę między statusem akcji w pakiecie kontekstuu a bieżącym wynikiem `POST /api/actions/{action_id}/validate`. `valid=true` oznacza tylko ścieżkę sprawdzenia/przygotowania, nie zapis zmian.
9. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokad, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- `/api/merchant/diagnostics` zwraca `live_data_available=false`, a użytkownik pyta o działania na problemach pliku produktowego, stan zatwierdzeń, widoczność produktów albo poprawki produktów.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- Użytkownik prosi o zapis zmian bez akcji do sprawdzenia w WILQ i jawnej zgody.

## Bezpieczeństwo Merchant

Używaj `act_review_merchant_feed_issues` tylko jako przygotowania do sprawdzenia, dopóki WILQ API nie wystawi akcji Merchant ze sprawdzoną ścieżką zapisu zmian. Nie twierdź, że zatwierdzenie zostało przywrócone, produkt naprawiony, przychód odzyskany albo główny plik produktowy zmieniony bez zdarzenia audytu.

Jeśli `product_performance_readiness.status=blocked`, nie twierdź, że znasz zwrot z reklam na poziomie produktu, odzyskany przychód produktu, wpływ naprawy produktu ani skalowanie produktu w Shopping/PMax. Jeśli `status=ready`, używaj tylko `performance_rows` z identyfikatorami dowodów i nadal nie twierdź, że naprawa pliku produktowego już dała efekt bez audytu sprzed i po zmianie.

Jeśli `price_impact_readiness.status=blocked`, nie oceniaj wpływu ceny produktu. Bieżąca cena z Ads wystarcza do kontroli danych; do wpływu ceny potrzebne są historyczne snapshoty ceny, data zmiany i dopasowane okno skuteczności sprzed i po zmianie. Jeśli `status=ready`, traktuj podgląd zmian jako sprawdzenie gotowości, nie rekomendację zmiany ceny.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji do sprawdzenia w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.
