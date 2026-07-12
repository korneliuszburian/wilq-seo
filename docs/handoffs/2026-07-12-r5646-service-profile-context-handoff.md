# Handoff — r564.6 Service Profile przy work itemie

## Stan

`wilq-seo-r564.6` dodaje do istniejącego snapshotu content work itemu compact
typed Service Profile context. Nie powstał endpoint ani write path.

## Granica i niezmienniki

- `wilq/content/knowledge/work_item_service_profile.py` projektuje wyłącznie
  kartę wskazaną przez `match_content_knowledge_cards()`.
- `ContentOpportunityEnrichment.service_fit` pozostaje opisem tematu i nigdy
  nie przypisuje usługi ani nie odblokowuje claimu.
- Snapshot workflow współdzieli ten sam `ContentKnowledgeCardMatch` z briefem i
  draft package; zablokowany snapshot ma `not_evaluated` zamiast zgadywania.
- Context pokazuje binding, status, policy wyłącznie dla dopasowanej karty
  usługi (pełny Claim Ledger pozostaje osobno), evidence/source lineage,
  freshness, missing contracts i safe next step. Dashboard nie łączy danych
  samodzielnie; raw ID są tylko w `Dowody i warunki`.
- `ekologus.pl` pozostał publicznym źródłem; Proudsite jest wyłącznie dev/draft.
  Publish i vendor write nie zostały zmienione i pozostają zablokowane.

## Aktualny dowód

- Po managed restarcie `GET /api/content/work-items/snapshot` dla homepage
  zwraca `bound` do `ekologus_service_homepage_overview`, connector
  `public_site`, evidence `ev_content_service_profile_source_facts`, freshness
  signal `2026-07-02` oraz `blocked` przed finalnym draftem z czterema
  brakującymi warunkami.
- Zablokowany work item zwraca `not_evaluated`, bez card ID i z własnym safe
  next step.
- Browser proof: `.local-lab/proof/r5646-service-profile/content-workflow-desktop.png`
  oraz `.local-lab/proof/r5646-service-profile/content-workflow-mobile.png`.
  W 390×844 decyzja, publiczna strona i start sekcji usługi są nad foldem;
  druga kontrola mobile pokazuje pełny context bez poziomego overflow
  (`scrollWidth=390`). Szczegóły dowodowe są zamknięte.
- Focused backend/API, shared-schema i dashboard tests, Ruff, mypy, lint oraz
  production build przechodzą. Complexity zachowuje istniejące przekroczenie
  pliku `wilq/content/workflow/api.py`; nowy projector jest małym modułem.
  `c9h9.16` śledzi ograniczony snapshot-assembly split.
- Independent re-review po poprawkach nie znalazł P0/P1/P2. Focused Playwright
  `content-workflow-layout.spec.ts` pozostaje historycznym stale-only testem:
  oczekuje starego nagłówka i `0 z 2`, choć aktualny live queue uczciwie zwraca
  fresh `1 z 3`. Dowód i docelowa behavior-based naprawa są przypięte do
  istniejącego `d380`; nie maskuj tego przez cofnięcie produktu do starego copy.

## Następna bezpieczna praca

Parent `r564` jest blokowany realnymi danymi: 2 kandydatów, 1 actionable przy
minimum 3. Nie twórz trzeciego tematu. Następny niezależny slice to `3bst.7`:
podnieść istniejący API-owned Ahrefs manual blocker i safe next step nad galerię
kandydatów, bez nowej reguły matchowania w React i bez akcji write. Następny
maintenance seam po decyzji produktowej: `c9h9.16`.
