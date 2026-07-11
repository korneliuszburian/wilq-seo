# Independent repository rebaseline — 2026-07-10

Audyt zbudowano z aktualnego repo, managed runtime, API, testów, renderów i
grafu Beads. Historyczne rozmowy, screenshoty i opisy Beads były wyłącznie
wskazówkami.

## Aktualne dowody

- Baseline: `main`, początkowo clean i zgodny z `origin/main` na `f450383c`.
- Managed API/dashboard: ready; health `ok`.
- DuckDB: 95 740 metric facts, 4 507 refresh runs.
- Konektory: 12 ogółem, 9 configured, 2 missing credentials, 1 disabled.
- Content diagnostics: `state=stale`, `requires_refresh=true`; ostatnie
  sukcesy głównych źródeł contentu pochodzą z 2026-07-07.
- Queue: `blocked`, 2 kandydatów, 0 actionable, minimum 3; evidence lineage z
  Ahrefs, GSC i publicznego WordPressa.
- Complexity changed report: 35 plików, 1 frozen (`actions/service.py`), 15
  violations. Hotspoty: Ads diagnostics 6 430 LOC, action service 5 989,
  ContentWorkflowSurface ok. 3 000, content API 1 478, Ads contract test 4 971.
- Latest `c9h9.5` diff report: 22 zmienione pliki, 0 frozen, 1 istniejące
  przekroczenie budżetu (`wilq/content/workflow/api.py`, 1 478 LOC).
- Browser proof: desktop 1440×900, mobile 390×844 i action detail pod
  `.local-lab/proof/independent-review-2026-07-10/`.

## Mapa systemu

Status używa wyłącznie wymaganego słownika.

| Obszar | Status | Aktualny stan | Dowód | Problem | Istniejący Bead | Brakujące zadanie |
| --- | --- | --- | --- | --- | --- | --- |
| API | `partially_complete` | Typed health, diagnostics, queue, snapshots i action readiness działają; direct WordPress live jest fail-closed. Queue/snapshot carry typed freshness and reuse one short-lived diagnostics build. | Live HTTP, focused content tests, API smoke. | Raw diagnostics rows remain broader than the gated queue; secondary routes still have cold gaps. | `.9`–`.13` | Wszystkie potwierdzone cold gaps mają zadania. |
| `/content-workflow` | `partially_complete` | Konkretna homepage, public/dev sections, GSC, typed freshness blocker, queue-owned first card, typed preview i preview-only CTA. | Fresh desktop/mobile render 2026-07-11, live queue/snapshot, queue budget `<5 s`, focused UI/E2E tests. | Mobile decyzja/CTA remains below triage; raw diagnostics rows are not the active queue truth. | `c9h9.4`, `r564.3`, `ho41` | Brak — potwierdzone scope istnieją. |
| Dashboard IA | `partially_complete` | Legacy planner usunięty; główne nav prowadzi do `/content-workflow`. | Route registry, negative route tests, render. | Część E2E utrwalała stare stringi; drugorzędne trasy mają cold latency. | `c9h9.8`–`.13`, `r564`, `ho41` | Utworzone na podstawie failure proof. |
| ActionObject safety | `partially_complete` | Preview/review/confirm/audit istnieją; direct content live i UI create są zablokowane. Typed existing-draft preview działa. | Live direct POST blocked/no write; mutation summary 0/0; action screenshot. | Canonical dev-only create apply nie istnieje; niższy boundary nadal ma raw authorization booleans nieosiągalne z produkcyjnego HTTP. | zamknięte `c9h9.3`, `r564.4`; otwarte `c9h9.4` | Brak duplikatu; exact apply jest wyspecyfikowany. |
| Connectors/freshness | `partially_complete` | Diagnostics, queue and selected snapshot expose current freshness; primary stale sources block actionability. | Live HTTP, `ContentFreshnessAssessment`, focused backend tests, desktop/mobile render. | Raw diagnostics decision rows remain historical review context; refresh job itself is external/read-only. | brak nowego freshness Bead | Brak nowego zadania freshness. |
| Tests/evals | `partially_complete` | Backend 765/2, shared 31/10, dashboard 138/138; 13/13 fresh skill evals score 9–10. | Full suites, strict coverage, smokes, queue budget E2E. | Full cold Playwright ujawnia realne Ads/custom/actions/knowledge/Merchant latency; stare assertions były test theater. | `.8`–`.13` | Wszystkie obserwowane failures mają zadanie. |
| Monolity | `partially_complete` | Domenowe seamy istnieją, ale główne runtime/test hotspots pozostają. | Complexity report i file/function counts. | Jeden frozen service zmieniony bez LOC growth; 15 existing changed-code violations. | `ho41`, `jnra`, `kgvy`, `50wa`, `0q74` | Nie utworzono duplikatów splitu. |
| Skills | `proved_complete` | 13 skills ma deterministic i non-interactive proof; GSC/Custom kontrakty poprawiono semantycznie. | Strict 13/13, 0 gaps/warnings; scores 9–10; wszystkie smokes pass. | To nie zastępuje realnego Wilku UAT ani usefulness każdej trasy. | `6rw.5` i istniejące eval Beads | Brak. |
| Docs/Beads | `partially_complete` | Recovery docs są przycięte; nowe realne gaps są w grafie; kierunki zależności poprawione. | `bd dep cycles`: none; `bd ready` wskazuje `.5` jako pierwszy P0. | Starsze broad parents nadal wymagają rebaseline; Goal 005 czeka na owner input. | `c9h9.2`, cleanup epics | Brak kolejnego epica. |

