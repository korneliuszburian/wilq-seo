# Pakiet do second opinion UX/UI

Ten folder zawiera aktualny baseline działającego `/content-workflow` oraz
prompt dla niezależnego reviewera.

## Screenshoty

| Plik | Viewport | Stan |
| --- | ---: | --- |
| `bdo-desktop-full.png` | 1440×8372 | BDO, pełny ekran desktop |
| `outsourcing-desktop-full.png` | 1440×8372 | outsourcing, pełny ekran desktop |
| `bdo-mobile-full.png` | 390×6475 | BDO, pełny ekran mobile |
| `outsourcing-mobile-full.png` | 390×6475 | outsourcing, pełny ekran mobile |
| `bdo-desktop-first-viewport.png` | 1440×900 | BDO, pierwszy viewport |
| `outsourcing-desktop-first-viewport.png` | 1440×900 | outsourcing, pierwszy viewport |
| `bdo-mobile-first-viewport.png` | 390×844 | BDO, pierwszy viewport |
| `outsourcing-mobile-first-viewport.png` | 390×844 | outsourcing, pierwszy viewport |
| `bdo-desktop-first-slice-live.png` | 1440×900 | BDO, po odchudzeniu kolejki i dodaniu kart metryk |
| `bdo-mobile-first-slice-live.png` | 390×844 | BDO, po odchudzeniu kolejki i dodaniu kart metryk |
| `bdo-desktop-no-duplicate-banner.png` | 1440×900 | BDO, aktualny ekran po usunięciu powtórzonego bannera freshness |
| `bdo-production-desktop-first-viewport.png` | 1440×900 | Production-ready hero/usługa/next step/evidence, desktop |
| `bdo-production-mobile-first-viewport-v2.png` | 390×844 | Production-ready header, hero/usługa/next step, mobile |
| `bdo-stale-scope-action.png` | 1440×900 | Live stale-scope state with explicit next action |
| `bdo-scope-final-desktop.png` | 1280×640 | Live current fixed point, compact hero and stale-scope CTA |
| `bdo-scope-final-form.png` | 1280×640 | Live post-CTA plan/page-assets viewport |
| `bdo-scope-final-mobile-v2.png` | 390×844 | Live mobile fixed point with explicit stale-scope CTA |

Zrzuty są wykonane z lokalnego dashboardu po zakończeniu ładowania i zostały
sprawdzone wizualnie po zapisie. Pliki `*-first-slice-live.png` pokazują aktualny
fixed point po pierwszym slice UX; wcześniejsze pliki pozostają baseline'em do
porównania.

## Uruchomienie

```text
http://127.0.0.1:5173/content-workflow
```

Prompt do reviewera znajduje się w `prompt.md`.
