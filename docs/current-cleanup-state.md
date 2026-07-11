# Current Cleanup State — 2026-07-11

Przeczytaj przed cleanupem, refaktorem dashboardu albo zmianą kontraktu API.
Historia slice’ów jest w git i Beads; ten plik opisuje tylko bieżący stan.

## Najbliższa instrukcja

Aktualny następny slice to `wilq-seo-r564.3`: mobile first viewport po zamknięciu
canonical dev-only ActionObject apply oraz szybkiej listy akcji. Jeśli zewnętrzny
refresh nadal blokuje świeży kandydat, wykonaj mały, testowalny seam `wilq-seo-jnra`
Action Service; nie przywracaj direct WordPress write.

## Prawda produktu

- `/content-workflow` jest jedynym głównym workspace’em `Treści i SEO`.
- Publiczny `ekologus.pl` jest SEO truth; Proudsite jest draft/dev workspace.
- Live queue: `blocked`, 2 kandydatów, 1 actionable, minimum 3.
- Managed runtime: 98 793 metric facts, 4 511 refresh runs; konektory
  12/9 configured/2 missing credentials/1 disabled.
- Źródła contentowe są stale. Queue i selected snapshot pokazują typed freshness,
  a primary stale proof daje `content_sources_require_refresh`.
- Read-only refresh 2026-07-11 nie odblokował kolejki: GSC zwrócił niepełny
  odczyt (2 evidence), WordPress ekologus przekroczył 60 s timeout; kolejka ma
  nadal 2 kandydatów, 1 actionable i `not_enough_actionable_candidates`.
- Queue-owned first decision renderuje przed snapshotem; cold queue po API
  prewarm ma budżet `<5 s`, a selected snapshot/enrichment mają lokalne stany
  (`c9h9.6` zamknięty).
- Desktop pokazuje konkretną homepage, public/dev sections, GSC, typed preview
  i preview-only CTA. Mobile ma teraz kompaktową decyzję/blocker/CTA przed
  ciężkim kontekstem; realny świeży kandydat nadal czeka na zewnętrzny proof.
- Review-only CTA dla kanonicznego apply jest warunkowy: wymaga gotowej paczki i
  handoffu, prowadzi wyłącznie do `/actions/act_apply_wordpress_draft_handoff`
  i nie wywołuje `/apply`; stale live queue pozostaje bez CTA. Browser proof:
  `.local-lab/proof/content-workflow-c9h9-4-review-only.png`.
- `r564.3` ma mobile-only decision card przed ciężkim kontekstem: temat/URL,
  rekomendacja, blocker i przycisk „Otwórz decyzję i dowody”. Przy stale live
  queue karta nie udaje gotowości; screenshot
  `.local-lab/proof/r564-3-mobile-stale-blocker.png` jest aktualnym proof.
- Mobile freshness został skondensowany, a source status bar jest poziomym
  scrollem; nie usuwamy statusów, tylko skracamy ich udział w first viewport.
- `c9h9.13` Merchant ma cache 15 s i prewarm w managed lifespan; HTTP proof po
  restarcie to `0.004860 s` / `0.007203 s`, a desktop/mobile screenshoty pokazują
  decyzję przed kolejką szczegółów. Bead jest zamknięty.
- `c9h9.11` `/api/actions` ma istniejący list seam z cache/prewarm; po restarcie
  pomiar HTTP po restarcie to `0.082513 s` / `0.021151 s`. Dashboard pokazuje akcję i bezpieczny
  CTA podczas oczekiwania na readiness, bez udawania gotowego zapisu. Proof:
  `.local-lab/proof/c9h9-11-actions-cold-browser-final.png` i
  `.local-lab/proof/c9h9-11-actions-detail-cold-browser-loaded.png`. Bead jest zamknięty.
- `c9h9.9` Ads ma summary cache read-through (15 s) bez blokowania API startupu;
  HTTP proof po restarcie `1.426757 s` / `0.016956 s`. Shared schema defaults
  naprawiają zgodność API/frontend, a Ads route pokazuje bezpieczny shell podczas
  oczekiwania na dane. Pełny desktop proof: `.local-lab/proof/c9h9-9-ads-first-decision-fixed-loaded.png`;
  focused current Playwright 1/1 (7.8 s) przechodzi, ale route-level cold first
  measured heading first paint `1.853 s` (<5 s), a Bead jest zamknięty. Lazy-route
  shell proof przy 2 s: `.local-lab/proof/c9h9-9-ads-route-shell-2s.png`.