## Audyt wymagań

| Wymaganie | Status | Dowód / luka |
| --- | --- | --- |
| Public/dev WordPress roles są rozdzielone | `proved_complete` | API/testy blokują dev canonical; UI opisuje public i dev osobno. |
| Konkretna strona/temat i aktualne public sections | `proved_complete` | Homepage URL/title i 12 publicznych sekcji są widoczne. |
| GSC/Ahrefs/WordPress signals z evidence IDs | `partially_complete` | Real IDs/connectors istnieją; Ahrefs candidate nie ma targetu, a current freshness znika. |
| Decyzja, powód, blocker i safe step w 30 s | `partially_complete` | Desktop je ma, ale cold load i mobile first viewport zawodzą. |
| Current vs proposed i dev workspace | `proved_complete` | Typed section diff i existing-draft action preview są renderowane; update/write pozostają blocked. |
| Brak automatic publish/destructive update | `proved_complete` | Typed literals, live HTTP i UI utrzymują oba `false`. |
| Każda rekomendacja ma current freshness | `partially_complete` | Active queue and selected snapshot carry current freshness and block stale primary proof; raw diagnostics rows remain broader review context. |
| Writes tylko validate → preview → review → confirm → audit → adapter | `partially_complete` | Bypass jest zamknięty; canonical apply jest bezpiecznie wyłączony do `c9h9.4`. |
| Unsupported CPA/ROAS/waste/revenue są blokowane | `proved_complete` | Ads/GA4/Merchant contracts i 13 skill evals zachowują blockers. |
| Marketer-first desktop i mobile | `partially_complete` | Desktop jest konkretny; mobile nie pokazuje decyzji/blockera/CTA w 844 px. |
| Legacy surfaces nie są active truth | `proved_complete` | Planner route/component/E2E nie ma w aktywnej aplikacji. |
| Beads graph odpowiada kodowi | `partially_complete` | Bieżący graf ma poprawne zależności i zero cykli; starsze parents są w `c9h9.2`. |
| Realny Wilku UAT Goal 005 | `blocked_by_external_state` | Check zwraca `blocked_missing_goal_005_uat_proof`; potrzeba UAT JSON lub explicit owner defer. |
| Canonical WordPress create apply | `not_started` | Direct path jest bezpiecznie wyłączony; implementacja należy do `c9h9.4`. |

## Największe blokery

1. Canonical dev-only WordPress apply pozostaje wyłączony do czasu typed
   ActionObject capability/audit (`c9h9.4`).
2. Safe live draft creation jest wyłączone do exact ActionObject apply, audit i
   dev-host guard (`c9h9.4`).
3. Mobile decision/blocker/CTA remains below the first triage viewport (`r564.3`).

## Największe ryzyka

1. Przywrócenie adaptera/CTA poza `apply_action` odtworzyłoby bypass albo
   dopuściło zły host.
2. Historyczny successful refresh może wyglądać jak current proof i prowadzić
   do pewnej rekomendacji ze starych danych.
3. Cold monolity i stare E2E strings pozwalają mylić zielone testy z
   użytecznością albo jedną wolną trasę z wieloma regresjami.

## Ukończone z dowodami

- Public/dev canonical separation i draft-only posture.
- Concrete homepage workbench z public/dev sections.
- Direct live bypass i wszystkie UI live branches usunięte (`c9h9.3`).
- Duplicate-create CTA usunięty; existing draft pozostaje open/preview-only
  (`r564.2`).
- Typed existing-draft preview card (`r564.4`).
- Stabilny pełny dashboard Vitest 137/137 (`c9h9.7`).
- Current freshness w queue/snapshot i refresh-first blocker (`c9h9.5`).
- Queue/snapshot cold waterfall usunięty przez reuse builda, API prewarm i
  progressive first card (`c9h9.6`).
- Legacy planner usunięty.
- 13/13 skill eval coverage i fresh passing outputs.

## Zadania utworzone w audycie

- `c9h9.3` P0 180 min — direct WordPress fail-closed — **closed**.
- `c9h9.4` P0 360 min — canonical dev-only create apply — depends on `.3`.
- `c9h9.5` P0 360 min — freshness w decisions/evidence — **closed**.
- `c9h9.6` P0 300 min — content cold waterfall — **closed 2026-07-11**.
- `r564.2` P0 180 min — duplicate draft prevention — **closed**.
- `r564.3` P1 240 min — mobile first viewport — depends on `.5`, `.6`,
  `r564.2`.
- `r564.4` P1 60 min — typed existing-draft preview — **closed**.
- `c9h9.7` P2 30 min — deterministic Service Profile test — **closed**.
- `c9h9.8` P1 90 min — current behavior E2E assertions — open.
- `c9h9.9` P1 240 min — Ads summary cold render — open.
- `c9h9.10` P2 180 min — narrow Custom Segments view — open.
- `c9h9.11` P1 240 min — lightweight action list — open.
- `c9h9.12` P2 180 min — knowledge cold contention — open.
- `c9h9.13` P1 240 min — Merchant first decision latency — open.

Produktowa kolejność pozostaje `.5` → `.6` → `.4` → `r564.3`; `.5` i `.6` są
zamknięte. Secondary
route latency nie wyprzedza głównej ścieżki content.

## Następny slice i warunek przejścia

Następny slice: `c9h9.4`. `c9h9.6` zamknięto po queue budget `<5 s`, cache reuse,
prewarm i browser proof bez globalnego loadera; dalej trzeba domknąć canonical
dev-only apply.
