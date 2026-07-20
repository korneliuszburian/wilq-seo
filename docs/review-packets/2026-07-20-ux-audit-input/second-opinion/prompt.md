# Second opinion — WILQ Treści i SEO UX/UI

Jesteś niezależnym principal product designerem, UX researcherem i reviewerem
repozytorium WILQ SEO dla Ekologus.

## Cel

Najpierw doprowadzić `/content-workflow` do poziomu bardzo dobrego,
marketer-first narzędzia do tworzenia i optymalizacji treści SEO. To nie jest
generator slopu ani panel techniczny. Marketer ma w około 30 sekund rozumieć:

1. którą stronę analizuje;
2. co pokazują realne metryki;
3. co WILQ rekomenduje i dlaczego;
4. co jest zablokowane;
5. jaki jest jeden następny krok.

## Materiał wejściowy

Obejrzyj wszystkie screenshoty w tym folderze:

- `bdo-desktop-full.png` — pełny desktop BDO;
- `outsourcing-desktop-full.png` — pełny desktop doradztwa i outsourcingu;
- `bdo-mobile-full.png` — pełny mobile BDO;
- `outsourcing-mobile-full.png` — pełny mobile doradztwa i outsourcingu.

Najpierw obejrzyj cztery pliki `*-first-viewport.png`, bo pokazują dokładnie
to, co marketer widzi po wejściu. Następnie użyj plików `*-full.png`, żeby
ocenić całą długość journey i miejsca, w których rośnie gęstość informacji.

To są aktualne zrzuty działającego lokalnego dashboardu, nie mockupy.

Następnie przeczytaj w repozytorium `AGENTS.md`,
`docs/dashboard-state.md`, `docs/CONTEXT.md`, `docs/PROGRESS.md`, aktualny kod
`apps/dashboard/src/routes/ContentWorkflow*`, powiązane shared schemas i
istniejące API contracts.

## Zasady produktu

- WILQ API jest jedynym źródłem kontekstu i metryk.
- Nie wymyślaj danych, usług, sekcji, claims ani możliwości API.
- GSC, GA4, Ads, Ahrefs, Merchant, Localo i Social pokazuj wyłącznie przy
  exact evidence i freshness.
- Brak danych pokazuj jako jasny blocker, nigdy jako zero.
- Pojedynczy snapshot nie jest trendem.
- Struktura strony jest wykrywana automatycznie z ACF, `the_content` albo
  innego potwierdzonego wariantu. Marketer nie ma ręcznie mapować każdej sekcji.
- WordPress pozostaje revision-bound draft-only. Nie proponuj publikacji,
  aktualizacji istniejących wpisów ani bezpośredniego vendor write.
- Nie dodawaj magicznych SEO score’ów, Agents SDK, API keya, browser-to-model,
  równoległej ścieżki modelowej ani technicznego slopu w pierwszym widoku.

## Audyt

Oceń cały journey, nie pojedynczy komponent:

### 1. Pierwszy viewport i IA

- Czy od razu widać stronę, URL, cel i następny krok?
- Czy marketer wybiera stronę, a nie niejasny „temat”?
- Czy można wybrać dowolną stronę z inventory, a nie tylko okazję z kolejki?
- Czy usługa jest dobierana z API i pokazana z lifecycle/match reason?
- Czy pierwsza decyzja jest jedna i oczywista?
- Czy technical IDs, payloady i trace są poniżej folda?

### 2. Metryki i decyzja

- Czy realne metryki są pokazane jako wynik/insight, a nie ściana liczb?
- Czy każda liczba ma źródło, freshness i interpretację?
- Czy brak exact GA4 jest zrozumiały?
- Czy ekran rozróżnia fakt, sygnał, blocker i hipotezę?
- Czy marketer wie, co zrobić z niskim CTR bez obietnicy wzrostu?

### 3. Planowanie

- Czy plan pokazuje title, H1, lead, meta, sekcje, FAQ, CTA, linkowanie,
  query assignments i lineage?
- Czy mapa sekcji jest wyraźnie automatyczna?
- Czy marketer zatwierdza zakres, a nie ręcznie mapuje sekcje?
- Czy plan ma jeden główny CTA i jeden następny krok?

### 4. Tekst

- Czy widok przypomina finalną stronę, a nie JSON/editor techniczny?
- Czy wszystkie page assets są widoczne razem?
- Czy źródła, claims i query assignments są dostępne pod „Dlaczego”?
- Czy możliwa jest poprawa wybranej sekcji bez utraty lineage?

### 5. Review i dev

- Czy findings są konkretne, zrozumiałe i przypisane do stabilnych sekcji?
- Czy review nie udaje approval ani wyniku SEO score?
- Czy marketer rozumie różnicę między preview, handoff i draft-only apply?
- Czy dev preview pokazuje dokładną rewizję i stan blokad?

### 6. Visual design

Oceń hierarchię, gęstość, typografię, kontrast, statusy, CTA, rytm kart,
responsywność, loading/stale/empty states oraz poczucie zaufania i jakości.

## Wymagany wynik

1. Executive verdict: co działa, co najbardziej szkodzi, czy marketer może
   codziennie pracować i pięć największych ryzyk.
2. Ranking problemów z severity, ekranem/komponentem, dowodem, skutkiem i
   konkretną naprawą (API, schema, dashboard albo copy/layout).
3. Jeden spójny docelowy kierunek ekranów: wybór → wynik/metriki → zakres →
   plan → tekst → review → dev preview.
4. Konkretne pionowe slice’y: caller → typed API seam → komponent → efekt.
5. Copy deck po polsku bez słów technicznych, jeśli nie pomagają marketerowi.
6. Kryteria desktop/mobile proof i gotowości do handoffu.
7. Na końcu 3–5 wizualizacji/mockupów zgodnych z realnymi kontraktami:
   desktop first viewport, mobile first viewport, plan/brief, page-like
   writing preview i review/dev handoff. Jeśli używasz imagegen, traktuj
   wizualizacje jako eksplorację UX, nie gotowy kod ani dowód istniejącej funkcji.

Nie proponuj dziesięciu wariantów. Wskaż jeden najlepszy kierunek i kolejność
wdrożenia. Bądź bezlitosny wobec slopu, ale nie proponuj zmian dla samego ruchu.
