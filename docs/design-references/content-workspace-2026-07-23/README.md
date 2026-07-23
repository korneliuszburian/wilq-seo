# Referencja projektu: Content & SEO workspace

Status: **kierunek produktu i hierarchii interfejsu**. Te kadry nie są danymi
referencyjnymi, specyfikacją kontraktu ani dowodem stanu produkcyjnego.

## Pliki

| Plik | Rola w produkcie | Co zachować | Czego nie kopiować literalnie |
| --- | --- | --- | --- |
| `01-entry-intent.png` | wejście do Treści i SEO | wybór „Odśwież istniejącą” lub „Utwórz nową”, wyszukiwarka, ograniczona lista spraw do pracy | liczników i rekomendacji bez API-owned źródeł; inventory jako domyślnego obiektu pracy |
| `02-page-context.png` | krótki kontekst wybranej strony | tytuł, URL, usługa, prosty obraz etapów pracy i jedno działanie | literalnego `refresh_existing`, obietnicy automatycznego przygotowania treści, technicznej dostawy WordPressa jako bieżącego kroku |
| `03-current-page-workspace.png` | widok aktualnej strony w workspace | zakładek Obecna strona / Nowa wersja / Porównanie, outline’u, szerokiego canvasu treści, wtórnego kontekstu | sugestii, że publiczna strona jest targetem dev; CTA prowadzącego do WordPressa przed target mappingiem |
| `04-section-comparison.png` | porównanie dokumentu sekcja po sekcji | jawnego „przed → po”, nawigacji po sekcjach, źródeł drugorzędnych i jednego CTA do review | wymyślonych trendów, scoringu intencji, statusów zmian bez danych i automatycznej interpretacji semantycznej |

## Stałe zasady copy i interakcji

* Pierwszy viewport odpowiada na: nad jaką stroną pracuję, co jest obecnie,
  jaki dokument przygotowuję i co mam zrobić teraz.
* Główna powierzchnia używa polskiego języka marketera. Nie pokazuje nazw
  endpointów, `work_item_id`, `revision_digest`, connectorów, `authoring_mode`,
  surowych statusów ani terminów ACF/Gutenberg.
* Dokument, publiczne źródło i target WordPress są trzema różnymi obiektami.
  Nieznany target nie blokuje pracy nad dokumentem; nie może też wyglądać jak
  gotowość do publikacji.
* Każdy widoczny sygnał, liczba, status lub różnica pochodzi z typed API albo
  jest jawnie przedstawiony jako niedostępny. Nie ma zer, trendów, score’ów ani
  mapowań „dla wyglądu”.
* Jeśli nie istnieje potwierdzona relacja sekcji źródło → dokument, porównanie
  mówi to wprost. Nigdy nie dopasowuje sekcji heurystycznie tylko po tytule.
* Kontekst techniczny, lineage, target, ograniczenia i raw identity są
  drugorzędne: disclosure lub panel pomocniczy, nie ściana kart przed treścią.
* Mobile zachowuje tę samą kolejność informacji w jednej kolumnie, bez poziomego
  overflow i bez ściskania dwóch wersji sekcji obok siebie.

## Integralność plików

* `01-entry-intent.png` — SHA-256 `b50c8484c38cdec9fe1a9bd6fc85d13dd0fdd7a9b97d845ef5852a6d34c37044`
* `02-page-context.png` — SHA-256 `5cbb7154865d7bf1b2c4aa586cb504cfcc02dea50a5e6cb6588ae771dc82a884`
* `03-current-page-workspace.png` — SHA-256 `49bbee67b3d6441915ccf4c572a92393024ef63f3e7db7ddc5b2bd95d567cbd5`
* `04-section-comparison.png` — SHA-256 `fd82ae33b7ec01df78d6d78e2b272a5200431beb03b9a8375c5c14549509695c`
