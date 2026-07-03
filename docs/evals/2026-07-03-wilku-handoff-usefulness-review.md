# Wilku handoff usefulness review

Data: 2026-07-03

Status: lokalny, read-only review materiałów do rozmowy z Wilkiem. To nie jest
realny Wilku UAT i nie domyka Goal 005.

Subagent reviewers nie uruchomili się z powodu limitu użycia, więc ten pass jest
lokalnym review w trzech rolach. Nie było publikacji, pushowania, zapisu do
WordPressa ani vendor write.

## Live proof

Sprawdzone lokalnie:

```bash
rtk uv run python scripts/goal_005_completion_check.py --api-base http://127.0.0.1:8000 --format json
rtk uv run python scripts/dashboard_usefulness_audit.py --api-base http://127.0.0.1:8000 --format markdown
```

Wynik:

- Goal 005 nadal blokuje `goal_005_uat_result_or_owner_defer`;
- nie wolno twierdzić: ukończony Goal 005, realny dowód użyteczności dla Wilka,
  production-depth readiness, gotowość finalnego draftu albo publikacji;
- dashboard audit: 15 powierzchni, 13 `demo_ready`, 2 `review_ready`, 0
  `blocked`, `pass=true`;
- Service Profile: 14 review actions, 5 prywatnych propozycji `ekologus-ai`,
  `promotion_ready=false`;
- `/content-workflow`: REST `configured`, WP-CLI `configured`, 21 layoutów ACF,
  write boundary zablokowany.

## Oceny 0-10

| Rola | Ocena | Wniosek |
| --- | ---: | --- |
| SEO/content strategist | 7.5 | Materiał dobrze tłumaczy źródła, BDO, claimy i social-history blocker, ale nadal jest zbyt meta-heavy jako pierwszy read. |
| Marketer/operator | 7 | Da się zrozumieć status, ale action IDs, `production-depth`, `source facts` i `skill eval` trzeba trzymać pod spodem. |
| Product/architecture reviewer | 8 | Truth model jest spójny: API jest mózgiem, output jest review-only, publikacja zablokowana. Największy brak to nadal realna sesja Wilka. |

Średnia użyteczność materiału do pokazania: **7.5/10**.

## Co jest mocne

1. Handoff jasno mówi, że WILQ nie jest gotowym generatorem ani autopublisherem.
2. Social duplicate risk jest ujęty poprawnie: bez historii LinkedIn/Facebook
   nie wolno obiecywać braku powtórek.
3. BDO specimen jest praktyczny: ma źródła, bezpieczny język, CTA i listę
   forbidden claims.
4. `ekologus-ai` jest traktowane jako prywatna propozycja do review, nie jako
   automatycznie zatwierdzona wiedza.
5. ACF/WordPress proof jest użyteczny, bo pokazuje realny kierunek authoringu,
   ale wyraźnie blokuje zapis i publikację.

## Co jest słabe albo mylące

1. Za dużo technicznych nazw w pierwszych sekcjach może uruchomić pytanie
   "co to są te dziwne ID?" zanim Wilku zobaczy wartość biznesową.
2. `dashboard usefulness score=10` dla wszystkich ekranów wygląda zbyt
   optymistycznie, jeśli czytać to jako realną użyteczność, a nie readiness
   contract.
3. Frazy `production-depth`, `source facts`, `review_required`, `skill eval`
   są potrzebne technicznie, ale nie powinny być pierwszym językiem rozmowy.
4. Pakiet ma dużo plików. Bez prowadzenia rozmowy łatwo zgubić kolejność:
   status -> praktyczny przykład -> decyzja Wilka.
5. Brakuje jednego zdania typu: "dzisiaj nie prosimy o publikację, prosimy
   tylko o decyzję review dla wiedzy i claimów".

## Zmiany wykonane po review

- `docs/handoffs/2026-07-02-co-pokazac-wilkowi.md` dostał krótki start:
  status, jeden praktyczny przykład, decyzja od Wilka.
- W najkrótszym statusie `source facts` zostały przepisane na "fakty ze
  źródeł", a `production-depth` na "wiedzę zatwierdzoną do finalnych treści".
- Sekcja `13/13 skill eval` została przepisana jako "13 umiejętności przeszło
  testy".

## Następne tuning targets

1. Dodać jeszcze krótszą kartę "co Wilku ma kliknąć/ocenić jako pierwsze" dla
   Service Profile, bez action IDs w pierwszym widoku.
2. Rozdzielić automatyczny dashboard score od realnego UAT score, żeby `10/10`
   nie brzmiało jak deklaracja idealnej użyteczności.
3. Przygotować prostą checklistę odpowiedzi Wilka: zatwierdź/popraw/odrzuć dla
   BDO, claim policy i social-history blocker.
4. Po realnym review Wilka przepuścić wynik przez
   `scripts/record_goal_005_content_uat_result.py` albo owner-defer guard.
5. Nie dodawać kolejnych guardów, dopóki nie poprawiają decyzji lub języka
   operatora.

