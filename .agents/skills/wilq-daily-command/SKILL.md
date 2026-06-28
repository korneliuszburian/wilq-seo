---
name: wilq-daily-command
description: Uruchamia dzienny polski WILQ brief operacyjny dla Ekologus z dowodami z WILQ API. Użyj, gdy marketer pyta "co mam dziś zrobić?", "pokaż plan dnia", "gdzie są największe szanse i blokady?", "podsumuj działania z Ads/GA4/GSC/Merchant/Localo", albo chce priorytetowy dzienny widok Centrum pracy. Musi wywołać WILQ API i nie wolno zmyślać metryk.
---

# WILQ Dzienny plan

## Skill Contract

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Trigger Contract

<triggers>

- "Co dziś powinien zrobić marketer Ekologus?"
- "Pokaż mi dzisiejszy plan działań z WILQ."
- "Gdzie mamy największą przestrzeń do poprawy: Ads, content, feed czy lokal?"
- "Zrób brief dnia dla ekologus.pl z realnych metryk."

</triggers>

## Kontrakt workflow

<workflow>

1. Przeczytaj `references/output-contract.md` przed finalną odpowiedzią lub planem działania.
2. Uruchom `uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000` przy sprawdzaniu ścieżki skill/API.
3. Wywołaj najpierw `GET /api/dashboard/command-center`. To jest kanoniczny first-screen view model operatora dla polskiego marketera.
4. Wywołaj `GET /api/marketing/brief` dla wspierających daily sections i podsumowania metryk.
5. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-daily-command"}`, żeby pobrać szersze dowody, szanse, akcje, reguły eksperckie i karty wiedzy.
6. Osadzony w pakiecie kontekstu `command_center` jest celowo kompaktowy: użyj `daily_decisions` jako kanonicznej listy decyzji dnia i potwierdź zgodność z `GET /api/dashboard/command-center` dla `primary_next_step`, liczby blokad, liczby zadań taktycznych oraz pola śladu decyzji dnia. Nie odbudowuj planu ze starych list `operator_brief` albo `action_plan`.
7. Osadzony `marketing_brief` musi zgadzać się z `GET /api/marketing/brief` dla języka, identyfikatorów sekcji, liczby blokad, liczby rekomendacji, identyfikatorów dowodów i identyfikatorów akcji.
8. Dzienny plan jest główna pętla dnia, nie pełnym rejestrem. Zachowaj kolejność, statusy i `primary_next_step` z WILQ API; nie nadawaj własnego rankingu domen ani nie promuj gotowości źródeł danych jako zadania marketingowego. Localo i social workflow pokaż tylko wtedy, gdy API zwraca je w `daily_decisions` albo użytkownik jawnie o nie prosi.
9. Endpointów refresh źródeł danych używaj tylko do jawnych odczytów danych i tylko gdy źródło danych jest skonfigurowane.
10. Sprawdź istniejącą akcję przez `POST /api/actions/{action_id}/validate` przed rekomendacją zapisu zmian.
11. W podstawowej odpowiedzi używaj polskich podsumowań dowodów i źródeł danych. Techniczne identyfikatory źródeł danych, dowodów, szans i akcji dodawaj tylko jako ślad techniczny, gdy API je udostępnia.

</workflow>

## API Contract

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `GET /api/dashboard/command-center`
- `GET /api/marketing/brief`
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

## Kontrakt dowodów

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

## Kontrakt odpowiedzi

<output_contract>

Trzymaj się `references/output-contract.md`. Odpowiedź ma być na tyle krótka, żeby operator mógł działać: status, dowody, diagnoza, akcje sprawdzone w WILQ, blokady i następne bezpieczne kroki.

Kontrakt językowy: wszystkie odpowiedzi dla operatora pisz po polsku z polskimi znakami. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans, identyfikatory akcji, ścieżki endpointów i wartości enumów zostaw bez zmian.

</output_contract>

## Kontrakt bezpieczeństwa

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
