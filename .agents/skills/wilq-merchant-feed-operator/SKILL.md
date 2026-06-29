---
name: wilq-merchant-feed-operator
description: Analizuje dowody Merchant Center dla produktów i pliku produktowego Ekologus przez WILQ API i przygotowuje bezpieczną kolejkę sprawdzenia problemów pliku produktowego. Użyj, gdy marketer pyta "czy plik produktowy jest OK?", "które produkty mają problemy?", "co blokuje Shopping/PMax produkty?", "sprawdź odrzucone produkty", "przygotuj kolejkę przeglądu problemów pliku produktowego", albo pyta o diagnostykę Merchant, ryzyka widoczności produktów, poprawki pliku produktowego, typy problemów, atrybuty, dostępność, ceny, GTIN/obrazy lub zatwierdzenia produktów. Nie wolno zmieniać danych produktu bez akcji do sprawdzenia w WILQ i audytu.
---

# WILQ Merchant Center

## Kontrakt skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Czy plik produktowy Ekologus/sklep.ekologus.pl jest zdrowy?"
- "Pokaż problemy produktów w Merchant Center."
- "Co może blokować widoczność produktów w Shopping/PMax?"
- "Przygotuj bezpieczną kolejkę sprawdzenia problemów pliku produktowego."

</triggers>

## Kontrakt workflow

<workflow>

1. Przeczytaj `references/output-contract.md` przed finalną odpowiedzią lub planem działania.
2. Uruchom `uv run python .agents/skills/wilq-merchant-feed-operator/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` przy sprawdzaniu ścieżki skill/API.
3. Wywołaj `GET /api/merchant/diagnostics` przed podsumowaniem zdrowia pliku produktowego/produktów, issue queue lub akcji do sprawdzenia produktowych.
4. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-merchant-feed-operator"}` i potwierdź, że `merchant_diagnostics` zgadza się z endpointem Merchant diagnostics.
5. Endpointów refresh źródeł danych używaj tylko do jawnych odczytów danych i tylko gdy źródło danych jest skonfigurowane.
6. Sprawdź istniejącą akcję przez `POST /api/actions/{action_id}/validate` przed rekomendacją zapisu zmian.
7. W podstawowej odpowiedzi używaj polskich podsumowań dowodów i źródeł danych. Techniczne identyfikatory źródeł danych, dowodów, szans i akcji dodawaj tylko jako ślad techniczny, gdy API je udostępnia.
8. Dla pytań o aktualny stan pliku produktowego użyj `freshness_assessment`: `requires_refresh=true` albo `state=stale|missing|blocked` oznacza nieaktualne dane albo blokadę, chyba że użytkownik jawnie pozwala na odczyt danych źródła danych.
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
- `POST /api/connectors/{connector}/refresh` z `mode=vendor_read` tylko wtedy, gdy źródło danych jest skonfigurowane i zadanie jawnie wymaga świeżego odczytu danych.

</allowed_endpoints>

## Kontrakt dowodów

<evidence_requirements>

Wymagane powierzchnie źródeł danych dla tego skilla:

- `google_merchant_center`

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API. Merchant Diagnostics sections i tactical items traktuj jako główne źródło. Jeśli dowody są zagregowane, stare, niepełne albo zablokowane dostępem do źródła danych, powiedz to wprost.

Jeśli `/api/merchant/diagnostics` zwraca `unknowns`, `product_sample_readiness.status=blocked`, `product_performance_readiness.status=blocked` albo `price_impact_readiness.status=blocked`, odpowiedź musi mieć sekcję "Czego nie wiemy" i nie może udawać kolejki produkt-po-produkcie, zwrotu z reklam na poziomie produktu, wpływu ceny ani wpływu naprawy na przychód.

</evidence_requirements>

## Kontrakt odpowiedzi

<output_contract>

Trzymaj się `references/output-contract.md`. Odpowiedź ma być na tyle krótka, żeby operator mógł działać: status, dowody, diagnoza, akcje do sprawdzenia w WILQ, blokady i następne bezpieczne kroki.

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
