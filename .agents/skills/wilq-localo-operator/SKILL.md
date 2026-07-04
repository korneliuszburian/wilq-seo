---
name: wilq-localo-operator
description: Obsługuje proces Localo i lokalnej widoczności dla Ekologus przez gotowość i dowody Localo w WILQ API. Użyj, gdy marketer pyta "jak poprawić lokalną widoczność?", "sprawdź Localo/GBP", "które lokalne frazy spadły?", "porównaj widoczność z konkurencją", "zrób lokalny SEO plan", albo pyta o lokalne rankingi, widoczność Google Business Profile, opinie, lokalnych konkurentów, akcje do sprawdzenia wpisu GBP lub blokady dostępu Localo. Nie wolno obiecywać metryk Localo bez dowodów WILQ API.
---

# WILQ Localo Operator

## Zasada skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed obietnicami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Jak poprawić lokalną widoczność Ekologus?"
- "Sprawdź Localo i GBP, ale bez zmyślania rankingów."
- "Czy mamy dowody lokalnych spadków albo konkurencji?"
- "Pokaż blokadę Localo i co trzeba zrobić dalej."

</triggers>

## Workflow operatora

<workflow>

1. Wywołaj `GET /api/localo/diagnostics` przed podsumowaniem metryk, szans albo akcji do sprawdzenia.
2. Pobierz `POST /api/codex/context-pack` tylko gdy wąski endpoint nie wystarcza albo potrzebujesz kontekstu wielu powierzchni. Nie rób z tego obowiązkowego kroku.
3. Endpointów refresh źródeł danych używaj tylko do jawnych odczytów danych i tylko gdy źródło danych jest skonfigurowane.
4. Jeśli użytkownik prosi o zapis albo podgląd zmiany, użyj `POST /api/actions/{action_id}/validate`; w review-only odpowiedzi wystarczy wskazać action_id i bezpieczny następny krok.
5. W podstawowej odpowiedzi używaj polskich podsumowań dowodów i źródeł danych. Techniczne identyfikatory źródeł danych, dowodów, szans i akcji dodawaj tylko jako ślad techniczny, gdy API je udostępnia.

</workflow>

## API

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `GET /api/localo/diagnostics`
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

- `localo`

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API. Jeśli dowody są zagregowane, stare, niepełne albo zablokowane dostępem do źródła danych, powiedz to wprost.

</evidence_requirements>

## Odpowiedź

<output>

Odpowiedź ma być krótka i użyteczna dla operatora: czy Localo działa do
diagnostyki, jakie obszary lokalne są gotowe do review, co trzeba sprawdzić
najpierw, co jest stare/brakujące i jaka decyzja ma zapaść po review.

Widocznie używaj tych sekcji:

- `Czy Localo działa`: dostęp, świeżość odczytu i czy workflow jest review-only.
- `Mapa lokalna`: miejsca/profile, frazy/rankingi, GBP, konkurencja i opinie tylko z metryk WILQ API.
- `Kolejność review`: 3-5 punktów, od których operator ma zacząć, np. średnia widoczność, pozycje w siatce, GBP, konkurencja, recenzje.
- `Braki i blokady`: stare dane, brak `local_tasks`, brak zapisu GBP, brak obietnicy poprawy widoczności/rankingu.
- `Podgląd bez zapisu`: action_id albo review preview, które można sprawdzić w WILQ bez mutacji.
- `Decyzja po review`: po sprawdzeniu operator może odświeżyć Localo, przygotować listę działań lokalnych, odłożyć temat albo zablokować claim.
- `Brief dla marketera`: 3-5 zdań normalnym językiem: co wiemy, co można sprawdzić, czego brakuje i następny bezpieczny krok.

Jeśli API zwraca `operator_summary.review_*`, użyj tych pól jako źródła
`Decyzja po review`, pytania review i następnego bezpiecznego kliknięcia.
To jest karta decyzyjna, nie osobny ActionObject; jako action candidate traktuj
tylko prawdziwe `review_action_ids` albo `action_ids` zwrócone przez WILQ API.

Jeśli `connector.freshness.state` jest `stale` albo notatka mówi `do
odświeżenia`, nie nazywaj odczytu świeżym. Powiedz: "dostęp działa, ale odczyt
jest do odświeżenia" i ustaw odświeżenie Localo jako pierwszy krok przed
finalną oceną.

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
