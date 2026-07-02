# Co pokazać Wilkowi

Status: krótka instrukcja do rozmowy. To nie jest dowód ukończonego UAT.

Data: 2026-07-02

## Jak zacząć

Powiedz prosto:

> Chcę Ci pokazać, co WILQ już rozumie o Ekologusie, czego jeszcze nie rozumie
> i dlaczego blokuje pisanie finalnych treści. To nie jest prezentacja gotowego
> generatora. To jest review systemu decyzyjnego.

## Co pokazać

### 0. Czym realnie jest WILQ

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

### 1. Aktualny stan WILQ

Pokaż:

- `docs/handoffs/2026-07-01-wilku-content-uat-ready.md`

Powiedz:

> Tu jest aktualny stan. Najważniejsze: WILQ nie udaje, że jest gotowy do
> finalnych treści. Blokuje pełny brief, bo brakuje zatwierdzonej karty usługi
> i zatwierdzonego CTA.

Zapytaj:

1. Czy rozumiesz, czemu WILQ jeszcze nie powinien pisać finalnej treści?
2. Czy blocker `Brakuje karty usługi; Brakuje karty CTA` jest jasny?
3. Czy to brzmi jak sensowna kontrola jakości, czy jak techniczny bełkot?

### 2. BDO

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

### 3. Eko-Opieka i Audyt zgodności

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

### 4. Styl marki i bezpieczeństwo prawne

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
