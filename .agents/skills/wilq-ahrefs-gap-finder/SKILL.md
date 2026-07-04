---
name: wilq-ahrefs-gap-finder
description: Analizuje dane Ahrefs dla Ekologus przez WILQ API i wskazuje defensywne okazje SEO, treściowe i backlinkowe. Użyj, gdy marketer pyta "gdzie konkurencja ma przewagę SEO?", "jakie mamy luki treści?", "co mówi Ahrefs o domenie?", "jak wykorzystać DR/backlinki?", albo pyta o luki względem konkurencji, rozbudowę treści/linków, kontekst autorytetu lub priorytety SEO z Ahrefs. Musi cytować WILQ identyfikatory dowodów i nie wolno zmyślać wartości Ahrefs.
---

# WILQ Luki z Ahrefs

## Zasada skilla

<operating_rule>

Używaj tego skilla jako workflow operatora WILQ API, nie jako raport oparty tylko o prompt. Przed wnioskami marketingowymi pobierz kontekst z WILQ API. Jeśli API jest niedostępne albo brakuje dowodów, zwróć blokadę zamiast wypełniać luki.

</operating_rule>

## Kiedy używać

<triggers>

- "Gdzie konkurencja ma przewagę SEO nad Ekologus?"
- "Znajdź luki treści, ale tylko jeśli mamy dowody z Ahrefs."
- "Jak wykorzystać DR/backlinki w planie treści?"
- "Czy Ahrefs potwierdza priorytet tej treści?"

</triggers>

## Workflow operatora

<workflow>

1. Wywołaj `GET /api/ahrefs/diagnostics` przed podsumowaniem metryk, okazji lub akcji do sprawdzenia.
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
- `GET /api/marketing/brief`
- `GET /api/ahrefs/diagnostics`
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

- `ahrefs`
- `google_search_console`
- `wordpress_ekologus`

Każda rekomendacja musi zawierać identyfikatory źródeł danych i identyfikatory dowodów z WILQ API. Jeśli dowody są zagregowane, stare, niepełne albo zablokowane dostępem do źródła danych, powiedz to wprost.

</evidence_requirements>

## Odpowiedź

<output>

Odpowiedź ma być krótka i użyteczna dla operatora: jakie luki można
przejrzeć, w jakiej kolejności, co porównać ręcznie i czego nie wolno obiecać
na podstawie samych danych Ahrefs.

Widocznie używaj tych sekcji:

- `Mapa luk`: rozdziel luki treści, luki linków, strony konkurencji, organic keywords i kontekst autorytetu.
- `Kolejność review`: wskaż pierwszy typ luki do ręcznego sprawdzenia i dlaczego teraz.
- `Co porównać ręcznie`: podaj checklistę: temat konkurenta, istniejący URL Ekologus, intencja, pokrycie treści, możliwość linkowania/źródeł.
- `Karta cross-checku GSC/WordPress`: zawsze dopisz krótką kartę z trzema
  polami: `Sprawdź w GSC`, `Sprawdź w WordPress` i `Decyzja po cross-checku`.
  Najpierw użyj pól `gap_read_contract.cross_check_status`,
  `cross_check_summary`, `cross_check_next_step` i
  `cross_check_candidates`, jeśli są dostępne w WILQ API. Jeśli
  `cross_check_status=api_backed`, przy karcie pokaż także
  `cross_check_source_connectors` i `cross_check_evidence_ids` jako dowody
  cross-checku. Karta ma mówić, czy temat z Ahrefs idzie dalej do content
  briefu, wymaga scalenia z istniejącą treścią, zostaje tylko w obserwacji
  albo jest zablokowany. Nie traktuj GSC/WordPress jako dowodów Ahrefs, jeśli
  WILQ nie zwraca API-backed cross-checku; nazwij je kolejnym krokiem
  walidacji przed briefem, nie źródłem bieżącej rekomendacji Ahrefs.
- `Decyzja po review`: użyj dokładnie tej etykiety i powiedz, czy po
  sprawdzeniu temat idzie do content briefu, link-review, dalszego GSC i
  WordPress cross-checku albo zostaje zablokowany.
- `Akcja do sprawdzenia`: jeśli WILQ API zwraca
  `act_prepare_content_refresh_queue`, nazwij ją jako bezpieczny handoff do
  kolejki odświeżenia treści. Nie opisuj jej jako zapisu, publikacji ani
  automatycznego briefu; to tylko przygotowanie review w widoku Treści.
- `Brief dla marketera`: 3-5 zdań normalnym językiem: co Ahrefs pokazuje, co to znaczy dla planu treści/linków, czego nie wolno jeszcze obiecać.
- `Zablokowane obietnice`: wzrost ruchu, wzrost autorytetu, przewaga konkurencyjna, produkcyjna treść i efekt SEO bez dalszego sprawdzenia.

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
