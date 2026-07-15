# PLANS.md — Goal 005 Knowledge Depth And UAT Closure

Status: active. Beads epic: `wilq-seo-1oa`.

To jest restartowalny plan bieżący, nie historia wykonania. Szczegóły produktu
są w `docs/goals/archive/005-goal.md`, stan dashboardu w
`docs/dashboard-state.md`, handoff cleanupu w `docs/current-cleanup-state.md`,
a kolejność pracy w Beads.

## Cel

Udowodnić, że WILQ pomaga realnemu marketerowi Ekologus podejmować decyzje
i tworzyć treści na podstawie aktualnych dowodów oraz reviewed knowledge.
Mechanicznie poprawny pipeline nie wystarcza: wynik ma być zrozumiały,
odtwarzalny, wersjonowany i bezpieczny przed przypadkowym zatwierdzeniem innej
treści niż ta, którą przeczytał człowiek.

## Granice

- WILQ API jest jedynym brainem produktu.
- Dashboard i Codex skills używają tych samych typed kontraktów API.
- Każda rekomendacja wymaga evidence IDs, source connectors i freshness.
- WordPress pozostaje draft-only; publikacja i destrukcyjne zmiany są poza
  bieżącym zakresem.
- Brak aktualnej wiedzy, dowodu, zgody lub poprawnego kontekstu jest blockerem,
  nie zaproszeniem do zgadywania.
- Nie budujemy nowego endpointu, ekranu, guardu ani testu bez konkretnego ryzyka
  operatora.
- Executor Codex ma używać istniejącego logowania ChatGPT/Codex po stronie
  serwera. Nie dodajemy zależności od OpenAI API keya, Agents SDK, Ollamy ani
  alternatywnej ścieżki modelu.

## Kanoniczny przebieg treści

```text
wybór strony i usługi
→ zakres i cel
→ plan sekcji + dowody
→ zapisana immutable revision
→ exact-version human review
→ revision-bound podgląd draftu WordPress
→ osobne review i potwierdzenie ActionObjectu
→ audit
→ okno pomiaru
→ learning proposal
```

Codex może w przyszłości przygotować propozycję child revision. Nie może
samodzielnie zmienić kroku workflow, zatwierdzić tekstu, wykonać ActionObjectu
ani zapisać WordPress.

## Stan produktu

- `/content-workflow` jest głównym workspace `Treści i SEO`.
- API zwraca pięć kroków: `scope`, `section_map`, `draft`, `review`,
  `dev_draft`. Każdy ma phase, readiness, blocker, możliwość otwarcia/zapisu
  i polski następny krok.
- Marketer mode pokazuje jedną decyzję i jeden aktywny workspace. Techniczne
  panele są za jawnym przełączeniem.
- Append-only revisions wiążą tekst z work itemem, bazową wersją, adresem,
  paczką planu i jej digestem. Exact review wiąże decyzję z revision ID oraz
  digestem treści.
- Zmiana planu/evidence unieważnia stare review i rebasuje edytor do bieżącego
  kontekstu. Równoległa inna decyzja review nie może nadpisać wcześniejszej bez
  odświeżenia.
- `dev_draft` pozostaje zablokowany, ponieważ istniejący legacy handoff i apply
  nie są jeszcze związane z exact revision.
- Live content queue jest świeża, ale ma 2 pozycje i 1 wykonalną przy minimum 3.
  Service Profile pozostaje `source_backed_review_required`.

## Plan wykonania

1. `wilq-seo-r564.8` jest zamknięty: append-only revisions, exact review,
   stateful browser proof i poprawiony timeout startu dashboardowego API są
   zweryfikowane.
2. Utworzyć P0 child `wilq-seo-r564` dla revision-bound WordPress handoff.
   Legacy human-review/audit ma fail-close dla revision-enabled work itemów;
   handoff i ActionObject muszą wskazywać dokładną zaakceptowaną wersję.
3. Udowodnić preview oraz draft-only apply na materiale syntetycznym/stagingowym
   bez publikacji i bez omijania review/confirm/audit.
4. Dopiero wtedy zaprojektować jeden server-side adapter WILQ API → Codex
   app-server/SDK. Pierwszy zakres: propozycja child revision i strumień statusu,
   bez automatycznej akceptacji i bez vendor write.
5. Kontynuować usefulness-first rozwój treści: wybór strony/usługi, mapowanie
   sekcji, dostęp do wersji, odzwierciedlenie strony i realny Wilku UAT.
6. Po każdym slice ponownie odczytać `bd ready --json` i
   `bd list --status=open --json`; nie wracać do ukończonych zakresów bez nowego
   dowodu regresji.

## Weryfikacja każdego slice

1. konkretny problem operatora lub ryzyko pilota;
2. najmniejsza zmiana w jednym kanonicznym seamie;
3. focused test albo smoke dla tej regresji;
4. API/dashboard/browser proof proporcjonalny do ryzyka;
5. aktualizacja bieżącego state record i Beada;
6. `rtk scripts/verify.sh` przed szerokim claimem;
7. commit, push i ponowny wybór pracy z roadmapy.

## Decyzje trwałe

- Nie przywracać all-panels-at-once UI ani ukrytej alternatywnej ścieżki
  runtime.
- Nie uznawać legacy package review za akceptację exact text.
- Nie traktować dev/staging WordPress jako kanonicznego dowodu SEO.
- Nie kasować starych danych storage bez osobnego manifestu i zgody.
- Nie przedstawiać stałej etykiety aktora jako uwierzytelnienia użytkownika.
- Nie kończyć Goal 005 bez realnego Wilku UAT albo jawnego owner defer.

## Otwarte blokery

- Owner/Wilku: reviewed Service Profile i decyzje o wiedzy.
- Owner/Wilku: realna sesja UAT albo jawne odroczenie z ryzykiem.
- Dane: za mała gęstość bezpiecznej kolejki treści.
- Kontrakt zewnętrzny: uwierzytelniony actor/tenant przed produkcyjnym użyciem.
- Techniczne, nadal wykonywalne repo-local: revision-bound WordPress seam,
  następnie adapter Codex app-server/SDK.

## Outcome

Goal 005 pozostaje aktywny. Nie ma dowodu produkcyjnej gotowości, finalnej
treści ani pełnej użyteczności dla Wilka.
