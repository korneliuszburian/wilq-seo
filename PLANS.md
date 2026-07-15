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

## Kontrakt jakości Treści i SEO 10/10

Ocena 10/10 nie wynika z liczby funkcji ani zielonych testów. Może zostać
nadana dopiero po realnym UAT Wilka, gdy jeden workspace pozwala bez pomocy
developera:

- w 30 sekund zrozumieć decyzję, dowody, freshness, blocker i następny krok;
- wybrać stronę, usługę, intencję, CTA i zakres, a następnie zobaczyć mapę
  sekcji odzwierciedlającą stronę;
- przejść krótki wizard plan → draft/Codex → exact review → draft WordPress,
  bez rozwijania ściany paneli i bez utraty kontekstu;
- zapisywać, wznawiać, porównywać i poprawiać dokładne wersje treści wraz z
  lineage dowodów;
- wysłać do WordPress wyłącznie przeczytaną i zatwierdzoną wersję, jako draft,
  z pełnym ActionObject/auditem i bez możliwości cichego replayu starej zgody;
- wrócić do biblioteki treści, historii decyzji i późniejszego pomiaru, zamiast
  szukać wyniku w logach lub technicznych payloadach.

Desktop, mobile i syntetyczny browser proof chronią kontrakt techniczny.
Końcową ocenę użyteczności 10/10 potwierdza dopiero marketer w realnym zadaniu;
do tego czasu dashboard zachowuje aktualną, niższą ocenę i jawny następny cel.

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
- Handoff i apply są związane z exact revision; wysyłają wyłącznie immutable
  title/sections i odrzucają legacy/v2/tamper przed adapterem. Zgoda bindingu
  jest atomowo jednorazowa, więc równoległy apply i replay nie tworzą drugiego
  draftu. Durable start, atomowy outcome i lokalne readback reconciliation
  domykają przerwany proces bez retry write. `dev_draft` pozostaje zablokowany
  w dashboardzie, bo UI nie prowadzi jeszcze exact ActionObject chain w
  kontekście wybranej rewizji.
- Live content queue jest świeża, ale ma 2 pozycje i 1 wykonalną przy minimum 3.
  Service Profile pozostaje `source_backed_review_required`.

## Plan wykonania

1. `wilq-seo-r564.8` jest zamknięty: append-only revisions, exact review,
   stateful browser proof i poprawiony timeout startu dashboardowego API są
   zweryfikowane.
2. `wilq-seo-r564.9` jest zweryfikowany: revision-bound handoff, exact
   ActionObject chain i syntetyczny draft-only apply bez publikacji.
3. Zbudować w `/content-workflow` zwarty inline multi-step dla wybranej rewizji:
   preview → review → confirm → apply, z jednym CTA i typed blockerem na krok.
4. Następnie wykonać jeden bounded server-side lab WILQ API → Codex app-server.
   Pierwszy zakres: propozycja child revision i strumień statusu, bez
   automatycznej akceptacji i bez vendor write.
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
- Dla osadzonego executora testować `codex app-server` przez lokalny
  stdio/Unix transport. Oficjalny manual wskazuje app-server dla rich clients
  z historią, approval i streamem eventów, a SDK dla automatyzacji/jobów.
  Decyzja pozostaje `lab-test`, bo lokalny CLI 0.144.4 oznacza app-server jako
  experimental. Browser nie łączy się z nim bezpośrednio; nie dodajemy API keya.
- Nie kończyć Goal 005 bez realnego Wilku UAT albo jawnego owner defer.

## Otwarte blokery

- Owner/Wilku: reviewed Service Profile i decyzje o wiedzy.
- Owner/Wilku: realna sesja UAT albo jawne odroczenie z ryzykiem.
- Dane: za mała gęstość bezpiecznej kolejki treści.
- Kontrakt zewnętrzny: uwierzytelniony actor/tenant przed produkcyjnym użyciem.
- Techniczne, nadal wykonywalne repo-local: inline revision-bound ActionObject
  UX, następnie ograniczony adapter Codex app-server.

## Outcome

Goal 005 pozostaje aktywny. Nie ma dowodu produkcyjnej gotowości, finalnej
treści ani pełnej użyteczności dla Wilka.
