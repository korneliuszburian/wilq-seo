# WILQ Ads Doctor Output Contract

## Cel

Diagnostyka Google Ads, jakość kampanii, search terms, negative keywords i bezpieczni kandydaci działań Ads.

Oczekiwany wynik: ustalenia Ads oparte na evidence, z kandydatami działań pozostającymi pending do walidacji przez WILQ API.

Product inspiration: treat BDOS.ai as an Ads operating-system reference for the operator experience, and the official Google Ads MCP server as the reference MCP adapter pattern for read-only account discovery, GAQL/reporting exploration and documentation-assisted diagnostics. WILQ API remains canonical for evidence IDs, opportunity IDs, action validation and audit.

## Wymagany kontekst API

Pobierz `GET /api/ads/diagnostics` przed analizą Ads. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-ads-doctor"}` i użyj osadzonego `ads_diagnostics` jako consistency check, także opcjonalnego `blocked_handoff`. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego connectora, gdy readiness ma znaczenie.

Wymagane connectory:

- `google_ads`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Używaj polskich etykiet operatora: `Status`, `Dowody`, `Diagnoza`, `Kandydaci działań`, `Walidacja` i `Następny krok`. API identifiers, connector IDs, evidence IDs, opportunity IDs i ActionObject IDs zostaw bez zmian.


1. `Status`: zasięg API, gotowość connectorów, `blocked_handoff.status` jeśli istnieje, i znane blockery.
2. `Dowody`: Ads diagnostics section IDs, evidence IDs, connector IDs, latest refresh status, freshness notes and metric summaries from WILQ API only.
3. `Diagnoza`: what `/api/ads/diagnostics` supports, with uncertainty if the evidence is aggregate, stale, incomplete or blocked by OAuth.
4. `Kandydaci działań`: opportunity IDs i ActionObject IDs, gdy są dostępne; w przeciwnym razie opisz brakujące API/evidence potrzebne do ich utworzenia.
5. `Walidacja`: wynik albo wymagane wywołanie `POST /api/actions/{action_id}/validate` przed apply/execution.
6. `Następny krok`: najmniejszy bezpieczny krok operatora.

## Warunki odmowy lub downgrade do blockera

Odmów albo obniż odpowiedź do blocker report, gdy:

- WILQ API jest niedostępne.
- Wymagany connector ma status `missing_credentials`, `disabled` albo failed dla żądanej operacji.
- `/api/ads/diagnostics` returns `live_data_available=false` and the user asks for spend, CPA, ROAS, search terms, negative keywords, campaign scaling or budget changes.
- Żądana metryka albo akcja nie występuje w context-pack, evidence, connector refresh runs, expert rules ani action objects.
- Użytkownik prosi o write execution bez zwalidowanego ActionObject i jawnej zgody.

## Reguły evidence

Brak evidence ID oznacza brak rekomendacji. Brak source connector oznacza brak rekomendacji. Brak zwalidowanego payload oznacza brak apply. Brak audit event oznacza brak write.

## MCP Boundary

If a Google Ads MCP server is available later, use it only as a read-only adapter unless WILQ has a validated write ActionObject for the requested operation. MCP tool output must be converted into WILQ evidence or refresh-run state before it becomes a recommendation.
