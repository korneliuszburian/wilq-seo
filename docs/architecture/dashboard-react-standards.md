# Standard React dashboardu WILQ

Ten dokument jest kontraktem utrzymaniowym dla tras dashboardu, nie instrukcją
formatowania. Celem jest, aby marketer dostał decyzję z API, a React tylko ją
czytelnie wyrenderował.

## Granice odpowiedzialności

- **Route shell**: nawigacja, wybór identyfikatora i wywołanie jednego hooka
  domenowego; nie interpretuje surowych odpowiedzi dostawców.
- **Domain query hook**: klucze React Query, `enabled` i normalizacja typów API;
  nie tworzy nowych reguł biznesowych ani copy decyzji.
- **View-model/API**: decyzja, dowody, świeżość, blocker i safe next step są
  własnością WILQ API. React nie składa ich z ID, nazw konektorów ani payloadów.
- **Presentational component**: dostaje typed props i renderuje znaczenie.
  Stan formularza i disclosure pozostaje lokalny.
- **Technical disclosure**: ActionObject, audit, payload i techniczne ID są
  poniżej pierwszej decyzji, chyba że bezpośrednio wyjaśniają blocker.

## Reguły review

1. Render ma być czysty; pochodne wartości licz w renderze, a `useMemo` stosuj
   tylko dla kosztownej pracy.
2. Nie dodawaj efektu do synchronizacji stanu, który już wynika z props/query.
3. Każda nowa trasa musi mieć jeden seam domenowy przed rozrostem layoutu.
4. Preferuj nazwane komponenty nad generycznymi fabrykami kart, gdy różni się
   znaczenie produktu.
5. Test trasy sprawdza decyzję, dowód, blocker i następny krok; nie utrwala
   przypadkowego tekstu starego route'u.

## Zastosowanie

`ContentWorkflowSurface` jest pierwszym dowodem: pobieranie kolejki, wybranego
work itemu, wzbogacenia i gotowości WordPressu znajduje się w
`contentWorkflowQueries.ts`, a route shell przekazuje wynik do stanów i
komponentów prezentacyjnych. `ActionDetailSurface` pozostaje następnym seamem:
jego query/readiness boundary należy utrzymać zgodnie z tym standardem przed
kolejnym redesignem.
