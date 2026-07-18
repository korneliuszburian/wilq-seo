# Pilot doradztwa i outsourcingu — aktualny wynik

## Jedna decyzja

**Dopasowanie usługi jest naprawione, ale przed planem trzeba odzyskać
inventory WordPress.** Nie budujemy struktury strony z samych zapytań GSC.

| Pole | Aktualny stan |
| --- | --- |
| Strona | `https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/` |
| Tryb | odświeżenie istniejącej treści |
| Usługa | Doradztwo i outsourcing środowiskowy |
| Karta | `ekologus_service_environmental_consulting_outsourcing` |
| Dopasowanie | `bound`; jedna rekomendowana karta po frazie „outsourcing ekologiczny” |
| Status karty | `source_backed_review_required`; wybór niepotwierdzony |
| Bieżący etap | `scope` |
| Pełny tekst | brak zapisanej rewizji |

Dawny błąd `unbound` nie występuje: URL i temat są poprawnie powiązane z
kartą doradztwa i outsourcingu, bez wyjątku zakodowanego dla tego case'u.

## Sygnał z danych

GSC zwraca 26 świeżych wierszy dla dokładnego URL-a: łącznie 50 wyświetleń,
0 kliknięć i CTR 0,00%. Najlepsza średnia pozycja 1,00 dotyczy pojedynczego
wyświetlenia, więc nie jest podstawą do claimu sukcesu.

| Zapytanie | Wyświetlenia | Kliknięcia | Śr. pozycja |
| --- | ---: | ---: | ---: |
| doradztwo środowiskowe | 7 | 0 | 20,29 |
| doradztwo z zakresu ochrony środowiska | 4 | 0 | 13,75 |
| doradztwo ochrona środowiska | 4 | 0 | 20,50 |
| usługi z zakresu ochrony środowiska | 3 | 0 | 12,33 |
| doradztwo w zakresie ochrony środowiska | 3 | 0 | 25,67 |

Część wierszy ma intencję lokalną (Śląsk, Kraków, Katowice, Bydgoszcz,
Warszawa), ale bez dokładnego dowodu Localo i decyzji o zasięgu usługi nie
wolno robić z tego lokalnej strony albo sekcji dla jednego miasta.

Źródło: `google_search_console`, odczyt 2026-07-15 22:31 UTC,
evidence `ev_refresh_refresh_google_search_console_6c051f7862d8`.

## Najważniejsza luka

WILQ potwierdza kanoniczny URL i istnienie publicznej strony, ale bieżący
snapshot nie zawiera jej H1 ani listy sekcji WordPress. Status planera to
`blocked` z kodem `missing_wordpress_section_inventory`.

To jest właściwa blokada. Bez inventory nie da się uczciwie zdecydować, co
zachować, scalić, przepisać albo usunąć. Obecne robocze nagłówki o „doradztwie
w ochronie środowiska” i „doradztwie środowiskowym Śląsk” są jedynie szkicem
kierunku, nie marketer-grade strukturą.

## Do decyzji ownera i marketera

1. Czy karta usługi poprawnie rozdziela doradztwo projektowe od stałego
   outsourcingu obsługi środowiskowej?
2. Jaki realny trigger prowadzi klienta do outsourcingu: brak kompetencji,
   przeciążenie zespołu, kontrola, raportowanie czy rozwój zakładu?
3. Jakie elementy usługi można opisać publicznie, a jakie wymagają eksperta?
4. Jaki zasięg geograficzny jest realny i czy lokalne query mają znaczenie dla
   tej jednej strony?
5. Po odzyskaniu inventory: które sekcje zachować, scalić, przepisać lub
   usunąć?

Następny bezpieczny krok: owner sprawdza kartę, a operator odświeża inventory
WordPress. Dopiero potem zatwierdzamy scope i budujemy plan.

## Ślad i blokady

- work item: `content_work_item_content_decision_https___www_ekologus_pl_oferta_doradztwo_i_outsourcing_ekologiczny`;
- input digest odczytu planera: `16f525d688f8ecbd998d212515131b7ba0e56d27ea7efbb7996de70855fdb650`;
- model na GET: `not_started`, brak próby external call;
- blockery: `service_selection_not_confirmed`, `service_card_not_approved`,
  `missing_wordpress_section_inventory`;
- rewizja/semantic review: nie dotyczy, bo revision count = 0;
- WordPress: blokują brak human review i audytu;
- pomiar: blokuje brak potwierdzonej publikacji;
- `publish_ready=false`.
