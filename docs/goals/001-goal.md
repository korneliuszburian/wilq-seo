# Active Goal — WILQ SEO Useful Controlled Pilot

Status: active.

Primary Beads epic: `wilq-seo-1oa`.

Follow-on review epic: `wilq-seo-v9ab`.

Date: 2026-07-16.

## Cel

Dowieźć uczciwy, użyteczny pilot WILQ Marketing Operating System dla Ekologus,
w którym Wilku może podjąć decyzję i przeprowadzić jedną pełną pracę nad
treścią bez pomocy developera:

```text
aktualne dowody i reviewed knowledge
→ wybór strony, usługi, intencji, CTA i sekcji
→ zatwierdzony zakres i mapa sekcji
→ exact persisted revision i grounded Codex proposal
→ human review
→ revision-bound WordPress draft-only
→ publication-bound measurement
→ review-only learning proposal
```

WILQ API pozostaje mózgiem produktu. Dashboard i skills używają tych samych
typed kontraktów. Codex korzysta wyłącznie z istniejącego lokalnego
`codex login`; browser nie łączy się z nim bezpośrednio.

## Aktualna prawda

- Techniczny pięciostopniowy workflow `scope → section_map → draft → review →
  dev_draft` istnieje w `/content-workflow` i ma jeden aktywny entrypoint.
- Exact homepage snapshot używa 29 bieżących, page-scoped sygnałów
  planistycznych GSC: 47 wyświetleń i 3 kliknięcia. Karta kontekstu, zakres,
  tytuł oraz oba publiczne odczyty snapshotu korzystają z tego samego zakresu;
  UI pokazuje cztery najwyższe wiersze i jawnie opisuje pełną liczność.
- Exact revisions, human review, revision-bound ActionObject, WordPress
  draft-only, measurement window i review-only learning są zaimplementowane.
- Realny wygenerowany tekst nadal uzyskał `needs_changes`; nie ma dowodu jakości
  10/10 ani gotowości do publikacji.
- Service Profile ma source-backed wiedzę, ale nadal
  `source_backed_review_required`; nie ma owner-approved production-depth cards.
- Realny Wilku content UAT i review realnego daily-check nie odbyły się.
- Runtime jest prywatnym pilotem loopback-only. Nie jest to dowód auth, TLS,
  multi-tenant ani gotowości produkcyjnej.
- Realna migracja storage, publikacja i vendor write pozostają poza obecną
  zgodą.

## Aktualne zadania

Beads jest jedynym operacyjnym grafem zadań. Bieżąca kolejność:

1. `wilq-seo-lt1` — po otrzymaniu reviewed sources skompilować owner-reviewed
   service/CTA/claim/evidence cards. To jest bramka ownera, nie pole do
   zgadywania.
2. `wilq-seo-jst` — przeprowadzić realny content UAT z Wilkiem albo zapisać
   jawny owner defer i residual risk.
3. `wilq-seo-v9ab.13` — dać Wilkowi realny polski daily-check do oceny albo
   zapisać jawny defer. Techniczna implementacja Goal 006 jest już wykonana.

`bd ready --json` pokazuje obecnie tylko dwa otwarte epiki nadrzędne. Nie ma
potwierdzonego repo-local taska poza trzema powyższymi bramkami człowieka;
nie wolno wymyślać technicznego cleanupu tylko po to, by utrzymać ruch.

Po każdym zamkniętym slice odczytaj ponownie `bd ready --json` i
`bd list --status=open --json`. Nie wracaj do zamkniętych technicznych epików
bez nowego dowodu regresji.

## Kryterium jakości

Pilot jest użyteczny dopiero, gdy Wilku w realnym zadaniu potrafi:

- w 30 sekund zrozumieć decyzję, dowody, freshness, blocker i następny krok;
- wybrać stronę, usługę, intencję, CTA i sekcje bez technicznej ściany;
- rozpoznać, które twierdzenia są approved, review-required albo zabronione;
- zapisać, wznowić, porównać i poprawić dokładną wersję treści;
- przekazać wyłącznie przeczytaną wersję jako WordPress draft przez
  ActionObject i audit;
- później zobaczyć server-owned pomiar i learning proposal bez automatycznego
  success claimu ani zmiany wiedzy.

Syntetyczne testy i browser proof chronią kontrakt techniczny. Oceny 10/10 nie
wolno nadać przed realnym UAT marketera i review konkretnej paczki tekstów.

## Granice

- Brak evidence ID, source connectora albo aktualności oznacza brak rekomendacji.
- Brak reviewed knowledge oznacza blocker, nie modelowe dopowiedzenie.
- WordPress pozostaje draft-only; publish/update/delete są poza journey.
- Nie dodawaj OpenAI API keya, Agents SDK, Ollamy ani drugiej ścieżki modelu.
- Nie buduj broad RAG, nowego ekranu, endpointu, guardu lub testu bez
  konkretnego ryzyka operatora.
- Nie wykonuj vendor write, realnej publikacji ani migracji storage bez osobnej
  zgody i właściwego okna.
- Nie claimuj owner/expert acceptance, jakości tekstu, efektu SEO/Ads ani
  gotowości produkcyjnej bez dowodu.

## Sposób pracy

Każdy slice ma: konkretny problem, minimalną zmianę, focused proof, aktualizację
właściwego state record, komentarz i zamknięcie Beada, świadomy commit i push.
Po pushu wybierz najwyżej wartościową bezpieczną pracę z aktualnego grafu.

Przed zmianą dashboardu czytaj `docs/dashboard-state.md`; przed cleanupem
`docs/current-cleanup-state.md`; bieżący skrót pozostaje w
`docs/PROGRESS.md`. Historia jest w git i zamkniętych Beads, nie w tym pliku.

## Zakończenie

Ten goal można zamknąć dopiero, gdy:

1. źródła wymagane przez realny content workflow są aktualne albo mają jawny
   zewnętrzny blocker;
2. wiedza użyta do tekstu jest owner-reviewed i zachowuje lineage;
3. realny Wilku content UAT jest wykonany albo owner jawnie go odracza z
   residual risk;
4. pierwszy ekran dashboardu prowadzi do użytecznej decyzji bez tłumaczenia
   developera;
5. WordPress pozostaje draft-only i exact-version review-bound;
6. realny daily-check jest reviewed albo jawnie odroczony;
7. focused proof i wymagany finalny `scripts/verify.sh` są zielone;
8. pozostały wyłącznie jawne bramki ownera lub osobnego maintenance/publish
   authority, bez potwierdzonej bezpiecznej pracy repo-local.
