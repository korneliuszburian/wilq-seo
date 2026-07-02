# BDO i sprawozdawczość - materiał do UAT z Wilkiem

Status: materiał do rozmowy i review. To nie jest finalny brief, draft ani
rekomendacja publikacji.

Data: 2026-07-02

## Etykieta UAT

To jest `review specimen`, czyli próbka do oceny języka, źródeł, CTA i blokad
WILQ dla tematu BDO.

To nie jest dzisiejszy aktywny work item z live kolejki, polecenie napisania
draftu ani rekomendacja publikacji. Jeśli Wilku zatwierdzi kierunek, następnym
krokiem jest decyzja review dla karty BDO i dopiero później ponowne sprawdzenie
live kolejki.

## Po co to pokazujemy

Chcemy sprawdzić, czy WILQ umie zrobić rzecz praktyczną: wziąć temat BDO,
połączyć go z realnym śladem źródeł i powiedzieć Wilkowi, co można bezpiecznie
przygotować, a czego nie wolno obiecać.

To jest propozycja do pierwszej rozmowy UAT, bo wcześniejszy audyt Sales Brief v2
wskazał `bdo co to` jako najmocniejszy temat review. Jednocześnie live kolejka
z 2026-07-02 nie wystawia dziś BDO jako aktywnego zadania contentowego, więc ten
materiał nie mówi: "piszemy teraz draft". Mówi: "sprawdźmy, czy kierunek BDO,
źródła i blokady są zrozumiałe dla Wilka".

## Skąd WILQ to bierze

Live WILQ API, 2026-07-02:

- `GET /api/content/service-profile`
  - karta: `ekologus_service_bdo_reporting`
  - status: `source_backed_review_required`
  - źródło: `https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/`
  - source fact: `ekologus_public_bdo_faq_2026_07_01`
  - review action: `service_profile_review_card_ekologus_service_bdo_reporting`
- `GET /api/content/diagnostics`
  - bieżące evidence IDs obejmują m.in.
    `ev_refresh_refresh_google_search_console_9b25d4143bea`,
    `ev_refresh_refresh_wordpress_ekologus_691cbe6ab27d`,
    `ev_connector_google_search_console_status`,
    `ev_connector_wordpress_ekologus_status`
  - live content queue ma dziś 3 decyzje, ale nie ma osobnej decyzji BDO.
- `GET /api/content/work-items/queue`
  - `queue_status=blocked`
  - `candidate_count=3`
  - `actionable_candidate_count=1`
  - BDO nie jest dziś aktywnym work itemem.

Historyczny proof Goal 005:

- `docs/audits/005-2026-07-01-sales-brief-signal-quality.md`
  - `bdo co to` było oznaczone jako `brief built` i `usable for review`
  - powód: GSC + WordPress evidence, istniejący URL, enrichment, measurement
    ready to plan, 3 source facts i 15 knowledge constraints.

Granica: WILQ ma publiczne i live dowody do review kierunku, ale karta BDO
nadal wymaga decyzji człowieka. Nie wolno traktować jej jako
`approved_current` ani production-depth.

## Jak WILQ rozumie temat

Najprostsze rozumienie:

> Ekologus może edukacyjnie tłumaczyć przedsiębiorcy, czym jest BDO, kiedy
> warto sprawdzić rejestrację, ewidencję i sprawozdawczość oraz jakie dokumenty
> przygotować do rozmowy z ekspertem.

To nie jest automatyczne rozstrzygnięcie, czy konkretna firma ma obowiązek BDO.
To jest ścieżka do uporządkowania pytań, dokumentów i kolejnego kroku.

## Co może być użyteczne dla Ekologus

Kierunek treści:

- odświeżenie lub nowy wariant edukacyjny wokół pytania "BDO - co musi wiedzieć
  przedsiębiorca?",
- prosty przewodnik: kiedy temat BDO powinien zapalić lampkę ostrzegawczą,
- lista informacji do przygotowania przed konsultacją z Ekologus,
- CTA do sprawdzenia zakresu obowiązków z ekspertem, bez obietnicy wyniku.

Kierunek sprzedażowy:

- nie sprzedawać "świętego spokoju od kar",
- sprzedawać uporządkowanie sytuacji, dokumentów i obowiązków,
- kierować rozmowę do konsultacji lub audytu zakresu BDO/sprawozdawczości.

## Język, który może działać

Bezpieczne propozycje:

- "BDO warto potraktować jako temat do uporządkowania, zanim wróci przy
  sprawozdaniu, ewidencji albo kontroli dokumentów."
- "Ekologus może pomóc sprawdzić, jakie informacje i dokumenty warto zebrać
  przed pracą nad BDO."
- "Treść edukacyjna może pomóc przedsiębiorcy zrozumieć, o co zapytać eksperta,
  ale nie zastępuje oceny sytuacji konkretnej firmy."
- "Jeżeli nie masz pewności, czy BDO dotyczy Twojej działalności, przygotuj opis
  działalności, rodzaj odpadów i dotychczasową dokumentację do rozmowy."

## Czego nie mówić bez review

Nie obiecywać:

