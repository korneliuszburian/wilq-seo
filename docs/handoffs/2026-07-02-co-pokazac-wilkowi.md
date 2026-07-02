# Co pokazać Wilkowi

Status: krótka instrukcja do rozmowy. To nie jest dowód ukończonego UAT.

Data: 2026-07-02

## Jak zacząć

Powiedz prosto:

> Chcę Ci pokazać, co WILQ już rozumie o Ekologusie, czego jeszcze nie rozumie
> i dlaczego blokuje pisanie finalnych treści. To nie jest prezentacja gotowego
> generatora. To jest review systemu decyzyjnego.

## Co pokazać

### Szybki status

Powiedz:

> WILQ ma już działające bramki przed demo. Sprawdza, czy dashboard pokazuje
> decyzje z dowodami, czy wiedza Ekologus nie jest udawana jako production-depth,
> czy Claim Ledger blokuje ryzykowne twierdzenia i czy skille mają evale.
> Nadal nie zamykamy Goal 005, bo brakuje realnej sesji UAT albo świadomego
> owner-defer.

Najkrótszy stan:

- dashboard usefulness: 12 powierzchni `demo_ready`, 1 `review_ready`, 0
  zablokowanych;
- wiedza Ekologus: 12 source facts, 5 prywatnych propozycji `ekologus-ai`,
  0% production-depth, wszystko nadal review-required;
- Claim Ledger: 10/10 checków, model nie może oznaczyć treści jako gotowej do
  publikacji;
- evale skilli: 13/13 skilli ma przypadek eval i wymagane pola outputu;
- poranna komenda WILQ musi już odpowiedzieć po ludzku: co zrobić najpierw,
  dlaczego teraz, z jakimi dowodami, co jest zablokowane i jaki jest następny
  bezpieczny krok;
- social: WILQ może przygotować kierunki LinkedIn/Facebook do review, ale nie
  może obiecać, że temat jest nowy albo niepowielony, dopóki nie ma historii
  postów jako metadata-only;
- completion guard nadal blokuje: nie wolno mówić, że Goal 005 jest domknięty.

Zapytaj:

1. Czy taki status jest jasny bez tłumaczenia technicznego?
2. Czy te blokady budują zaufanie, czy przeszkadzają w pracy?
3. Którą część chcesz zobaczyć jako pierwszą: wiedzę usług, treści, Ads/GA4,
   czy social/history?

### 0. Centrum pracy: co zrobić najpierw

Pokaż:

- dashboard `/command-center`
- eval proof:
  `.local-lab/evals/codex-skill/20260702T150140Z/wilq-daily-command/result.json`

Powiedz:

> To jest najbliższe temu, co BDOS robi rano. WILQ nie tylko pokazuje kafelki.
> Ma powiedzieć: co zrobić najpierw, dlaczego teraz, na jakich dowodach, czego
> nie wolno obiecać i jaka akcja jest bezpieczna do sprawdzenia. W aktualnym
> proofie najpierw wskazuje Merchant, bo tak wynika z `daily_decisions` i
> `primary_next_step`.

Zapytaj:

1. Czy taka poranna kolejka jest dla Ciebie użyteczna?
2. Czy chcesz, żeby pierwsza decyzja była bardziej marketingowa, sprzedażowa
   czy techniczno-pomiarowa?
3. Czy powód "dlaczego teraz" jest wystarczająco czytelny?

### 1. Czym realnie jest WILQ

Pokaż:

- `docs/handoffs/2026-07-02-wilq-marketing-content-model.md`

Powiedz:

> To nie ma być generator tekstów. To ma być system decyzyjny dla marketingu:
> bierze dane z GSC, GA4, Ads, Merchant, WordPress, Ahrefs, Localo i wiedzy
> Ekologus, sprawdza czy temat już był, czy claim jest dozwolony, czy mamy
> świeże dowody i dopiero wtedy pozwala iść w brief, draft albo akcję.

Zapytaj:

1. Czy ten model pracy ma sens dla marketingu Ekologus?
2. Czy bardziej wartościowa jest sama generacja tekstu, czy decyzja: co wolno,
   czego nie wolno i co ma największy sens?
3. Jakie historyczne posty LinkedIn/Facebook możemy dodać jako metadata-only,
   żeby WILQ nie powielał tematów?

Powiedz też:

> Dla sociala WILQ ma już twardą blokadę: bez historii postów LinkedIn/Facebook
> nie może powiedzieć, że temat jest nowy albo że nie powielamy wcześniejszej
> komunikacji. Na start wystarczą metadane: kanał, data, temat, usługa, claim,
> CTA, format, URL albo ID posta i źródło dowodu. Nie potrzebujemy raw treści
> postów ani komentarzy, żeby zbudować pierwszy dedupe contract.

### 2. Aktualny stan WILQ

Pokaż:

- `docs/handoffs/2026-07-01-wilku-content-uat-ready.md`
- `docs/handoffs/2026-07-02-wilku-claim-ledger-gate.md`

Powiedz:

> Tu jest aktualny stan. Najważniejsze: WILQ nie udaje, że jest gotowy do
> finalnych treści. Blokuje pełny brief, bo brakuje zatwierdzonej karty usługi
> i zatwierdzonego CTA. Dodatkowo ma Claim Ledger, czyli listę tego, co wolno
> powiedzieć, co wymaga człowieka i czego model nie może przemycić do szkicu.

