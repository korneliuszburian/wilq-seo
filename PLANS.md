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
wybór strony, usługi, sekcji, intencji i CTA
→ zakres, cel i evidence-backed opportunity
→ plan sekcji + claim ledger + dowody
→ zapisana immutable revision
→ exact-version human review
→ revision-bound podgląd draftu WordPress
→ osobne review i potwierdzenie ActionObjectu
→ audit
→ okno pomiaru
→ learning proposal
```

Codex może przygotować propozycję child revision przez jeden API-owned seam.
Nie może samodzielnie zmienić kroku workflow, zatwierdzić tekstu, wykonać
ActionObjectu ani zapisać WordPress.

## Kontrakt jakości Treści i SEO 10/10

Ocena 10/10 nie wynika z liczby funkcji ani zielonych testów. Może zostać
nadana dopiero po realnym UAT Wilka, gdy jeden workspace pozwala bez pomocy
developera:

- w 30 sekund zrozumieć decyzję, dowody, freshness, blocker i następny krok;
- wybrać stronę, usługę, intencję, CTA i zakres, a następnie zobaczyć mapę
  sekcji odzwierciedlającą stronę;
- zobaczyć tylko metryki, zapytania i keyword/Ads signals, które mają aktualne
  source connectors, evidence IDs i freshness; brak danych ma blokować wniosek,
  a nie tworzyć fikcyjny wolumen lub „SEO score”;
- rozumieć, dlaczego każda ważna teza, nagłówek i CTA znalazły się w tekście,
  z rozdzieleniem approved facts, review-required claims i pomysłów;
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
  domykają przerwany proces bez retry write. `dev_draft` prowadzi teraz zwarty
  inline ActionObject chain w kontekście exact revision; typed konflikt
  zatrzymuje apply bez retry, a syntetyczny browser proof nie wykonuje realnego
  WordPress write.
- Operator workflow tworzenia treści jest obecnie oceniony na około 6/10,
  jakość realnego wygenerowanego tekstu na około 5/10, a 8/10 dotyczy wyłącznie
  bezpieczeństwa exact-version handoffu. Marketer może już wybrać sekcje
  reviewed base revision, uruchomić grounded Codex proposal i zobaczyć
  base-vs-child diff, findings oraz semantyczną bramkę review. Realny output
  nadal był generyczny i `needs_changes`, więc nie jest to dowód jakości 10/10.
  Cztery stare publiczne Structured Outputs routes nadal tworzą alternatywny
  API-key entrypoint poza dashboardem; usuwa je `wilq-seo-r564.14`.
- Live content queue jest świeża, ale ma 2 pozycje i 1 wykonalną przy minimum 3.
  Service Profile pozostaje `source_backed_review_required`.

## Plan wykonania

1. `wilq-seo-r564.8` jest zamknięty: append-only revisions, exact review,
   stateful browser proof i poprawiony timeout startu dashboardowego API są
   zweryfikowane.
2. `wilq-seo-r564.9` jest zweryfikowany: revision-bound handoff, exact
   ActionObject chain i syntetyczny draft-only apply bez publikacji.
3. `wilq-seo-r564.10` jest zweryfikowany: zwarty inline multi-step prowadzi
   exact revision przez preview → review → confirm → impact → apply, z jednym
   aktywnym CTA i typed blockerem bez retry.
4. `wilq-seo-r564.11` jest zamknięty: bounded WILQ API → Codex app-server lab.
   Realny login ChatGPT utworzył `unreviewed` child revision z pełnym inputem i
   trwałym lineage, bez vendor write. Quality ocenia wyłącznie utrwalane wybrane
   sekcje i deklarowane lineage, wymaga semantycznego review i zwróciło
   `needs_changes`; model-only CTA/meta/linki nie poprawiają oceny child revision.
   Odkryty w broad gate błąd `normalized_page_path` jest zamknięty w
   `wilq-seo-r564.12`: canonical path przechodzi, pozostałe kształty są
   fail-closed.
5. `wilq-seo-r564.13` podłącza seam do aktywnego kroku `draft`: typed wybór
   sekcji, pending, diff, lineage i findings; mylący marketerowy WordPress
   dry-run i osierocone panele są usunięte. Cross-work-item wynik i brak sekcji
   są fail-closed, a browser proof desktop/mobile nie dotyka WordPressa.
6. `wilq-seo-r564.14` usuwa niegrounded legacy public runtime po migracji
   skilla/testów, bez usuwania internal contractów używanych przez Codex
   proposal. Potem kontynuować usefulness-first rozwój:
   jawny wybór strony/usługi/sekcji/intencji/CTA, metryki i słowa kluczowe tylko
   z aktualnych typed źródeł, porównanie wersji, bibliotekę treści oraz realny
   Wilku UAT.
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
- Techniczne, nadal wykonywalne repo-local: dashboardowy wybór sekcji +
  diff/findings dla app-server proposal, wycofanie legacy runtime po audycie
  referencji oraz użytecznościowy proof paczki tekstów.

## Outcome

Goal 005 pozostaje aktywny. Nie ma dowodu produkcyjnej gotowości, finalnej
treści ani pełnej użyteczności dla Wilka.
