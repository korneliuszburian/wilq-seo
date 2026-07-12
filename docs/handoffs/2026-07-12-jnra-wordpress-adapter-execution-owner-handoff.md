# Handoff: `jnra` WordPress adapter execution owner — 2026-07-12

## Decyzja

Wykonanie obsługiwanego adaptera (`execute_supported_wordpress_mutation_adapter`)
zostało przeniesione z `service.py` do istniejącego
`wilq/actions/wordpress_mutation_requirements.py`. Owner obejmuje zarówno
typed capability, readiness, jak i redacted live/dry-run result assembly;
`service.py` zachowuje cienką fasadę orkiestracyjną dla starego call shape.

## Dowody

- `tests/actions/test_action_mutation_readiness_api.py`,
  `tests/actions/test_mutation_readiness_contracts.py`,
  `tests/actions/test_audit_store_contracts.py` i
  `tests/content/test_wordpress_execution_api.py`: 39 testów przechodzi.
- Ruff, mypy, complexity (`--changed --allow-frozen --allow-budget-violations`)
  i `git diff --check` przechodzą. Nowy owner module nie przekracza budżetu;
  raport pokazuje tylko znane wyjątki testowych funkcji i zamrożony monolit.
- Managed stack po restarcie: API/dashboard `ready`, health `ok`.
- Live readiness po rozgrzaniu: HTTP 200 w 18.9 s,
  `ready_to_request_apply=false`, `vendor_write_possible=false`,
  `publication_allowed=false`; cold pierwszy request przekroczył 20 s i
  potwierdza istniejący diagnostics warm-up koszt, nie nowy vendor write.
- Content queue: `fresh`, `blocked`, 2 kandydatów / 1 actionable / minimum 3.
- Browser proof desktop/mobile:
  `.local-lab/proof/continuation-2026-07-12/wordpress-adapter-owner-desktop.png`
  i `wordpress-adapter-owner-mobile.png`.
- Brak nowych endpointów, vendor writes, credentiali lub publikacji.

## Beads

- `wilq-seo-c9h9.4` pozostaje zamknięty.
- `wilq-seo-jnra` pozostaje P0 `in_progress`; komentarz zaktualizowany, bez
  duplikatu.
- Utworzono `wilq-seo-c9h9.14` (P1): cold mutation-readiness latency po
  restarcie. Bead zależy od `jnra` i nie jest duplikatem zamkniętych c9h9.6 ani
  zbre.

## Następny slice

Reaudyt `service.py` i roadmapy. Nie kontynuować mechanicznego usuwania fasad;
następny zakres musi poprawić większy ownership boundary albo realną decyzję
marketera.

## Otwarte blokery

- Cold diagnostics/readiness warm-up jest mierzalnym istniejącym kosztem:
  pierwszy request po restarcie przekraczał 20 s.
- Content queue: `not_enough_actionable_candidates` — 1 actionable przy
  wymaganych 3, mimo świeżych źródeł.
- Goal 005: brak realnego Wilku UAT albo jawnego owner defer.
