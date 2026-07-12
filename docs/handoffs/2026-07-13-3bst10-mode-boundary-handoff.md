# Handoff — `wilq-seo-3bst.10`

## Decyzja

Dodano widoczną granicę trybów na głównej trasie content workflow:

- `Marketer`: decyzja, blocker i następny bezpieczny krok;
- `Audyt techniczny`: dowody, kontrakty i szczegóły workflow, z automatycznym
  otwarciem sekcji technicznej.

Nie dodano API ani nowych reguł biznesowych. Safety i write path pozostają bez
zmian.

## Dowody

- Vitest `ContentWorkflowSurface`: 16/16.
- ESLint, TypeScript, Vite build i `git diff --check`: passed.
- Live API: health `ok`; queue nadal ma 2 kandydatów i blocker
  `not_enough_actionable_candidates`.
- Browser screenshot marketer mode pokazuje przełącznik, decyzję, blocker i
  CTA above the fold; kliknięcie `Audyt techniczny` zmienia opis zakresu i
  otwiera techniczne szczegóły.

## Następny krok

Odczytać `bd ready`; następny potwierdzony task dotyczy dalszego marketer-mode
IA/decision queue albo screenshot usefulness packet. Nie kopiować tego trybu do
nowego endpointu.
