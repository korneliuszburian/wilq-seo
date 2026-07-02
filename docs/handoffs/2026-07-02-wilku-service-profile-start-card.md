# Service Profile: co pokazać Wilkowi

Data: 2026-07-02

## Krótko

WILQ Service Profile pokazuje, co system wie o usługach Ekologus, claimach,
CTA i wymaganych dowodach. To jest dobry ekran do review wiedzy, ale nie jest
jeszcze zielonym światłem do production-depth treści.

Najważniejsze: ekologus-ai daje realnie lepszą, bardziej konkretną wiedzę, ale
wszystko z prywatnych/reviewed źródeł nadal wymaga decyzji Wilka albo ownera.

## Aktualny stan

- Endpoint: `/api/content/service-profile`.
- Karty wiedzy: 10.
- Karty usługowe: 7.
- Approved-current: 0.
- Source-backed review-required: 7.
- Production-depth: 0.
- Prywatne propozycje ekologus-ai: 5.
- Review actions: 13.
- Produkcyjne treści pozostają zablokowane.

## Co jest do sprawdzenia

1. Najpierw publiczne karty usług Ekologus.
2. Potem prywatne propozycje ekologus-ai:
   - Eko-Opieka / Eko Kalendarz,
   - Audyt zgodności,
   - styl marki i claim policy,
   - bezpieczeństwo prawne,
   - source trace i evidence pack.
3. Dopiero po reviewerze, freshness, retention i source lineage można myśleć o
   reviewed source fact.

## Czego nie wolno zrobić

- Nie promować prywatnej propozycji do wiedzy produkcyjnej bez review.
- Nie twierdzić, że karta jest approved-current, skoro `approved_current_count=0`.
- Nie odblokowywać production-depth draftu tylko dlatego, że ekologus-ai coś
  podpowiada.
- Nie przepisywać raw private text do promptów ani treści.

## Ocena użyteczności

- Użyteczność jako ekran review wiedzy: 8/10.
- Użyteczność jako źródło produkcyjnej wiedzy do treści: 4/10, bo nie ma jeszcze
  approved-current service cards.
- Użyteczność ekologus-ai jako prywatnego/reviewed źródła: 8/10, bo wnosi
  konkretne propozycje usług, claim policy i evidence policy.
- Pierwszy ekran po zmianie: 7.5/10, bo pokazuje `Wiedza Ekologus: co dziś
  sprawdzić`, kolejność review i blokady produkcji przed listami technicznymi.

## Co jeszcze dopracować

- Przeprowadzić prawdziwy review Wilka/ownera dla wybranych kart i propozycji.
- Po zatwierdzeniu zapisać reviewer, freshness, confidence i source lineage.
- Dopiero potem pozwolić Claim Ledger i Content Workflow używać zatwierdzonej
  wiedzy jako production-depth.
