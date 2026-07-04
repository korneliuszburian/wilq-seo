# WILQ Strateg treści Kontrakt odpowiedzi

## Cel

Planowanie treści z dowodów WILQ API, istniejącego spisu treści i kart wiedzy.

Oczekiwany wynik: priorytetowy plan treści z identyfikatorami dowodów, identyfikatory źródeł danych, kontrolą istniejących treści i akcjami do sprawdzenia.

## Wymagany kontekst API

Najpierw pobierz `GET /api/content/diagnostics`. Następnie pobierz `POST /api/codex/context-pack` z `{"skill":"wilq-content-strategist"}` i potwierdź, że istnieje osadzone `content_diagnostics`. Użyj `GET /api/connectors/{connector}/status` dla każdego wymaganego źródła danych, gdy gotowość ma znaczenie.

Wymagane źródła danych:

- `google_search_console`
- `google_analytics_4`
- `ahrefs`
- `wordpress_ekologus`
- `wordpress_sklep`

## Kształt odpowiedzi

Zwracaj te sekcje, gdy użytkownik uruchamia ten skill:

Kontrakt językowy: odpowiadaj marketerowi Ekologus po polsku z polskimi znakami. Zacznij od decyzji contentowej, nie od raportu pól API. Widoczna odpowiedź musi zawierać polskie etykiety: `Można zrobić teraz`, `Dlaczego`, `Mapa decyzji`, `Co sprawdzić w briefie`, `Brief do pokazania Wilkowi` i `Zablokowane do czasu dowodów`. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans i identyfikatory akcji zostaw bez zmian.


1. `Można zrobić teraz`: najważniejsza decyzja contentowa i akcja do sprawdzenia.
2. `Dlaczego`: jednozdaniowy dowód łączący źródła, np. istniejący URL w WordPress + sygnał GSC + wniosek "odświeżyć/scalić, nie tworzyć od zera".
3. `Mapa decyzji`: rozdziel co idzie jako odświeżyć/scalić, co zostaje do ręcznej oceny i czego nie pisać bez dowodów.
4. `Co sprawdzić w briefie`: intencja, odbiorca, obiekcje, H1/H2/FAQ, CTA, kanibalizacja, aktualność prawna i Claim Ledger.
5. `Brief do pokazania Wilkowi`: krótki pakiet review: rekomendowany tryb, źródła, kąt treści, odbiorca, CTA, ryzyka duplikacji i zablokowane twierdzenia.
6. `Zablokowane do czasu dowodów`: tematy bez bezpośredniego wiersza dowodowego, finalny draft, publikacja WordPress i obietnice efektu.
7. `Ślad techniczny`: tactical queue item IDs, identyfikatory szans, identyfikatory akcji, identyfikatory dowodów i wynik wymaganego sprawdzenia w WILQ.

W ustrukturyzowanym JSON eval albo handoffie etykiety `Mapa decyzji` i `Brief do pokazania Wilkowi` muszą pojawić się w widocznych polach decyzyjnych, np. w `operator_next_step`, `recommendations[].label_pl` albo `action_candidates[].label_pl`. Nie wystarczy wrzucić ich do `notes`.

## Kolejka decyzji

Użyj `content_diagnostics.decision_queue` z WILQ API jako kanonicznej kolejki
treści. Skill nie powinien sam klasyfikować adresów ani przepisywać reguł
deduplikacji z promptu.

## Warunki odmowy lub obniżenia do blokady

Odmów albo obniż odpowiedź do raportu blokady, gdy:

- WILQ API jest niedostępne.
- Wymagane źródło danych ma status `missing_credentials`, `disabled` albo niepowodzenie dla żądanej operacji.
- Żądana metryka albo akcja nie występuje w pakiecie kontekstu, dowodach, odczytach źródeł danych, regułach eksperckich ani akcjach do sprawdzenia.
- `content_diagnostics.live_data_available=false`, a użytkownik prosi o plan treści zamiast statusu gotowości/blokady.
- Użytkownik prosi o zapis zmian bez akcji do sprawdzenia w WILQ i jawnej zgody.

## Reguły dowodów

Brak identyfikatora dowodu oznacza brak rekomendacji. Brak źródła danych oznacza brak rekomendacji. Brak akcji do sprawdzenia w WILQ oznacza brak zapisu zmian. Brak zdarzenia audytu oznacza brak zapisu zmian.

## Bezpieczeństwo treści

Używaj `act_prepare_content_refresh_queue` wyłącznie jako przygotowanie bez zapisu. Skill może sugerować planowanie refresh/create/merge/block i podgląd zmian, ale nie może obiecywać edycji WordPress, publikacji, wzrostu pozycji, wzrostu leadów ani gwarancji braku duplikacji bez sprawdzonej w WILQ ścieżki zapisu zmian i audytu.
