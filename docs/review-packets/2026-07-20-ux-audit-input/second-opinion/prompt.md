# External review — pierwszy viewport `/content-workflow`

Jesteś niezależnym principal product designerem i reviewerem UX dla WILQ,
narzędzia marketingowego Ekologus. Nie masz dostępu do lokalnego dashboardu:
oceniasz wyłącznie aktualne screenshoty i fakty API z `README.md` w tym folderze.

## Kontekst produktu

WILQ ma prowadzić marketera przez konkretną pracę nad stroną. API jest jedynym
źródłem prawdy dla strony, usługi, metryk, świeżości, blokad i rewizji. Nie wolno
proponować wymyślonych metryk, magicznych score’ów, automatycznej publikacji,
bezpośredniego WordPress write ani nowej ścieżki modelowej.

Poprzedni fixed point `9e09fd13` został zaakceptowany: warsztat zapisuje
`content_html` jako exact revision i nie uruchamia WordPressa. Nie oceniasz tu
HTML authoringu, generowania Codexa, review, handoffu ani selektora wszystkich
adresów.

## Materiał do obejrzenia

1. `bdo-current-desktop-first-viewport.png`
2. `bdo-current-mobile-first-viewport.png`
3. `bdo-current-desktop-sources-open.png`
4. `README.md` — aktualny, ograniczony kontekst API i proof sieciowy.

## Proponowany pojedynczy Execution goal

Po załadowaniu `/content-workflow` marketer widzi w pierwszym viewporcie:

1. jaką stronę edytuje;
2. dla jakiej usługi;
3. że wynikiem jest **„Wersja robocza HTML do review”**;
4. dlaczego warto zająć się nią teraz;
5. jedno właściwe następne działanie.

### In scope

- zwarty kontekst: rzeczywisty tytuł WordPress, URL i usługa;
- rezultat „Wersja robocza HTML do review” oraz jeden, jasny stan aktualności
  rewizji;
- zastąpienie dużej karty „Następny krok” zwartym stanem z jednym istniejącym
  CTA;
- zastąpienie siatki „Decyzja dla strony” krótkim „Dlaczego teraz?” wyłącznie z
  obecnego sygnału GSC i ograniczenia GA4;
- ten sam układ na mobile: bez drugiego nagłówka modułu i bez wypchnięcia CTA
  poza pierwszy viewport.

### Out of scope

- selektor strony, inventory i wybór wszystkich 601 adresów;
- warsztat HTML, `content_html`, zapis rewizji, mapa/nawigacja sekcji;
- Codex, generowanie, prompty i review;
- paczka HTML, WordPress dev i każdy WordPress write;
- nowe metryki, źródła, score lub zmiana interpretacji danych.

### Nienaruszalne kontrakty

- exact revision, lineage i review pozostają bez zmian;
- HTML jest wynikiem redakcyjnym, a WordPress dev tylko opcjonalnym handoffem;
- brak wymyślonych danych; pojedynczy GSC snapshot nie jest trendem;
- zachowanie wyboru strony oraz głównego CTA pozostaje funkcjonalnie to samo;
- otwieranie i zamykanie „Źródeł i ograniczeń” nie tworzy rewizji, nie generuje
  treści i nie wykonuje WordPress write.

## Kryteria akceptacji implementacji

1. Desktop 1440×900 odpowiada bez przewijania na pięć pytań z goalu.
2. iPhone 14 (390×844) pokazuje te same pięć odpowiedzi i CTA; brak poziomego
   overflow.
3. Pokazany tytuł jest tytułem WordPress; zapytanie `bdo co to` nie udaje tytułu
   strony.
4. Stan rewizji pojawia się tylko raz i mówi jasno, czy jest aktualny wobec
   bieżącego kontekstu.
5. „Dlaczego teraz?” komunikuje 181 wyświetleń / 0 kliknięć z dostępnego GSC
   odczytu oraz brak exact GA4 bez dopowiadania trendu lub okresu.
6. Źródła są na żądanie, nie jako domyślny pierwszy ekran.
7. Jest jedno wizualnie nadrzędne CTA; detale i linki nie konkurują z nim.
8. Proof widoku nie wykonuje rewizji, generowania, review, handoffu ani
   WordPress write.

## Zadanie reviewera

Wydaj jeden werdykt: **ACCEPT** albo **NEEDS_CHANGES** dla powyższego
Execution goalu jako następnego małego pionowego slice’a.

Następnie dostarcz:

1. Najwyżej pięć konkretnych obserwacji z obecnych kadrów — każda z dowodem w
   pliku, skutkiem dla marketera i minimalną zmianą w scope.
2. Weryfikację, czy scope jest wystarczająco wąski i czy czegoś krytycznego nie
   brakuje, aby kryteria dało się uczciwie udowodnić.
3. Jeżeli werdykt to `NEEDS_CHANGES`, przepisz tylko konieczne fragmenty goalu;
   nie proponuj nowego programu prac ani listy życzeń.
4. Jeden docelowy układ pierwszego viewportu w kolejności informacji, bez
   mockupów i bez nowych danych/API.
5. Dokładny browser proof desktop/mobile, który rozróżnia sukces od obecnego
   stanu.

Pisz po polsku. Bądź rygorystyczny wobec powtórzeń, ściany kart i języka
systemowego, ale nie poszerzaj scope’u o inventory, generowanie lub WordPress.
