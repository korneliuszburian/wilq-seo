---
name: wilq-social-publisher
description: Przygotowuje bezpieczne akcje do sprawdzenia dla treści LinkedIn/Facebook dla Ekologus przez dowody z WILQ API i sprawdzenie w WILQ. Użyj, gdy marketer pyta "przygotuj post z tych danych", "co opublikować na Facebooku albo LinkedIn?", "zamień insight z GSC/GA4/Merchant/Ads na post", "zrób kolejkę social", albo pyta o adaptację danych na social, szkice postów oparte na dowodach, ponowne użycie treści lub gotowość publikacji. Nie wolno publikować ani szkicować niewspartych obietnic bez dowodów WILQ.
---

# WILQ Posty społecznościowe

## Zasada skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Przygotuj post LinkedIn z tej karty contentowej."
- "Co opublikować na Facebooku na podstawie GSC/GA4/Merchant?"
- "Zrób social queue, ale pokaż twierdzenia, których nie wolno użyć."
- "Czy możemy publikować, czy brakuje uprawnień?"

</triggers>

## Workflow operatora

<workflow>

1. Wywołaj `GET /api/social/history-inventory`, żeby sprawdzić, czy WILQ ma historię postów i czy wolno mówić o braku powtórek.
2. Pobierz `POST /api/codex/context-pack` tylko wtedy, gdy przygotowujesz szkice z wielu źródeł albo potrzebujesz `social_draft_context`.
3. Odpowiedz review-only: kierunek posta, dowody, zablokowane twierdzenia, ryzyko powtórki i następny krok. Nie publikuj.
4. Jeśli użytkownik prosi o zapis albo podgląd zmiany, użyj `POST /api/actions/{action_id}/validate`; w review-only odpowiedzi wystarczy wskazać action_id i bezpieczny następny krok.
5. Endpointów refresh źródeł danych używaj tylko do jawnych odczytów danych i tylko gdy źródło danych jest skonfigurowane.

</workflow>

## API

<allowed_endpoints>

- `GET /api/health`
- `GET /api/system/status`
- `POST /api/codex/context-pack`
- `GET /api/marketing/brief`
- `GET /api/social/history-inventory`
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

- `linkedin`
- `facebook`

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API. Jeśli dowody są zagregowane, stare, niepełne albo zablokowane dostępem do źródła danych, powiedz to wprost.

</evidence_requirements>

## Odpowiedź

<output>

Odpowiedź ma być krótka i użyteczna dla operatora: status, dowody, diagnoza, akcje do sprawdzenia w WILQ, blokady i następne bezpieczne kroki.

W social odpowiedź musi dać coś, co marketer może od razu ocenić:

- `Można zrobić teraz`: przygotować szkic do review, nie publikację.
- `Pakiet do review`: temat, główna teza, CTA do ręcznego sprawdzenia i źródło inspiracji.
- `Wariant LinkedIn`: 2-4 zdania szkicu albo kierunku posta, bez obietnic efektu.
- `Wariant Facebook`: 2-4 zdania szkicu albo kierunku posta, prostszym językiem niż LinkedIn.
- `Historia do sprawdzenia`: powiedz normalnie, że nie wiemy jeszcze, czy podobny post już był na LinkedIn/Facebooku, więc nie wolno pisać, że temat jest nowy albo bezpieczny do powtórzenia.
- `Decyzja po review`: co może się stać po sprawdzeniu historii i twierdzeń: zaakceptować szkic do ręcznego przygotowania, przerobić CTA, zablokować temat albo poczekać na historię social.
- `Dowód`: krótkie ludzkie streszczenie źródeł, a surowe ID w śladzie technicznym.
- `Zablokowane`: publikacja, claim o skuteczności i claim o braku powtórek.

Nie pokazuj marketerowi surowych markerów typu `social_history_inventory_v1`, `metadata-only` albo `source_evidence_id` jako wyjaśnienia blokady. Tłumacz to normalnie: "nie wiemy jeszcze, czy podobny post już był na LinkedIn/Facebooku, więc nie wolno pisać, że temat jest nowy albo bezpieczny do powtórzenia".

Język: wszystkie odpowiedzi dla operatora pisz po polsku z polskimi znakami. Identyfikatory API, identyfikatory źródeł danych, identyfikatory dowodów, identyfikatory szans, identyfikatory akcji, ścieżki endpointów i wartości enumów zostaw bez zmian.

</output>

## Bezpieczeństwo

<safety_rules>

<!-- no-invented-metrics guardrail: do not invent metrics. -->
<!-- Polish language rule: operator-facing responses must be in Polish with Polish diacritics. -->

- Nie wymyślaj metryk, rankingów, liczby produktów, stanu kampanii, spisu treści, uprawnień social ani ustaleń Localo.
- Nie drukuj sekretów, ścieżek credentiali, wartości tokenów ani surowych vendor response bodies.
- Nie wywołuj endpointów zapisu zmian, chyba że WILQ API wystawia akcję, sprawdzenie w WILQ przechodzi i użytkownik jawnie prosi o zapis zmian.
- Nie omijaj sprawdzenia w WILQ, identyfikatorów dowodów ani wymagań audytu.
</safety_rules>
