# Content Workflow Dashboard Roast - 2026-07-07

## Werdykt

`/content-workflow` miał sensowny tor pracy i realne bramki, ale po panelu
"co dziś zrobić" zbyt długo prowadził marketera przez kolejkę, proof, WordPress
readiness, aktywację szkicu, write readiness, Claim Ledger, wzbogacenie i kroki
workflowu zanim pokazał właściwe przyciski operatora.

To jest dobry backendowy system kontroli, ale słaby pierwszy ekran. Marketer
powinien najpierw zobaczyć decyzję i dostępne bezpieczne akcje, a dopiero potem
dowody oraz techniczne readiness.

## Co było słabe

- `Decyzje operatora` były niżej niż techniczne panele gotowości.
- `Kolejka tematów` była ważniejsza wizualnie niż praca na wybranym work itemie.
- WordPress/ACF/write readiness zajmowały środek ekranu przed kontrolkami
  pracy, mimo że nie wolno jeszcze publikować ani robić live write.
- Ekran bronił bezpieczeństwa, ale nie prowadził wystarczająco szybko do
  następnego działania.

## Co zmieniono

- `Decyzje operatora` są teraz od razu po panelu "Workflow treści: co dziś
  zrobić".
- `Kolejka tematów`, proof, WordPress readiness, Claim Ledger, enrichment,
  kroki workflowu i safety panels zostają niżej jako kontekst.
- Nie dodano nowych kart. Zmieniono tylko hierarchię pierwszego ekranu.

## Dowód

```bash
rtk pnpm --filter @wilq/dashboard exec vitest run src/routes/ContentWorkflowSurface.test.tsx
rtk pnpm --dir apps/dashboard typecheck
rtk pnpm --dir apps/dashboard exec playwright test e2e/content-workflow-layout.spec.ts --workers=1
```

Playwright proof zapisuje screenshot:

```txt
.local-lab/proof/dashboard-content-workflow/*/content-workflow-decisions-first.png
```

## Następny roast

- `/knowledge`: czy pokazuje decyzję review, czy katalog rekordów.
- `/service-profile`: czy owner widzi co ma zatwierdzić, czy tylko linię
  genealogii wiedzy.
- `/actions`: czy pierwszy ekran mówi "co sprawdzić", czy od razu pokazuje
  payloady.
