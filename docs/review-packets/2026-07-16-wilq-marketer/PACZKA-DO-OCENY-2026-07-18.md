# WILQ — paczka do oceny przez marketera

Stan: 18 lipca 2026 · środowisko lokalne, read-only · WordPress draft-only

## Co masz sprawdzić

Otwórz `http://127.0.0.1:5173/content-workflow`. Na pierwszym ekranie zobaczysz
pełny read-only inventory WordPress (aktualnie 601 adresów), wyszukiwarkę,
status materiału, dostępne metryki i rozpoznane sekcje ACF. Rekomendowane
okazje są osobną kolejką — nic nie jest wybierane automatycznie.

Aktualny coverage rozdziela zakresy: podstawowy sitemap ma 102/102 adresy,
a publiczna mapa dodatkowe 500 adresów; katalog deduplikuje oba źródła. To
potwierdza zakres adresów, ale nie oznacza kompletności pól ACF dla każdej strony.

Wyszukaj dowolną stronę, kliknij `Sprawdź materiał`, a następnie `Rozpocznij
workflow`. Dla adresu spoza kolejki WILQ tworzy jego identyfikator workflow na
podstawie dokładnego URL-u. Pierwszy ekran powinien pokazać wybraną stronę,
decyzję, podstawowe metryki, źródła i następny krok; pełny materiał WordPress
ładuje się osobno. Treść może pochodzić z WordPress REST/ACF albo z
wyrenderowanego `the_content` — panel pokazuje, którą ścieżkę odczytu wybrał.

Nie oceniasz tu publikacji ani wzrostu wyników. Oceniasz, czy z ekranu da się
podjąć właściwą decyzję bez pomocy developera.

## Dowód na aktualnym API

Testowany adres BDO:
`https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/`

- decyzja: odśwież istniejącą treść;
- GSC: 266 wyświetleń, 1 kliknięcie, CTR 0,38%, 18 zapytań, najlepsza średnia pozycja 8,50;
- okres GSC: 15 lipca 2026 — pojedynczy exact snapshot, nie trend; wcześniejsze liczby z paczki zostały zastąpione przez nowszy odczyt;
- WordPress: 789 słów z odczytu materiału, 12 rozpoznanych nagłówków, ACF dostępny;
- źródła: WordPress ekologus.pl i Google Search Console;
- świeżość: GSC settled/partial, GA4 settling/unverified;
- bezpieczny krok: sprawdzić materiał, wybrać kartę usługi i wygenerować plan;
- realny plan BDO został już zapisany w API (6 sekcji, 4 FAQ, 2 CTA), ale pełny
  tekst i WordPress draft pozostają zablokowane do wymaganych review.

### Co oznaczają adresy bez materiału

Inventory może pokazać `Sam adres`, `Sama struktura`, `Skrót treści` albo
`Treść + struktura`. `Sam adres` nie oznacza błędu ani pustej strony: REST/ACF
nie zwróciły wystarczającego materiału w snapshotcie, więc przy świadomym
wyborze WILQ wykonuje jeden read-only odczyt publicznego HTML. Taki materiał ma
status `review-required` i nie odblokowuje draftu bez potwierdzenia człowieka.

Karty usług są dopasowywane dopiero po wyborze strony. Dwie karty pilotowe
(BDO oraz doradztwo i outsourcing) mają obecnie `approved_current`; pozostałe
karty są widoczne, ale pozostają `wymaga review` i nie mogą zasilić produkcyjnego
draftu.

WILQ API ma 12 konektorów, 9 skonfigurowanych i 2 bez credentials. Brak danych
nie jest zastępowany domysłem.

### Baza wiedzy i materiały Ekologusa

WILQ widzi manifest 15 zatwierdzonych, oczyszczonych materiałów, ale ich
kontrolowany import excerptów nie został jeszcze aktywowany (`import_pending
15/15`). Nie oznacza to, że model może czytać surowe transkrypcje. Przed pełnym
tekstem trzeba wykonać import z checksumem, lineage i jawną decyzją review.

## Formularz zwrotny

Wypełnij [KARTĘ-OCENY-DO-ODESLANIA.md](KARTA-OCENY-DO-ODESLANIA.md). Odpowiedz
krótko:

1. Czy w 30 sekund wiesz, którą stronę wybrano i co należy zrobić?
2. Czy metryki są zrozumiałe i wystarcza ich do decyzji?
3. Czy widzisz, czego brakuje i dlaczego plan jest zablokowany?
4. Czy znalazłeś maksymalnie trzy rzeczy, które trzeba poprawić?

To jest paczka do realnego Wilku UAT. Bez wypełnionej karty nie oznaczamy
narzędzia jako gotowego dla marketera.

## Artefakty techniczne

- browser proof: `proof/` oraz `WILQ-DEMO-DZIALAJACEGO-WORKFLOW.webm`;
- aktualny fixed point: sprawdź `git rev-parse --short HEAD` przed nagraniem;
- wynik completion check: brak realnego UAT — cel pozostaje otwarty;
- zasady i kolejność: [`PLANS.md`](../../../../PLANS.md).
