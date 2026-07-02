# Eko-Opieka: karta startowa dla Wilka

Status: materiał do decyzji review, nie gotowa treść publikacyjna.

Data testu: 2026-07-02

## Decyzja na dziś

Wilku, potrzebujemy od Ciebie jednej decyzji:

> Czy Eko-Opieka / Eko Kalendarz to realny kierunek sprzedaży Ekologus?

WILQ mówi: **tak, to wygląda jak wartościowy kierunek**, ale tylko jako
`review_required`. Nie wolno jeszcze pisać finalnej treści SEO ani strony,
bo brakuje zatwierdzonej karty usługi, zatwierdzonego CTA i decyzji człowieka
co do claimów.

Wybierz jedno:

- `approve` - kierunek jest prawdziwy, można go rozwijać w WILQ;
- `needs_changes` - kierunek ma sens, ale trzeba poprawić zakres/język/CTA;
- `stale` - materiał jest nieaktualny i wymaga odświeżenia;
- `reject` - nie używać tego kierunku w treściach.

## Co WILQ rozumie

Eko-Opieka nie jest "programem IT" ani zwykłym newsletterem. WILQ rozumie ją
jako cykliczną opiekę ekspercką nad terminami, decyzjami, dokumentami i
ryzykami środowiskowymi klienta.

Najprościej:

> Ekologus pomaga firmie pilnować obowiązków środowiskowych zanim temat wróci
> przy sprawozdaniu, kontroli, decyzji albo problemie operacyjnym.

Eko Kalendarz może być częścią tej opieki: mapa terminów, przypomnienia,
przegląd decyzji, kwartalny przegląd ryzyk i lista kolejnych działań.

## Czego WILQ nie pozwala mówić

Bez Twojego review WILQ blokuje:

- obietnicę pełnej zgodności prawnej;
- obietnicę braku kar;
- twierdzenie, że klient na pewno ma albo nie ma konkretny obowiązek;
- sprzedawanie Eko-Opieki jako automatycznego programu IT;
- użycie danych obecnych klientów w publicznej treści.

Bezpieczniejszy język: "pomaga uporządkować", "wskazuje, co wymaga
sprawdzenia", "ułatwia pilnowanie terminów", "może być podstawą do konsultacji
albo audytu".

## Dowody z WILQ

Live WILQ API na 2026-07-02:

- Service Profile status: `source_backed_review_required`
- `ready_for_daily_content`: `false`
- `approved_current_count`: `0`
- `production_depth_card_count`: `0`
- private proposal:
  `private_proposal_ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01`
- source fact:
  `ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01`
- target card:
  `ekologus_service_eko_opieka_calendar`
- freshness: `current`
- audience: `company_wide`
- retention: `pending_owner_decision`
- review action:
  `service_profile_review_private_proposal_ekologus_ai_kb001_eko_opieka_review_candidate_2026_07_01`

WILQ wymaga w review potwierdzenia: source trace, blocked claims, klasy danych,
source block refs, aktualność źródła, audience/scope, retencję, ścieżkę
usunięcia i eval gates.

## Ocena użyteczności

Testy wykonane:

- `wilq-content-operator` smoke: przeszedł;
- `wilq-content-operator` UAT packet: wygenerowany z live API;
- live Service Profile: sprawdzony;
- dwie niezależne oceny reviewerów: SEO/content i marketer/operator.

Wyniki:

- jako materiał do pokazania Wilkowi: **7-8/10**;
- jako realna oszczędność pracy marketera: **6.5/10**;
- jako gotowość do produkcyjnej treści SEO: **3/10**.

Wniosek: prywatna wiedza z `ekologus-ai` wyraźnie poprawia jakość kierunku.
Bez niej WILQ miałby głównie generyczne "doradztwo i outsourcing
środowiskowy". Z nią widzi konkretny koncept: abonament, cykliczną opiekę,
Eko Kalendarz, reaktywację obecnych/dawnych klientów, język sprzedażowy i
zakazane claimy.

## Co to znaczy praktycznie

To jest dobry materiał do 15-minutowej rozmowy z Wilkiem.

To nie jest jeszcze:

- finalny brief SEO;
- finalny landing page;
- gotowy artykuł;
- approved-current wiedza Ekologus;
- dowód, że temat powinien iść na stronę zamiast mailingu, posta albo rozmowy
  handlowej.

## Pytania do Wilka

1. Czy Eko-Opieka / Eko Kalendarz to realna oferta, czy robocza nazwa?
2. Czy głównym odbiorcą jest zarząd, specjalista ds. ochrony środowiska/BHP,
   czy obecny klient Ekologus?
3. Czy pierwszy krok sprzedażowy to konsultacja, audyt, płatny przegląd czy
   mailing do dawnych klientów?
4. Jakich obietnic absolutnie nie wolno używać?
5. Czy ten temat ma iść najpierw jako strona, post, mailing czy materiał
   handlowy?

## Następny krok po decyzji

Jeśli Wilku zatwierdzi albo poprawi kierunek, WILQ powinien dopiero wtedy:

1. zapisać wynik review przez Service Profile review action;
2. zaktualizować source facts/kartę usługi w trybie review;
3. sprawdzić WordPress/GSC, czy temat już istnieje i czy nie grozi duplikacją;
4. przygotować brief i claim ledger;
5. dopiero potem generować draft przez WILQ API, nadal jako draft-only.
