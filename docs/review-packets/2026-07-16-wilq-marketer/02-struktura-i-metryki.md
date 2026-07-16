# 2. Struktura i metryki

## Zasada

Plan nie powstaje z listy fraz. Najpierw WILQ rozlicza wszystkie dostępne
źródła, potem używa wyłącznie faktów dokładnie pasujących do strony i usługi.
Każde źródło otrzymuje status: `used`, `not_applicable`, `missing`, `stale` albo
`blocked`.

## Bieżąca ocena źródeł dla BDO

| Źródło | Status | Wpływ na plan |
| --- | --- | --- |
| WordPress | `used` | aktualny tytuł, H1 i nagłówki tworzą inventory do zachowania, scalenia, przepisania lub usunięcia po review |
| Service Profile | `blocked` | karta pasuje do usługi, ale owner jej jeszcze nie zatwierdził |
| GSC | `used` | dokładne zapytania strony i ich metryki mogą być przypisane do sekcji |
| GA4 | `missing` | bez dokładnego sygnału landing page nie wyciągamy wniosków o zachowaniu |
| Google Ads | `not_applicable` | brak ścisłego mapowania term → landing page → usługa |
| Ahrefs | `missing` | brak dokładnego cross-source sygnału dla tej strony |
| Keyword Planner | `missing` | brak developer tokena lub exact mappingu; wolumen i CPC nie są zgadywane |
| Merchant | `not_applicable` | to nie jest strona produktowa |
| Localo | `not_applicable` | brak potwierdzonej lokalnej intencji |
| Social | `not_applicable` | może użyć dopiero zatwierdzonej treści, nie steruje planem strony |

To jest stan zapisanej rundy, nie obietnica live freshness. Wygenerowanie planu
wymaga ponownego zbudowania `ContentPlanningInput`; zmiana inventory, usługi,
wiedzy, zapytań albo metryk zmienia digest i unieważnia wcześniejszy plan.

## Baseline BDO do interpretacji

- 11 aktualnych wierszy popytu GSC przypisanych do dokładnej strony;
- 65 wyświetleń, 0 kliknięć, CTR 0,00%;
- najlepsza średnia pozycja 9,00;
- główny sygnał językowy: „bdo co to”.

GSC nie jest pełnym uniwersum zapytań. Niski CTR jest sygnałem możliwego
niedopasowania tytułu, opisu lub odpowiedzi, a nie automatycznym dowodem słabej
treści.

## Decyzja dla każdej sekcji

Marketer powinien zobaczyć istniejące inventory obok rekomendacji:

- `zachowaj` — sekcja odpowiada na ważne pytanie i wymaga co najwyżej korekty;
- `scal` — kilka fragmentów odpowiada na to samo pytanie;
- `przepisz` — cel sekcji zostaje, ale odpowiedź jest niewystarczająca;
- `usuń po review` — usunięcie wymaga jawnej decyzji człowieka;
- `utwórz` — istniejąca strona nie odpowiada na udowodnione pytanie odbiorcy.

Każda planowana sekcja musi mieć stabilne `section_id`, cel, pytanie czytelnika,
dyspozycję inventory oraz dozwolone identyfikatory query, evidence i claim.
Niepewne query pozostaje `page_only`; WILQ nie zgaduje sekcji.

## Co marketer zatwierdza

1. kolejność pytań czytelnika;
2. zachowanie lub zmianę każdej istniejącej sekcji;
3. przypisanie zapytań do sekcji;
4. miejsce CTA i linków wewnętrznych;
5. elementy wymagające eksperta zamiast generowania.

Plan pozostaje niezatwierdzoną propozycją, dopóki człowiek nie zapisze decyzji.
