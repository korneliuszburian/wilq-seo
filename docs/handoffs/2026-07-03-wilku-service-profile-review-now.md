# Service Profile - co pokazać Wilkowi teraz

Status: materiał do rozmowy oceniającej, nie dowód ukończenia Goal 005.

Data: 2026-07-03

## Najkrótszy status

WILQ jest już użyteczny jako system oceny wiedzy, ale nie jest jeszcze
zatwierdzony do finalnych treści.

- Umiejętności operatorskie: 13/13 przeszło nieinteraktywny test jakości na
  poziomie 9/10.
- Wiedza Ekologus: źródła są zebrane, ale wymagają oceny; nie są jeszcze
  zatwierdzoną aktualną wiedzą.
- Wiedza zatwierdzona do finalnych treści: 0%.
- Zatwierdzone fakty usługowe: 0%.
- Service Profile: tylko do odczytu, 14 decyzji do oceny, bez edycji kart i bez
  promowania faktów źródłowych.
- Prywatne propozycje `ekologus-ai`: 5, wszystkie wymagają oceny,
  są zredagowane i nie dają prawa do finalnych treści.

Powiedz Wilkowi:

> WILQ nie udaje, że już zna ofertę Ekologus. Ma kolejkę decyzji: co zatwierdzić,
> co poprawić, co odrzucić i czego nadal nie wolno używać w treściach.

## Co pokazać jako pierwsze

Pokaż `/service-profile`, ale zacznij od decyzji, nie od technicznych
identyfikatorów.

Najpierw przejrzeć publiczną kartę usługi BDO, bo to jest obecny pierwszy
element do oceny z aktualnego Service Profile i wejścia do rozmowy Goal 005:

1. **BDO i sprawozdawczość środowiskowa**
   - typ oceny: publiczna karta usługi;
   - priorytet: średni;
   - decyzja do zapisania: zatwierdź, wróć z poprawkami, oznacz jako
     nieaktualne albo odrzuć;
   - trzeba sprawdzić: ślad źródłowy, zablokowane claimy i krótką notatkę
     dlaczego akceptujemy albo co poprawić;
   - pytanie do Wilka: czy ta karta brzmi jak realna oferta Ekologus i czy
     claimy o BDO są poprawnie zablokowane przed oceną?

Potem przejrzeć polityki i prywatne propozycje, bo one ustawiają język i
bezpieczeństwo dla kolejnych usług:

2. **Bezpieczeństwo prawne, poufność i zgody**
   - typ oceny: prywatna propozycja polityki twierdzeń;
   - priorytet: wysoki;
   - decyzja: zatwierdź, wróć z poprawkami, oznacz jako nieaktualne albo odrzuć.
3. **Styl marki i polityka twierdzeń Ekologus**
   - typ oceny: prywatna propozycja polityki twierdzeń;
   - priorytet: wysoki;
   - decyzja: zatwierdź, wróć z poprawkami, oznacz jako nieaktualne albo odrzuć.
4. **Ślad źródłowy i pakiet dowodów**
   - typ oceny: prywatna propozycja wymagań dowodowych;
   - priorytet: wysoki;
   - decyzja: zatwierdź, wróć z poprawkami, oznacz jako nieaktualne albo odrzuć.
5. **Audyt zgodności środowiskowej**
   - typ oceny: prywatna propozycja usługi;
   - priorytet: średni;
   - decyzja: zatwierdź, wróć z poprawkami, oznacz jako nieaktualne albo odrzuć.
6. **Eko-Opieka i Eko Kalendarz**
   - typ oceny: prywatna propozycja usługi;
   - priorytet: średni;
   - decyzja: zatwierdź, wróć z poprawkami, oznacz jako nieaktualne albo odrzuć.

Pozostałe publiczne karty usług też wymagają oceny. Najbardziej praktyczne do
następnych rozmów: konsulting/outsourcing środowiskowy, odpady/opakowania,
operaty wodnoprawne, szkolenia, remediacja/monitoring i sorbenty. Operaty
wodnoprawne mają już kartę do oceny, ale nadal nie są zatwierdzoną aktualną
wiedzą, więc nie odblokowują finalnych treści.

