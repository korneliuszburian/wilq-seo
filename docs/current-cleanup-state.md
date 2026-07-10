# Current Cleanup State — 2026-07-11

Przeczytaj przed cleanupem, refaktorem dashboardu albo zmianą kontraktu API.
Historia slice’ów jest w git i Beads; ten plik opisuje tylko bieżący stan.

## Najbliższa instrukcja

Następny slice to `wilq-seo-c9h9.6`: usuń cold waterfall po ustabilizowaniu
freshness w queue/snapshot. Nie zaczynaj od splitu monolitu ani od przywracania
WordPress write.

## Prawda produktu

- `/content-workflow` jest jedynym głównym workspace’em `Treści i SEO`.
- Publiczny `ekologus.pl` jest SEO truth; Proudsite jest draft/dev workspace.
- Live queue: `blocked`, 2 kandydatów, 0 actionable, minimum 3.
- Managed runtime: 95 740 metric facts, 4 507 refresh runs; konektory
  12/9 configured/2 missing credentials/1 disabled.
- Źródła contentowe są stale. Queue i selected snapshot pokazują typed freshness,
  a primary stale proof daje `content_sources_require_refresh`.
- Cold selected snapshot przekracza 30 s w Playwright (`c9h9.6`).
- Desktop pokazuje konkretną homepage, public/dev sections, GSC, typed preview
  i preview-only CTA. Mobile nadal chowa decyzję/blocker/CTA poniżej first fold.

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
- Future create należy wyłącznie do `c9h9.4`. Canonical apply ma zbudować typed
  capability wewnątrz `apply_action` i powiązać exact action, work item,
  handoff, draft package, dev host, operatora i mutation audit. Publish, update
  i delete pozostają poza zakresem.

## Bieżący graf

Zamknięte w tym slice:

- `c9h9.3` — direct WordPress live fail-closed;
- `r564.2` — duplicate create usunięty wraz z direct live CTA;
- `r564.4` — typed existing-draft preview card;
- `c9h9.7` — stabilny full-suite Service Profile test.
- `c9h9.5` — freshness w queue/snapshot i refresh-first blocker.

Otwarte product blockers:

- `c9h9.6` — content cold waterfall; zależy od `.5`;
- `c9h9.4` — canonical dev-only apply; direct path pozostaje wyłączony;
- `r564.3` — mobile first viewport; zależy od `.5`, `.6` i zamkniętego
  `r564.2`;
- `c9h9.8` — stale dashboard E2E behavior assertions;
- `c9h9.9`–`c9h9.13` — potwierdzone latency blokery Ads, Custom Segments,
  Actions, Knowledge i Merchant.

`ho41` jest wyłącznie route/component boundary. `jnra` jest splitem action
service. Żaden z nich nie może przejąć product semantics freshness/write.

## Complexity checkpoint

- `wilq/briefing/ads_diagnostics.py`: 6 430 LOC;
- `wilq/actions/service.py`: 5 989 LOC;
- `apps/dashboard/src/routes/ContentWorkflowSurface.tsx`: ok. 3 000 LOC;
- `wilq/content/workflow/api.py`: 1 478 LOC;
- `tests/api_contracts/test_ads_contracts.py`: 4 971 LOC; największy test
  2 914 linii.

Latest `c9h9.5` changed report: 22 pliki, 0 frozen, 1 existing violation w
`wilq/content/workflow/api.py` (1 478 LOC). Poprzedni baseline miał 35 plików / 1
frozen / 15 violations; ten slice nie zmienił frozen service. Nie mieszaj
mechanicznego splitu z P0 freshness.

## Proof checkpoint

- 765 backend passed / 2 skipped baseline; c9h9.5 focused content tests green;
  Ruff i mypy green.
- Shared 31 passed / 10 skipped; dashboard 137/137; lint/typecheck/build green.
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
3. Claim `c9h9.6` i zmierz cold waterfall przez istniejące queue/snapshot/
   enrichment seam, bez nowego endpointu i bez business logic w React.
4. Warunek przejścia do `c9h9.4`: pierwszy content decision renderuje się w
   lokalnym budżecie, a lokalne loading states nie ukrywają blockerów.
