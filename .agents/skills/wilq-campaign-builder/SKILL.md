---
name: wilq-campaign-builder
description: Przygotowuje evidence-bound kolejkę przeglądu istniejących kampanii Google Ads dla Ekologus przez WILQ API. Użyj, gdy marketer chce ocenić istniejące kampanie, landing page, metryki, ryzyka budżetowe albo bezpieczny podgląd review-only. Nie obiecuje kompletnej struktury nowej kampanii, słów kluczowych, assetów, sitelinków, targetowania ani budżetu bez osobnego kontraktu danych. Musi sprawdzać propozycje w WILQ przed zapisem zmian i nie wolno omijać audytu.
---

# WILQ Plan kampanii

## Zasada skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Oceń istniejące kampanie dla tej usługi Ekologus."
- "Pokaż, co trzeba sprawdzić przed zmianą budżetu lub kampanii."
- "Połącz landing page, GSC, GA4 i Ads w kolejkę review."
- "Pokaż podgląd zmian i ryzyka przed zapisem zmian."

## Zakres, który faktycznie dostarcza API

WILQ zwraca evidence-bound `campaign_candidates` z istniejących odczytów Ads,
policzonymi metrykami, priorytetem review, kontekstem landing page, jawnie
brakującymi kontraktami oraz niemutującym `budget_payload_preview`. To jest
materiał do decyzji człowieka i native-UI handoff, nie generator nowej kampanii.

Skill nie może wymyślać ani przedstawiać jako gotowych:

- słów kluczowych, grup reklam, assetów, sitelinków lub copy reklam;
- typu kampanii, targetowania, budżetu docelowego, CPA/ROAS albo prognozy;
- gotowości, skuteczności, wzrostu ani opłacalności kampanii.

Jeżeli użytkownik prosi o którykolwiek z tych elementów, odpowiedź ma zawierać
blokadę `missing_read_contracts` i najmniejszy następny krok do pozyskania
brakującego, zatwierdzonego źródła. Nie wypełniaj luki brainstormem.

</triggers>

## Workflow operatora

<workflow>

1. Wywołaj `GET /api/ads/diagnostics`, żeby sprawdzić gotowość konta, kampanii, search terms, rekomendacji i brakujące dane przed review.
2. Pobierz `GET /api/marketing/brief` tylko jako tło marketingowe; nie używaj go zamiast danych Ads.
3. `POST /api/codex/context-pack` pobieraj tylko gdy potrzebujesz połączyć Ads z GA4, GSC i WordPress albo przygotować szerszy podgląd kampanii.
4. Odpowiedz jako kolejka review: istniejące kampanie, landing/context, ryzyka, dowody, brakujące kontrakty, zablokowane twierdzenia i action ID do preview/review. Nie zapisuj kampanii.
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

Odpowiedź ma być krótka i użyteczna dla operatora: jaka propozycja kampanii
jest możliwa do review, jaki landing/context trzeba sprawdzić, jakie akcje
dają podgląd bez zapisu i czego nie wolno obiecać.

Widocznie używaj tych sekcji:

- `Plan kampanii`: typ propozycji, usługa/temat, strona wejścia i źródła danych, z których wynika pomysł.
- `Podgląd bez zapisu`: co można przygotować jako preview/review w WILQ, bez zapisu zmian.
- `Co sprawdzić przed kampanią`: strona wejścia, intencja z GSC, jakość ruchu z GA4, istniejące kampanie/rekomendacje Ads i brakujące kontrakty.
- `Decyzja po review`: po sprawdzeniu operator może przygotować podgląd, odłożyć kampanię, poprosić o landing/content review albo zablokować temat.
- `Zablokowane obietnice`: skuteczność kampanii, wzrost konwersji, gwarancja pozycji, zmiana kampanii i zapis bez preview/review/zgody.
- `Brief dla marketera`: 3-5 zdań normalnym językiem: co WILQ może przygotować, z czego to wynika, czego nie wolno obiecać i jaki jest następny bezpieczny krok.

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
