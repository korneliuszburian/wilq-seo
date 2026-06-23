# WILQ Merchant Feed Operator Output Contract

## Cel

Triage Merchant Center dla product status, feed issues i product visibility.

Oczekiwany wynik: podsumowanie feed issues i kandydaci działań produktowych z Merchant evidence IDs oraz validation blockers.

## Wymagany kontekst API

Pobierz `GET /api/merchant/diagnostics` przed analizą Merchant/feed. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-merchant-feed-operator"}` i użyj osadzonego `merchant_diagnostics` jako consistency check. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `google_merchant_center`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` i `Następny krok`. API identifiers, connector IDs, evidence IDs, opportunity IDs i ActionObject IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów, `freshness_assessment` i znane blockery. Jeśli `freshness_assessment.requires_refresh=true` albo `state=stale|missing|blocked`, oznacz wynik jako stale/blocker review zamiast aktualnego stanu produkcyjnego.
2. `Dowody`: Merchant diagnostics section IDs, evidence IDs, connector IDs, latest refresh state, issue dimensions, metric summaries i product sample readiness wyłącznie z WILQ API.
3. `Kolejka review`: grupuj finalne rekomendacje po `decision_queue`. `issue_clusters` pokazuj tylko jako drilldown raportowania. Jeśli `count_semantics=reported_issue_occurrences`, wartości `product_count`, `issue_count`, `max zgłoszeń` i `raporty razem` opisuj jako wystąpienia/zgłoszenia problemu, nie jako unikalne produkty, SKU ani listę produktów do poprawy.
4. `Przykładowe produkty`: jeśli `product_sample_readiness.sample_products_available=true`, pokaż kilka `sample_product_ids` albo tytułów jako materiał do review. Nie traktuj próbek jako pełnej listy SKU ani zgody na feed write.
5. `Czego nie wiemy`: opisz `unknowns` z `/api/merchant/diagnostics`, szczególnie brak unikalnej liczby produktów, brak pełnego SKU workflow albo brak próbek dla części klastrów.
6. `Diagnoza`: co `/api/merchant/diagnostics` wspiera, z uncertainty jeśli evidence jest aggregate, stale, niepełne albo zablokowane permissions.
7. `Kandydaci działań`: opportunity IDs i ActionObject IDs, gdy są dostępne; w przeciwnym razie opisz brakujące API/evidence potrzebne do ich utworzenia.
8. `Walidacja`: pokaż różnicę między statusem ActionObject w context-packu a bieżącym wynikiem `POST /api/actions/{action_id}/validate`. `valid=true` oznacza tylko review/prepare path, nie apply.
9. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- `/api/merchant/diagnostics` zwraca `live_data_available=false`, a użytkownik pyta o feed issue actions, approval state, product visibility albo product fixes.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, connector refresh runs, expert rules ani action objects.
- Użytkownik prosi o write execution bez zwalidowanego ActionObject i jawnej zgody.

## Bezpieczeństwo Merchant

Używaj `act_review_merchant_feed_issues` tylko jako prepare/review candidate, dopóki WILQ API nie wystawi zwalidowanej Merchant action w trybie apply. Nie claimuj, że approval został przywrócony, produkt naprawiony, revenue odzyskane albo primary feed zmieniony bez audit event.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak zwalidowanego payload oznacza brak apply. Brak audit event oznacza brak write.