## Pytania do Wilka

1. Czy publiczna karta BDO jest dobrym pierwszym testem Service Profile, czy
   wymaga poprawki zanim cokolwiek przejdzie do finalnych treści?
2. Czy źródła i zablokowane claimy przy BDO są czytelne, czy Wilku nadal pyta
   "skąd to wzięliśmy"?
3. Czy po BDO zatwierdzamy polityki twierdzeń i bezpieczeństwa, czy kolejną
   konkretną usługę?
4. Czy `Eko-Opieka / Eko Kalendarz` to realna oferta, roboczy język handlowy,
   czy temat do odrzucenia?
5. Czy `Audyt zgodności środowiskowej` może być pierwszym płatnym krokiem w
   komunikacji, czy wymaga innej nazwy?
6. Jakich claimów WILQ ma zawsze blokować bez człowieka: kary, WIOŚ, decyzje,
   kontrole, pozwolenia, dane klientów?
7. Co w tych propozycjach brzmi jak Ekologus, a co jak generyczne SEO/AI?

## Jak zapisać decyzję

WILQ ma przygotowany plik wejściowy do uzupełnienia po rozmowie:

Najwygodniej zacząć od krótkiej karty rozmowy:

```bash
rtk uv run python scripts/record_service_profile_review_result.py --print-session-card --review-type public_service_cards --api-base http://127.0.0.1:8000
rtk uv run python scripts/record_service_profile_review_result.py --print-session-card --review-type private_source_proposals --api-base http://127.0.0.1:8000
```

Sekcja techniczna: wartości decyzji w JSON to `approve`, `needs_changes`,
`stale`, `reject`. W rozmowie mówimy: zatwierdź, wróć z poprawkami, oznacz
jako nieaktualne albo odrzuć.

```bash
.local-lab/proof/service-profile-private-review-input-20260703.json
.local-lab/proof/service-profile-public-review-input-20260703.json
```

Jeżeli pliki trzeba odświeżyć z aktualnego API, wygeneruj je tak:

```bash
rtk uv run python scripts/record_service_profile_review_result.py --print-input-example --review-type public_service_cards --api-base http://127.0.0.1:8000 > .local-lab/proof/service-profile-public-review-input-20260703.json
rtk uv run python scripts/record_service_profile_review_result.py --print-input-example --review-type private_source_proposals --api-base http://127.0.0.1:8000 > .local-lab/proof/service-profile-private-review-input-20260703.json
```

Po uzupełnieniu decyzji sprawdzić wynik:

```bash
rtk uv run python scripts/record_service_profile_review_result.py .local-lab/proof/service-profile-private-review-result-20260703.json --api-base http://127.0.0.1:8000 --format markdown
rtk uv run python scripts/record_service_profile_review_result.py .local-lab/proof/service-profile-public-review-result-20260703.json --api-base http://127.0.0.1:8000 --format markdown
```

## Czego nie mówić

- Nie mówimy, że Goal 005 jest ukończony.
- Nie mówimy, że WILQ ma wiedzę zatwierdzoną do finalnych treści.
- Nie mówimy, że prywatne propozycje `ekologus-ai` są zatwierdzone.
- Nie mówimy, że WILQ może pisać finalne treści bez oceny człowieka.
- Nie promujemy faktów źródłowych ani kart bez osobnej decyzji człowieka.

## Co będzie sukcesem tej rozmowy

Nie musi być pełnego zatwierdzenia. Wystarczy jedno z tych:

- Wilku mówi, które 2-3 propozycje są najbliżej prawdy;
- Wilku wskazuje, co poprawić w polityce twierdzeń;
- Wilku odrzuca błędny kierunek, zanim wejdzie do treści;
- Wilku rozumie, dlaczego WILQ blokuje finalny content.

To będzie realny proof użyteczności, a nie tylko zielony test.