- `c9h9.12` Knowledge ma progressive disclosure: operating-map ładuje się jako
  pierwszy odczyt, cards/playbooks dopiero po kliknięciu. `list_workflows()` nie
  buduje już marketing briefu; standalone map core to `4.878 s`, HTTP po restarcie
  ma nieblokujący prewarm uruchamiany po rozpoczęciu lifespan; health pozostaje
  gotowy, a pierwszy/ponowny odczyt po rozgrzaniu wyniósł `0.003550 s` / `0.003175 s`.
  Proof: `.local-lab/proof/c9h9-12-knowledge-progressive-3s.png`; focused current
  Playwright `1/1` w `2.7 s` (29.2 s z harnessem).
- `c9h9.10` Custom Segments jest zamknięty po przejściu na istniejący Ads
  summary projection i focused Playwright `1/1` w `4.4 s`; pełny Ads payload
  nie wraca do tej trasy.
- `jnra` ma kolejny mały seam: konstruktory ActionObjectów Google Ads dla
  kontekstu biznesowego i potwierdzenia celu są teraz w istniejącym module
  `wilq/actions/google_ads/business_context.py`; `service.py` zachowuje gating
  odczytu, evidence i delegację. Keyword Planner ma analogiczny konstruktor w
  `wilq/actions/google_ads/keyword_planner.py`. Focused action contract
  `business_context` / `keyword_planner` / `strategy_review`, Ruff, mypy i diff
  check przechodzą. Static OAuth repair ma teraz konstruktor w
  `wilq/actions/google_ads/oauth.py`, bez zmiany helper commands, evidence ani
  no-write posture. Bead pozostaje otwarty dla kolejnych niezależnych seamów;
  nie wolno upraszczać ActionObject safety loop. Publiczny Service Profile
  knowledge-promotion constructor jest teraz w `wilq/actions/service_profile.py`;
  private proposal constructor jest w tym samym module, więc oba Service Profile
  review seams są zakończone. WordPress draft-handoff constructor jest teraz w
  `wilq/actions/wordpress_draft.py`; apply-mode constructor pozostaje osobnym
  seamem, bo korzysta z service-owned apply contract buildera. Apply-mode
  constructor jest teraz również domenowym delegatem; sam builder kontraktu
  pozostaje w service jako granica bezpieczeństwa. Static Google Ads
  recommendation-review seed deleguje teraz do `google_ads/recommendations.py`;
  read-required payload i blokada apply pozostają bez zmian. Static Merchant
  feed-issue seed deleguje teraz do `wilq/actions/merchant.py`; GA4 pełny
  konstruktor faktów deleguje do `wilq/actions/ga4/tracking_quality.py`, a
  content refresh seed deleguje do
  `wilq/actions/content_refresh.py`. Static seed slice w
  `seed_core_prepare_actions` jest zamknięty; większa logika content workflow
  pozostaje poza tym seamem.
  `seed_metric_action_candidates` jest teraz cienkim orkiestratorem domenowych
  grup Merchant, GA4, Content, Google Ads, Localo i Social; Social działa w
  `wilq/actions/social.py`, Merchant ma pełny konstruktor faktów, klastrów i
  preview w `wilq/actions/merchant.py`, Localo ma konstruktor oparty na faktach w
  `wilq/actions/localo/visibility.py`, a Content ma typed candidate factory w
  `wilq/actions/content_refresh.py`. Wspólne priorytety, etykiety i deduplikacja
  są w `wilq/actions/metric_utils.py`; pierwszy Ads campaign candidate factory
  jest w `wilq/actions/google_ads/campaign_review.py`. Payloady i kolejność
  rejestracji pozostają bez zmian; campaign, recommendation, change-history i
  search-term i custom-segment candidate factories są w modułach Google Ads, a `jnra` pozostaje otwarty dla
  kolejnych grup.

## Granica bezpieczeństwa

- Content router zawsze przekazuje `create_draft=None` i
  `action_apply_authorized=False`.
- Direct live zwraca `action_apply_required` przed adapterem.
- Readiness: `ready=false`,
  `write_authorization_status=blocked_outside_action_apply`, suggested `null`.
- Central mutation summary: 0 vendor-write possible i 0 attempted.
- React ma wyłącznie builder `mode=dry_run`, `write_authorization=null`; UI nie
  utrwala już niemożliwego direct live contractu.
- Existing draft jest otwierany/podglądany; brak create/duplicate CTA.
- Create należy do zamkniętego `c9h9.4`: canonical apply buduje typed capability
  wewnątrz `apply_action` i wiąże exact action, work item, handoff, draft package,
  dev host, operatora i mutation audit. Publish, update i delete pozostają poza
  zakresem.

