# WILQ pod marketing i treści

Status: materiał do pokazania Wilkowi. To nie jest claim, że system jest już
ukończony.

Data: 2026-07-02

## Jedno zdanie

WILQ ma być dla marketingu Ekologus tym, czym BDOS jest dla Google Ads:
systemem operacyjnym, który zbiera dane, pilnuje dowodów, blokuje ryzykowne
wnioski i zamienia to w bezpieczne decyzje, briefy, drafty, akcje do
sprawdzenia i pomiar efektu.

## Co to realnie robi

WILQ nie ma być "generatorem treści". Ma odpowiedzieć:

- co dziś warto zrobić;
- z jakich źródeł to wynika;
- czy dane są świeże;
- czy temat już istnieje na stronie albo w socialach;
- czy pasuje do realnej usługi Ekologus;
- co wolno powiedzieć w treści;
- czego nie wolno powiedzieć bez oceny człowieka;
- czy można przygotować brief, draft albo tylko pytania do Wilka;
- co zmierzyć po publikacji albo zmianie.

## Przykłady jak w BDOS, tylko dla Ekologus

### Poranny marketing

Polecenie:

```txt
sprawdź co mam dziś zrobić w marketingu Ekologus
```

WILQ ma zwrócić kolejkę dnia z GSC, GA4, Ads, Merchant, WordPress, Ahrefs,
Localo i wiedzy Ekologus. Nie ma mówić "pisz artykuł", jeśli brakuje dowodu,
świeżych danych albo zatwierdzonej usługi.

### Decyzja treściowa

Polecenie:

```txt
które strony odświeżyć, scalić albo zablokować?
```

WILQ patrzy na zapytania i strony z GSC, spis treści WordPress, ryzyko
duplikacji, Service Profile i karty wiedzy. Wynik to decyzja: odświeżyć,
scalić, utworzyć, zostawić albo zablokować.

### Brief sprzedażowy

Polecenie:

```txt
przygotuj brief pod BDO
```

WILQ może zrobić brief tylko wtedy, gdy ma dopasowanie do usługi, CTA, problem
kupującego, politykę twierdzeń i dowody. Jeśli brakuje karty usługi albo CTA,
ma pokazać blokadę, a nie udawać gotowość.

### Claim Ledger

Polecenie:

```txt
co wolno powiedzieć w tym tekście?
```

WILQ rozdziela claimy na:

- dozwolone;
- słabe;
- wymagane;
- zabronione;
- wymagające człowieka.

Claimy o karach, prawie, decyzjach, produktach, efekcie pomiarowym albo źródłach
prywatnych nie mogą przejść jako finalna treść bez review.

### Szkic i kontrola jakości

Polecenie:

```txt
napisz draft i sprawdź, czy nie wyszedł poza ledger
```

WILQ ma sprawdzić, czy draft używa tylko dozwolonych claimów, zawiera wymagane
claimy i nie dodaje obietnic typu "unikniesz kary", "gwarantujemy efekt",
"to działa najlepiej" bez dowodu.

### Social i repurpose

Polecenie:

```txt
zrób post na LinkedIn z tej okazji
```

WILQ może przygotować kierunek posta do oceny, ale nie może powiedzieć, że temat
jest nowy albo że nie powtarzamy się, dopóki nie ma historii postów z
LinkedIn/Facebooka.

## Historia LinkedIn/Facebook jest wymagana

To jest ważne: tak, musimy brać pod uwagę historyczne posty z LinkedIna i
Facebooka.

Bez tej historii WILQ nie może twierdzić:

- "ten temat jest nowy";
- "nie powielamy komunikacji";
- "można bezpiecznie zrobić repurpose";
- "to pasuje do dotychczasowej komunikacji";
- "to już było sprawdzone".

Na start nie potrzebujemy pełnych treści postów ani komentarzy. Wystarczy spis
samych metadanych:

- kanał;
- data publikacji;
- temat;
- usługa;
- claim;
- CTA;
- format;
- URL albo ID posta;
- `source_evidence_id`.

WILQ ma już kontrakt techniczny na to jako `social_history_inventory_v1`. Obecny
status: brakuje dowodów `linkedin_historical_posts` i
`facebook_historical_posts`, więc twierdzenie "brak powtórzeń historycznych
postów" jest zablokowane.

## Co już jest sprawdzone

Na 2026-07-02 testy umiejętności nie są tylko teorią. Mamy pełne odtworzenie
13/13 workflowów operatorskich: deterministyczny smoke plus nieinteraktywny
test Codexa z WILQ API.

Przeszły:

- Daily Command;
- Ads Doctor;
- Merchant Feed Operator;
- GA4 Analyst;
- Ahrefs Gap Finder;
- GSC Content Doctor;
- Content Strategist;
- Content Operator;
- Campaign Builder;
- Custom Segments;
- Demand Gen Operator;
- Localo Operator;
- Social Publisher.

Najważniejsze: testy sprawdzają, czy odpowiedź jest po polsku, używa WILQ API,
ma identyfikatory dowodów i źródła danych, nie wymyśla metryk, blokuje
ryzykowne twierdzenia i daje następny krok, który marketer rozumie.

Najprostszy podział:

- gotowe jako operacje do oceny: Daily, Ads, Merchant, GA4, GSC, Ahrefs, Localo,
  Content Strategist, Campaign Builder i Custom Segments;
- blokowane poprawnie: Content Operator, bo pełna treść wymaga Service Profile,
  Claim Ledger, oceny człowieka i okna pomiarowego;
- blokowane poprawnie: Demand Gen, bo w danych jest 18 kampanii Ads, ale 0
  kampanii Demand Gen, 0 reklam, 0 kreacji i 0 stron wejścia Demand Gen;
- blokowane poprawnie: Social Publisher, bo brakuje historii LinkedIn/Facebook
  i dostępów, więc nie wolno obiecać braku powtórek ani publikacji.

To jest dobry stan przed rozmową z Wilkiem: WILQ zaczyna zachowywać się jak system operacyjny,
który umie powiedzieć "działaj", "sprawdź" albo "nie wolno jeszcze".

## Czego jeszcze nie wolno twierdzić

Nie mówimy jeszcze:

- że WILQ jest skończony;
- że Goal 005 jest domknięty;
- że mamy wiedzę Ekologus zatwierdzoną do finalnych treści;
- że WILQ może pisać finalne treści bez oceny człowieka;
- że social dedupe jest gotowy;
- że publikacja albo kampania da wynik biznesowy;
- że API może zapisywać zmiany bez walidacji, podglądu, zgody człowieka i
  audytu.

## Co powiedzieć Wilkowi

Najprościej:

> Budujemy WILQ jako system decyzyjny dla marketingu Ekologus. Nie chodzi o to,
> żeby AI pisało dużo tekstu. Chodzi o to, żeby wiedziało, skąd bierze
> rekomendację, czy temat już był, czy wolno użyć danego claimu, czy mamy
> świeże dane i czy po publikacji był efekt. Tam, gdzie nie ma dowodu albo
> oceny człowieka, WILQ ma blokować finalną treść.

## Pytania do Wilka

1. Czy taki podział na decyzję, brief, listę dozwolonych twierdzeń, szkic,
   ocenę i pomiar ma sens w realnej pracy?
2. Czy obecne blokady są zrozumiałe, czy brzmią zbyt technicznie?
3. Jakie historyczne posty LinkedIn/Facebook możemy zinwentaryzować jako
   formie samych metadanych?
4. Które usługi Ekologus muszą być zatwierdzone jako pierwsze?
5. Jakich claimów WILQ ma absolutnie nie przepuszczać?
