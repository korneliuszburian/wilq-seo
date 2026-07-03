# Service Profile review - co pokazać Wilkowi teraz

Status: materiał do rozmowy review, nie dowód ukończenia Goal 005.

Data: 2026-07-03

## Najkrótszy status

WILQ jest już użyteczny jako system review, ale nie jest jeszcze zatwierdzony
do finalnych treści.

- Skille operatorskie: 13/13 przeszło non-interactive eval na poziomie 9/10.
- Wiedza Ekologus: `source_backed_review_required`, nie `approved_current`.
- Production-depth: 0%.
- Approved service facts: 0%.
- Service Profile: read-only, 14 akcji review, bez edycji kart i bez promocji
  source facts.
- Prywatne propozycje `ekologus-ai`: 5, wszystkie `review_required`,
  redacted-only i bez prawa do production-depth.

Powiedz Wilkowi:

> WILQ nie udaje, że już zna ofertę Ekologus. Ma kolejkę decyzji: co zatwierdzić,
> co poprawić, co odrzucić i czego nadal nie wolno używać w treściach.

## Co pokazać jako pierwsze

Pokaż `/service-profile`, ale zacznij od decyzji, nie od technicznych ID.

Najpierw przejrzeć publiczną kartę usługi BDO, bo to jest obecny pierwszy
review item z live Service Profile i Goal 005 UAT input:

1. **BDO i sprawozdawczość środowiskowa**
   - ActionObject:
     `service_profile_review_card_ekologus_service_bdo_reporting`;
   - target card: `ekologus_service_bdo_reporting`;
   - zakres: public service card;
   - priorytet: medium;
   - wymagane pola: `action_id`, `target_card_id`, `decision`,
     `source_trace_clear`, `blocked_claims_reviewed`, `notes`;
   - decyzja: `approve`, `needs_changes`, `stale` albo `reject`;
   - pytanie do Wilka: czy ta karta brzmi jak realna oferta Ekologus i czy
     claimy o BDO są poprawnie zablokowane przed review?

Potem przejrzeć policy/private proposals, bo one ustawiają język i bezpieczeństwo
dla kolejnych usług:

2. **Bezpieczeństwo prawne, poufność i zgody**
   - zakres: private claim-policy proposal;
   - priorytet: high;
   - decyzja: `approve`, `needs_changes`, `stale` albo `reject`.
3. **Styl marki i claim policy Ekologus**
   - zakres: private claim-policy proposal;
   - priorytet: high;
   - decyzja: `approve`, `needs_changes`, `stale` albo `reject`.
4. **Source trace i evidence pack**
   - zakres: private evidence-policy proposal;
   - priorytet: high;
   - decyzja: `approve`, `needs_changes`, `stale` albo `reject`.
5. **Audyt zgodności środowiskowej**
   - zakres: private service proposal;
   - priorytet: medium;
   - decyzja: `approve`, `needs_changes`, `stale` albo `reject`.
6. **Eko-Opieka i Eko Kalendarz**
   - zakres: private service proposal;
   - priorytet: medium;
   - decyzja: `approve`, `needs_changes`, `stale` albo `reject`.

Pozostałe publiczne karty usług też wymagają review. Najbardziej praktyczne do
następnych rozmów: konsulting/outsourcing środowiskowy, odpady/opakowania,
operaty wodnoprawne, szkolenia, remediacja/monitoring i sorbenty. Operaty
wodnoprawne mają już kartę do review, ale nadal nie są `approved_current`, więc
nie odblokowują production-depth treści.

## Pytania do Wilka

1. Czy publiczna karta BDO jest dobrym pierwszym testem Service Profile, czy
   wymaga poprawki zanim cokolwiek przejdzie do production-depth?
2. Czy źródła i zablokowane claimy przy BDO są czytelne, czy Wilku nadal pyta
   "skąd to wzięliśmy"?
3. Czy po BDO zatwierdzamy polityki claimów i bezpieczeństwa, czy kolejną
   konkretną usługę?
4. Czy `Eko-Opieka / Eko Kalendarz` to realna oferta, roboczy język handlowy,
   czy temat do odrzucenia?
5. Czy `Audyt zgodności środowiskowej` może być pierwszym płatnym krokiem w
   komunikacji, czy wymaga innej nazwy?
6. Jakich claimów WILQ ma zawsze blokować bez człowieka: kary, WIOŚ, decyzje,
   kontrole, pozwolenia, dane klientów?
7. Co w tych propozycjach brzmi jak Ekologus, a co jak generyczne SEO/AI?

## Jak zapisać decyzję

WILQ ma przygotowany live JSON wejściowy do uzupełnienia:

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
- Nie mówimy, że WILQ ma production-depth knowledge.
- Nie mówimy, że prywatne propozycje `ekologus-ai` są zatwierdzone.
- Nie mówimy, że WILQ może pisać finalne treści bez human review.
- Nie promujemy source facts ani kart bez osobnego review/promotion request.

## Co będzie sukcesem tej rozmowy

Nie musi być pełnego zatwierdzenia. Wystarczy jedno z tych:

- Wilku mówi, które 2-3 propozycje są najbliżej prawdy;
- Wilku wskazuje, co poprawić w claim policy;
- Wilku odrzuca błędny kierunek, zanim wejdzie do treści;
- Wilku rozumie, dlaczego WILQ blokuje finalny content.

To będzie realny proof użyteczności, a nie tylko zielony test.
