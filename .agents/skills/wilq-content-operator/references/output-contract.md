# Content Operator — kontrakt odpowiedzi

Czytaj tylko podczas evala albo debugowania formatu odpowiedzi. `SKILL.md`
jest właścicielem normalnego przebiegu sesji.

Widoczna odpowiedź po polsku zawiera kolejno:

- `Jedna decyzja`;
- `Dlaczego` — źródło i maksymalnie kilka faktów, bez wymyślonych metryk;
- `Co już jest` — exact plan, rewizja lub review, jeśli istnieje;
- `Co blokuje` — tylko rzeczywisty blocker;
- `Następny bezpieczny krok` — jedna czynność;
- `Ślad WILQ` — ID i dowody pod decyzją, nie nad nią.

## Minimalny ślad

- istniejąca strona: `work_item_id`, planning input/proposal digest, a po
  utworzeniu tekstu `revision_id` oraz revision digest;
- nowa strona: `brief_id`, foundation, proposal/digest i revision identity;
- delivery: action ID wyłącznie po utworzeniu ActionObjectu;
- measurement: deployment ID i deployment-bound window tylko po potwierdzonym
  publicznym wdrożeniu.

## Niedozwolone skróty

- brak `section_map`, legacy snapshotu i starego WordPress execution;
- brak client-owned metryk, digestów, URL-i lub measurement outcome;
- brak direct OpenAI/WordPress i brak publish/update/delete;
- brak twierdzenia o sukcesie SEO, leadach lub publikacji bez właściwego
  persisted dowodu.
