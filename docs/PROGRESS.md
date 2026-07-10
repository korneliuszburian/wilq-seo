# WILQ Progress Ledger

Krótki recovery ledger, nie append-only changelog. Historyczne proof pozostaje
w git, Beads i `docs/progress/archive/`.

## Stan bieżący — 2026-07-10

- Główną trasą marketera jest `/content-workflow`; usunięty planner nie jest
  aktywną prawdą produktu.
- `ekologus.pl` pozostaje publicznym źródłem i canonical SEO. Proudsite jest
  wyłącznie workspace’em draft/dev.
- Managed API i dashboard są zdrowe. DuckDB ma 95 740 metric facts i 4 507
  refresh runs. Konektory: 12 ogółem, 9 skonfigurowanych, 2 bez credentials,
  1 wyłączony.
- Kolejka contentowa jest `blocked`: 2 kandydatów, 1 actionable, minimum 3.
  Homepage ma dowody z GSC i publicznego WordPressa; Ahrefs-only candidate nie
  ma bezpiecznego targetu/canonical.
- Diagnostyka wie, że GSC, oba WordPressy, GA4 i Ahrefs są stale, ale queue i
  source strip nie przenoszą jeszcze aktualnej freshness. To P0 `c9h9.5`.
- Cold `/content-workflow` nadal przekracza 30 s w Playwright, czekając na
  selected snapshot. To potwierdzony P0 `c9h9.6`, nie testowy timeout do
  podniesienia.

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
- przyszły create wraca wyłącznie przez exact canonical apply w `c9h9.4`.

`r564.4` również jest zamknięty. Existing-draft update action ma domenową typed
preview card z current/proposed/blocked state; raw payload pozostaje w technical
details. Screenshoty są lokalnie w
`.local-lab/proof/independent-review-2026-07-10/`.

## Aktualny browser/usefulness proof

- Desktop 1440×900: konkretna homepage, 12 sekcji publicznych, 9 sekcji dev,
  GSC, decyzja „odśwież”, preview-only CTA i brak duplicate-create.
- Mobile 390×844: URL i źródła są widoczne, ale decyzja, blocker i CTA nadal są
  poniżej first viewport; `r564.3` pozostaje otwarty.
- `/actions/act_prepare_wordpress_existing_draft_update`: first viewport mówi
  „Przygotuj i oceń bez zapisu zmian” oraz „Zapis zablokowany”; pełny render ma
  typed preview i technical disclosure.
- Manual usefulness `/content-workflow` pozostaje 5/10: konkret i bezpieczeństwo
  są użyteczne, ale freshness, cold load i mobile nadal blokują wynik.

## Weryfikacja

- Backend: 765 passed, 2 skipped, 1 deprecation warning; Ruff i mypy dla 233
  modułów przechodzą.
- Shared schemas: 31 passed, 10 skipped.
- Dashboard: 24 files, 137/137 Vitest; lint, typecheck i production build
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
- Pełny cold Playwright nie jest zielony. Potwierdzone osobne blokery mają
  Beads: content `c9h9.6`, Ads `c9h9.9`, Custom Segments `c9h9.10`, actions
  `c9h9.11`, knowledge `c9h9.12`, Merchant `c9h9.13`. Stare E2E strings są
  porządkowane w `c9h9.8`; timeoutów nie podnoszono.
- Complexity: 35 changed files, 1 frozen file (`wilq/actions/service.py`), 15
  changed-code violations. Service ma nadal 5 989 LOC; zmieniono jedną linię
  fallbacku preview bez wzrostu LOC. Pozostałe wyjątki dotyczą istniejących
  hotspotów `tests/test_codex_skill_eval_cases.py` i
  `wilq/content/workflow/api.py`.

## Kolejność wykonania

1. `c9h9.5` — current freshness jako część decyzji/evidence i refresh-first
   blocker.
2. `c9h9.6` — usunięcie cold waterfall po ustabilizowaniu semantyki freshness.
3. `c9h9.4` — exact dev-only ActionObject apply; raw booleany zastępuje typed
   capability powiązana z action/work item/payload/target/audit.
4. `r564.3` — decision/blocker/CTA w mobile first viewport.
5. Secondary route latency: `c9h9.9`–`c9h9.13`; nie wyprzedza głównego content
   P0.

`docs/audits/2026-07-10-cleanup-rebaseline.md` zawiera bieżącą mapę statusów i
ryzyk. Pełne specyfikacje pozostają wyłącznie w Beads.
