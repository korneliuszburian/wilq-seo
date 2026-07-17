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

2. **Czytaj jeden snapshot i status planera.** Pobierz
   `GET /api/content/work-items/{work_item_id}/snapshot`, a następnie model-free
   `GET /api/content/work-items/{work_item_id}/planning-proposals`. Snapshot jest
   źródłem prawdy dla pięciu kroków
   `scope → section_map → draft → review → dev_draft`; status planera mówi
   `not_generated`, `ready`, `stale` albo `blocked` i nigdy sam nie uruchamia
   modelu. Enrichment lub knowledge cards pobieraj tylko wtedy, gdy operator
   prosi o ślad głębszy niż snapshot.

   Dla `scope` pokaż stronę, usługę, intencję, odbiorcę, problem, CTA oraz
   `planning_workspace.proposal.search_demand`: metryki GSC, okres, freshness,
   dowody i sekcje. Puste Ads/Keyword Planner oznacza brak exact
   term+page+service mappingu, nie zgodę na brainstorming.

   **Done when:** odpowiedź nazywa bieżący krok, decyzję człowieka, dowody,
   blocker i najmniejszy bezpieczny następny krok.

3. **Zapisz wybór usługi przed modelem.** Dla świeżego itemu jawna decyzja
   operatora najpierw zapisuje review bazowego `scope` przez
   `POST /api/content/work-items/{work_item_id}/planning-review`: `stage=scope`,
   exact `expected_planning_digest`, dozwolone `service_card_id`, `decision`,
   `reviewed_by` oraz `checked_items` dla approval albo `notes` dla zmian.
   Następnie odśwież snapshot i model-free GET planera. Karta bez
   `approved_current` pozostaje zewnętrzną bramką ownera; skill nie zapisuje
   jej review ani nie obchodzi lifecycle.

   **Done when:** API utrwaliło human-confirmed service selection dla bieżącego
   baseline digestu albo zwróciło typed konflikt/blokadę.

4. **Generuj plan tylko na polecenie.** Gdy odświeżony GET zwraca aktualny
   planning input i operator prosi o plan, wywołaj
   `POST /api/content/work-items/{work_item_id}/planning-proposals` z exact
   `service_card_id`, `expected_planning_input_digest`, krótkim opcjonalnym
   `operator_hint` i atrybucją `requested_by`. Nie rekonstruuj inputu ani planu
   w rozmowie. `409 stale_input`, unknown service, typed blocker albo błąd
   runtime zatrzymuje sesję bez fallbacku.

   **Done when:** istnieje persisted proposal związany z exact inputem albo
   jawny blocker i model nie został zastąpiony inną ścieżką.

5. **Zatwierdzaj wygenerowany plan etapami.** Jawne `approved` albo
   `needs_changes` zapisuj przez
   `POST /api/content/work-items/{work_item_id}/planning-review` z `stage`,
   exact `expected_planning_digest`, `decision`, `reviewed_by` oraz
   `checked_items` dla approval albo `notes` dla zmian. Przy `scope` przekaż
   wybrane `service_card_id`; potem osobno oceń `section_map`. Konflikt `409`
   wymaga odświeżenia; nie retry ze starym digestem i nie przenoś decyzji na
   inną propozycję.

   **Done when:** oba current planning reviews odnoszą się do tej samej
   wygenerowanej propozycji albo operator dostał dokładną instrukcję poprawy.

6. **Twórz i oceniaj pełny dokument.** Po dwóch aktualnych approvals i wyłącznie
   na jawne polecenie wywołaj
   `POST /api/content/work-items/{work_item_id}/initial-draft` z exact
   `expected_proposal_id`, `expected_planning_digest`,
   `expected_planning_input_digest` oraz `requested_by`. Wynik jest pełną
   rewizją v2 `unreviewed`, nigdy approvalem.

   Dla tej rewizji najpierw czytaj model-free
   `GET .../draft-revisions/{revision_id}/semantic-review`. Jawna prośba o
   advisory review prowadzi do `POST` na ten sam endpoint z
   `expected_revision_digest` i `requested_by`. Semantic review jest
   exact-digest advisory: nie zapisuje human acceptance, ActionObjectu ani
   `publish_ready=true`. Decyzję człowieka zapisuj osobno przez
   `POST .../draft-revisions/{revision_id}/review` z
   `expected_revision_digest`, `reviewed_by`, `decision` i: dla approval
   `checked_items` oraz `evidence_ids`, a dla pozostałych decyzji `notes`.

   **Done when:** pełny dokument, advisory findings i decyzja człowieka są
   rozdzielone oraz związane z jednym exact revision digestem.

7. **Poprawiaj tylko wybrane sekcje.** Gdy exact human review ma
   `needs_changes` albo `rejected`, a readiness pozwala na poprawkę, operator
   wskazuje stabilne `section_id`. Wywołaj
   `POST .../draft-revisions/{base_revision_id}/codex-proposal` z exact
   `expected_base_digest`, niepustym `selected_section_ids` i `requested_by`.
   Nie wysyłaj równocześnie legacy headings. Wynik jest niezmienną `unreviewed`
   child revision; ponownie przechodzi semantic review i osobną decyzję
   człowieka.

   **Done when:** odświeżony snapshot pokazuje child revision, diff i jej własny
   status review; poprawka nie zmieniła niewybranych page assets.

8. **Przekaż tylko revision-bound draft.** Czytaj
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

9. **Zakończ na dowodzie, nie obietnicy.** Measurement opisuj tylko ze stanu
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
- `GET /api/content/work-items/{work_item_id}/planning-proposals`
- `POST /api/content/work-items/{work_item_id}/planning-proposals`
- `POST /api/content/work-items/{work_item_id}/planning-review`
- `POST /api/content/work-items/{work_item_id}/initial-draft`
- `GET /api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/semantic-review`
- `POST /api/content/work-items/{work_item_id}/draft-revisions/{revision_id}/semantic-review`
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
