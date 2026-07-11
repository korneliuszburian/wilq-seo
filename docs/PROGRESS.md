# WILQ Progress Ledger

Krótki recovery ledger, nie append-only changelog. Historyczne proof pozostaje
w git, Beads i `docs/progress/archive/`.

## Stan bieżący — 2026-07-11

- Główną trasą marketera jest `/content-workflow`; usunięty planner nie jest
  aktywną prawdą produktu.
- `ekologus.pl` pozostaje publicznym źródłem i canonical SEO. Proudsite jest
  wyłącznie workspace’em draft/dev.
- Managed API i dashboard są zdrowe. DuckDB ma 95 740 metric facts i 4 507
  refresh runs. Konektory: 12 ogółem, 9 skonfigurowanych, 2 bez credentials,
  1 wyłączony.
- Kolejka contentowa jest `blocked`: 2 kandydatów, 0 actionable, minimum 3.
  Homepage ma dowody z GSC i publicznego WordPressa; Ahrefs-only candidate nie
  ma bezpiecznego targetu/canonical.
- Queue i selected snapshot przenoszą teraz typed freshness; stale primary
  sources dają `content_sources_require_refresh`, `recommended_mode=block` i
  refresh-first `safe_next_step`. To zamyka P0 `c9h9.5`.
- Cold `/content-workflow` nie blokuje już pierwszej decyzji: API prewarmuje
  content diagnostics, queue reuse’uje ten sam build, a queue-owned karta
  renderuje się przed snapshotem. Focused E2E ma budżet queue `<5 s` i brak
  globalnego loadera; `c9h9.6` jest zamknięty.

## Zamknięty slice bezpieczeństwa

`c9h9.3` jest zamknięty:

- direct `POST /api/content/work-items/wordpress-draft-execution` zachowuje
  dry-run, ale nie dostaje realnego adaptera WordPress;
- `mode=live` zwraca `action_apply_required`,
  `external_write_attempted=false`, publish/destructive `false`;
- readiness jest zawsze fail-closed:
  `blocked_outside_action_apply`, `ready=false`, brak suggested authorization;
- React nie ma `runExecutionLive`, prepare-write CTA ani create-new-draft CTA;
  nawet sfabrykowane `ready=true` kończy się `dry_run` z autoryzacją `null`;
- istniejący draft jest tylko otwierany/podglądany, więc `r564.2` zamknięto;
- create przechodzi wyłącznie przez exact canonical apply z zamkniętego `c9h9.4`;
  direct content write pozostaje wyłączony.

`r564.4` również jest zamknięty. Existing-draft update action ma domenową typed
preview card z current/proposed/blocked state; raw payload pozostaje w technical
details. Screenshoty są lokalnie w
`.local-lab/proof/independent-review-2026-07-10/`.

## Zamknięty slice freshness

`c9h9.5` jest zamknięty:

- `ContentWorkItemQueueResponse`, kandydat i oba snapshot variants mają wspólny
  `ContentFreshnessAssessment` oraz typed queue candidate;
- stale/missing/blocked GSC lub publiczny WordPress blokują actionability przed
  planem, zachowując evidence IDs i source connectors;
- `/content-workflow` pokazuje refresh-first blocker above-fold na desktopie i
  mobile, bez raw payloadu;
- current freshness pochodzi z connector age/status, nie z regexu ani opisu.

Proof: live queue/snapshot HTTP, 5 focused backend test files, 31 shared schema
tests, dashboard typecheck/Vitest oraz screenshots w
`.local-lab/proof/independent-review-2026-07-11/`.

## Zamknięty slice cold-load

`c9h9.6` jest zamknięty:

- content diagnostics mają krótki, czyszczony po mutacji cache request-flow;
- pierwszy build reuse’uje content metric facts w tactical queue zamiast robić
  drugą lekturę metric store;
- API prewarmuje ten cache przed health w managed runtime, fail-open przy
  niedostępnym źródle;
- dashboard pokazuje queue-owned decyzję, dowody, źródła i safe next step, gdy
  snapshot/enrichment są jeszcze w toku; błędy są lokalne, nie globalne;
- browser proof: queue po prewarm `0.023 s`, focused Playwright `1 passed` z
  asercją `<5 s`, dashboard Vitest `138/138`.

## Aktualny browser/usefulness proof

- Desktop 1440×900 i mobile 390×844: stale-source blocker, źródła, powód i
  refresh-first next step są widoczne przed kolejką; homepage jest domyślnym
  wyborem zamiast Ahrefs-only braku canonical.
- Decision/CTA dla świeżego workflow mają teraz queue-owned first card; pełna
  mobile triage nadal wymaga `r564.3`.