- "na pewno musisz zarejestrować firmę w BDO",
- "na pewno nie musisz rejestrować firmy w BDO",
- "unikniesz kary",
- "gwarantujemy zgodność",
- konkretnych terminów, stawek, sankcji albo interpretacji bez świeżego review,
- że WILQ sam rozstrzyga obowiązek konkretnej firmy.

Bezpieczniejszy język:

- "warto sprawdzić",
- "może wymagać weryfikacji",
- "zależy od działalności i dokumentów firmy",
- "pomaga przygotować pytania do eksperta",
- "wymaga review Wilka/ownera przed finalnym draftem".

## Propozycja krótkiej treści do oceny

### Nagłówek

BDO: co przedsiębiorca powinien sprawdzić, zanim zacznie działać na ostatnią
chwilę

### Lead

BDO często wraca dopiero wtedy, gdy trzeba uporządkować ewidencję, przygotować
sprawozdanie albo odpowiedzieć na pytanie, czy firma ma konkretny obowiązek.
Zamiast zgadywać, warto zebrać podstawowe informacje o działalności, odpadach i
dokumentach, a potem sprawdzić je z ekspertem.

### Struktura

1. Kiedy BDO staje się tematem do sprawdzenia:
   działalność, odpady, ewidencja, sprawozdawczość, dokumenty.
2. Czego nie da się rozstrzygnąć ogólnie:
   obowiązku konkretnej firmy bez znajomości jej sytuacji.
3. Co przygotować przed rozmową:
   opis działalności, rodzaje odpadów, dotychczasową dokumentację, pytania.
4. Jak może pomóc Ekologus:
   uporządkować pytania, sprawdzić dokumenty, wskazać kolejny krok.
5. CTA:
   "Przygotuj opis działalności i dokumenty BDO. Ekologus może pomóc sprawdzić,
   co wymaga weryfikacji."

## Propozycja posta LinkedIn/Facebook

BDO nie jest tematem, który warto zostawiać na ostatnią chwilę.

Problem zaczyna się zwykle nie od samego formularza, tylko od pytań:

- czy działalność firmy w ogóle wymaga sprawdzenia pod kątem BDO,
- czy dokumenty i ewidencja są uporządkowane,
- czy sprawozdawczość nie wróci jako pilny temat tuż przed terminem,
- jakie informacje trzeba przygotować, żeby ekspert mógł ocenić sytuację.

Bezpieczny pierwszy krok to nie zgadywanie. To zebranie opisu działalności,
rodzajów odpadów i dotychczasowych dokumentów, a potem rozmowa z osobą, która
może wskazać, co wymaga weryfikacji.

CTA: jeśli BDO wraca u Ciebie jako znak zapytania, przygotuj dokumenty i opisz
działalność firmy. Ekologus może pomóc sprawdzić, od czego zacząć.

## Pytania do Wilka

1. Czy BDO ma być osobnym kierunkiem treściowym, czy częścią większego tematu
   "sprawozdawczość i obowiązki środowiskowe"?
2. Czy CTA ma prowadzić do konsultacji, audytu zgodności, Eko-Opieki czy
   zwykłej rozmowy rozpoznawczej?
3. Czy możemy publicznie mówić "przygotuj opis działalności, rodzaje odpadów i
   dokumentację", czy to za konkretnie?
4. Jakich sformułowań o karach, terminach i obowiązkach absolutnie unikać?
5. Czy istnieją aktualniejsze publiczne źródła Ekologus dla BDO niż obecny
   artykuł `bdo-co-musi-wiedziec-przedsiebiorca`?
6. Czy ten temat ma być pokazany jako edukacyjny artykuł, strona usługi, post,
   czy materiał handlowy do rozmów z klientami?
7. Czy WILQ dobrze rozdziela: edukacja BDO vs rozstrzygnięcie obowiązku
   konkretnej firmy?

## Co WILQ powinien zrobić po opinii

Jeżeli Wilku zatwierdzi kierunek:

- zapisać decyzję review dla `service_profile_review_card_ekologus_service_bdo_reporting`,
- oznaczyć ślad źródłowy i blocked claims jako sprawdzone,
- przygotować osobny audited promotion request, ale dopiero przez WILQ action
  path,
- odświeżyć GSC i WordPress i sprawdzić, czy BDO wraca jako live work item,
- dopiero potem budować Sales Brief lub draft.

Jeżeli Wilku poprawi kierunek:

- zapisać, co zmienić w karcie BDO, CTA albo claim policy,
- utworzyć follow-up Beads, jeśli decyzja nie jest `approve`,
- nie używać BDO jako production-depth wiedzy do finalnego draftu.

Jeżeli Wilku odrzuci kierunek:

- zostawić kartę jako `source_backed_review_required` albo `rejected`,
- nie używać BDO jako domyślnego CTA w treściach,
- nie pisać draftu BDO mimo historycznego Sales Brief proof.

## Jednozdaniowy werdykt dla rozmowy

BDO jest dobrym tematem do UAT wiedzy i języka sprzedażowego, ale nie jest dziś
aktywnym live work itemem w kolejce treści; najpierw potrzebujemy decyzji Wilka
o karcie BDO, źródłach, CTA i blokowanych twierdzeniach.
