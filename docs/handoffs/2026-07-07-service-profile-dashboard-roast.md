# Service Profile Dashboard Roast - 2026-07-07

## Werdykt

`/service-profile` miał dobry pierwszy panel review, ale od razu po nim
pokazywał pełny katalog gotowości wiedzy: approval readiness, source coverage,
luki, usługi, claim policy, prywatne propozycje i akcje review. To było
poprawne audytowo, ale słabe jako ekran dla Wilka/ownera.

Service Profile ma najpierw odpowiedzieć: "co mam zatwierdzić albo odrzucić
teraz?", a dopiero potem pokazywać pełny katalog źródeł.

## Co zmieniono

- Pierwszy ekran zostawia `Wiedza Ekologus: co dziś sprawdzić` i pierwszy
  review item.
- Pełny przegląd wiedzy jest ukryty pod przyciskiem.
- Gotowość zatwierdzenia, audyt pokrycia, luki, sekcje usług, claim policy,
  źródła prywatne i akcje review nadal są dostępne po rozwinięciu.
- Nie dodano nowej warstwy review; zmieniono hierarchię informacji.

## Dowód

```bash
rtk pnpm --filter @wilq/dashboard exec vitest run src/routes/ServiceProfileSurface.test.tsx
rtk pnpm --dir apps/dashboard typecheck
rtk pnpm --dir apps/dashboard exec playwright test e2e/service-profile-layout.spec.ts --workers=1
```

Playwright proof zapisuje screenshot:

```txt
.local-lab/proof/dashboard-service-profile/*/service-profile-review-first.png
```

## Następny roast

- `/actions`: surowe payloady i ActionObject szczegóły muszą zostać pod
  marketer-readable "co sprawdzić przed decyzją".
