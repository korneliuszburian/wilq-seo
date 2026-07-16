# Content Operator — techniczny kontrakt odpowiedzi

Czytaj ten plik tylko podczas debugowania lub evala ustrukturyzowanego outputu.
Zwykła sesja marketera ma działać z instrukcji w `SKILL.md` i wąskiego snapshotu.

## Wymagany ślad

- `work_item_id` wybranego elementu kolejki;
- bieżący `current_step_id` oraz persisted planning/revision decision;
- `planning_digest`, a po zapisie tekstu także exact `revision_id` i digest;
- `source_connectors` i `evidence_ids` użyte w rekomendacji;
- GSC query rows tylko z `planning_workspace.proposal.search_demand`;
- `action_id` oraz revision binding, jeśli sesja dochodzi do `dev_draft`.

## Dozwolone przejścia

```text
queue
  -> selected snapshot
  -> scope planning-review
  -> section_map planning-review
  -> exact draft revision
  -> exact revision human review
  -> optional exact Codex child proposal
  -> revision-bound activation/readiness
  -> ActionObject validate/preview/review/confirm/impact-check/apply
  -> WordPress draft-only readback
```

Każde `409` oznacza odświeżenie snapshotu i ponowną decyzję człowieka. Nie
rekonstruuj digestu, bindingu ani payloadu z wcześniejszej odpowiedzi.

## Kształt odpowiedzi

Widoczne pola decyzyjne muszą po polsku odpowiedzieć na:

- `Decyzja teraz`;
- `Dlaczego`;
- `Co już jest zapisane`;
- `Co blokuje`;
- `Następny bezpieczny krok`;
- `Ślad WILQ`.

Nie wystarczy lista endpointów. Wynik ma wskazać jedną czynność Wilka i
zatrzymać się, jeśli brakuje jego approval, exact bindingu albo dowodu.
Identyfikatory źródeł i dowodów pozostają w `Ślad WILQ`, poniżej decyzji.

## Niedozwolone skróty

- client-owned stage POST-y do preflight/brief/draft package;
- legacy quality/revision apply poza exact revision workspace;
- `wordpress-draft-execution` i synthetic authoring preview jako substytut
  ActionObjectu;
- caller-supplied measurement outcome;
- direct OpenAI/WordPress oraz publish/update/delete.