## Bieżący graf

Zamknięte w tym slice:

- `c9h9.3` — direct WordPress live fail-closed;
- `r564.2` — duplicate create usunięty wraz z direct live CTA;
- `r564.4` — typed existing-draft preview card;
- `c9h9.7` — stabilny full-suite Service Profile test.
- `c9h9.5` — freshness w queue/snapshot i refresh-first blocker.
- `c9h9.6` — queue/snapshot cold waterfall usunięty przez prewarm, reuse builda
  i progressive first card.
- `c9h9.4` — backend i shared frontend mają ten sam typed apply input,
  `applyAction` używa istniejącej granicy `/apply`, a realny capability builder
  wiąże bieżący snapshot, review/audit, canonical URL i aktora. Dev-host guard
  blokuje public/arbitrary host przed HTTP. Bead jest zamknięty po route-level
  readiness proof i review-only CTA.

Otwarte product blockers:

- `r564.3` — mobile first viewport; świeży, nieblokowany content candidate nadal
  zależy od zewnętrznego refreshu.
- `c9h9.9`, `c9h9.10`, `c9h9.11`, `c9h9.12` i `c9h9.8` są zamknięte po
  API/browser proof; obecny pełny `dashboard-api.spec.ts` przechodzi 13/13.

`ho41` jest wyłącznie route/component boundary. `jnra` jest splitem action
service. Żaden z nich nie może przejąć product semantics freshness/write.

## Complexity checkpoint

- `wilq/briefing/ads_diagnostics.py`: 6 475 LOC;
- `wilq/actions/service.py`: 4 983 non-empty LOC;
- `wilq/actions/merchant.py`: 308 non-empty LOC;
- `wilq/actions/social.py`: 154 non-empty LOC;
- `wilq/actions/metric_utils.py`: 25 non-empty LOC;
- `wilq/actions/content_refresh.py`: 1 985 non-empty LOC;
- `apps/dashboard/src/routes/ContentWorkflowSurface.tsx`: ok. 3 000 LOC;
- `wilq/content/workflow/api.py`: 1 478 LOC;
- `tests/api_contracts/test_ads_contracts.py`: 4 971 LOC; największy test
  2 914 linii.

Latest complexity report (2026-07-11): 382 plików Python,
131657 non-empty LOC. Bounded content seed extraction, metric-candidate
orchestration, Social, Localo, Merchant, GA4, Content and Ads campaign/
recommendation/change-history/search-term/custom-segment module extraction were audited with
`--allow-frozen --allow-budget-violations`: service.py remains a frozen-growth
file because the seam removes inline code, while pre-existing content/service
budget findings remain tracked for the broader `jnra` cleanup. Historyczne duże
testy pozostają osobnym otwartym cleanup scope; bieżący seed seam nie zwiększa
ich rozmiaru.

## Proof checkpoint

- 765 backend passed / 2 skipped baseline; c9h9.5 i c9h9.6 focused content tests
  green;
- c9h9.4 pod-slice: action mutation + WordPress adapter + content execution tests
  green; public/arbitrary host ma zero HTTP; dashboard ContentWorkflow
  review-only CTA ma focused Vitest 15/15, lint i typecheck green;
  Ruff i mypy green.
- Shared 31 passed / 10 skipped; dashboard 138/138; lint/typecheck/build green.
- Security, API/CLI smoke i wszystkie deterministic skill smokes green.
- 13/13 skill evals fresh/passing, scores 9–10; strict coverage bez gaps.
- Live direct POST i readiness są fail-closed.
- Aktualne screenshoty desktop/mobile/action są w lokalnym, ignorowanym
  `.local-lab/proof/independent-review-2026-07-10/`.
- Full cold E2E ma jawne otwarte blockers; nie nazywaj całego `verify.sh`
  zielonym, dopóki nie zostaną rozwiązane. Goal 005 nadal czeka na realny Wilku
  UAT albo owner defer.

## Resume

1. Potwierdź clean/synced `main` po commicie tego slice’a.
2. Odczytaj live connectors, diagnostics i queue; nie używaj liczb z pamięci.
3. Kontynuuj `r564.3`: browser proof 390×844 ma pokazać URL/temat,
   decyzję, blocker i bezpieczny CTA bez scrolla, jeśli refresh da świeżego kandydata.
4. Podczas zewnętrznej blokady świeżego content proof wykonuj `jnra` tylko przez
   mały seam z testem zachowania; nie oznaczaj `r564.3` jako complete bez świeżego kandydata.
