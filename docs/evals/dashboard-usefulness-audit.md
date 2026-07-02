# WILQ dashboard usefulness audit

- API: `http://127.0.0.1:8000`
- Surfaces: 15
- Demo-ready: 13
- Review-ready: 2
- Blocked: 0
- Pass: `true`

| Ekran | Status | Gotowość | Score | Rekordy | Ślady | Dowody | Akcje | Decyzje | Następny krok |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Centrum pracy | `production` | `demo_ready` | 10 | 0 | 0 | 22 | 10 | 20 | Najpierw otwórz widok Merchant i przejrzyj kolejkę problemów pliku produktowego. |
| Google Ads | `production` | `demo_ready` | 10 | 0 | 0 | 2 | 9 | 55 | Użyj wierszy kampanii do sprawdzenia aktywności. Przed wnioskami o stracie budżetu, koszcie pozyskania celu, zwrocie z reklam albo wykluczeniach uzupełnij brakujące dane. |
| Merchant | `production` | `demo_ready` | 10 | 0 | 0 | 4 | 1 | 42 | Można użyć danych do kolejki sprawdzenia bez dodatkowego odświeżenia. |
| Treści | `production` | `demo_ready` | 10 | 0 | 0 | 16 | 5 | 55 | Przejdź przez top decyzje contentowe: odśwież, scal, utwórz albo zablokuj. Potem sprawdź w WILQ tylko właściwą akcję. |
| GA4 | `production` | `demo_ready` | 10 | 0 | 0 | 19 | 1 | 33 | Można użyć danych GA4 do sprawdzenia bez dodatkowego odświeżenia. |
| Service Profile | `production` | `demo_ready` | 10 | 0 | 0 | 1 | 13 | 36 | Przejrzyj karty review-required i luki usługowe z Wilkiem przed użyciem ich jako production-depth. |
| Workflow treści | `production` | `demo_ready` | 10 | 0 | 0 | 2 | 0 | 36 | Zacznij od istniejącej treści: zachowaj istniejący adres albo przygotuj odświeżenie/scalenie z dowodami. |
| Ahrefs | `production` | `demo_ready` | 10 | 0 | 0 | 8 | 0 | 20 | Połącz luki Ahrefs z GSC i WordPress, potem przygotuj kolejkę sprawdzenia. |
| Localo | `production` | `demo_ready` | 10 | 0 | 0 | 2 | 1 | 35 | Użyj tych danych jako dowodu dla sprawdzenia Localo. |
| Demand Gen | `experimental` | `review_ready` | 10 | 0 | 0 | 12 | 1 | 1 | Sprawdź gotowość Demand Gen w WILQ jako akcję tylko do przeglądu. Zanim WILQ pokaże propozycje uruchomienia albo zmiany trybu kampanii, potwierdź dostępność danych o jakości str... |
| Publikacje social | `experimental` | `review_ready` | 10 | 0 | 0 | 7 | 2 | 2 | Przygotuj szkice do sprawdzenia z dowodami; publikacja i claim o braku powtórzeń pozostają zablokowane do czasu konfiguracji uprawnień LinkedIn/Facebook oraz sprawdzenia histori... |
| Akcje | `production` | `demo_ready` | 10 | 19 | 0 | 41 | 19 | 0 | Użyj po wybraniu konkretnej akcji z Centrum pracy; to rejestr dowodów, walidacji i blokad, nie kolejka startowa. |
| Szanse | `production` | `demo_ready` | 10 | 5 | 0 | 22 | 9 | 0 | Użyj jako rejestr szans po Centrum pracy; decyzję uruchamiaj przez powiązaną akcję i dowody. |
| Procesy | `production` | `demo_ready` | 10 | 15 | 0 | 20 | 10 | 15 | Otwórz Centrum pracy i przejdź decyzje według priorytetu. |
| Baza wiedzy | `production` | `demo_ready` | 10 | 15 | 49 | 0 | 0 | 0 | Użyj do trace i review źródeł wiedzy; sama karta nie oznacza production-depth bez zatwierdzenia. |
