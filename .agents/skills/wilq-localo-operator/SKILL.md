---
name: wilq-localo-operator
description: Obsługuje workflow Localo i lokalnej widoczności dla Ekologus przez WILQ API readiness i dowody Localo. Użyj, gdy marketer pyta "jak poprawić lokalną widoczność?", "sprawdź Localo/GBP", "które lokalne frazy spadły?", "porównaj widoczność z konkurencją", "zrób lokalny SEO plan", albo pyta o lokalne rankingi, widoczność Google Business Profile, reviews, lokalnych konkurentów, akcji do sprawdzenia GBP post lub blokery dostępu Localo. Nie wolno obiecywać metryk Localo bez WILQ dowodów z WILQ API.
---

# WILQ Localo Operator

## Skill Contract

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed obietnicami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blocker zamiast wypełniać luki.

</operating_rule>

## Trigger Contract

<triggers>

- "Jak poprawić lokalną widoczność Ekologus?"
- "Sprawdź Localo i GBP, ale bez zmyślania rankingów."
- "Czy mamy evidence lokalnych spadków albo konkurencji?"
- "Pokaż blocker Localo i co trzeba zrobić dalej."

</triggers>

## Workflow Contract

<workflow>

1. Przeczytaj `references/output-contract.md` przed finalną odpowiedzią lub planem działania.
2. Uruchom `uv run python .agents/skills/wilq-localo-operator/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` przy sprawdzaniu ścieżki skill/API.
3. Wywołaj `GET /api/localo/diagnostics` przed podsumowaniem metryk, opportunities lub akcji do sprawdzenia.
4. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-localo-operator"}` i potwierdź, że osadzone `localo_diagnostics` zgadza się z endpointem.
5. Endpointów refresh connectorów używaj tylko do jawnych odczytów danych i tylko gdy connector jest skonfigurowany.
6. Sprawdź istniejącą akcję przez `POST /api/actions/{action_id}/validate` przed rekomendacją zapisu zmian.
7. Zwracaj identyfikatory: source connector IDs, evidence IDs, opportunity IDs i action IDs wszędzie tam, gdzie API je udostępnia.

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

- `localo`

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
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj endpointów zapisu zmian, chyba że WILQ API wystawia akcję, sprawdzenie w WILQ przechodzi i użytkownik jawnie prosi o zapis zmian.
- Nie omijaj sprawdzenia w WILQ, evidence IDs ani wymagań audytu.
</safety_rules>
