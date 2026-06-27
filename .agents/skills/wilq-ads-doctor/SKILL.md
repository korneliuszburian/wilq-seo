---
name: wilq-ads-doctor
description: Diagnozuje Google Ads dla Ekologus przez WILQ API evidence i bezpieczne kontrakty akcji. Użyj, gdy marketer pyta "pokaż przestrzeń do polepszenia adsów", "znajdź ostatnie kampanie i ich efekty", "co pali budżet?", "sprawdź wyszukiwane hasła", "czy dodać wykluczające słowa kluczowe?", "czemu kampania nie dowozi?", albo pyta o rekomendacje Ads, jakość kampanii, koszt pozyskania celu, zwrot z reklam, koszt reklam, przegląd kampanii lub sprawdzenie akcji Ads w WILQ. Nie wolno zmyślać Ads metryk ani omijać sprawdzania w WILQ.
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
- "Sprawdź wyszukiwane hasła i przygotuj wykluczające słowa kluczowe, jeśli dowody na to pozwalają."
- "Czy możemy ocenić koszt pozyskania celu, zwrot z reklam albo zmarnowany koszt na podstawie obecnych danych?"

</triggers>

## Workflow Contract

<workflow>

1. Przeczytaj `references/output-contract.md` przed finalną odpowiedzią lub planem działania.
2. Uruchom `uv run python .agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` przy sprawdzaniu ścieżki skill/API.
3. Wywołaj `GET /api/ads/diagnostics` przed diagnozą gotowości Google Ads, zmarnowanego kosztu, wyszukiwanych haseł, jakości kampanii, rekomendacji lub wykluczających słów kluczowych.
4. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-ads-doctor"}` i potwierdź, że `ads_diagnostics` zgadza się z endpointem Ads diagnostics, także opcjonalny `blocked_handoff`, `budget_pacing_read_contract`, `recommendations_read_contract`, `impression_share_read_contract`, `change_history_read_contract`, `search_terms_read_contract`, `search_term_safety_read_contract`, `keyword_match_context_read_contract`, `keyword_planner_read_contract`, `custom_segments_read_contract`, `negative_keywords_read_contract`, ID akcji przeglądu kampanii i action IDs.
5. Endpointów refresh connectorów używaj tylko do jawnych odczytów danych i tylko gdy connector jest skonfigurowany.
6. Sprawdź istniejącą akcję przez `POST /api/actions/{action_id}/validate` przed rekomendacją zapisu zmian.
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
- `POST /api/connectors/{connector}/refresh` z `mode=vendor_read` tylko wtedy, gdy connector jest skonfigurowany i zadanie jawnie wymaga świeżego odczytu danych.

</allowed_endpoints>

## Evidence Contract

<evidence_requirements>

Wymagane powierzchnie connectorów dla tego skilla:

- `google_ads`

Każda rekomendacja musi zawierać source connector IDs i evidence IDs z WILQ API.

Używaj kontraktów z `/api/ads/diagnostics` jako źródła prawdy:

- `status`, `allowed_metrics`, `missing_read_contracts`, `blocked_claims`,
  `action_ids`, pola podglądu zmian i wiersze decyzji mówią, co wolno opisać.
- Gdy kontrakt jest `ready`, streszczaj wyłącznie fakty i metryki wskazane przez
  ten kontrakt. Nie dopowiadaj skutku biznesowego bez osobnego pola kontraktu.
- Gdy kontrakt jest `blocked` albo ma `missing_read_contracts`, pokaż blokadę,
  brakujące dane źródłowe i zablokowane obietnice zamiast tworzyć diagnozę skuteczności.
- akcje do sprawdzenia traktuj jako przygotowanie do sprawdzenia w WILQ, dopóki API nie zwraca
  sprawdzonej w WILQ ścieżki zapisu zmian, podglądu, potwierdzenia i audytu.
- Jeśli `live_data_available=false`, zwróć `blocked_handoff` i nie diagnozuj
  kosztu reklam, kosztu pozyskania celu, zwrotu z reklam, wyszukiwanych haseł,
  zmarnowanego budżetu ani wykluczających słów kluczowych.

</evidence_requirements>

## Output Contract

<output_contract>

Trzymaj się `references/output-contract.md`. Odpowiedź ma być na tyle krótka, żeby operator mógł działać: status, dowody, diagnoza, akcje sprawdzone w WILQ, blokady i następne bezpieczne kroki.

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
