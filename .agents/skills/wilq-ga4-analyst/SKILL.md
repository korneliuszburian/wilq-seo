---
name: wilq-ga4-analyst
description: Analizuje zachowanie GA4 dla Ekologus przez WILQ API evidence. Użyj, gdy marketer pyta "które landing pages działają słabo?", "czy ruch z kampanii ma sens?", "czemu użytkownicy nie angażują się?", "czy tracking jest zepsuty?", "porównaj źródła ruchu", albo pyta o engagement, sessions, jakość campaign/source, conversion diagnostics lub tracking gaps. Musi cytować GA4 evidence IDs i nie wolno zmyślać wartości analytics.
---

# WILQ GA4 Analyst

## Skill Contract

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed claimami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje evidence, zwróć blocker zamiast wypełniać luki.

</operating_rule>

## Trigger Contract

<triggers>

- "Które landing pages w Ekologus są najsłabsze?"
- "Sprawdź jakość ruchu z kampanii i źródeł."
- "Czy GA4 pokazuje problem marketingowy czy problem pomiaru?"
- "Znajdź tracking gaps, zanim ocenimy kampanie."

</triggers>

## Workflow Contract

<workflow>

1. Przeczytaj `references/output-contract.md` przed finalną odpowiedzią lub planem działania.
2. Uruchom `uv run python .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` przy walidacji ścieżki skill/API.
3. Wywołaj `GET /api/ga4/diagnostics` przed podsumowaniem GA4 behavior, jakości landingów, conversion readiness lub tracking blockers.
4. Użyj `ga4_diagnostics.decision_queue` jako głównej kolejki decyzji: `fix_measurement`, `review_landing_mapping`, `review_traffic_quality`.
5. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-ga4-analyst"}` i potwierdź, że osadzony kontrakt `ga4_diagnostics` zgadza się z route.
6. Endpointów refresh connectorów używaj tylko do jawnych read-only refreshy i tylko gdy connector jest skonfigurowany.
7. Zwaliduj istniejący ActionObject przez `POST /api/actions/{action_id}/validate` przed rekomendacją apply/execution.
8. Zwracaj identyfikatory: source connector IDs, evidence IDs, opportunity IDs i action IDs wszędzie tam, gdzie API je udostępnia.

</workflow>

## API Contract

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `POST /api/codex/context-pack`
- `GET /api/marketing/brief`
- `GET /api/ga4/diagnostics`
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
- `POST /api/connectors/{connector}/refresh` z `mode=vendor_read` tylko wtedy, gdy connector jest skonfigurowany i zadanie jawnie wymaga świeżego read.

</allowed_endpoints>

## Evidence Contract

<evidence_requirements>

Wymagane powierzchnie connectorów dla tego skilla:

- `google_analytics_4`

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
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj write/apply endpoints, chyba że WILQ API wystawia action, walidacja przechodzi i użytkownik jawnie prosi o wykonanie.
- Nie omijaj walidacji ActionObject, evidence IDs ani wymagań audytu.
</safety_rules>
