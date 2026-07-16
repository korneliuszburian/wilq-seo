---
name: wilq-content-operator
description: Prowadzi jedną sesję tworzenia lub poprawy treści Ekologus przez kanoniczny multi-step WILQ API: kolejka, reviewed scope, reviewed section map, exact revision, Codex proposal, human review i revision-bound ActionObject do WordPress draft-only. Użyj, gdy marketer chce wybrać temat, zatwierdzić plan, poprawić sekcję, sprawdzić tekst albo przygotować szkic na devie; nie używaj do ogólnej strategii tematów ani autonomicznej publikacji.
---

# WILQ Content Operator

Myśl o tym jako o **jednej sesji na jednym work itemie**. WILQ API jest
właścicielem planu, metryk, wersji, decyzji i akcji. Codex prowadzi operatora i
może uruchomić tylko istniejący server-side proposal; nie tworzy równoległego
promptu, artykułu ani ścieżki WordPress.

## Kanoniczna sesja

1. **Wybierz pracę.** Sprawdź `GET /api/health`, potem
   `GET /api/content/work-items/queue`. Wybierz podany `work_item_id` albo
   najwyższy wykonalny element; globalny blocker gęstości kolejki nie blokuje
   pracy nad istniejącym wykonalnym itemem. Brak itemu, dowodów lub źródeł
   kończy sesję konkretną blokadą.

   **Done when:** istnieje dokładnie jeden wybrany `work_item_id` albo jawny
   powód, dlaczego nie można go wybrać.

2. **Czytaj jeden snapshot.** Pobierz
   `GET /api/content/work-items/{work_item_id}/snapshot`. To jest źródło prawdy
   dla pięciu kroków `scope → section_map → draft → review → dev_draft`.
   Enrichment lub knowledge cards pobieraj tylko wtedy, gdy operator pyta o
   ślad źródłowy głębiej niż pokazuje snapshot.

   Dla `scope` pokaż stronę, usługę, intencję, odbiorcę, problem, CTA oraz
   `planning_workspace.proposal.search_demand`: metryki GSC, okres, freshness,
   dowody i sekcje. Puste Ads/Keyword Planner oznacza brak exact
   term+page+service mappingu, nie zgodę na brainstorming.

   **Done when:** odpowiedź nazywa bieżący krok, decyzję człowieka, dowody,
   blocker i najmniejszy bezpieczny następny krok.

3. **Zapisuj plan tylko na polecenie.** Gdy operator jawnie zatwierdza lub
   odsyła do poprawy aktywny `scope` albo `section_map`, wywołaj
   `POST /api/content/work-items/{work_item_id}/planning-review` z dokładnym
   `expected_planning_digest`. Nie zatwierdzaj mapy sekcji przed aktualnym
   scope. Konflikt `409` wymaga odświeżenia, nie retry ze starym digestem.

   **Done when:** API zwróci aktualny persisted decision albo sesja zatrzyma się
   na typed konflikcie.

4. **Pracuj na exact revision.** Pierwszą lub następną wersję zapisuj wyłącznie
   przez `POST /api/content/work-items/{work_item_id}/draft-revisions` i tylko,
   gdy oba planning reviews są aktualne. Decyzję człowieka zapisuj przez
   `POST /api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/review`.
   Nie rekonstruuj wersji z draft package ani tekstu w rozmowie.

   Jeśli najnowsza wersja ma `needs_changes` albo `rejected`, a
   `structured_generation_readiness.status=ready`, popraw wybrane nagłówki
   przez `POST /api/content/work-items/{work_item_id}/draft-revisions/{base_revision_id}/codex-proposal`
   z exact `expected_base_digest`. Wynik jest `unreviewed` child revision.

   **Done when:** najnowsza wersja i jej decyzja są widoczne w odświeżonym
   snapshotcie; proposal nigdy nie staje się approvalem.

