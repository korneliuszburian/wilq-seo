---
name: wilq-content-strategist
description: 'Planuje strategię treści Ekologus z WILQ API, dowodami, kartami wiedzy, GSC, GA4, Ahrefs, Merchant i spisem treści WordPress. Użyj, gdy marketer pyta "co napisać albo odświeżyć?", "zrób plan treści", "przygotuj brief SEO", "jakie treści dadzą największą szansę?", "co zrobić z tym adresem albo zapytaniem?", albo chce decyzje: zachować, odświeżyć, scalić, przepisać, utworzyć albo zablokować. Musi używać evidence IDs, source connector IDs i knowledge card IDs jako identyfikatorów źródeł, nie generycznego brainstormingu.'
---

# WILQ Content Strategist

## Skill Contract

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed obietnicami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Trigger Contract

<triggers>

- "Co napisać lub odświeżyć dla ekologus.pl, żeby realnie pomóc marketerowi?"
- "Przygotuj brief SEO dla tej karty z Command Center."
- "Zrób kolejkę zachowania, odświeżenia, scalenia, nowej treści albo blokady z GSC, GA4 i WordPress."
- "Jak przełożyć dane z Ads/Merchant/GSC na treści i CTA?"

</triggers>

## Workflow Contract

<workflow>

1. Przeczytaj `references/output-contract.md` przed finalną odpowiedzią lub planem działania.
2. Uruchom `uv run python .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` przy sprawdzaniu ścieżki skill/API.
3. Wywołaj `GET /api/content/diagnostics` przed budową planu treści lub kolejki.
4. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-content-strategist"}` i potwierdź, że istnieje osadzone `content_diagnostics`.
5. Użyj `content_diagnostics.decision_queue` jako kanonicznej kolejki decyzji. Nie odtwarzaj klasyfikacji contentowej w promptach.
6. Endpointów refresh connectorów używaj tylko do jawnych odczytów danych i tylko gdy connector jest skonfigurowany.
7. Sprawdź istniejącą akcję przez `POST /api/actions/{action_id}/validate` przed rekomendacją zapisu zmian.
8. Zwracaj identyfikatory: source connector IDs, evidence IDs, opportunity IDs i action IDs wszędzie tam, gdzie API je udostępnia.

</workflow>

## API Contract

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `POST /api/codex/context-pack`
- `GET /api/content/diagnostics`
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

- `google_search_console`
- `google_analytics_4`
- `ahrefs`
- `wordpress_ekologus`
- `wordpress_sklep`

Każda rekomendacja musi zawierać source connector IDs i evidence IDs z WILQ API. Jeśli dowody są zagregowane, stare, niepełne albo zablokowane dostępem do źródła danych, powiedz to wprost.

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
