# Independent repository rebaseline — 2026-07-12 continuation

Audyt zbudowano z aktualnego repo, managed runtime, API, testów, renderów i
grafu Beads. Historyczne rozmowy, screenshoty i opisy Beads były wyłącznie
wskazówkami.

## Aktualne dowody

- Baseline: `main`, clean i zgodny z `origin/main` na `ba033433` podczas tego
  continuation; żadnych lokalnych zmian przed aktualizacją tego ledgeru.
- Managed API/dashboard: ready; health `ok`.
- DuckDB: 98 919 metric facts, 4 574 refresh runs; connector summary z API:
  12 ogółem, 9 skonfigurowanych, 2 bez credentials. Nie drukowano ścieżek
  prywatnych ani payloadów vendorów.
- Live konektory: Google Search Console ma świeży ostatni odczyt, a Google Ads,
  GA4, WordPress i Ahrefs pozostają stale; to nie jest dowód bieżącej decyzji
  publikacyjnej. `GET /api/connectors` zwraca 12 typed statusów.
- Content diagnostics: dwa decision rows z evidence IDs i source connectors;
  dashboard pokazuje refresh-first blocker dla WordPress/GA4/Ahrefs, więc
  świeżość zależna od tych źródeł blokuje bezpieczną decyzję.
- Complexity report 2026-07-12: 405 plików Python, 133 807 non-empty LOC,
  0 changed-code violations; hotspoty: Ads diagnostics 6 616 LOC, action
  service 4 003 LOC, content diagnostics 1 478 LOC.
- Dashboard usefulness audit: 14 surfaces, 12 `demo_ready`, 2 `review_ready`,
  0 `blocked`, `pass=true`; skrypt nie zastępuje świeżości konektorów.
- Browser proof z aktualnego runtime: `.local-lab/proof/continuation-2026-07-12/`
  (`content-workflow-desktop.png`, `content-workflow-mobile.png` oraz tekst).

## Mapa systemu

Status używa wyłącznie wymaganego słownika.

| Obszar | Status | Aktualny stan | Dowód | Problem | Istniejący Bead | Brakujące zadanie |
| --- | --- | --- | --- | --- | --- | --- |
| API | `partially_complete` | Typed health, diagnostics, queue, snapshots i action readiness działają; direct WordPress live jest fail-closed. Queue/snapshot carry typed freshness and reuse one short-lived diagnostics build. | Live HTTP, focused content tests, API smoke. | Raw diagnostics rows remain broader than the gated queue; secondary routes still have cold gaps. | `.9`–`.13` | Wszystkie potwierdzone cold gaps mają zadania. |
| `/content-workflow` | `partially_complete` | Konkretna homepage, public/dev sections, typed freshness blocker, queue-owned decision card, typed preview i review-only CTA. | Live API, focused content/dashboard tests, desktop/mobile browser proof 2026-07-12. | Mobile decision jest w first viewport, ale świeży candidate zależy od zewnętrznego refreshu; stale sources blokują publikacyjną pewność. | zamknięte `c9h9.4`, otwarty `r564.3` | Dokończyć tylko po świeżym, nieblokowanym candidate proof. |
| Dashboard IA | `partially_complete` | Legacy planner usunięty; główne nav prowadzi do `/content-workflow`. | Route registry, negative route tests, render. | Część E2E utrwalała stare stringi; drugorzędne trasy mają cold latency. | `c9h9.8`–`.13`, `r564`, `ho41` | Utworzone na podstawie failure proof. |
| ActionObject safety | `proved_complete` | Preview/review/confirm/audit oraz canonical dev-only create apply są spięte przez typed capability; direct content live i UI create pozostają fail-closed. | Route integration, mutation audit, dev-host zero-HTTP tests, shared dashboard contract. | Live UI nadal blokuje zapis bez bieżącego review/audytu — to zamierzony stan bezpieczeństwa. | zamknięte `c9h9.3`, `c9h9.4`, `r564.4` | Brak nowego zadania w tym seamie. |
| Connectors/freshness | `partially_complete` | Diagnostics, queue and selected snapshot expose current freshness; primary stale sources block actionability. | Live HTTP, `ContentFreshnessAssessment`, focused backend tests, desktop/mobile render. | Raw diagnostics decision rows remain historical review context; refresh job itself is external/read-only. | brak nowego freshness Bead | Brak nowego zadania freshness. |
| Tests/evals | `partially_complete` | Focused content/action backend suite, dashboard ContentWorkflow/CommandCenter 17/17 i 13/13 fresh skill evals pozostają zielone. | `pytest`, Vitest, strict skill coverage, complexity i browser proof. | Full cold Playwright i zewnętrzna świeżość nie są zastępowane przez wąskie zielone testy. | zamknięte `.8`–`.13`, otwarty `r564.3` | Utrzymać aktualny proof i nie zamykać r564.3 bez fresh candidate. |
| Monolity | `partially_complete` | Domenowe seamy istnieją, ale główne runtime/test hotspots pozostają. | Complexity report i file/function counts. | Jeden frozen service zmieniony bez LOC growth; 15 existing changed-code violations. | `ho41`, `jnra`, `kgvy`, `50wa`, `0q74` | Nie utworzono duplikatów splitu. |
| Skills | `proved_complete` | 13 skills ma deterministic i non-interactive proof; GSC/Custom kontrakty poprawiono semantycznie. | Strict 13/13, 0 gaps/warnings; scores 9–10; wszystkie smokes pass. | To nie zastępuje realnego Wilku UAT ani usefulness każdej trasy. | `6rw.5` i istniejące eval Beads | Brak. |
| Docs/Beads | `partially_complete` | `c9h9.2` rebaseline odświeżony do `ba033433`; statusy c9h9.3–.13 sprawdzone z aktualnego JSONL. | `bd show`, `bd ready --json`, aktualny audit ledger. | `r564.3` i parent `r564` pozostają otwarte przez zewnętrzny refresh; Goal 005 czeka na owner input. | `c9h9.2`, `r564.3` | Po tym ledgerze prowadzić tylko do `r564.3` albo innego potwierdzonego ready Beada. |

