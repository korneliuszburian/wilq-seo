# Knowledge Dashboard Roast - 2026-07-07

## Werdykt

`/knowledge` miał właściwy kierunek: zaczynał od wpływu wiedzy na decyzje, a
nie od katalogu kart. Problem był subtelniejszy: sam preview potrafił pokazać
do pięciu decyzji naraz, więc pierwszy ekran znowu mógł wyglądać jak lista
poprawnych rekordów zamiast jednej decyzji review.

## Co było słabe

- Panel "Co ta wiedza zmienia w decyzjach" był dobry, ale w środku dalej
  renderował kilka kart decyzji.
- Wiedza powinna najpierw odpowiadać: "która decyzja teraz zależy od wiedzy?".
- Pełna mapa, źródła i zasady pracy powinny zostać pod przyciskami, dopóki
  operator nie potrzebuje szczegółów.

## Co zmieniono

- Preview `/knowledge` pokazuje jedną najważniejszą decyzję z wiedzy.
- Pozostałe decyzje z wiedzy są ukryte pod przyciskiem.
- Pełna mapa wiedzy, źródła wiedzy i zasady pracy nadal są dostępne w
  rozwijanych sekcjach.
- Nie dodano nowej powierzchni ani nowej warstwy guardów; zmieniono hierarchię.

## Dowód

```bash
rtk pnpm --filter @wilq/dashboard exec vitest run src/routes/KnowledgePanels.test.tsx
rtk pnpm --dir apps/dashboard typecheck
rtk pnpm --dir apps/dashboard exec playwright test e2e/knowledge-layout.spec.ts --workers=1
```

Playwright proof zapisuje screenshot:

```txt
.local-lab/proof/dashboard-knowledge/*/knowledge-decision-first.png
```

## Następny roast

- `/service-profile`: owner ma widzieć pierwszą rzecz do zatwierdzenia, nie
  katalog stanów wiedzy.
- `/actions`: operator ma widzieć "co sprawdzić przed decyzją", nie raw payload.
