---
name: wilq-campaign-builder
description: Buduje bezpieczne akcje kampanii Google Ads do sprawdzenia dla Ekologus przez kontrakty WILQ API. Użyj, gdy marketer pyta "stwórz strukturę kampanii", "zaplanuj PMax/Search/Shopping", "przygotuj kampanię na usługę/produkt", "jakie keywords/assets/sitelinki?", "daj podgląd zmian", albo chce strukturę kampanii, plan ad group, pomysły keyword/asset, budżety, targeting lub bezpieczny podgląd zmian. Musi sprawdzać action IDs w WILQ przed zapisem zmian i nie wolno omijać audytu.
---

# WILQ Campaign Builder

## Skill Contract

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed claimami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje evidence, zwróć blocker zamiast wypełniać luki.

</operating_rule>

## Trigger Contract

<triggers>

- "Przygotuj strukturę kampanii Search dla tej usługi Ekologus."
- "Zbuduj draft PMax/Shopping bez zapisu zmian."
- "Jakie assets, keywords i sitelinki możemy przygotować z obecnego evidence?"
- "Pokaż podgląd zmian i ryzyka przed zapisem zmian."

</triggers>

## Workflow Contract

<workflow>

1. Przeczytaj `references/output-contract.md` przed finalną odpowiedzią lub planem działania.
2. Uruchom `uv run python .agents/skills/wilq-campaign-builder/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` przy sprawdzaniu ścieżki skill/API.
3. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-campaign-builder"}` przed podsumowaniem metryk, opportunities lub akcji do sprawdzenia.
4. Endpointów refresh connectorów używaj tylko do jawnych odczytów danych i tylko gdy connector jest skonfigurowany.
5. Sprawdź istniejący action ID przez `POST /api/actions/{action_id}/validate` przed rekomendacją zapisu zmian.
6. Zwracaj identyfikatory: source connector IDs, evidence IDs, opportunity IDs i action IDs wszędzie tam, gdzie API je udostępnia.

</workflow>

## API Contract

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
- `POST /api/connectors/{connector}/refresh` z `mode=vendor_read` tylko wtedy, gdy connector jest skonfigurowany i zadanie jawnie wymaga świeżego odczytu danych.

</allowed_endpoints>

## Evidence Contract

<evidence_requirements>

Wymagane powierzchnie connectorów dla tego skilla:

- `google_ads`
- `google_analytics_4`
- `google_search_console`

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

- Nie wymyślaj metryk, rankingów, liczby produktów, stanu kampanii, spisu treści, dostępów social ani ustaleń Localo.
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj endpointów zapisu zmian, chyba że WILQ API wystawia akcję, sprawdzenie w WILQ przechodzi i użytkownik jawnie prosi o zapis zmian.
- Nie omijaj sprawdzenia w WILQ, evidence IDs ani wymagań audytu.
</safety_rules>
