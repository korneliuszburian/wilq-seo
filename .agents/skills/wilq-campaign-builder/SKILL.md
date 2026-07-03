---
name: wilq-campaign-builder
description: Buduje bezpieczne akcje kampanii Google Ads do sprawdzenia dla Ekologus przez WILQ API. Użyj, gdy marketer pyta "stwórz strukturę kampanii", "zaplanuj PMax/Search/Shopping", "przygotuj kampanię na usługę/produkt", "jakie słowa kluczowe, materiały i sitelinki?", "daj podgląd zmian", albo chce strukturę kampanii, plan grup reklam, pomysły słów kluczowych i materiałów, budżety, kierowanie lub bezpieczny podgląd zmian. Musi sprawdzać propozycje w WILQ przed zapisem zmian i nie wolno omijać audytu.
---

# WILQ Plan kampanii

## Zasada skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Przygotuj strukturę kampanii Search dla tej usługi Ekologus."
- "Zbuduj draft PMax/Shopping bez zapisu zmian."
- "Jakie materiały, słowa kluczowe i sitelinki możemy przygotować z obecnych dowodów?"
- "Pokaż podgląd zmian i ryzyka przed zapisem zmian."

</triggers>

## Workflow operatora

<workflow>

1. Wywołaj `GET /api/ads/diagnostics`, żeby sprawdzić gotowość konta, kampanii, search terms, rekomendacji i brakujące dane przed planem kampanii.
2. Pobierz `GET /api/marketing/brief` tylko jako tło marketingowe; nie używaj go zamiast danych Ads.
3. `POST /api/codex/context-pack` pobieraj tylko gdy potrzebujesz połączyć Ads z GA4/GSC/WordPress albo przygotować szerszy podgląd kampanii.
4. Odpowiedz jako plan do sprawdzenia: struktura, ryzyka, dowody, zablokowane claimy i action ID do preview/review. Nie zapisuj kampanii.
5. Jeśli użytkownik prosi o zapis albo podgląd zmiany, użyj `POST /api/actions/{action_id}/validate`; w review-only odpowiedzi wystarczy wskazać action_id i bezpieczny następny krok.
6. Endpointów refresh źródeł danych używaj tylko do jawnych odczytów danych i tylko gdy źródło danych jest skonfigurowane.

</workflow>

## API

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `POST /api/codex/context-pack`
- `GET /api/marketing/brief`
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

- `google_ads`
- `google_analytics_4`
- `google_search_console`

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API. Jeśli dowody są zagregowane, stare, niepełne albo zablokowane dostępem do źródła danych, powiedz to wprost.

</evidence_requirements>

## Odpowiedź

<output>

Odpowiedź ma być krótka i użyteczna dla operatora: status, dowody, diagnoza, akcje do sprawdzenia w WILQ, blokady i następne bezpieczne kroki.

Język: wszystkie odpowiedzi dla operatora pisz po polsku z polskimi znakami. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans, identyfikatory akcji, ścieżki endpointów i wartości enumów zostaw bez zmian.

</output>

## Bezpieczeństwo

<safety_rules>

<!-- no-invented-metrics guardrail: do not invent metrics. -->
<!-- Polish language rule: operator-facing responses must be in Polish with Polish diacritics. -->

- Nie wymyślaj metryk, rankingów, liczby produktów, stanu kampanii, spisu treści, dostępów social ani ustaleń Localo.
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj endpointów zapisu zmian, chyba że WILQ API wystawia akcję, sprawdzenie w WILQ przechodzi i użytkownik jawnie prosi o zapis zmian.
- Nie omijaj sprawdzenia w WILQ, identyfikatorów dowodów ani wymagań audytu.
</safety_rules>
