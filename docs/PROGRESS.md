# WILQ progress — current handoff

Stan na: 2026-09-11. To jest krótki handoff codebase’u; nie zastępuje
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
- `tests/content` ma ~43 czerwone testy **zastane już na bazie `c38140c2c`**
  (nie regresja tej fali; główny kandydat: harness dynamic planning nie tworzy
  source-pack binding wymaganego przez falę packet);
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
