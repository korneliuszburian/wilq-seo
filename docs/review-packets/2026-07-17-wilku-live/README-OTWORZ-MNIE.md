# WILQ — paczka do prawdziwej oceny przez Wilka

**Data odczytu:** 18 lipca 2026, około 06:45 CEST  
**Adres aplikacji:** http://127.0.0.1:5173/content-workflow

## Co masz zrobić

1. Otwórz aplikację i wybierz dowolny adres z katalogu — BDO nie jest
   automatycznie wybrane.
2. Kliknij **Sprawdź materiał**. Zobacz, czy WILQ pokazuje realny tekst z
   WordPressa, `the_content` albo ACF oraz stan metryk.
3. Dla adresu z materiałem kliknij **Rozpocznij workflow**. Zwróć uwagę na
   decyzję, powód, metryki i jeden następny krok.
4. Nie oceniaj samego „ładnego ekranu”. Odpowiedz, czy na tej podstawie da się
   codziennie wybrać właściwą pracę i napisać lepszą treść.
5. Wypełnij `FORMULARZ-OCENY-WILKU.md` i odeślij ten plik.

## Najważniejsze uczciwe zastrzeżenie

To jest paczka do realnej oceny operatora, nie deklaracja ukończenia produktu.
Planowanie Codex może zakończyć się typed blockerem/runtime timeoutem. Korpus
15 materiałów Ekologusa ma status `import_pending` (0/15 zaimportowanych do
generatora), więc WILQ nie może udawać, że zna prywatne sformułowania firmy.
Żaden ekran nie publikuje do WordPressa.

## Dwa adresy kontrolne

| Adres | Co sprawdza | Aktualny stan |
|---|---|---|
| `https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/` | strona z realnym tekstem i GSC | `ready`, materiał `content_and_structure`, metryki dostępne; wymaga wyboru karty usługi i review wiedzy |
| `https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/` | strona ofertowa i ogólny matcher | `ready`, binding rozwiązuje publiczny materiał dynamicznie jako `content_and_structure`, metryki dostępne; confidence materiału pozostaje `review_required` |

Dokładne identyfikatory i źródła są w `LIVE-PROOF.md`. Nie traktuj ich jako
metryk „na zawsze” — po odświeżeniu mogą zmienić się evidence ID, zakres i
wartości. Stan katalogu ma jawny blocker coverage: ostatni refresh nie zapisał
liczników źródłowych sitemap.

## Nowy live readback planów (18 lipca)

Przez kanoniczny planning API uruchomiono realny Codex app-server dla obu
adresów kontrolnych. Plany są zapisane, ale nadal wymagają decyzji człowieka i
nie odblokowują pełnego draftu:

| Case | Proposal / run | Wynik |
|---|---|---|
| BDO | \`content_planning_proposal_6a68bd59362641ce90f390b3dfb328c2\` / \`codex_content_planning_87135135b26d4b58b81f77b4412dac6d\` | 8 sekcji · 4 FAQ · 2 CTA · 1 link |
| Doradztwo i outsourcing | \`content_planning_proposal_275274ee443c48339785b0e14ec65f86\` / \`codex_content_planning_3424be8f758a4e89bfc9f2653431edc9\` | 5 sekcji · 3 FAQ · 2 CTA · 1 link |

Oba plany mają pełne title/H1/lead/meta, query assignments z dokładnych
wierszy GSC, evidence lineage oraz \`publish_ready=false\`. Nie zatwierdzono
ich jako UAT ani jako finalnego tekstu.

## Co jest live, a co nie

- **Live:** API WILQ, katalog WordPress, resolver `the_content`/ACF/public HTML,
  GSC i statusy konektorów, dynamiczne wiązanie URL → work item, dashboard i
  browser proof.
- **Synthetic:** część scenariuszy testowych z pełnym tekstem i sekcjami,
  użytych do sprawdzenia nawigacji, review i draft-only. Nie są tekstem
  Ekologusa ani UAT.
- **Brak:** owner review wszystkich kart, kontrolowany import materiałów,
  realny human review treści, pełny dokument po zatwierdzeniu planu i WordPress
  draft. Samo live Codex generation nie jest zgodą na publikację.

Nie wpisuj „działa produkcyjnie” tylko dlatego, że test przeglądarkowy jest
zielony.
