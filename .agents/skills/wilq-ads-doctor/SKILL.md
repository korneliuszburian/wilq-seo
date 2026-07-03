---
name: wilq-ads-doctor
description: Diagnozuje Google Ads dla Ekologus z dowodami z WILQ API i bezpieczne akcje do sprawdzenia. Użyj, gdy marketer pyta "pokaż przestrzeń do polepszenia adsów", "znajdź ostatnie kampanie i ich efekty", "co pali budżet?", "sprawdź wyszukiwane hasła", "czy dodać wykluczające słowa kluczowe?", "czemu kampania nie dowozi?", albo pyta o rekomendacje Ads, jakość kampanii, koszt pozyskania celu, zwrot z reklam, koszt reklam, przegląd kampanii lub sprawdzenie akcji Ads w WILQ. Nie wolno zmyślać Ads metryk ani omijać sprawdzania w WILQ.
---

# WILQ widok Google Ads

## Zasada skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Pokaż mi przestrzeń do polepszenia adsów w Ekologus."
- "Znajdź ostatnie kampanie i ich efekty."
- "Co teraz pali budżet w Google Ads?"
- "Sprawdź wyszukiwane hasła i przygotuj wykluczające słowa kluczowe, jeśli dowody na to pozwalają."
- "Czy możemy ocenić koszt pozyskania celu, zwrot z reklam albo zmarnowany koszt na podstawie obecnych danych?"

</triggers>

## Workflow operatora

<workflow>

1. Wywołaj `GET /api/ads/diagnostics` przed diagnozą gotowości Google Ads, zmarnowanego kosztu, wyszukiwanych haseł, jakości kampanii, rekomendacji lub wykluczających słów kluczowych.
2. Pobierz `POST /api/codex/context-pack` tylko gdy wąski endpoint nie wystarcza albo potrzebujesz kontekstu wielu powierzchni. Nie rób z tego obowiązkowego kroku.
3. Gdy użytkownik pyta szeroko o całą kolejkę Ads, czyli budżety, rekomendacje, wskaźniki kampanii, wyszukiwane hasła, wykluczenia i segmenty niestandardowe naraz, pobierz też `POST /api/codex/context-pack` z `{"skill":"wilq-ads-doctor","full_context":true}` albo użyj pełnego `GET /api/ads/diagnostics` jako kompletnej kolejki decyzji. Domyślny context-pack może być skompaktowany i nie wolno go przedstawiać jako pełnej kolejki, jeśli ma mniej decyzji niż `/api/ads/diagnostics`.
4. Jeśli ostatni odczyt Google Ads jest stary albo connector status wskazuje stale/requires_refresh, uruchom read-only refresh `POST /api/connectors/google_ads/refresh` z `mode=vendor_read`, o ile źródło danych jest skonfigurowane i użytkownik pyta o aktualny stan. Jeżeli refresh nie jest możliwy, zacznij odpowiedź od blokady świeżości i nie dawaj decyzji operacyjnych na podstawie starego snapshotu.
5. Jeśli użytkownik prosi o zapis albo podgląd zmiany, użyj `POST /api/actions/{action_id}/validate`; w review-only odpowiedzi wystarczy wskazać action_id i bezpieczny następny krok.
6. W podstawowej odpowiedzi używaj polskich podsumowań dowodów i źródeł danych. Techniczne identyfikatory źródeł danych, dowodów, szans i akcji dodawaj tylko jako ślad techniczny, gdy API je udostępnia.

</workflow>

## API

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `POST /api/codex/context-pack`
- `GET /api/ads/diagnostics`
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

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API.

Używaj pól z `/api/ads/diagnostics` jako źródła prawdy:

- `status`, `allowed_metrics`, `missing_read_contracts`, `blocked_claims`,
  `action_ids`, pola podglądu zmian i wiersze decyzji mówią, co wolno opisać.
- Gdy status odczytu jest `ready`, streszczaj wyłącznie fakty i metryki wskazane przez
  te pola. Nie dopowiadaj skutku biznesowego bez osobnego pola API.
- Gdy status odczytu jest `blocked` albo ma `missing_read_contracts`, pokaż blokadę,
  brakujące dane źródłowe i zablokowane obietnice zamiast tworzyć diagnozę skuteczności.
- akcje do sprawdzenia traktuj jako przygotowanie do sprawdzenia w WILQ, dopóki API nie zwraca
  sprawdzonej w WILQ ścieżki zapisu zmian, podglądu, potwierdzenia i audytu.
- Jeśli `live_data_available=false`, zwróć `blocked_handoff` i nie diagnozuj
  kosztu reklam, kosztu pozyskania celu, zwrotu z reklam, wyszukiwanych haseł,
  zmarnowanego budżetu ani wykluczających słów kluczowych.

</evidence_requirements>

## Odpowiedź

<output>

Odpowiedź ma być krótka i użyteczna dla operatora: status, dowody, diagnoza, akcje do sprawdzenia w WILQ, blokady i następne bezpieczne kroki.

Szerokie pytania Ads odpowiadaj jak operator, nie jak eksport diagnostyki: najpierw 3-5 priorytetów review, potem najważniejsze blokady, a pełne listy decyzji/metryk streszczaj tylko wtedy, gdy użytkownik o nie prosi. Nie wypisuj wszystkich pól API, jeżeli nie zmieniają kolejności działania.

Widoczne odpowiedzi układaj w prosty schemat:

- `Można zrobić teraz`: 3-5 pozycji review w kolejności działania, np. kampanie i budżety, rekomendacje, wyszukiwane hasła, wykluczenia, segmenty.
- `Jak sprawdzić`: przy każdej pozycji podaj jedno konkretne pytanie kontrolne albo kryterium decyzji, które Wilku ma sprawdzić po wejściu w `/ads-doctor`.
- `Dlaczego teraz`: jednozdaniowy dowód, np. odczyt Google Ads jest dostępny i WILQ ma kolejkę decyzji do ręcznej oceny.
- `Decyzja po review`: co może być następną bezpieczną decyzją po ręcznym sprawdzeniu, np. przygotować listę pytań, zostawić do obserwacji, odrzucić rekomendację, poprosić o brakujący kontrakt albo dopiero wtedy przejść do preview akcji.
- `Zablokowane`: czego nie wolno twierdzić ani zapisać bez brakujących dowodów lub zgody.
- `Ślad techniczny`: identyfikatory dowodów, akcji, raw kontrakty i nazwy pól API.

Jeżeli odpowiadasz w ustrukturyzowanym JSON eval albo krótkim handoffie, widoczne pola decyzyjne (`operator_next_step`, `recommendations[].label_pl`, `action_candidates[].label_pl`) muszą nadal zawierać etykiety `Jak sprawdzić` i `Decyzja po review`, a nie tylko ogólną listę priorytetów.

Nie pokazuj marketerowi surowych markerów typu `latest_refresh_status`, `live_data_available`, `target_roas_or_cpa`, `human_strategy_review`, `keyword_planner_enrichment` albo `forecast_or_audience_size`. Tłumacz je normalnie: "odczyt jest dostępny", "brakuje celu kosztu pozyskania albo zwrotu z reklam lub strategii człowieka", "brakuje wzbogacenia Keyword Planner albo prognozy rozmiaru odbiorców". Surowe wartości zostaw w `notes`.

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
