# WILQ GA4 Analyst Output Contract

## Cel

Diagnostyka GA4 behavior, landing-page i tracking oparta o Analytics Data API evidence.

Oczekiwany wynik: diagnostyka GA4 z metric summaries, evidence IDs, caveats i bezpiecznymi kandydatami działań.

## Wymagany kontekst API

Najpierw pobierz `GET /api/ga4/diagnostics`. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-ga4-analyst"}` i potwierdź, że `ga4_diagnostics` istnieje przed analizą marketingową. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `google_analytics_4`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` i `Następny krok`. Identyfikatory API, connector IDs, evidence IDs, opportunity IDs i ActionObject IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów i znane blockery.
2. `Dowody`: `ga4_diagnostics.decision_queue`, `ga4_diagnostics.sections`, evidence IDs, connector IDs, landing/source/campaign metric facts, tactical item IDs i freshness notes wyłącznie z WILQ API.
3. `Diagnoza`: użyj najpierw `decision_queue`. Klasyfikuj każdy item jako `fix_measurement`, `review_landing_mapping` albo `review_traffic_quality`, potem wyjaśnij, co evidence wspiera. Dodaj niepewność, gdy evidence jest zagregowane, stare, nie ma conversion-like facts albo ma tylko behavior metrics.
4. `Kandydaci działań`: decision IDs, opportunity IDs, tactical queue IDs i ActionObject IDs, jeśli są dostępne; w przeciwnym razie opisz brakujące API/evidence potrzebne do ich utworzenia.
5. `Walidacja`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed apply/execution.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, connector refresh runs, expert rules ani action objects.
- `ga4_diagnostics.live_data_available=false`, a użytkownik prosi o jakość landingów, conversion readiness, tracking gap, jakość kampanii albo behavior recommendations.
- Użytkownik prosi o write execution bez zwalidowanego ActionObject i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak zwalidowanego payload oznacza brak apply. Brak audit event oznacza brak write.

## Bezpieczeństwo GA4

`active_users`, `sessions` i `engagement_rate` wspierają traffic-quality review, nie claimy ROAS, revenue, conversion-drop ani profitability. Jeśli brakuje conversion-like facts, powiedz to wprost i utrzymaj następny krok jako review/prepare-only.

Reguły `decision_queue`:

- `fix_measurement` means tracking/reporting review first; do not turn it into a content or campaign recommendation.
- `review_landing_mapping` means verify URL/WordPress mapping before judging the landing page.
- `review_traffic_quality` oznacza, że evidence może wspierać traffic-quality/message-match review, ale nie claimy ROAS/revenue/profitability.