Zapytaj:

1. Czy rozumiesz, czemu WILQ jeszcze nie powinien pisać finalnej treści?
2. Czy blocker `Brakuje karty usługi; Brakuje karty CTA` jest jasny?
3. Czy rozdział na dozwolone, wymagające review i zablokowane twierdzenia jest
   użyteczny?
4. Czy to brzmi jak sensowna kontrola jakości, czy jak techniczny bełkot?

### 3. BDO

Pokaż:

- `docs/handoffs/2026-07-02-wilku-bdo-uat-review.md`

Powiedz:

> To jest przykład tematu, który wygląda sensownie do pierwszego review:
> BDO i sprawozdawczość. Chcę sprawdzić, czy język, ryzyka i CTA brzmią jak
> Ekologus.

Zapytaj:

1. Czy tak wolno mówić o BDO?
2. Co tu brzmi jak Ekologus?
3. Co brzmi jak generyczne SEO albo AI?
4. Jakiego claimu absolutnie nie wolno użyć?

### 4. Eko-Opieka i Audyt zgodności

Pokaż:

- `docs/handoffs/2026-07-01-wilku-eko-opieka-review.md`
- `docs/handoffs/2026-07-01-wilku-audyt-zgodnosci-review.md`

Powiedz:

> To są propozycje kierunków z prywatnej wiedzy `ekologus-ai`. Nie traktujemy
> ich jako zatwierdzonej oferty. Chcę wiedzieć, czy to są realne kierunki
> sprzedaży Ekologus, czy AI coś dopowiedziało.

Zapytaj:

1. Czy Eko-Opieka / Eko Kalendarz to realna rzecz, czy tylko robocza nazwa?
2. Czy Audyt zgodności może być pierwszym płatnym krokiem?
3. Czy te tematy nadają się na stronę, post, mailing czy rozmowę handlową?
4. Co trzeba poprawić, zanim WILQ może zrobić brief?

### 5. Styl marki i bezpieczeństwo prawne

Pokaż:

- `docs/handoffs/2026-07-02-wilku-ekologus-ai-policy-review.md`

Powiedz:

> Tu nie chodzi o ofertę, tylko o zasady języka. Czy WILQ ma pilnować, żeby
> treści były konkretne, spokojne, bez pustych obietnic, bez gwarancji braku
> kar i bez interpretacji prawnej bez człowieka?

Zapytaj:

1. Czy "konkretnie, spokojnie i ekspercko" dobrze opisuje język Ekologus?
2. Czy blokować straszenie karami bez aktualnego review prawnego?
3. Czy claimy o WIOŚ, kontrolach, karach i decyzjach zawsze mają wymagać
   człowieka?
4. Jakich sformułowań WILQ ma nigdy nie używać?

### 6. Evale i pre-demo gate

Pokaż wynik komendy, jeśli chcesz mieć dowód techniczny:

```bash
rtk scripts/pre_demo_gate.sh --skip-dashboard --skip-shared-schema --no-skills
```

Powiedz:

> To jest nasz minimalny gate przed pokazaniem. Nie sprawdza tylko, czy coś się
> odpala. Sprawdza też, czy wiedza nie udaje zatwierdzonej, czy Claim Ledger
> nadal blokuje ryzykowne twierdzenia i czy wszystkie skille mają evale.

Zapytaj:

1. Czy taki gate wystarcza jako checkpoint przed pokazaniem kolejnych wersji?
2. Czy do gate’a dodać jeszcze coś, co z Twojej perspektywy łapie realne ryzyko
   marketingowe?

## Najważniejsze dwa pytania

Zadaj je na końcu:

1. Czy po tych materiałach rozumiesz, co WILQ wie, czego jeszcze nie wie i czemu
   blokuje pisanie finalnej treści?
2. Co tu jest najbardziej użyteczne, a co najbardziej przeszkadza?

## Czego nie mówić

Nie mów:

- że Goal 005 jest ukończony;
- że WILQ jest gotowy do finalnych draftów;
- że mamy production-depth wiedzę Ekologus;
- że `ekologus-ai` jest automatycznie zatwierdzoną bazą wiedzy;
- że WILQ może publikować albo pisać bez review człowieka.

Powiedz zamiast tego:

> Mamy działający system review, źródeł, blokad i pytań do człowieka. Teraz
> potrzebujemy Twojej opinii, żeby zdecydować, które kierunki można zatwierdzić,
> które poprawić, a których nie używać.

## Co zapisać po rozmowie

Po rozmowie zapisz:

- co Wilku zatwierdza;
- co wymaga zmian;
- co odrzuca;
- gdzie zapytał "skąd to wzięło?";
- co brzmiało generycznie albo nie jak Ekologus;
- czy rozumie blokady;
- jaki jest jeden następny krok.

Wynik pełnej sesji zapisuj przez:

```bash
rtk uv run python scripts/record_goal_005_content_uat_result.py .local-lab/proof/goal-005-content-uat-result-YYYYMMDD.json --api-base http://127.0.0.1:8000 --format markdown
```

Jeżeli po rozmowie dalej są follow-upy, to jest poprawny wynik. WILQ ma wtedy
pozostać zablokowany przed completion claim, ale z lepszym feedbackiem.