## Audyt wymagań

| Wymaganie | Status | Dowód / luka |
| --- | --- | --- |
| Public/dev WordPress roles są rozdzielone | `proved_complete` | API/testy blokują dev canonical; UI opisuje public i dev osobno. |
| Konkretna strona/temat i aktualne public sections | `proved_complete` | Homepage URL/title i 12 publicznych sekcji są widoczne. |
| GSC/Ahrefs/WordPress signals z evidence IDs | `partially_complete` | Real IDs/connectors istnieją; Ahrefs candidate nie ma targetu, a current freshness znika. |
| Decyzja, powód, blocker i safe step w 30 s | `partially_complete` | Aktualny desktop/mobile render pokazuje je w pierwszym widoku; świeżość źródeł nadal blokuje bieżącą decyzję. |
| Current vs proposed i dev workspace | `proved_complete` | Typed section diff i existing-draft action preview są renderowane; update/write pozostają blocked. |
| Brak automatic publish/destructive update | `proved_complete` | Typed literals, live HTTP i UI utrzymują oba `false`. |
| Każda rekomendacja ma current freshness | `partially_complete` | Active queue and selected snapshot carry current freshness and block stale primary proof; raw diagnostics rows remain broader review context. |
| Writes tylko validate → preview → review → confirm → audit → adapter | `proved_complete` | Jedyna ścieżka create dev przechodzi przez typed request/capability, audyt i istniejący adapter; content router nie ma własnego write. |
| Unsupported CPA/ROAS/waste/revenue są blokowane | `proved_complete` | Ads/GA4/Merchant contracts i 13 skill evals zachowują blockers. |
| Marketer-first desktop i mobile | `partially_complete` | Browser proof 390×844 pokazuje URL, decyzję, blocker i CTA; pełna gotowość pozostaje zależna od świeżego candidate. |
| Legacy surfaces nie są active truth | `proved_complete` | Planner route/component/E2E nie ma w aktywnej aplikacji. |
| Beads graph odpowiada kodowi | `partially_complete` | Bieżący graf ma poprawne zależności i zero cykli; starsze parents są w `c9h9.2`. |
| Realny Wilku UAT Goal 005 | `blocked_by_external_state` | Check zwraca `blocked_missing_goal_005_uat_proof`; potrzeba UAT JSON lub explicit owner defer. |
| Canonical WordPress create apply | `proved_complete` | Typed ActionApplyRequest, capability builder, route integration, audit and dev-host guard są wypchnięte; live UI pozostaje blokowane bez gotowości. |

## Największe blokery

1. Live źródła contentu są stale, więc queue ma `blocked`, 0 actionable i
   blokery `content_sources_require_refresh` oraz `not_enough_actionable_candidates`.
2. Goal 005 nadal czeka na realny Wilku UAT albo jawny owner defer.
3. Mobile proof jest już w first viewport, ale `r564.3` nie ma jeszcze świeżego,
   nieblokowanego candidate z zewnętrznego refreshu.

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
- `c9h9.4` P0 360 min — canonical dev-only create apply — **closed 2026-07-11**; typed capability, route proof, review-only CTA and guards.
- `c9h9.5` P0 360 min — freshness w decisions/evidence — **closed**.
- `c9h9.6` P0 300 min — content cold waterfall — **closed 2026-07-11**.
- `r564.2` P0 180 min — duplicate draft prevention — **closed**.
- `r564.3` P1 240 min — mobile first viewport — depends on `.5`, `.6`,
  `r564.2`.
- `r564.4` P1 60 min — typed existing-draft preview — **closed**.
- `c9h9.7` P2 30 min — deterministic Service Profile test — **closed**.
- `c9h9.8` P1 90 min — current behavior E2E assertions — **closed**.
- `c9h9.9` P1 240 min — Ads summary cold render — **closed**.
- `c9h9.10` P2 180 min — narrow Custom Segments view — **closed**.
- `c9h9.11` P1 240 min — lightweight action list — **closed 2026-07-11**; cache/prewarm, progressive card, list/detail proof i focused action Playwright pass.
- `c9h9.12` P2 180 min — knowledge cold contention — **closed**.
- `c9h9.13` P1 240 min — Merchant first decision latency — **closed 2026-07-11**;
  cache/prewarm, focused contract and desktop/mobile proof pass.

Produktowa kolejność po zamknięciu `.5` → `.6` → `.4` pozostaje przy `r564.3`
(mobile triage). Aktualny API/browser proof potwierdza layout, ale stale źródła
nie pozwalają udawać gotowego candidate. Secondary route latency nie wyprzedza
głównej ścieżki content.

## Następny slice i warunek przejścia

Następny slice: `r564.3`. Aktualny browser proof spełnia mobile URL/temat,
decision, blocker i bezpieczny CTA, ale zewnętrzny stan nadal nie dostarcza
świeżego, nieblokowanego candidate. Warunek przejścia: odczyt źródeł potwierdzi
świeżość i candidate gotowy do pracy; wtedy ponowić desktop/mobile proof i dopiero
rozważyć zamknięcie Beada.
