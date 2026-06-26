---
name: wilq-daily-command
description: Uruchamia dzienny polski WILQ operating brief dla Ekologus z WILQ API evidence. Użyj, gdy marketer pyta "co mam dziś zrobić?", "pokaż plan dnia", "gdzie są największe szanse i blockery?", "podsumuj działania z Ads/GA4/GSC/Merchant/Localo", albo chce priorytetowy daily command center. Musi wywołać WILQ API i nie wolno zmyślać metryk.
---

# WILQ Daily Command

## Skill Contract

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed claimami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje evidence, zwróć blocker zamiast wypełniać luki.

</operating_rule>

## Trigger Contract

<triggers>

- "Co dziś powinien zrobić marketer Ekologus?"
- "Pokaż mi dzisiejszy plan działań z WILQ."
- "Gdzie mamy największą przestrzeń do poprawy: Ads, content, feed czy lokal?"
- "Zrób brief dnia dla ekologus.pl z realnych metryk."

</triggers>

## Workflow Contract

<workflow>

1. Przeczytaj `references/output-contract.md` przed finalną odpowiedzią lub planem działania.
2. Uruchom `uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000` przy sprawdzaniu ścieżki skill/API.
3. Wywołaj najpierw `GET /api/dashboard/command-center`. To jest kanoniczny first-screen view model operatora dla polskiego marketera.
4. Wywołaj `GET /api/marketing/brief` dla wspierających daily sections i metric summaries.
5. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-daily-command"}`, żeby pobrać szersze evidence, opportunities, actions, expert rules i knowledge cards.
6. Osadzony w context packu `command_center` jest celowo kompaktowy: użyj `daily_decisions` jako kanonicznej daily decision list i potwierdź zgodność z `GET /api/dashboard/command-center` dla `primary_next_step`, blocker count, tactical item count oraz daily decision trace fields. Nie odbudowuj planu z legacy list `operator_brief` albo `action_plan`.
7. Osadzony `marketing_brief` musi zgadzać się z `GET /api/marketing/brief` dla language, section IDs, blocker count, recommendation count, evidence IDs i action IDs.
8. Daily Command jest core daily loop, nie pełnym registry. Zachowaj kolejność, statusy i `primary_next_step` z WILQ API; nie nadawaj własnego rankingu domen ani nie promuj connector readiness jako zadania marketingowego. Localo i social workflow pokaż tylko wtedy, gdy API zwraca je w `daily_decisions` albo użytkownik jawnie o nie prosi.
9. Endpointów refresh connectorów używaj tylko do jawnych odczytów danych i tylko gdy connector jest skonfigurowany.
10. Sprawdź istniejącą akcję przez `POST /api/actions/{action_id}/validate` przed rekomendacją zapisu zmian.
11. Zwracaj identyfikatory: source connector IDs, evidence IDs, opportunity IDs i action IDs wszędzie tam, gdzie API je udostępnia.

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

## Evidence Contract

<evidence_requirements>

Wymagane powierzchnie connectorów dla tego skilla:

- `google_ads`
- `google_search_console`
- `google_analytics_4`
- `google_merchant_center`
- `ahrefs`
- `localo`
- `wordpress_ekologus`
- `wordpress_sklep`

Każda rekomendacja musi zawierać source connector IDs i evidence IDs z WILQ API. Jeśli evidence jest zagregowane, stare, niepełne albo zablokowane credentialami, powiedz to wprost.

</evidence_requirements>

## Output Contract

<output_contract>

Trzymaj się `references/output-contract.md`. Odpowiedź ma być na tyle krótka, żeby operator mógł działać: status, dowody, diagnoza, akcje sprawdzone w WILQ, blockery i następne bezpieczne kroki.

Kontrakt językowy: wszystkie odpowiedzi dla operatora pisz po polsku z polskimi znakami. API IDs, connector IDs, evidence IDs, opportunity IDs, action IDs, endpoint paths i enum values zostaw bez zmian.

</output_contract>

## Safety Contract

<safety_rules>

<!-- no-invented-metrics guardrail: do not invent metrics. -->
<!-- Polish language contract: operator-facing responses must be in Polish with Polish diacritics. -->

- Nie wymyślaj metryk, rankingów, liczby produktów, stanu kampanii, inventory treści, social permissions ani ustaleń Localo.
- Nie promuj `act_prepare_linkedin_social_drafts` ani `act_prepare_facebook_social_drafts` w daily briefie; to należy do `wilq-social-publisher`.
- Nie promuj Localo jako zadania dnia poza `command_center.daily_decisions`. Jeśli użytkownik pyta o Localo, użyj dedykowanego `wilq-localo-operator`.
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj endpointów zapisu zmian, chyba że WILQ API wystawia akcję, sprawdzenie w WILQ przechodzi i użytkownik jawnie prosi o zapis zmian.
- Nie omijaj sprawdzenia w WILQ, evidence IDs ani wymagań audytu.
</safety_rules>
