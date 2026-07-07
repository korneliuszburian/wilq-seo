# Content Dashboard Roast - 2026-07-07

## Werdykt

`/content-planner` miał już dobre dane i sensowną wybraną decyzję, ale ekran
nadawał za duży priorytet statusowi danych, preflightowi i powtarzalnej
kolejce. To tworzyło wrażenie "nasranych kart": marketer mógł widzieć dużo
poprawnych informacji, ale niekoniecznie jedną decyzję do wykonania.

## Co było słabe

- Pierwsza konkretna decyzja contentowa była pod statusem danych i preflightem.
- Panel `Treści: co dziś zrobić` powtarzał tę samą funkcję co selected decision
  i pełny przegląd.
- `Stan danych treści` jest ważny, ale nie powinien otwierać ekranu, jeśli
  WILQ ma już jedną wybraną decyzję i bezpieczny następny krok.
- Audit ilościowy dawał `/content-planner` 10/10, ale nie wykrywał problemu
  hierarchii informacji.

## Co zmieniono

- Selected decision jest teraz pierwszą sekcją po nagłówku route.
- `Stan danych treści` i `Czy można pisać?` są niżej jako kontekst, nie jako
  główna odpowiedź.
- Usunięto duplikujący panel `Treści: co dziś zrobić` z defaultowego widoku.
- Pełna kolejka, proof, bramy i akcje nadal są dostępne w rozwijanych sekcjach.

## Dowód

```bash
rtk pnpm --filter @wilq/dashboard exec vitest run src/routes/App.test.tsx -t "content route renders condensed selected decision"
rtk pnpm --filter @wilq/dashboard exec vitest run src/routes/ContentDiagnosticSurface.test.ts
rtk pnpm --dir apps/dashboard typecheck
rtk pnpm --dir apps/dashboard exec playwright test e2e/content-planner-layout.spec.ts --workers=1
```

Playwright proof zapisuje screenshot:

```txt
.local-lab/proof/dashboard-content-planner/*/content-planner-decision-first.png
```

## Następny roast

- `/content-workflow`: sprawdzić, czy workflow nie jest maszyną do kart zamiast
  prowadzić przez jeden work item.
- `/knowledge` i `/service-profile`: sprawdzić, czy pokazują decyzję ownera,
  a nie katalog wiedzy.
- `/actions`: surowe payloady muszą zostać pod spodem; pierwsza odpowiedź ma
  mówić "co sprawdzić przed decyzją".
