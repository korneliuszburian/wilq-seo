---
name: wilq-custom-segments
description: Proponuje akcje do sprawdzenia segmentów niestandardowych Google Ads dla Ekologus wyłącznie z dowodów WILQ API, takich jak wyszukiwane hasła, dowody Keyword Planner, istniejące kampanie i sprawdzone źródła danych. Użyj, gdy marketer pyta "jakie segmenty niestandardowe stworzyć?", "zbuduj segmenty z wyszukiwanych haseł", "jak wykorzystać zapytania i konkurencję w odbiorcach?", albo pyta o pomysły segmentów dla Demand Gen/YouTube/PMax lub kierowanie reklam z terminów źródłowych. Nigdy nie wolno wymyślać terminów odbiorców.
---

# WILQ Segmenty Niestandardowe

## Kontrakt skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Jakie segmenty niestandardowe możemy zrobić z realnych wyszukiwanych haseł?"
- "Zbuduj propozycje odbiorców dla Demand Gen/PMax."
- "Czy mamy dowody na segmenty konkurencyjne albo intencyjne?"
- "Nie wymyślaj fraz, pokaż tylko segmenty z dowodów WILQ."

</triggers>

## Kontrakt workflow

<workflow>

1. Przeczytaj `references/output-contract.md` przed finalną odpowiedzią lub planem działania.
2. Uruchom `uv run python .agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000` przy sprawdzaniu ścieżki skill/API.
3. Wywołaj `GET /api/ads/diagnostics` przed diagnozą segmentów niestandardowych, terminów odbiorców lub kierowania reklam z wyszukiwanych haseł.
4. Wywołaj `POST /api/codex/context-pack` z `{"skill":"wilq-custom-segments"}` i potwierdź, że `ads_diagnostics.custom_segments_read_contract` zgadza się z endpointem Ads diagnostics.
5. Endpointów refresh źródeł danych używaj tylko do jawnych odczytów danych i tylko gdy źródło danych jest skonfigurowane.
6. Sprawdź istniejącą akcję przez `POST /api/actions/{action_id}/validate` przed rekomendacją zapisu zmian.
7. W podstawowej odpowiedzi używaj polskich podsumowań dowodów i źródeł danych. Techniczne identyfikatory źródeł danych, dowodów, szans i akcji dodawaj tylko jako ślad techniczny, gdy API je udostępnia.

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
- `POST /api/connectors/{connector}/refresh` z `mode=vendor_read` tylko wtedy, gdy źródło danych jest skonfigurowane i zadanie jawnie wymaga świeżego odczytu danych.

</allowed_endpoints>

## Kontrakt dowodów

<evidence_requirements>

Wymagane powierzchnie źródeł danych dla tego skilla:

- `google_ads`
- `google_search_console`

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API. Jeśli `custom_segments_read_contract.status=blocked`, zwróć blokadę i brakujące kontrakty zamiast wymyślać audience terms. Jeśli kontrakt ma akcje do sprawdzenia, używaj wyłącznie źródłowych terminów, podglądu zmian, dowodów, akcji do sprawdzenia i zablokowanych obietnic z API.

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
