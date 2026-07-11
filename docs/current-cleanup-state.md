# Current Cleanup State — 2026-07-11

Przeczytaj przed cleanupem, refaktorem dashboardu albo zmianą kontraktu API.
Historia slice’ów jest w git i Beads; ten plik opisuje tylko bieżący stan.

## Najbliższa instrukcja

Aktualny następny slice to `wilq-seo-r564.3`: mobile first viewport po zamknięciu
canonical dev-only ActionObject apply oraz szybkiej listy akcji. Nie zaczynaj od
splitu monolitu ani od przywracania direct WordPress write.

## Prawda produktu

- `/content-workflow` jest jedynym głównym workspace’em `Treści i SEO`.
- Publiczny `ekologus.pl` jest SEO truth; Proudsite jest draft/dev workspace.
- Live queue: `blocked`, 2 kandydatów, 0 actionable, minimum 3.
- Managed runtime: 95 740 metric facts, 4 507 refresh runs; konektory
  12/9 configured/2 missing credentials/1 disabled.
- Źródła contentowe są stale. Queue i selected snapshot pokazują typed freshness,
  a primary stale proof daje `content_sources_require_refresh`.
- Read-only refresh 2026-07-11 nie odblokował kolejki: GSC zwrócił niepełny
  odczyt (2 evidence), WordPress ekologus przekroczył 60 s timeout; kolejka ma
  nadal 2 kandydatów, 0 actionable i `not_enough_actionable_candidates`.
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
  pierwszy odczyt, cards/playbooks dopiero po kliknięciu. Cache 15 s daje
  `18.940732 s` cold / `0.053012 s` warm; prewarm jest celowo wyłączony, bo
  blokowałby startup health. Proof: `.local-lab/proof/c9h9-12-knowledge-progressive-3s.png`.

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

- `r564.3` — mobile first viewport; zależy od `.5`, `.6` i zamkniętego
  `r564.2`;
- `c9h9.8` — stale dashboard E2E behavior assertions;
- `c9h9.10`, `c9h9.12` — potwierdzone latency blokery Custom Segments i
  Knowledge. `c9h9.9` i `c9h9.11` są zamknięte po API/browser proof.

`ho41` jest wyłącznie route/component boundary. `jnra` jest splitem action
service. Żaden z nich nie może przejąć product semantics freshness/write.

## Complexity checkpoint

- `wilq/briefing/ads_diagnostics.py`: 6 430 LOC;
- `wilq/actions/service.py`: 5 989 LOC;
- `apps/dashboard/src/routes/ContentWorkflowSurface.tsx`: ok. 3 000 LOC;
- `wilq/content/workflow/api.py`: 1 478 LOC;
- `tests/api_contracts/test_ads_contracts.py`: 4 971 LOC; największy test
  2 914 linii.

Latest `c9h9.4` complexity report (2026-07-11): 378 plików Python,
131261 non-empty LOC, 8 zmienionych plików Python, 0 frozen growth files i 3
budget violations w focused tests (121, 105 i 130 linii). Łącznie slice zmienił
backend, connector, schemas, shared schema i dashboard API/testy; to celowy,
ograniczony seam typed apply/adapter, nie mechaniczny split.

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
4. Podczas zewnętrznej blokady świeżego content proof wykonuj `c9h9.12` Knowledge
   cold contention; nie oznaczaj `r564.3` jako complete bez świeżego kandydata.
