# Handoff — `wilq-seo-3bst.11`

## Decyzja

Pierwszy viewport `/content-workflow` został uproszczony do języka operatora:
„Podgląd na devie”, konkretne działanie i jasne „Nic nie zostanie
opublikowane”. Techniczne nazwy ścieżki zapisu nie są już głównym copy karty;
pozostają w szczegółach i kontraktach.

## Dowody

- `ContentWorkflowSurface.tsx` i test aktualizują copy bez zmiany API.
- Vitest: 15/15; ESLint; TypeScript; Vite build; `git diff --check` — passed.
- Browser screenshot po live API pokazuje public canonical, decyzję usługi,
  blocker i CTA preview above the fold; technical details remain below fold.

## Następny krok

Odczytać `bd ready` i wybrać kolejny istniejący task marketer-mode lub harness.
Nie powtarzać copy dla content route; nowe zmiany UI muszą mieć osobny screenshot
i usefulness proof.
