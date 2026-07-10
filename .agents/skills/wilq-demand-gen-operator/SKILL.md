---
name: wilq-demand-gen-operator
description: Obsługuje gotowość Demand Gen, jakość kreacji i workflow Ads-to-GA4 dla Ekologus z dowodami z WILQ API. Użyj, gdy marketer pyta "czy Demand Gen ma sens?", "sprawdź tryb kampanii Demand Gen/Discovery", "sprawdź jakość kreacji i ruchu", "czy kampania dowozi jakościowy ruch?", albo pyta o plan Demand Gen, gotowość creative/asset, jakość ruchu kampanii, GA4 cross-checks lub bezpieczne akcje do sprawdzenia. Musi zachować dowody i bramki sprawdzenia w WILQ.
---

# WILQ Demand Gen Operator

## Zasada skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Czy Demand Gen ma sens dla Ekologus na podstawie obecnych danych?"
- "Sprawdź jakość ruchu z kampanii i dopasowanie stron wejścia."
- "Przygotuj brief gotowości Demand Gen bez zapisu zmian."
- "Jakie assets/kreacje wymagają poprawy według dowodów?"

</triggers>

## Workflow operatora

<workflow>

1. Wywołaj `GET /api/demand-gen/diagnostics` przed podsumowaniem metryk, szans albo akcji do sprawdzenia.
2. Pobierz `POST /api/codex/context-pack` tylko gdy wąski endpoint nie wystarcza albo potrzebujesz kontekstu wielu powierzchni. Nie rób z tego obowiązkowego kroku.
3. Endpointów refresh źródeł danych używaj tylko do jawnych odczytów danych i tylko gdy źródło danych jest skonfigurowane.
4. Jeśli użytkownik prosi o zapis albo podgląd zmiany, użyj `POST /api/actions/{action_id}/validate`; w review-only odpowiedzi wystarczy wskazać action_id i bezpieczny następny krok.
5. W podstawowej odpowiedzi używaj polskich podsumowań dowodów i źródeł danych. Techniczne identyfikatory źródeł danych, dowodów, szans i akcji dodawaj tylko jako ślad techniczny, gdy API je udostępnia.

</workflow>

## API

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `POST /api/codex/context-pack`
- `GET /api/marketing/brief`
- `GET /api/demand-gen/diagnostics`
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

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API. Jeśli dowody są zagregowane, stare, niepełne albo zablokowane dostępem do źródła danych, powiedz to wprost.

</evidence_requirements>

## Odpowiedź

<output>

Odpowiedź ma być krótka i użyteczna dla operatora: czy Demand Gen da się
teraz ocenić, dlaczego workflow jest zatrzymany, jakie dowody Ads/GA4 już są,
czego brakuje do oceny kreacji/ruchu i kiedy warto wrócić do tematu.

Widocznie używaj tych sekcji:

- `Werdykt Demand Gen`: czy WILQ widzi kampanie Demand Gen/Discovery i czy ocena jest review-only albo zablokowana.
- `Dlaczego stop`: konkretny powód blokady, np. 0 kampanii Demand Gen/Discovery mimo dostępnych danych Ads/GA4.
- `Co mamy z Ads/GA4`: liczba ocenionych kampanii/kanałów i źródła dowodów tylko z WILQ API.
- `Czego brakuje do oceny`: kampania Demand Gen/Discovery, dane kreacji/assets, landing-quality per kampania, GA4 traffic-quality dla tej kampanii.
- `Podgląd bez zapisu`: action_id albo review preview, które można sprawdzić w WILQ bez zmiany kampanii.
- `Kiedy wrócić`: warunki, po których Demand Gen można oceniać dalej, np. po pojawieniu się kampanii i danych kreacji/ruchu.
- `Zablokowane obietnice`: rekomendacja uruchomienia, gotowość trybu, ocena jakości kreacji, skuteczność assetów, zmiana kampanii i wzrost skuteczności.
- `Brief dla marketera`: 3-5 zdań normalnym językiem: co wiemy, dlaczego nie rekomendujemy launchu, co sprawdzić teraz i czego potrzeba do kolejnego kroku.

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
