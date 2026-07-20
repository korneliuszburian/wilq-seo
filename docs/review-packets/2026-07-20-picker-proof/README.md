# Picker proof — 2026-07-20

Aktualny browser proof dla `/content-workflow` na outsourcingowym work itemie:

- `outsourcing-desktop-scope.png` — 1440×900;
- `outsourcing-mobile-scope.png` — 390×844.

Sprawdzone na live managed stack:

- pierwszy ekran pokazuje stronę, usługę, następny krok i realne metryki;
- główny picker zachowuje kolejkę kandydatów;
- pełny inventory otwiera się progresywnie przez wyszukiwarkę tytułu/adresu;
- wyszukanie `bdo-co-musi` zwraca dokładny adres BDO;
- mobile `scrollWidth=390` przy viewport `390`, bez poziomego overflow.

To jest syntetyczny/browser proof interfejsu, nie Wilku UAT ani dowód jakości treści.