- `c9h9.4` jest zamknięty: centralny apply ma typed `wordpress_draft` input,
  capability binding, route audit i dev-host guard; live CTA pozostaje
  zablokowane bez realnej gotowości.
- `r564.3` w toku: dodano mobile-only `Decyzja mobilna` po bannerze źródeł i
  statusach, z URL/tematem, rekomendacją, najważniejszym blockerem i bezpiecznym
  CTA otwierającym decyzję/dowody. CTA nie wykonuje zapisu. Focused
  ContentWorkflow Vitest 15/15, dashboard lint/typecheck green; live mobile
  screenshot `.local-lab/proof/r564-3-mobile-stale-blocker.png` pokazuje uczciwy
  refresh-first blocker przy aktualnym stale runtime.
- Próba read-only odświeżenia dla `r564.3` 2026-07-11: GSC zwrócił HTTP 200,
  ale kontrakt oznaczył odczyt jako niepełny (`evidence_count=2`); WordPress
  ekologus nie odpowiedział w 60 s. Kolejka po próbie nadal ma 2 kandydatów,
  0 actionable i blokery `content_sources_require_refresh` oraz
  `not_enough_actionable_candidates`. Świeży kandydat pozostaje zablokowany
  przez stan zewnętrzny, nie przez brak implementacji karty.
- Mobile freshness banner jest teraz skondensowany (summary poniżej desktop
  breakpointu), a pięć statusów źródeł tworzy poziomy scroll zamiast pięciu
  pionowych kart. Dzięki temu decision card ma realną szansę wejść w 390×844;
  Vitest 15/15, lint/typecheck i nowy screenshot stale proof przechodzą.
- `c9h9.13` Merchant jest zamknięty: istniejący `/api/merchant/diagnostics` ma
  15-sekundowy cache i managed-runtime prewarm, bez nowego endpointu. HTTP po
  restarcie: `0.004860 s` pierwszy odczyt, `0.007203 s` drugi; desktop/mobile
  proof pokazuje Produkty, freshness, blocker i safe next step. Focused Merchant
  contracts 13/13, dashboard App 22/22, lint/typecheck, Ruff i mypy przechodzą.
- `c9h9.11` jest zamknięty: `/api/actions` używa istniejącej listy z 15-sekundowym
  cache/prewarm i po restarcie dał `0.061183 s` / `0.024930 s`; lista zachowuje
  evidence IDs bez ciężkiego detail buildera. Karta „Najbliższa bezpieczna akcja”
  pokazuje akcję także podczas oczekiwania na mutation readiness, ale oznacza
  readiness jako sprawdzane i zapis jako zablokowany. Focused action Vitest 2/2,
  dashboard lint/typecheck i backend cache test przechodzą; browser proof:
  `.local-lab/proof/c9h9-11-actions-cold-browser-final.png` oraz
  `.local-lab/proof/c9h9-11-actions-detail-cold-browser-loaded.png`.
- `c9h9.9` jest zamknięty: istniejący `/api/ads/diagnostics?view=summary` ma
  15-sekundowy cache read-through; po restarcie HTTP `1.426757 s` cold i
  `0.016956 s` warm. Shared schema przestał odrzucać API summary przez trzy
  nieadsowe pola review (defaults zamiast wymagań); 5 decyzji Ads i wszystkie
  mają evidence. Ads route nie blokuje już first paint na kolejce akcji i ma
  bezpieczny shell „Odczyt Ads w toku”. Proof: `.local-lab/proof/c9h9-9-ads-first-decision-fixed-loaded.png`;
  focused current Playwright `apps/dashboard/e2e/ads-summary-current.spec.ts`
  passes 1/1 in 7.8 s. Route-level cold first paint is still above the 5 s
  measured heading first paint `1.853 s` (<5 s). Lazy-route shell proof at 2 s:
  `.local-lab/proof/c9h9-9-ads-route-shell-2s.png`.
- `c9h9.12` jest w toku: `/knowledge` ładuje operating-map jako jedyny pierwszy
  odczyt, a karty/playbooki dopiero po disclosure. `list_workflows()` używa już
  tylko `build_daily_command_center()`, a standalone cold map core spadł do
  `4.878 s` (11 bindings, 15 kart, 14 playbooków). Cache mapy ma 15 s; po
  restarcie managed runtime uruchamia nieblokujący prewarm w tle: health pozostaje
  gotowy, a pierwszy HTTP odczyt mapy po rozgrzaniu wyniósł `0.003550 s`, drugi
  `0.003175 s`. Browser proof przy 3 s pokazuje
  decyzję i blokery bez pustego globalnego loadera:
  `.local-lab/proof/c9h9-12-knowledge-progressive-3s.png`; focused current
  Playwright `1/1` przechodzi w `2.7 s` (29.2 s z uruchomieniem harnessu).
  Pozostaje sprawdzić stabilność prewarmu na kolejnych restartach; nie wolno
  przywracać współbieżnych katalogów ani traktować starego payloadu jako świeżego.
