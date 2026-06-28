---
name: wilq-gsc-content-doctor
description: Zamienia dowody Google Search Console dla Ekologus w SEO/content diagnostics przez WILQ API. Użyj, gdy marketer pyta "które strony odświeżyć?", "gdzie mamy dużo wyświetlenia i niski CTR?", "jakie query tracą kliknięcia?", "co poprawić w treściach SEO?", "które strony scalić/utworzyć/odświeżyć/zablokować?", albo pyta o zapytania, strony, CTR, wyświetlenia, pozycje, spadek efektów treści, szanse blisko topu, przepisanie treści lub szanse SEO. Musi zwracać identyfikatory dowodów i nie wolno zmyślać metryk wyszukiwania.
---

# WILQ GSC Content Doctor

## Skill Contract

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Trigger Contract

<triggers>

- "Które treści na ekologus.pl odświeżyć najpierw?"
- "Znajdź query z dużymi wyświetlenia i słabym CTR."
- "Pokaż SEO szanse z GSC i WordPress inventory."
- "Czy mamy kanibalizację albo strony do merge?"

</triggers>

## Kontrakt workflow

<workflow>

1. Przeczytaj `references/output-contract.md` przed finalną odpowiedzią lub planem działania.
2. Uruchom `uv run python .agents/skills/wilq-gsc-content-doctor/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` przy sprawdzaniu ścieżki skill/API.
3. Wywołaj `GET /api/content/diagnostics` przed podsumowaniem metryk SEO i treści albo zadań kolejki lub akcji do sprawdzenia.
4. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-gsc-content-doctor"}` i potwierdź, że osadzone `content_diagnostics` zgadza się z endpointem.
5. Endpointów refresh źródeł danych używaj tylko do jawnych odczytów danych i tylko gdy źródło danych jest skonfigurowane.
6. Sprawdź istniejącą akcję przez `POST /api/actions/{action_id}/validate` przed rekomendacją zapisu zmian.
7. W podstawowej odpowiedzi używaj polskich podsumowań dowodów i źródeł danych. Techniczne identyfikatory źródeł danych, dowodów, szans i akcji dodawaj tylko jako ślad techniczny, gdy API je udostępnia.

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
- `POST /api/connectors/{connector}/refresh` z `mode=vendor_read` tylko wtedy, gdy źródło danych jest skonfigurowane i zadanie jawnie wymaga świeżego odczytu danych.

</allowed_endpoints>

## Kontrakt dowodów

<evidence_requirements>

Wymagane powierzchnie źródeł danych dla tego skilla:

- `google_search_console`
- `wordpress_ekologus`
- `wordpress_sklep`

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API. Jeśli dowody są zagregowane, stare, niepełne albo zablokowane dostępem do źródła danych, powiedz to wprost.

</evidence_requirements>

## Kontrakt odpowiedzi

<output_contract>

Trzymaj się `references/output-contract.md`. Odpowiedź ma być na tyle krótka, żeby operator mógł działać: status, dowody, diagnoza, akcje sprawdzone w WILQ, blokady i następne bezpieczne kroki.

Kontrakt językowy: wszystkie odpowiedzi dla operatora pisz po polsku z polskimi znakami. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans, identyfikatory akcji, ścieżki endpointów i wartości enumów zostaw bez zmian.

</output_contract>

## Kontrakt bezpieczeństwa

<safety_rules>

<!-- no-invented-metrics guardrail: do not invent metrics. -->
<!-- Polish language contract: operator-facing responses must be in Polish with Polish diacritics. -->

- Nie wymyślaj metryk, rankingów, liczby produktów, stanu kampanii, spisu treści, dostępów social ani ustaleń Localo.
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj endpointów zapisu zmian, chyba że WILQ API wystawia akcję, sprawdzenie w WILQ przechodzi i użytkownik jawnie prosi o zapis zmian.
- Nie omijaj sprawdzenia w WILQ, identyfikatorów dowodów ani wymagań audytu.
</safety_rules>
