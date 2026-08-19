# Pakiet review treści dla Wilku — 2026-08-15

Rola dokumentu: `current state` pakietu UAT dla marketera (Bead `wilq-seo-jst`).
Nie jest publikacją, zapisem decyzji ani dowodem pełnego UAT. Zawiera tylko to,
co WILQ potwierdza dowodami; brak wartości = jawny blocker.

## Wprowadzenie — do czego służy ta sesja

WILQ przygotował **5 kompletnych rewizji treści** przez pełny pipeline
(plan → draft → pre-save readability gate → regulatory assurance → semantic
review). Każda ma `publish_ready=false` i `human_review_required=true`.
Celem tej sesji jest **werdykt Wilku na 5 rewizji**, nie publikacja.

## Dane sesji (do uzupełnienia przez Wilku)

- Data sesji: `<YYYY-MM-DD>`
- Uczestnik / osoba: `Wilku`
- Wybrany work item / rewizja: (poniżej, do wyboru)
- Czas do zrozumienia statusu: `<np. 8 minut>`
- Punkty niezrozumienia: `<co było niejasne>`

## Co WILQ pokazuje (dowody)

| Strona | Rewizja | Sekcje | FAQ | CTA | Semantic review |
|---|---|---|---|---|---|
| BDO – co musi wiedzieć przedsiębiorca? | `content_revision_f4c23cfcd5b6449c83281545b4883e2c` | 8 | 3 | 2 | 9/9 strong, 0 findings |
| Szkolenia z ochrony środowiska | `content_revision_66f7eec3ec9646a5a8ed5327a44e3da8` | 7 | 3 | 2 | 9/9 strong, 0 findings |
| Doradztwo i outsourcing ekologiczny | `content_revision_62ef7b61f6fd4a399a41d3ab33094fc9` | 3 | 3 | 1 | 9/9 strong, 0 findings |
| Opracowania dokumentacji i ekspertyz | `content_revision_b14c7fc23fcc4907aadf24c431cc656a` | 6 | 2 | 2 | 9/9 strong, 0 findings |
| Pomiary i analizy środowiska | `content_revision_787c4e52b3f941f3a048a63355e8cf45` | 3 | 1 | 1 | 9/9 strong, 0 findings |

Pełna treść i instrukcja zapisu decyzji pozostają retained local artifactem pod
`docs/agents/reports/content-review/paczka-tresci-5-stron-2026-08-12.md`; nie są
zależnością tego commitowanego kontraktu UAT. Manifest pięciu rewizji:
`docs/review-packets/2026-08-15-wilku-content-uat/revision.manifest.json`
(source fixed point: `0eada7073e637623ca2f24887f40c1908b7957cb`).

## Rekomendacja WILQ na dziś

- **BDO, szkolenia, doradztwo, opracowania, pomiary** — wszystkie 5 rewizji ma
  9/9 strong w semantic review. WILQ rekomenduje **przeczytanie i decyzję per
  rewizja**: `approved` / `needs_changes` / `rejected`.
- Decyzję zapisuje się przez
  `POST /api/content/work-items/{id}/draft-revisions/{revision_id}/review`
  z `decision` i `reviewed_by`.

## Blokery (czego WILQ NIE potwierdza)

- **Publikacja jest zablokowana** — `publish_ready=false` dla wszystkich rewizji;
  brak jakiegokolwiek zapisu do WordPressa.
- **Trzy strony są poza paczką z jawnych powodów:**
  - Dokumentacja środowiskowa w procesie inwestycyjnym — `lineage_mismatch`
    (Codex używał headingów z inputu w niepoprawnej formie); fail-closed zadziałał.
  - Ocena wpływu / BHP i P.POŻ / KIP — brak karty usługi w Service Profile.
- **Produkcja/deploy WILQ** — otwarte decyzje OWNER (P1–P4 w
  `docs/architecture/production-target-decision.md`).
- **Czego nie dotykać:** nie odblokowuj publikacji, nie zmieniaj wiedzy, nie
  traktuj 9/9 jako zgody na wypuszczenie treści.

## Pytania do Wilku (3–5)

1. Czy rozumiesz, czemu każda rewizja jest `review_required` mimo 9/9 semantic review?
2. Czy tekst na którejś stronie brzmi generycznie albo nie jak Ekologus? (wymień stronę/sekcję)
3. Gdzie pytasz „skąd WILQ to wziął?" — czy źródła i dowody są dla Ciebie czytelne?
4. Która rewizja jest najbliżej `approved`, a która wymaga poprawek i dlaczego?
5. Co trzeba poprawić w procesie, zanim WILQ będzie gotowy na pełny UAT?

## Jak zapisać dowód sesji

1. Wypełnij pola „Dane sesji".
2. Dla każdej rewizji zapisz decyzję (approved/needs_changes/rejected) z notatką.
3. Zapisz wynik przez `scripts/record_goal_005_content_uat_result.py`
   (patrz `docs/agents/artifacts.md`) albo w tym pliku poniżej.

## Wynik sesji (uzupełnia Wilku)

| Rewizja | Decyzja | Notatka |
|---|---|---|
| BDO |  |  |
| Szkolenia |  |  |
| Doradztwo |  |  |
| Opracowania |  |  |
| Pomiary |  |  |

- Werdykt sesji: `<przejdź do pełnego testu treści / zostań przy review / popraw materiały i wróć / odrzuć ten kierunek>`
- Największy brak produktu: `<...>`
- Miejsca generyczne/off-brand: `<...>`
- Follow-up (Beady): `<...>`
