# 5. Stan pipeline'u treści i metryk

Ten widok rozdziela działający kontrakt, lokalną implementację w toku, brakujący
produkt i zewnętrzną decyzję. Zielony test nie zastępuje użytecznego wyniku dla
marketera.

| Etap | Co musi istnieć | Stan | Następna praca |
| --- | --- | --- | --- |
| Wybór strony | exact work item, canonical URL, cel refresh | działa | utrzymać jeden selektor w `/content-workflow` |
| Wybór usługi | dozwolone candidates, lifecycle, reasons, jawne potwierdzenie | działa dla obu pilotów | owner review obu kart |
| Dynamiczne wejście | inventory, fakty, 10 ocen źródeł, queries, claims, metryki, digest | działa kontrakt v1 | poszerzać wyłącznie przez exact lineage |
| Persistowany plan | idempotentny POST, immutable history, stale `409`, brak model call na GET | działa | marketer review pełnej strategii i section map |
| Pełny dokument | wszystkie page assets i jeden document digest, kompatybilność v1 | implementacja lokalna w toku | fixed-point review, commit i aktywacja |
| Initial full draft | jeden jawny POST po aktualnym, zatwierdzonym planie | brak | zbudować atomowy zapis bez fallbacku |
| Page preview | finalny układ strony, nawigacja po sekcjach, meta/FAQ/CTA/linki | brak | podłączyć do zapisanej rewizji v2 |
| Quality gates | deterministyczne bramki pełnego digestu | częściowo | objąć wszystkie page assets i pełny dry-run |
| Semantic review | persistowany advisory review exact digestu | brak | dodać bez auto-approval i vendor write |
| Poprawki | tylko wybrane sekcje, immutable child revision | częściowo | podłączyć do pełnego dokumentu i findings |
| WordPress | exact ActionObject, dry-run, nowy draft na devie | mechaniczny kontrakt istnieje | pełny renderer v2 i osobne human confirmation |
| Pomiar | publication-bound baseline, observation i learning proposal | kontrakt istnieje | użyć dopiero po realnej publikacji ownera |
| Realny pilot | BDO i outsourcing tym samym workflow | zablokowany | owner review, trzy role review i realny Wilku UAT |

## Najważniejsze braki, których nie wolno ukryć

- 0 kart usług ma obecnie udowodniony w tej paczce status `approved_current`;
- Keyword Planner wymaga developer tokena;
- realny Wilku UAT nie został wykonany;
- WordPress draft wymaga osobnego potwierdzenia;
- aktywacja nowych tabel w realnym local state wymaga backupu i maintenance window;
- auth, TLS, tenant isolation, monitoring, HA i credentials pozostają osobnymi
  produkcyjnymi blockerami.

## Definicja domknięcia dwóch pilotów

Pipeline nie jest skończony, dopóki oba case'y nie mają:

1. owner-reviewed karty usługi;
2. planu utworzonego z aktualnego `planning_input_digest`;
3. pełnej, trwałej rewizji ze wszystkimi page assets;
4. deterministic review bez critical/high findings;
5. semantic findings związanych z exact digestem;
6. ocen 10/10 od SEO reviewera, content editora i marketera;
7. WordPress dry-run oraz human-confirmed ActionObject;
8. realnego Wilku UAT potwierdzającego czas do decyzji i użyteczność.

Do czasu spełnienia tych warunków WILQ może być mechanicznie sprawny, ale nie
może twierdzić, że dostarczył gotową produkcyjnie treść 10/10.
