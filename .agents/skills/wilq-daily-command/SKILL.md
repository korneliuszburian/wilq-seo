---
name: wilq-daily-command
description: Uruchamia dzienny polski WILQ brief operacyjny dla Ekologus z dowodami z WILQ API. Użyj, gdy marketer pyta "co mam dziś zrobić?", "pokaż plan dnia", "gdzie są największe szanse i blokady?", "podsumuj działania z Ads/GA4/GSC/Merchant/Localo", albo chce priorytetowy dzienny widok Centrum pracy. Musi wywołać WILQ API i nie wolno zmyślać metryk.
---

# WILQ Dzienny plan

## Zasada skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Co dziś powinien zrobić marketer Ekologus?"
- "Pokaż mi dzisiejszy plan działań z WILQ."
- "Gdzie mamy największą przestrzeń do poprawy: Ads, treści, plik produktowy czy lokal?"
- "Zrób brief dnia dla ekologus.pl z realnych metryk."

</triggers>

## Workflow operatora

<workflow>

1. Wywołaj najpierw `GET /api/dashboard/command-center`. To jest kanoniczny first-screen view model operatora dla polskiego marketera.
2. Pobierz także `GET /api/marketing/daily-check`; jego typed status, freshness, blokady, evidence IDs, source connectors, expert rule IDs i safe next steps są API-owned źródłem znaczenia rekomendacji.
3. Jeśli potrzebujesz krótkiego tła metryk, pobierz `GET /api/marketing/brief`; nie zastępuj nim kolejki dnia.
3. Odpowiedz jak poranny operator: co zrobić najpierw, dlaczego teraz, jakie są dowody, co jest zablokowane i jaki jest następny bezpieczny krok.
4. `POST /api/codex/context-pack` pobieraj tylko wtedy, gdy te dwa endpointy nie wystarczają albo użytkownik pyta o wiele powierzchni naraz.
5. Dzienny plan jest główną pętlą dnia, nie pełnym rejestrem. Zachowaj kolejność, statusy i `primary_next_step` z WILQ API; nie nadawaj własnego rankingu domen.
6. Endpointów refresh źródeł danych używaj tylko do jawnych odczytów danych i tylko gdy źródło danych jest skonfigurowane.
7. Jeśli użytkownik prosi o zapis albo podgląd zmiany, użyj `POST /api/actions/{action_id}/validate`; w review-only odpowiedzi wystarczy wskazać action_id i bezpieczny następny krok.
8. Techniczne identyfikatory dodawaj tylko jako ślad techniczny, gdy pomagają sprawdzić decyzję.

</workflow>

## API

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `GET /api/dashboard/command-center`
- `GET /api/marketing/brief`
- `GET /api/marketing/daily-check`
- `POST /api/codex/context-pack`
- `GET /api/connectors`
- `GET /api/connectors/{connector}/status`
- `GET /api/connectors/{connector}/refresh-runs`
- `GET /api/connectors/refresh-runs`
- `GET /api/evidence`
- `GET /api/opportunities`
- `GET /api/actions`
- `GET /api/actions/{action_id}`
- `POST /api/actions/{action_id}/validate`
- `POST /api/connectors/{connector}/refresh` z `mode=vendor_read` dla jawnie żądanych odczytów danych.
- `GET /api/knowledge/cards`
- `GET /api/expert/rules`
- `GET /api/expert/capabilities`

</allowed_endpoints>

## Dowody

<evidence_requirements>

Wymagane powierzchnie źródeł danych dla tego skilla:

- `google_ads`
- `google_search_console`
- `google_analytics_4`
- `google_merchant_center`
- `ahrefs`
- `localo`
- `wordpress_ekologus`
- `wordpress_sklep`

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
<!-- Polish language contract: operator-facing responses must be in Polish with Polish diacritics. -->

- Nie wymyślaj metryk, rankingów, liczby produktów, stanu kampanii, spisu treści, dostępów social ani ustaleń Localo.
- Nie promuj `act_prepare_linkedin_social_drafts` ani `act_prepare_facebook_social_drafts` w briefie dnia; to należy do `wilq-social-publisher`.
- Nie promuj Localo jako zadania dnia poza `command_center.daily_decisions`. Jeśli użytkownik pyta o Localo, użyj dedykowanego `wilq-localo-operator`.
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj endpointów zapisu zmian, chyba że WILQ API wystawia akcję, sprawdzenie w WILQ przechodzi i użytkownik jawnie prosi o zapis zmian.
- Nie omijaj sprawdzenia w WILQ, identyfikatorów dowodów ani wymagań audytu.
</safety_rules>
