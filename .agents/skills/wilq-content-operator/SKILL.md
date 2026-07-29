---
name: wilq-content-operator
description: "Prowadzi marketera przez jedną kanoniczną ścieżkę WILQ: wybór istniejącej strony albo brief nowej strony, jedno przygotowanie tekstu, exact review oraz oddzielne przygotowanie szkicu dev. Użyj, gdy trzeba realnie przygotować lub odświeżyć treść; nie używaj do strategii tematów ani publikacji."
---

# WILQ Content Operator

<!-- no-invented-metrics guardrail: do not invent metrics. -->
<!-- Polish language contract: operator-facing responses must be in Polish with Polish diacritics. -->

Prowadź **jedną pracę nad treścią naraz**. Marketer ma dostać prostą drogę:

```text
wybór strony albo brief
  → przygotuj tekst
  → sprawdź tekst
  → opcjonalny szkic na dev
```

WILQ API przechowuje exact identyfikatory, digesty, dowody i audyt. Nie
zastępuj ich własnym stanem ani nie każ marketerowi przepisywać decyzji,
identyfikatora operatora lub technicznych formularzy.

`Przygotuj tekst` jest jedną jawną czynnością marketera. WILQ może w jej
ramach najpierw utworzyć exact plan, odczytać jego końcowy stan i dopiero potem
uruchomić exact draft. Plan pozostaje serwerowym bezpiecznikiem i źródłem
lineage, ale nie jest osobnym ekranem akceptacji ani zadaniem dla marketera.

## Istniejąca strona

1. Odczytaj `GET /api/health`, potem `GET /api/content/workflow-entry`.
   Wybierz wskazany `work_item_id` albo pokaż blokadę danych. Nie zaczynaj od
   kolejki, snapshotu ani katalogu WordPressa.

2. Odczytaj `GET /api/content/work-items/{work_item_id}/document-workspace`
   oraz `GET /api/content/work-items/{work_item_id}/planning-proposals`.
   Pokaż publiczne źródło, stan dokumentu, faktycznie zapisane lineage i jedno
   `next_action`. „Zmiany w treści” oznaczają wyłącznie obserwowane nagłówki i
   fragmenty; nie są visual diffem ani oceną semantycznej równoważności.

3. Po jasnym „przygotuj tekst” użyj exact `service_card_id` oraz
   `expected_planning_input_digest` z odczytu, aby utworzyć lub odczytać plan
   przez `POST /api/content/work-items/{work_item_id}/planning-proposals`.
   Odczytuj wyłącznie ten sam status, aż przestanie być `generating`, a potem
   uruchom `POST .../initial-draft` z jego exact proposal ID i digestami.
   Pokaż intencję, strukturę i źródła razem z powstałym tekstem, nie jako
   osobną decyzję. Gdy plan jest zablokowany, pokaż jego realny blocker i nie
   uruchamiaj draftu.

4. Pełny tekst jest immutable rewizją. Pokaż go przed dalszym krokiem. Po
   jawnym „zatwierdź tekst” zapisz `POST .../draft-revisions/{revision_id}/review`
   z exact `expected_revision_digest` i evidence IDs rewizji. „Tekst wymaga
   zmian” wymaga krótkiej notatki; poprawka powstaje wyłącznie przez exact
   child revision, nigdy przez edycję istniejącej rewizji.

5. Dopiero approved exact revision może wejść w delivery: read-only
   `target-discovery` i `target-mapping`, osobne potwierdzenie mappingu,
   utworzenie ActionObjectu i lifecycle `/api/actions`. ActionObject nie jest
   WordPressem. `apply` wymaga osobnego polecenia człowieka i może utworzyć
   najwyżej jeden szkic na dev; publish, update i delete są poza tą ścieżką.

## Nowa strona

Nowa strona nie ma starego URL-a, inventory ani porównania. Prowadź ją przez:

1. Najpierw odczytaj `GET /api/content/new-page-topics`. Jeżeli marketer
   wybierze kwalifikowany temat, użyj jego exact ID i digestu wyłącznie do
   wypełnienia briefu; brak takiego tematu nie blokuje ręcznego briefu. Dopiero
   po jawnym wyborze albo własnym briefie wywołaj `POST /api/content/new-page-briefs`,
   następnie odczytaj brief.
2. Pokaż guard pokrycia serwisu i pozwól wybrać zatwierdzoną usługę. Tylko ta
   realna decyzja tworzy `planning-foundation`; nie zgaduj usługi na podstawie
   tytułu briefu.
3. Po jasnym „przygotuj tekst” wywołaj `POST .../planning-proposal`, odczytuj
   wyłącznie jego exact status, a po gotowym planie automatycznie uruchom exact
   initial draft z proposal ID i digestami. Nie zapisuj planning review — plan
   jest wejściem do generowania, a review dotyczy dopiero powstałego tekstu.
4. Review tekstu, delivery ActionObject, potwierdzenie publicznego wdrożenia i
   measurement mają te same granice jak dla istniejącej strony.

## Konflikty i granice

- `409` oznacza: odczytaj ponownie dokładnie ten sam workspace, pokaż aktualny
  bezpieczny następny krok i nie retry ze starym digestem.
- Brak albo nieświeże źródło/evidence to blocker, nie zaproszenie do zgadywania.
- Nie używaj `section_map`, legacy snapshotu, `wordpress-draft-handoff`,
  `wordpress-draft-execution`, `draft-activation-packet` ani direct WordPress.
- Nie uruchamiaj generowania, review, ActionObjectu, apply, deploymentu ani
  measurementu tylko dlatego, że ekran został otwarty. Każdy zapis wymaga
  jasno wyrażonej czynności marketera.
- Public deployment tylko potwierdza zaobserwowane publiczne wdrożenie; nie
  publikuje. Measurement i learning dotyczą wyłącznie exact deploymentu.

## Odpowiedź dla marketera

Pisz po polsku, krótko i w tej kolejności:

1. `Jedna decyzja:` co można teraz zrobić;
2. `Dlaczego:` źródła i najważniejszy fakt;
3. `Co już jest:` stan przygotowania tekstu / rewizja / review, bez surowych payloadów;
4. `Co blokuje:` tylko realna blokada, jeśli istnieje;
5. `Następny bezpieczny krok:` dokładnie jedna czynność;
6. `Ślad WILQ:` work item, revision/planning/action ID i evidence poniżej
   części decyzyjnej.

**Done when:** marketer widzi jedną zrozumiałą czynność albo konkretny,
evidence-bound blocker; żadna czynność nie sugeruje publikacji ani wyniku SEO.
