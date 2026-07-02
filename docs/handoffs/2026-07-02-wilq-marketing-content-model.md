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
- czego nie wolno powiedzieć bez review człowieka;
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

WILQ patrzy na GSC query/page, WordPress inventory, canonical/duplicate risk,
Service Profile i knowledge cards. Wynik to decyzja: odświeżyć, scalić,
utworzyć, zostawić albo zablokować.

### Brief sprzedażowy

Polecenie:

```txt
przygotuj brief pod BDO
```

WILQ może zrobić brief tylko wtedy, gdy ma service fit, CTA, buyer problem,
claim policy i dowody. Jeśli brakuje karty usługi albo CTA, ma pokazać blocker,
a nie udawać gotowość.

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

### Draft i quality review

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

WILQ może przygotować review-only kierunek posta, ale nie może powiedzieć, że
temat jest nowy albo że nie powtarzamy się, dopóki nie ma historii postów z
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

Na start nie potrzebujemy raw treści postów ani komentarzy. Wystarczy
metadata-only inventory:

- kanał;
- data publikacji;
- temat;
- usługa;
- claim;
- CTA;
- format;
- URL albo ID posta;
- `source_evidence_id`.

WILQ ma już kontrakt na to jako `social_history_inventory_v1`. Obecny status:
brakuje dowodów `linkedin_historical_posts` i `facebook_historical_posts`, więc
claim "brak powtórzeń historycznych postów" jest zablokowany.

## Co już jest sprawdzone

Na 2026-07-02 realne evale skillów nie są tylko teorią. Przeszły
non-interactive Codex evale z WILQ API dla:

- Daily Command;
- Ads Doctor;
- Merchant Feed Operator;
- GA4 Analyst;
- Ahrefs Gap Finder;
- GSC Content Doctor;
- Content Operator;
- Social Publisher.

Najważniejsze: evale sprawdzają, czy odpowiedź jest po polsku, używa WILQ API,
ma evidence IDs, source connectors, nie wymyśla metryk, blokuje unsafe claimy i
daje następny krok, który marketer rozumie.

## Czego jeszcze nie wolno twierdzić

Nie mówimy jeszcze:

- że WILQ jest skończony;
- że Goal 005 jest domknięty;
- że mamy production-depth wiedzę Ekologus;
- że WILQ może pisać finalne treści bez review;
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
> review, WILQ ma blokować finalną treść.

## Pytania do Wilka

1. Czy taki podział na decyzję, brief, ledger, draft, review i pomiar ma sens w
   realnej pracy?
2. Czy obecne blokady są zrozumiałe, czy brzmią zbyt technicznie?
3. Jakie historyczne posty LinkedIn/Facebook możemy zinwentaryzować jako
   metadata-only?
4. Które usługi Ekologus muszą być zatwierdzone jako pierwsze?
5. Jakich claimów WILQ ma absolutnie nie przepuszczać?
