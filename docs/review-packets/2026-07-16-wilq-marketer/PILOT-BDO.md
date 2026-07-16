# Pilot BDO — aktualny wynik

## Jedna decyzja

**Odświeżyć istniejącą stronę, ale jeszcze nie generować tekstu.** Najpierw
owner potwierdza kartę usługi, a marketer przebudowuje mapę sekcji tak, aby
każde pytanie czytelnika miało jedno konkretne miejsce.

| Pole | Aktualny stan |
| --- | --- |
| Strona | `https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/` |
| Tryb | odświeżenie istniejącej treści |
| Usługa | BDO i sprawozdawczość środowiskowa |
| Karta | `ekologus_service_bdo_reporting` |
| Status karty | `source_backed_review_required`; wybór niepotwierdzony |
| Bieżący etap | `scope` |
| Plan człowieka | scope i mapa sekcji niezatwierdzone |
| Pełny tekst | brak zapisanej rewizji |

## Sygnał z danych

GSC zwraca 11 świeżych wierszy dla dokładnego URL-a: łącznie 65 wyświetleń,
0 kliknięć i CTR 0,00%. Najlepsza średnia pozycja w zestawie to 9,00. To
sygnał do sprawdzenia odpowiedzi strony i snippetu, nie dowód, że samo
przepisanie treści poprawi wynik.

| Zapytanie | Wyświetlenia | Kliknięcia | Śr. pozycja |
| --- | ---: | ---: | ---: |
| bdo co to | 41 | 0 | 10,49 |
| bdo | 7 | 0 | 9,00 |
| co to jest bdo | 6 | 0 | 13,67 |
| prawo bdo | 2 | 0 | 12,50 |
| bdo co to znaczy | 2 | 0 | 11,00 |

Źródło: `google_search_console`, odczyt 2026-07-15 22:31 UTC,
evidence `ev_refresh_refresh_google_search_console_6c051f7862d8`. GSC nie
pokazuje pełnego uniwersum zapytań.

## Co zastaliśmy na stronie

WordPress zwraca H1 „BDO - CO MUSI WIEDZIEĆ PRZEDSIĘBIORCA? - Ekologus” i 12
nagłówków. Najważniejsze decyzje inventory:

| Fragment | Rekomendacja do review | Dlaczego |
| --- | --- | --- |
| „Kto musi złożyć wniosek o wpis do Rejestru?” | zachować i zaktualizować ekspercko | odpowiada na ważne pytanie, ale jest twierdzeniem wysokiego ryzyka |
| pytania o ewidencję, kary i logowanie | scalić w logiczny blok FAQ po review | obecna strona jest listą luźnych odpowiedzi |
| szkolenie z 13 marca 2020 | usunąć albo zastąpić po review | nieaktualne wydarzenie rozbija główną intencję strony |
| „Może Cię również zainteresować”, case i logotyp klienta | zachować tylko jako elementy poboczne | nie mogą udawać odpowiedzi na pytanie o BDO |

Źródło inventory: `wordpress_ekologus`, evidence
`ev_refresh_refresh_wordpress_ekologus_c7eddd6d1b0e`.

## Ocena obecnego planu

WILQ proponuje odbiorcę „osoba odpowiedzialna za decyzję środowiskową w
firmie”, intencję ryzyka lub obowiązku i CTA konsultacyjne bez gwarancji
wyniku. Ten kierunek jest sensowny do review.

Obecna mapa sekcji **nie jest jeszcze wystarczająca**. Ma tylko dwa generyczne
nagłówki:

- „Co wiemy z zapytań: ochrona środowiska bdo”;
- „Co wiemy z zapytań: bdo dla kogo”.

Prawie wszystkie query są przypisane do obu sekcji przez wspólny token „bdo”.
Nie rozdziela to pytań „co to jest”, „kogo dotyczy”, „jak zacząć”, „jakie są
obowiązki” i „kiedy potrzebna jest pomoc”. Plan trzeba poprawić przed draftem.

## Do decyzji ownera i marketera

1. Czy karta usługi poprawnie opisuje odbiorcę, zakres i realne CTA?
2. Które twierdzenia o obowiązkach, terminach, karach i wyjątkach są dozwolone
   dopiero po review eksperta?
3. Czy strona ma najpierw odpowiedzieć „co to jest BDO”, a dopiero potem
   prowadzić do kwalifikacji sytuacji firmy?
4. Które z 12 obecnych elementów zachować, scalić, przepisać lub usunąć?

Po tych decyzjach następny bezpieczny krok to zatwierdzenie exact scope i mapy
sekcji. Dopiero wtedy można utworzyć modelowy plan i pełną rewizję.

## Ślad i blokady

- work item: `content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`;
- input digest odczytu planera: `a0c31f4c5d68f39a3cf67376ad508dea79601f53be19c6043dd85903772ac97e`;
- model na GET: `not_started`, brak próby external call;
- blockery: `service_selection_not_confirmed`, `service_card_not_approved`;
- rewizja/semantic review: nie dotyczy, bo revision count = 0;
- WordPress: blokują brak human review i audytu;
- pomiar: blokuje brak potwierdzonej publikacji;
- `publish_ready=false`.
