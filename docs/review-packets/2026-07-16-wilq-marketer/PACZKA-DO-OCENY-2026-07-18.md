# WILQ — paczka do oceny przez marketera

Stan: 18 lipca 2026 · środowisko lokalne, read-only · WordPress draft-only

## Co masz sprawdzić

Otwórz `http://127.0.0.1:5173/content-workflow`, wybierz dowolny adres z
inventory i kliknij rozpoczęcie workflow. Pierwszy ekran powinien pokazać
wybraną stronę, decyzję, podstawowe metryki, źródła i następny krok; pełny
materiał WordPress ładuje się osobno.

Nie oceniasz tu publikacji ani wzrostu wyników. Oceniasz, czy z ekranu da się
podjąć właściwą decyzję bez pomocy developera.

## Dowód na aktualnym API

Testowany adres BDO:
`https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/`

- decyzja: odśwież istniejącą treść;
- GSC: 15 237 wyświetleń, 14 kliknięć, CTR 0,09%, 31 zapytań, najlepsza pozycja 1,0;
- okres GSC: 15 lipca 2026 — pojedynczy snapshot, nie trend;
- WordPress: 789 słów z odczytu materiału, 12 rozpoznanych nagłówków, ACF dostępny;
- źródła: WordPress ekologus.pl i Google Search Console;
- świeżość: GSC settled/partial, GA4 settling/unverified;
- bezpieczny krok: sprawdzić materiał, wybrać kartę usługi i wygenerować plan;
- generowanie i WordPress pozostają zablokowane do wymaganych review.

WILQ API ma 12 konektorów, 9 skonfigurowanych i 2 bez credentials. Brak danych
nie jest zastępowany domysłem.

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
- aktualny commit: `42609ca9` na `origin/main`;
- wynik completion check: brak realnego UAT — cel pozostaje otwarty;
- zasady i kolejność: [`PLANS.md`](../../../../PLANS.md).
