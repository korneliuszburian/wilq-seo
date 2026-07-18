# WILQ — dwa realne piloty treści do decyzji marketera

To nie jest opis architektury ani demonstracja testów. To cztery krótkie
dokumenty z aktualnym wynikiem pracy WILQ dla dwóch istniejących stron
Ekologus. Stan odczytano z lokalnego WILQ API 16 lipca 2026 po odświeżeniu
procesu API.

## Decyzja w 30 sekund

Obie strony warto dalej analizować jako **odświeżenie istniejącej treści**, ale
żadna nie jest jeszcze gotowa do wygenerowania finalnego tekstu.

| Pilot | Co już wiemy | Co blokuje następny etap |
| --- | --- | --- |
| [BDO](PILOT-BDO.md) | 65 wyświetleń, 0 kliknięć, 11 zapytań; istniejące H1 i 12 nagłówków WordPress są dostępne | trzeba potwierdzić kartę usługi i poprawić zbyt ogólną mapę sekcji |
| [Doradztwo i outsourcing](PILOT-DORADZTWO-OUTSOURCING.md) | poprawne przypisanie usługi; 50 wyświetleń, 0 kliknięć, 26 zapytań | trzeba potwierdzić kartę usługi i pobrać aktualne H1 oraz sekcje WordPress |

Najbardziej wartościowa decyzja ownera teraz: przejrzeć obie karty usług na
podstawie sekcji „Do decyzji” w dokumentach pilotów. Bez tego model pozostaje
celowo zablokowany i nie produkuje tekstu z niezatwierdzonych twierdzeń.

## Co faktycznie działa

- ten sam workflow rozpoznaje dwie różne strony i dwie różne karty usług;
- dane GSC i WordPress są świeże w progu 48 godzin;
- WILQ rozróżnia wynik możliwy do planowania od zgody na draft;
- odczyt planu nie uruchamia modelu, a blokady są jawne;
- brak rewizji blokuje semantic review, WordPress i pomiar zamiast tworzyć
  fikcyjny wynik;
- obietnice wzrostu pozycji, leadów i widoczności pozostają zablokowane do
  zakończonego okna pomiaru.

## Co jeszcze nie działa wystarczająco dobrze

- żadna z dwóch kart usług nie ma `approved_current`;
- BDO ma inventory, ale obecne dwie sekcje planu są generyczne i przypisują
  niemal każde zapytanie do obu sekcji;
- outsourcing nie ma w snapshotcie aktualnego H1 ani listy sekcji WordPress;
- nie istnieje realna pełna rewizja tych pilotów, więc nie ma page preview,
  semantic findings, diffu ani WordPress dry-run dla konkretnego tekstu;
- nie wykonano realnego Wilku UAT ani publikacji.

## Jak użyć paczki

1. Przejrzyj [pilot BDO](PILOT-BDO.md).
2. Przejrzyj [pilot doradztwa i outsourcingu](PILOT-DORADZTWO-OUTSOURCING.md).
3. Wypełnij odpowiednią część [formularzy oceny](FORMULARZE-OCENY.md).

Najpierw potrzebujemy decyzji o usługach i planie. Ocena finalnego tekstu ma
sens dopiero po zapisaniu exact revision; ta paczka nie udaje, że tekst już
istnieje.