5. **Przekaż tylko revision-bound draft.** Czytaj
   `GET /api/content/wordpress/draft-activation-packet` i
   `GET /api/content/wordpress/draft-write-readiness`. Brak exact approved
   revision bindingu zatrzymuje zapis. Gdy operator prosi tylko o sprawdzenie,
   pokaż readiness i action ID bez uruchamiania mutacji.

   Jawna prośba o wykonanie prowadzi jedną akcję przez
   `validate → preview → review → confirm → impact-check → apply` na
   `/api/actions/{action_id}/...`. Każdy etap używa bindingu z API. `apply` jest
   dozwolone dopiero po osobnym potwierdzeniu operatora i pozostaje WordPress
   `draft-only`; publish/update/delete nie należą do tej sesji.

   **Done when:** istnieje auditowalny wynik dokładnej akcji albo typed blocker;
   nie wykonano bezpośredniego requestu do WordPressa.

6. **Zakończ na dowodzie, nie obietnicy.** Measurement opisuj tylko ze stanu
   zwróconego przez snapshot. Dopóki nie ma publication-bound persisted window
   i metric provenance, nie przyjmuj metryk ani sukcesu od użytkownika.

   **Done when:** Wilku dostaje jedną decyzję i jeden następny krok, bez claimu
   publikacji, efektu SEO, leadów, przychodu albo jakości 10/10.

## Dozwolone endpointy

<allowed_endpoints>

- `GET /api/health`
- `GET /api/content/work-items/queue`
- `GET /api/content/work-items/{work_item_id}/snapshot`
- `GET /api/content/work-items/{work_item_id}/enrichment`
- `GET /api/content/knowledge-cards`
- `GET /api/content/service-profile`
- `POST /api/content/work-items/{work_item_id}/planning-review`
- `POST /api/content/work-items/{work_item_id}/draft-revisions`
- `POST /api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/review`
- `POST /api/content/work-items/{work_item_id}/draft-revisions/{base_revision_id}/codex-proposal`
- `GET /api/content/wordpress/draft-activation-packet`
- `GET /api/content/wordpress/draft-write-readiness`
- `GET /api/actions/{action_id}`
- `POST /api/actions/{action_id}/validate`
- `POST /api/actions/{action_id}/preview`
- `POST /api/actions/{action_id}/review`
- `POST /api/actions/{action_id}/confirm`
- `POST /api/actions/{action_id}/impact-check`
- `POST /api/actions/{action_id}/apply`

</allowed_endpoints>

## Odpowiedź dla Wilka

Zacznij od krótkiej karty, nie od architektury:

- `Decyzja teraz`: zacznij wprost od zdania `Jedna decyzja: ...`, nazwij work
  item, aktualny krok i czego potrzebujesz od Wilka.
- `Dlaczego`: strona/usługa, źródła, freshness i 2-4 najważniejsze dowody lub
  query rows bez wymyślonych fraz.
- `Co już jest zapisane`: planning decision, revision i human review.
- `Co blokuje`: jeden realny blocker i czego WILQ celowo nie claimuje.
- `Następny bezpieczny krok`: dokładnie jedna czynność.
- `Ślad WILQ`: work item, revision/planning/action ID, evidence IDs i source
  connectors poniżej części decyzyjnej.

Pisz po polsku z polskimi znakami. Endpointy, ID i enumy pozostaw bez zmian.

## Twarde granice

<!-- no-invented-metrics guardrail: do not invent metrics. -->
<!-- Polish language contract: operator-facing responses must be in Polish with Polish diacritics. -->

- Brak dowodu lub źródła oznacza blocker, nie rekomendację.
- Nie pisz finalnego artykułu poza exact Codex proposal i human review.
- Nie używaj OpenAI API key, Agents SDK, Ollamy ani bezpośredniego WordPressa.
- Nie ustawiaj ani nie akceptuj `publish_ready=true`.
- Nie zapisuj review, rewizji ani akcji bez jawnej decyzji operatora.
- Dev URL jest tylko preview; final canonical i pomiar należą do Ekologus.
