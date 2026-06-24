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
4. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-ads-doctor"}` i potwierdź, że `ads_diagnostics` zgadza się z endpointem Ads diagnostics, także opcjonalny `blocked_handoff`, `budget_pacing_read_contract`, `recommendations_read_contract`, `impression_share_read_contract`, `change_history_read_contract`, `search_terms_read_contract`, `search_term_safety_read_contract`, `keyword_match_context_read_contract`, `keyword_planner_read_contract`, `custom_segments_read_contract`, `negative_keywords_read_contract`, campaign review ActionObject i ActionObject IDs.
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
- `POST /api/connectors/{connector}/refresh` z `mode=vendor_read` tylko wtedy, gdy connector jest skonfigurowany i zadanie jawnie wymaga świeżego read.

</allowed_endpoints>

## Evidence Contract

<evidence_requirements>

Wymagane powierzchnie connectorów dla tego skilla:

- `google_ads`

Każda rekomendacja musi zawierać source connector IDs i evidence IDs z WILQ API.

Używaj typed contracts z `/api/ads/diagnostics` jako źródła prawdy:

- `status`, `allowed_metrics`, `missing_read_contracts`, `blocked_claims`,
  `action_ids`, `payload_preview` i decision rows mówią, co wolno opisać.
- Gdy kontrakt jest `ready`, streszczaj wyłącznie fakty i metryki wskazane przez
  ten kontrakt. Nie dopowiadaj skutku biznesowego bez osobnego contract field.
- Gdy kontrakt jest `blocked` albo ma `missing_read_contracts`, pokaż blocker,
  brakujące kontrakty i blocked claims zamiast tworzyć diagnozę performance.
- ActionObjects traktuj jako prepare/review-only, dopóki API nie zwraca
  zwalidowanego apply support, payload preview, confirm i audit boundary.
- Jeśli `live_data_available=false`, zwróć `blocked_handoff` i nie diagnozuj
  spend, CPA, ROAS, search terms, wasted budget ani negative keywords.

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
