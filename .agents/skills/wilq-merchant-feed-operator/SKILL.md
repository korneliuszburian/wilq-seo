---
name: wilq-merchant-feed-operator
description: Analizuje Merchant Center product/feed evidence dla Ekologus przez WILQ API i przygotowuje bezpieczną kolejkę sprawdzenia problemów feedu. Użyj, gdy marketer pyta "czy feed produktowy jest OK?", "które produkty mają problemy?", "co blokuje Shopping/PMax produkty?", "sprawdź disapproved products", "przygotuj kolejkę przeglądu problemów feedu", albo pyta o diagnostykę Merchant, ryzyka widoczności produktów, feed edits, issue types, affected attributes, availability, prices, GTIN/images lub product approvals. Nie wolno zmieniać danych produktu bez akcji sprawdzonych w WILQ i audytu.
---

# WILQ Merchant Feed Operator

## Skill Contract

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed claimami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje evidence, zwróć blocker zamiast wypełniać luki.

</operating_rule>

## Trigger Contract

<triggers>

- "Czy feed produktowy Ekologus/sklep.ekologus.pl jest zdrowy?"
- "Pokaż problemy produktów w Merchant Center."
- "Co może blokować widoczność produktów w Shopping/PMax?"
- "Przygotuj bezpieczną kolejkę sprawdzenia problemów feedu."

</triggers>

## Workflow Contract

<workflow>

1. Przeczytaj `references/output-contract.md` przed finalną odpowiedzią lub planem działania.
2. Uruchom `uv run python .agents/skills/wilq-merchant-feed-operator/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` przy sprawdzaniu ścieżki skill/API.
3. Wywołaj `GET /api/merchant/diagnostics` przed podsumowaniem zdrowia feedu/produktów, issue queue lub akcji do sprawdzenia produktowych.
4. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-merchant-feed-operator"}` i potwierdź, że `merchant_diagnostics` zgadza się z endpointem Merchant diagnostics.
5. Endpointów refresh connectorów używaj tylko do jawnych odczytów danych i tylko gdy connector jest skonfigurowany.
6. Sprawdź istniejącą akcję przez `POST /api/actions/{action_id}/validate` przed rekomendacją zapisu zmian.
7. Zwracaj identyfikatory: source connector IDs, evidence IDs, opportunity IDs i action IDs wszędzie tam, gdzie API je udostępnia.
8. Dla pytań o aktualny stan feedu użyj `freshness_assessment`: `requires_refresh=true` albo `state=stale|missing|blocked` oznacza nieaktualne dane albo blocker, chyba że użytkownik jawnie pozwala na odczyt danych connectora.
9. Finalną kolejkę pracy grupuj po `decision_queue`. `issue_clusters` traktuj jako drilldown raportowy; `product_count` przy `count_semantics=reported_issue_occurrences` nie jest liczbą unikalnych SKU ani produktów.

</workflow>

## API Contract

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `POST /api/codex/context-pack`
- `GET /api/merchant/diagnostics`
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
- `POST /api/connectors/{connector}/refresh` z `mode=vendor_read` tylko wtedy, gdy connector jest skonfigurowany i zadanie jawnie wymaga świeżego odczytu danych.

</allowed_endpoints>

## Evidence Contract

<evidence_requirements>

Wymagane powierzchnie connectorów dla tego skilla:

- `google_merchant_center`

Każda rekomendacja musi zawierać source connector IDs i evidence IDs z WILQ API. Merchant Diagnostics sections i tactical items traktuj jako główne źródło. Jeśli evidence jest zagregowane, stare, niepełne albo zablokowane credentialami, powiedz to wprost.

Jeśli `/api/merchant/diagnostics` zwraca `unknowns`, `product_sample_readiness.status=blocked`, `product_performance_readiness.status=blocked` albo `price_impact_readiness.status=blocked`, odpowiedź musi mieć sekcję "Czego nie wiemy" i nie może udawać kolejki produkt-po-produkcie, zwrotu z reklam na poziomie produktu, wpływu ceny ani wpływu naprawy na przychód.

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