- `c9h9.10` jest zamknięty: Custom Segments korzysta z istniejącego Ads summary
  projection zamiast pełnego payloadu; focused Playwright `1/1` w `4.4 s`
  potwierdza kandydatów, forecast, evidence i blokady claims bez audience-size
  ani write. Nie dodano endpointu.
- W `c9h9.4` dodano warunkowy review-only CTA w panelu dev draft: pojawia się
  tylko po `draft_package_ready && handoff_ready`, prowadzi do istniejącej
  akcji `act_apply_wordpress_draft_handoff` i jawnie mówi, że nie wykonuje
  zapisu/publikacji. Live stale queue nadal nie pokazuje CTA; browser proof
  `.local-lab/proof/content-workflow-c9h9-4-review-only.png` pokazuje refresh-first
  blocker i brak nieautoryzowanego CTA above fold.
- `/actions/act_prepare_wordpress_existing_draft_update`: first viewport mówi
  „Przygotuj i oceń bez zapisu zmian” oraz „Zapis zablokowany”; pełny render ma
  typed preview i technical disclosure.
- Manual usefulness `/content-workflow` pozostaje 6/10: freshness i pierwsza
  decyzja są jawne, ale pełna karta świeżego workflow i mobile triage nadal
  wymagają dopracowania.

## Weryfikacja

- Backend baseline: 765 passed, 2 skipped; ten slice: 5 content test files
  passed, 1 deprecation warning; Ruff i mypy dla zmienionych modułów
  modułów przechodzą.
- Shared schemas: 31 passed, 10 skipped.
- Dashboard: 24 files, 138/138 Vitest; lint, typecheck i production build
  przechodzą. Potwierdzony full-suite flake Service Profile naprawiono lokalnym
  async budgetem bez usuwania asercji (`c9h9.7`, zamknięty).
- Focused content/action UI: 31/31; action-detail Playwright przechodzi.
- Security, 7/7 API smoke, oba CLI smoke, brief/action/language guard oraz daily
  + 12 deterministic skill smokes przechodzą.
- Skill coverage: 13/13, 0 gaps/warnings; wszystkie 13 evali są fresh/passing,
  score 9–10. GSC i Custom Segments przechodzą `quick_validate`.
- Goal 005 pozostaje `blocked_missing_goal_005_uat_proof`: potrzebny jest realny
  wynik Wilku UAT albo jawny owner defer z residual risk. To stan zewnętrzny, nie
  brak eval coverage.
- Najnowszy zamknięty slice `c9h9.4`: typed ActionApplyRequest w backendzie i
  `@wilq/shared-schemas`, dashboardowy `applyAction` korzysta z tej samej
  granicy `/apply`; realny builder capability wiąże work item/handoff/draft
  package/canonical URL/confirm actor, a connector blokuje public/arbitrary host
  przed HTTP. Focused action mutation, shared-schema, dashboard API, WordPress
  adapter i content execution tests przechodzą; route-level proof i review-only
  CTA są zamknięte w Beadzie.
- Pełny cold Playwright nie jest zielony. Potwierdzone osobne blokery mają
  Beads: Ads `c9h9.9`, Custom Segments `c9h9.10`, actions
  `c9h9.11` jest zamknięty, knowledge `c9h9.12`; Merchant `c9h9.13` jest zamknięty. Stare E2E strings są
  porządkowane w `c9h9.8`; timeoutów nie podnoszono.
- Latest `c9h9.6` complexity run: 10 changed files, 2 frozen growth files and 2
  focused budget violations in `wilq/briefing/content_diagnostics.py`. Main and
  diagnostics changed only for the documented cache/prewarm seam; no broad
  split was introduced.
- Latest `c9h9.4` complexity run: 378 Python files / 131261 non-empty LOC,
  8 changed Python files, 0 frozen growth files, 3 focused test-function
  budget violations (121, 105 and 130 lines). The extra route proof is a
  deliberate integration test; no production monolith grew.

## Kolejność wykonania

1. `r564.3` — decision/blocker/CTA w mobile first viewport; świeży kandydat nadal zależy od zewnętrznego refresh.
2. `c9h9.12` — knowledge cold contention (aktywny slice podczas zewnętrznej blokady content).
3. Secondary route latency: brak nowego potwierdzonego Beada; `c9h9.12`
   pozostaje aktywnym cold-map seamem.

`docs/audits/2026-07-10-cleanup-rebaseline.md` zawiera bieżącą mapę statusów i
ryzyk. Pełne specyfikacje pozostają wyłącznie w Beads.
