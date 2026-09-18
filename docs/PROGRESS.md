# WILQ progress — current handoff

Stan na: 2026-09-18. To jest krótki handoff codebase’u; nie zastępuje
`PLANS.md`, aktywnego Beada, canonical CSV ani WILQ API. Historyczne proofy i
metryki zostają w git oraz w oznaczonych raportach.

## Fixed point

- aktywna gałąź: `wip/dirty-integration-20260916` (integracyjna; `main` i
  `origin` pozostają nietknięte do rozbicia checkpointu);
- punkt odniesienia: recovery checkpoint `533b906fb` (112 plików brudnego
  checkoutu) plus cohesive, change-contract-backed commity na wierzchu;
- `scripts/lint.sh`, `scripts/typecheck.sh`, focused falsifiery nowych fal,
  managed API `8000` i dashboard `5173` są zaobserwowane jako zielone na tym
  punkcie;
- findings audytu F-01 (data_readiness), F-03/F-04/F-05 (etykiety Ads i preview
  cards), F-06/F-07/F-08/F-09 (reguły safety przeniesione do domeny) oraz
  dokumenty current-state F-12..F-17 są zamknięte; audytowy F-21 okazał się
  false-positive — `"ekologus"` to workspace PRODUKTOWY, a
  `"ekologus_local_pilot"` to tożsamość AUDYTOWA; walidacja logu rekomendacji
  została przeniesiona do domeny, ale porównuje workspace produktowy;
- `scripts/marketer_language_guard.py`, `scripts/live_contract_smoke.py`
  (`status: completed`, 0 błędów) i `scripts/dashboard_usefulness_audit.py`
  (`pass: true`) są zielone; żywy pipeline `planning-proposals` dla BDO zwraca
  typed blocker `stale_planning_sources` (fail-closed, wymaga refreshu źródeł);
- pełny `pytest tests`: **25 czerwonych, wszystkie w `tests/content`** (rodzina
  bramki source-pack/refresh authority); **0 poza `tests/content`**. Naprawiono
  2 realne bugi produktu (redakcja `*_digest` psująca schemat audytu;
  keep-eligibility pin cascade po zmianie `source_facts.py`);
- pozostałe 25 wymaga zbudowania pełnego łańcucha authority w syntetycznym
  harnessie (klasyfikacja → tożsamość → row-authority receipt → source pack)
  albo decyzji ownera o migracji legacy testów na `packet_plan_draft_fixtures`;
- realna generacja treści pozostaje niezweryfikowana bez limitów Codex;
  kontrakt `runtime_blocked` jest udowodniony focused testem.

## Cleanup

- clean worktrees odpowiadające scalonym PR-om zostały usunięte, ale ich
  gałęzie zachowano;
- stare detached DB/logi i untracked Playwright artifacts przeniesiono do
  `/mnt/storage/krn/archive/wilq-seo-cleanup-20260911`;
- zatrzymano tylko niezarządzany Vite na porcie `37621`; managed stacku nie
  zmieniano;
- pozostały wyłącznie aktywny checkout, dirty `main` do osobnej decyzji oraz
  open PR #19. Nie usuwamy gałęzi bez jednoznacznego ownera/PR.

## Następny ruch

1. rozbić checkpoint `533b906fb` na cohesive, zrecenzowane commity (WIP=1 na
   `wilq-seo-90u5`) i przywrócić `.codex/config.toml` wspieraną ścieżką;
2. rozstrzygnąć stale current-state/review docs według referencji i consumerów;
3. naprawić zastane czerwone testy `tests/content` (m.in. source-pack binding w
   harnessie dynamic planning);
4. przejść przez S8–S12 runtime gates;
5. dopiero po zielonym codebase rozpocząć evidence-bound produkcję treści.

Nie wykonano publicznego WordPress publish/update/delete ani generowania treści
w tym handoffie.
