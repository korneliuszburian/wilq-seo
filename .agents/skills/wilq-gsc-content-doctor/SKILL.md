---
name: wilq-gsc-content-doctor
description: Zamienia dowody Google Search Console dla Ekologus w SEO/content diagnostics przez WILQ API. Użyj, gdy marketer pyta "które strony odświeżyć?", "gdzie mamy dużo wyświetlenia i niski CTR?", "jakie query tracą kliknięcia?", "co poprawić w treściach SEO?", "które strony scalić/utworzyć/odświeżyć/zablokować?", albo pyta o zapytania, strony, CTR, wyświetlenia, pozycje, spadek efektów treści, szanse blisko topu, przepisanie treści lub szanse SEO. Musi zwracać identyfikatory dowodów i nie wolno zmyślać metryk wyszukiwania.
---

# WILQ Treści z GSC

## Zasada skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Które treści na ekologus.pl odświeżyć najpierw?"
- "Znajdź query z dużymi wyświetlenia i słabym CTR."
- "Pokaż SEO szanse z GSC i WordPress inventory."
- "Czy mamy kanibalizację albo strony do merge?"

</triggers>

## Workflow operatora

<workflow>

1. Wywołaj `GET /api/content/diagnostics` przed podsumowaniem metryk SEO i treści albo zadań kolejki lub akcji do sprawdzenia.
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
- `GET /api/content/diagnostics`
- `GET /api/marketing/brief`
- `GET /api/marketing/tactical-queue`
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

- `google_search_console`
- `wordpress_ekologus`
- `wordpress_sklep`

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API. Jeśli dowody są zagregowane, stare, niepełne albo zablokowane dostępem do źródła danych, powiedz to wprost.

</evidence_requirements>

## Odpowiedź

<output>

Odpowiedź ma być krótka i użyteczna dla operatora: wybór strony lub tematu,
powód, tryb decyzji, ręczny check strony, blokady i następne bezpieczne kroki.
Traktuj ją jak kartę review gotową do pokazania Wilkowi bez dopisku od
developera: po pierwszych 30 sekundach ma być jasne, którą stronę sprawdzić,
dlaczego teraz, jakie pytanie ma odpowiedzieć Wilku i który podgląd można
bezpiecznie kliknąć bez zapisu ani publikacji.

Zaczynaj od widocznej decyzji operatorskiej, nie od surowych pól API:

- `Można zrobić teraz`: jedna bezpieczna decyzja lub akcja do sprawdzenia.
- `Dlaczego`: jednozdaniowe streszczenie dowodów, np. GSC wskazuje sygnał, a WordPress potwierdza istniejący adres.
- `Mapa decyzji`: nazwij tryb `odświeżyć`, `scalić`, `utworzyć` albo `zablokować`, wskaż URL/temat i powiedz, czy to decyzja gotowa do review, czy tylko sygnał z GSC.
- `Co sprawdzić ręcznie`: użyj dokładnie tej etykiety i dodaj krótką checklistę intencji zapytań, nagłówków/CTA, kanibalizacji i decyzji odświeżyć vs scalić.
- `Jak sprawdzić na stronie`: podaj 3-5 konkretnych miejsc do obejrzenia: title/meta, H1/H2, sekcje brakujące wobec intencji, CTA/usługa, canonical/linkowanie wewnętrzne.
- `Brief do pokazania Wilkowi`: 3-5 zdań normalnym językiem: co WILQ proponuje, z jakich dowodów, czego nie wolno jeszcze obiecać i jaka jest decyzja review.
- `Karta decyzji dla Wilka`: na końcu dopisz krótką kartę z trzema polami:
  `Decyzja po review`, `Pytanie do Wilka` i `Następny bezpieczny klik`.
  Karta ma mówić, czy po ręcznym sprawdzeniu marketer ma zatwierdzić
  odświeżenie, scalenie, zmianę briefu albo blokadę tematu. Nie może obiecywać
  publikacji, wzrostu SEO ani zapisu WordPress.
  Jeśli API zwraca `marketer_decision.review_*`, użyj tych pól jako źródła
  karty. To jest notatka decyzyjna dla Wilka, nie osobny ActionObject; jako
  action candidate traktuj tylko prawdziwe `review_action_ids` lub `action_ids`
  zwrócone przez WILQ API.
- `Zablokowane`: co nie jest jeszcze gotową decyzją publikacyjną i dlaczego.

Nie pokazuj marketerowi surowych markerów typu `partial_possible` jako uzasadnienia. Tłumacz je normalnie: "dane są częściowe, więc to sygnał do ręcznej oceny, nie gotowa decyzja publikacyjna". Surowe markery, endpointy i identyfikatory trzymaj w śladzie technicznym.

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
