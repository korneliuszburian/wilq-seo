# Current Cleanup State — 2026-07-10

Przeczytaj przed cleanupem, refaktorem dashboardu albo zmianą kontraktu API.
Historia slice’ów jest w git i Beads; ten plik opisuje tylko bieżący stan.

## Najbliższa instrukcja

Następny slice to `wilq-seo-c9h9.5`: current freshness musi stać się częścią
content decision/evidence. Nie zaczynaj od splitu monolitu ani od przywracania
WordPress write. Dopiero gdy stale/missing proof daje API-owned refresh-first
blocker, przejdź do cold-load `c9h9.6`.

## Prawda produktu

- `/content-workflow` jest jedynym głównym workspace’em `Treści i SEO`.
- Publiczny `ekologus.pl` jest SEO truth; Proudsite jest draft/dev workspace.
- Live queue: `blocked`, 2 kandydatów, 1 actionable, minimum 3.
- Managed runtime: 95 740 metric facts, 4 507 refresh runs; konektory
  12/9 configured/2 missing credentials/1 disabled.
- Źródła contentowe są stale. Queue i React source strip nadal nie zachowują
  tej semantyki (`c9h9.5`).
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

Otwarte product blockers:

- `c9h9.5` — freshness w content decisions/evidence;
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
- `wilq/content/workflow/api.py`: 1 440 LOC;
- `tests/api_contracts/test_ads_contracts.py`: 4 971 LOC; największy test
  2 914 linii.

Changed report: 35 plików, 1 frozen (`service.py`), 15 violations. Jedyna zmiana
w frozen service to zachowanie domenowych `preview_cards` jako fallback; nie
dodaje WordPress semantics ani LOC. Użyj `--allow-frozen` i
`--allow-budget-violations` tylko z tym udokumentowanym wyjątkiem. Nie mieszaj
mechanicznego splitu z P0 freshness.

## Proof checkpoint

- 765 backend passed / 2 skipped; Ruff i mypy green.
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
3. Claim `c9h9.5` i rozszerz istniejący queue/snapshot view-model, bez nowego
   endpointu i bez business logic w React.
4. Warunek przejścia do `c9h9.6`: stale primary proof daje refresh-first
   blocker, freshness jest widoczna w first view, evidence lineage zostaje.
