# Handoff: c9h9.14 diagnostics cache hardening — 2026-07-12

## Decyzja

Wzmocniono istniejący cache `build_content_diagnostics_cached`: domyślne okno
wynosi 60 s zamiast 15 s, aby jeden drogi startupowy build przeżył dashboardowy
waterfall. `wordpress_draft_activation_packet` korzysta teraz z tego cache
zamiast omijać go przez bezpośredni `build_content_diagnostics(actions=[])`.
Refresh/mutation nadal wywołują `clear_content_diagnostics_cache`, więc nie
zmieniono kontraktu świeżości ani evidence-first.

## Dowody

- Regresyjny test TTL był czerwony przy 15 s (`calls == 2` po 30 s), a zielony
  po zmianie (`calls == 1`). Test ownera activation packet wymusza cached path i
  odrzuca uncached builder.
- Focused content/mutation/action/WordPress suite: 30 testów przechodzi.
- Ruff, mypy, complexity i `git diff --check` przechodzą; raport pokazuje tylko
  znane budżety w istniejącym frozen diagnostics module.
- Quiet managed restart po zamknięciu osieroconych Chrome: cold queue
  `0.003760 s`, cold mutation readiness `1.442645 s`, warm readiness `1.481090 s`.
- Browser proof: `.local-lab/proof/continuation-2026-07-12/c9h9-14-cache-mobile.png`;
  decision/blocker/CTA pozostają widoczne, bez write CTA.
- Safety: `ready_to_request_apply=false`, `vendor_write_possible=false`,
  `publication_allowed=false`; brak endpointów/vendor writes/publikacji.

## Beads

- `wilq-seo-c9h9.14` zamknięty jako external-state false positive po quiet
  re-audicie; nie tworzyć ponownie bez świeżej reprodukcji kodowej.
- `wilq-seo-jnra` pozostaje P0 `in_progress`.

## Następny slice

Reaudyt roadmapy i wybór następnego potwierdzonego seam/task; nie wracać do
zamkniętego c9h9.14 ani do już przeniesionych adapter/readiness boundaries.

## Otwarte blokery

- Content queue pozostaje `fresh`, ale `blocked`: 2 kandydatów, 1 actionable,
  minimum 3.
- Goal 005 nadal wymaga realnego Wilku UAT albo jawnego owner defer.
