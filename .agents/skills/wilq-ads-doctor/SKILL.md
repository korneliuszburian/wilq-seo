---
name: wilq-ads-doctor
description: Diagnozuje Google Ads dla Ekologus przez WILQ API evidence i bezpieczne kontrakty ActionObject. Użyj, gdy marketer pyta "pokaż przestrzeń do polepszenia adsów", "znajdź ostatnie kampanie i ich efekty", "co pali budżet?", "sprawdź search terms", "czy dodać negative keywords?", "czemu kampania nie dowozi?", albo pyta o rekomendacje Ads, jakość kampanii, CPA/ROAS/spend, campaign review lub walidację Ads ActionObject. Nie wolno zmyślać Ads metryk ani omijać walidacji ActionObject.
---

# WILQ Ads Doctor

## Skill Contract

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed claimami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje evidence, zwróć blocker zamiast wypełniać luki.

</operating_rule>

## Trigger Contract

<triggers>

- "Pokaż mi przestrzeń do polepszenia adsów w Ekologus."
- "Znajdź ostatnie kampanie i ich efekty."
- "Co teraz pali budżet w Google Ads?"
- "Sprawdź search terms i przygotuj negative keywords, jeśli evidence na to pozwala."
- "Czy możemy ocenić CPA, ROAS albo wasted spend na podstawie obecnych danych?"

</triggers>

## Workflow Contract

<workflow>

1. Przeczytaj `references/output-contract.md` przed finalną odpowiedzią lub planem działania.
2. Uruchom `uv run python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` przy walidacji ścieżki skill/API.
3. Wywołaj `GET /api/ads/diagnostics` przed diagnozą gotowości Google Ads, wasted spend, search terms, jakości kampanii, rekomendacji lub negative keywords.
4. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-ads-doctor"}` i potwierdź, że `ads_diagnostics` zgadza się z endpointem Ads diagnostics, także opcjonalny `blocked_handoff`, `budget_pacing_read_contract`, `recommendations_read_contract`, `search_terms_read_contract`, `negative_keywords_read_contract`, campaign review ActionObject i ActionObject IDs.
5. Endpointów refresh connectorów używaj tylko do jawnych read-only refreshy i tylko gdy connector jest skonfigurowany.
6. Zwaliduj istniejący ActionObject przez `POST /api/actions/{action_id}/validate` przed rekomendacją apply/execution.
7. Zwracaj identyfikatory: source connector IDs, evidence IDs, opportunity IDs i action IDs wszędzie tam, gdzie API je udostępnia.

</workflow>

## API Contract

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
- `POST /api/connectors/{connector}/refresh with mode=vendor_read only when the connector is configured and the task explicitly needs a fresh read.`

</allowed_endpoints>

## Evidence Contract

<evidence_requirements>

Wymagane powierzchnie connectorów dla tego skilla:

- `google_ads`

Każda rekomendacja musi zawierać source connector IDs i evidence IDs z WILQ API. Jeśli `/api/ads/diagnostics` zwraca `live_data_available=false`, zwróć `blocked_handoff`, OAuth/API blocker i blocked claims zamiast diagnozować spend, CPA, ROAS, search terms lub negative keywords. Jeśli `budget_pacing_read_contract.status=ready`, wolno opisać koszt z 7 dni względem budżetu dziennego jako kontekst review; nie wolno rekomendować skalowania, pauzowania ani apply budżetu bez historii zmian, impression share, celu biznesowego, preview i walidacji ActionObject. Jeśli `recommendations_read_contract.status=ready`, wolno opisać typy Google Ads recommendations jako input do review; nie wolno ich automatycznie przyjmować, odrzucać ani claimować poprawy performance. Jeśli `act_prepare_ads_campaign_review_queue` istnieje, traktuj go wyłącznie jako prepare-only kolejkę review kampanii. Jeśli `negative_keywords_read_contract.status=ready`, traktuj kandydatów wyłącznie jako kolejkę review/safety; nie claimuj waste i nie rekomenduj apply bez walidacji ActionObject.

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
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj write/apply endpoints, chyba że WILQ API wystawia action, walidacja przechodzi i użytkownik jawnie prosi o wykonanie.
- Nie omijaj walidacji ActionObject, evidence IDs ani wymagań audytu.
</safety_rules>
