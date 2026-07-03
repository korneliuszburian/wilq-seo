---
name: wilq-custom-segments
description: Proponuje akcje do sprawdzenia segmentów niestandardowych Google Ads dla Ekologus wyłącznie z dowodów WILQ API, takich jak wyszukiwane hasła, dowody Keyword Planner, istniejące kampanie i sprawdzone źródła danych. Użyj, gdy marketer pyta "jakie segmenty niestandardowe stworzyć?", "zbuduj segmenty z wyszukiwanych haseł", "jak wykorzystać zapytania i konkurencję w odbiorcach?", albo pyta o pomysły segmentów dla Demand Gen/YouTube/PMax lub kierowanie reklam z terminów źródłowych. Nigdy nie wolno wymyślać terminów odbiorców.
---

# WILQ Segmenty Niestandardowe

## Zasada skilla

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

## Workflow operatora

<workflow>

1. Wywołaj `GET /api/ads/diagnostics` przed diagnozą segmentów niestandardowych, terminów odbiorców lub kierowania reklam z wyszukiwanych haseł.
2. Pobierz `POST /api/codex/context-pack` tylko gdy wąski endpoint nie wystarcza albo potrzebujesz kontekstu wielu powierzchni. Nie rób z tego obowiązkowego kroku.
3. Endpointów refresh źródeł danych używaj tylko do jawnych odczytów danych i tylko gdy źródło danych jest skonfigurowane.
4. Jeśli użytkownik prosi o zapis albo podgląd zmiany, użyj `POST /api/actions/{action_id}/validate`; w review-only odpowiedzi wystarczy wskazać action_id i bezpieczny następny krok.
5. W podstawowej odpowiedzi używaj polskich podsumowań dowodów i źródeł danych. Techniczne identyfikatory źródeł danych, dowodów, szans i akcji dodawaj tylko jako ślad techniczny, gdy API je udostępnia.

</workflow>

## API

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

## Dowody

<evidence_requirements>

Wymagane powierzchnie źródeł danych dla tego skilla:

- `google_ads`
- `google_search_console`

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API. Jeśli `custom_segments_read_contract.status=blocked`, zwróć blokadę i brakujące dane zamiast wymyślać audience terms. Jeśli pola API mają akcje do sprawdzenia, używaj wyłącznie źródłowych terminów, podglądu zmian, dowodów, akcji do sprawdzenia i zablokowanych obietnic z API.

</evidence_requirements>

## Odpowiedź

<output>

Odpowiedź ma być krótka i użyteczna dla operatora: jaki segment można sprawdzić,
z jakich haseł źródłowych wynika, co trzeba odsiać ręcznie, jaki podgląd można
przygotować bez zapisu i jaka decyzja ma zapaść po review.

Widocznie oddzielaj:

- `Mapa segmentu`: nazwa/intent segmentu z API, review_priority, review_score i review_reason jako kolejność ręcznej oceny, nie dowód skuteczności.
- `Hasła źródłowe`: pokaż tylko `source_terms` z WILQ API; nie dopisuj nowych fraz ani synonimów.
- `Review intencji`: co trzeba odsiać ręcznie: intencję haseł, dopasowanie do usługi, ryzyko zbyt szerokiego segmentu, landing page i przypadkowe terminy.
- `Podgląd bez zapisu`: jaki action_id/preview można sprawdzić w WILQ bez zmiany kierowania.
- `Decyzja po review`: po sprawdzeniu operator może przygotować podgląd, zawęzić segment, odłożyć temat albo zablokować segment.
- `Zablokowane`: zapis kierowania, rozmiar odbiorców, prognoza, skuteczność kampanii, zwrot z reklam i wzrost konwersji.
- `Brief dla marketera`: 3-5 zdań normalnym językiem: co WILQ może przygotować, z czego to wynika, czego brakuje i jaki jest następny bezpieczny krok.
- `Ślad techniczny`: raw kontrakty, identyfikatory dowodów i action_id.

Nie pokazuj marketerowi surowych markerów typu `keyword_planner_enrichment`, `forecast_or_audience_size`, `custom_segments_read_contract` ani `audience_forecast_read_contract`. Tłumacz je normalnie: "brakuje wzbogacenia Keyword Planner" i "brakuje prognozy rozmiaru odbiorców". Surowe wartości zostaw w `notes`.

Język: wszystkie odpowiedzi dla operatora pisz po polsku z polskimi znakami. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans, identyfikatory akcji, ścieżki endpointów i wartości enumów zostaw bez zmian.

</output>

## Bezpieczeństwo

<safety_rules>

<!-- no-invented-metrics guardrail: do not invent metrics. -->
<!-- Polish language rule: operator-facing responses must be in Polish with Polish diacritics. -->

- Nie wymyślaj metryk, rankingów, liczby produktów, stanu kampanii, spisu treści, dostępów social ani ustaleń Localo.
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj endpointów zapisu zmian, chyba że WILQ API wystawia akcję, sprawdzenie w WILQ przechodzi i użytkownik jawnie prosi o zapis zmian.
- Nie omijaj sprawdzenia w WILQ, identyfikatorów dowodów ani wymagań audytu.
</safety_rules>
