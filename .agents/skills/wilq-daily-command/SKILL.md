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
2. Uruchom `uv run python .agents/skills/wilq-daily-command/scripts/smoke_context_pack.py --api-base http://127.0.0.1:8000` przy walidacji ścieżki skill/API.
3. Wywołaj najpierw `GET /api/dashboard/command-center`. To jest kanoniczny first-screen view model operatora dla polskiego marketera.
4. Wywołaj `GET /api/marketing/brief` dla wspierających daily sections i metric summaries.
5. Call `POST /api/codex/context-pack` with `{"skill":"wilq-daily-command"}` to get wider evidence, opportunities, actions, expert rules and knowledge cards.
6. The `command_center` embedded in the context pack is compact by design: use `daily_decisions` as the canonical daily decision list and verify it agrees with `GET /api/dashboard/command-center` on `primary_next_step`, blocker count, tactical item count and daily decision trace fields. Do not rebuild the plan from legacy `operator_brief` or `action_plan` lists.
7. The embedded `marketing_brief` must agree with `GET /api/marketing/brief` on language, section IDs, blocker count, recommendation count, evidence IDs and action IDs.
8. Daily Command jest core daily loop, nie pełnym registry. Priorytetyzuj Merchant, Content/GSC/WordPress, GA4 i Ads. Localo pokazuj tylko jako realny blocker albo ograniczenie claimów, nie jako gotowe zadanie dnia bez lokalnych ranking/GBP facts. Social draft ActionObjects pomiń, chyba że użytkownik jawnie prosi o social workflow.
9. Endpointów refresh connectorów używaj tylko do jawnych read-only refreshy i tylko gdy connector jest skonfigurowany.
10. Zwaliduj istniejący ActionObject przez `POST /api/actions/{action_id}/validate` przed rekomendacją apply/execution.
11. Zwracaj identyfikatory: source connector IDs, evidence IDs, opportunity IDs i action IDs wszędzie tam, gdzie API je udostępnia.

</workflow>

## API Contract

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `GET /api/dashboard/command-center`
- `GET /api/marketing/brief`
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
- `POST /api/connectors/{connector}/refresh with mode=vendor_read for explicitly requested read-only refreshes.`
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

Trzymaj się `references/output-contract.md`. Odpowiedź ma być na tyle krótka, żeby operator mógł działać: status, dowody, diagnoza, zwalidowani kandydaci działań, blockery i następne bezpieczne kroki.

Kontrakt językowy: wszystkie odpowiedzi dla operatora pisz po polsku z polskimi znakami. API IDs, connector IDs, evidence IDs, opportunity IDs, ActionObject IDs, endpoint paths i enum values zostaw bez zmian.

</output_contract>

## Safety Contract

<safety_rules>

<!-- no-invented-metrics guardrail: do not invent metrics. -->
<!-- Polish language contract: operator-facing responses must be in Polish with Polish diacritics. -->

- Nie wymyślaj metryk, rankingów, liczby produktów, stanu kampanii, inventory treści, social permissions ani ustaleń Localo.
- Nie promuj `act_prepare_linkedin_social_drafts` ani `act_prepare_facebook_social_drafts` w daily briefie; to należy do `wilq-social-publisher`.
- Nie promuj Localo readiness jako zadania dnia, jeśli WILQ nie ma Localo ranking/GBP evidence. W daily briefie Localo może być blockerem albo blocked claim.
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj write/apply endpoints, chyba że WILQ API wystawia action, walidacja przechodzi i użytkownik jawnie prosi o wykonanie.
- Nie omijaj walidacji ActionObject, evidence IDs ani wymagań audytu.
</safety_rules>
