# WILQ Progress Ledger

Aktualizuj ten plik przy istotnym postępie, zmianie blockerów albo wyniku
testu skilla. To ma być krótki recovery ledger, nie pełny changelog.

Pełne archiwum sprzed kompaktowania:
`docs/progress/archive/2026-06-19-progress-ledger.md`.

## Maintenance Rule

- Trzymaj tutaj aktualny stan, ostatnie 3-5 slice'ów, aktywne luki i następny
  krok.
- Nie dopisuj kolejnych setek linii historii. Starsze wpisy przenoś do
  `docs/progress/archive/`.
- Git i dedykowane ledgery są źródłem długiej historii. Ten plik ma pomagać po
  utracie contextu.

## Current Snapshot

Data: 2026-06-19

Stan produktu:

- Goal 001 nadal aktywny: `docs/goals/001-goal.md`.
- WILQ API jest system brain. Dashboard i Codex skills mają korzystać z tych
  samych kontraktów API, evidence IDs, ActionObject IDs i source connectors.
- Lokalny stack prowadź przez `scripts/local_stack.sh start|stop|restart|status|logs`.
  Kanoniczne URL-e: API `http://127.0.0.1:8000`, dashboard
  `http://127.0.0.1:5173/command-center`.
- Operator-facing output ma być po polsku z polskimi znakami.
- Nie wolno naprawiać błędów reasoning przez dopisywanie edge-case'ów do skill
  references. Naprawa ma iść przez typed API state, knowledge cards, expert
  rules, context-packi, evale i dashboard.

Aktualny proof produktowy:

- Full `scripts/verify.sh` przeszedł po najnowszym slice:
  API smoke, skill smokes, dashboard route tests, Playwright e2e `9 passed`
  i dashboard production build.
- Ostatni product/performance commit przed tym docs-maintenance slice:
  `792ad2f perf(codex): scope non-daily context packs`.

Aktualny maintenance:

- `docs/PROGRESS.md` został skompaktowany do recovery ledgeru.
- Pełna historia sprzed kompaktowania leży w
  `docs/progress/archive/2026-06-19-progress-ledger.md`.

## Last Completed Slices

1. Non-daily skill context-pack compaction, 2026-06-19 22:45 Europe/Warsaw.
   Default context-packs pomijają ciężkie diagnostic sections i metric facts
   dla content, GA4 i Merchant scoped packs. Campaign Builder nie ciągnie już
   Merchant jako domyślnego scope'u i używa lekkiego `content_landing_context`.
   Demand Gen buduje Ads + GA4 równolegle i nie ciągnie Merchant bez konkretnego
   kontraktu Demand Gen/Merchant. Live proof po `scripts/local_stack.sh restart`:
   `wilq-campaign-builder` `90711 bytes`, cold `1.867s`, warm `0.158s`;
   `wilq-demand-gen-operator` `100349 bytes`, cold `2.574s`, warm `0.156s`;
   `wilq-content-strategist` `91731 bytes`, cold `2.044s`, warm `0.166s`;
   `wilq-ga4-analyst` `28578 bytes`, cold `1.927s`, warm `0.147s`;
   `wilq-merchant-feed-operator` `24007 bytes`, cold `1.819s`,
   warm `0.153s`; `wilq-ads-doctor` `185126 bytes`, cold `1.392s`,
   warm `0.156s`; `wilq-custom-segments` `187121 bytes`, cold `1.408s`,
   warm `0.194s`; `wilq-daily-command` `120504 bytes`, cold `1.918s`,
   warm `0.236s`. Full `scripts/verify.sh` passed.

2. Custom segments review-only payload preview, 2026-06-19 22:08
   Europe/Warsaw. `/api/ads/diagnostics.custom_segments_read_contract` exposes
   `payload_preview` with `member_type=KEYWORD`, `api_mutation_ready=false`,
   `apply_allowed=false` and `destructive=false`. Remaining missing contracts:
   `keyword_planner_enrichment` and `forecast_or_audience_size`. Non-interactive
   eval passed:
   `.local-lab/evals/codex-skill/20260619T201200Z/wilq-custom-segments/result.json`.
   Full `scripts/verify.sh` passed.

3. Dashboard bundle split, 2026-06-19 21:44 Europe/Warsaw. Vite manual chunks
   split React, TanStack, icons, schemas and misc vendor code. Production build
   no longer emits the >500 KB chunk warning in that proof. Full
   `scripts/verify.sh` passed.

4. Daily command context-pack payload compaction, 2026-06-19 21:32
   Europe/Warsaw. Default `wilq-daily-command` context-pack compacts
   `active_action_objects`, removes heavy `connector_health` from embedded
   Command Center, caps Marketing Brief metric facts and keeps full data behind
   `full_context=true` plus dedicated API endpoints. Non-interactive eval
   passed:
   `.local-lab/evals/codex-skill/20260619T193056Z/wilq-daily-command/result.json`.
   Full `scripts/verify.sh` passed.

5. DailyRuntime cold-path compaction, 2026-06-19 21:13 Europe/Warsaw. Shared
   DailyRuntime now builds core daily products together and reuses them across
   Command Center, Marketing Brief and daily skill context-pack. Cold API after
   restart stayed around `1.9-2.1s`, warm cache around `0.17-0.28s`. Full
   `scripts/verify.sh` passed.

## Active Gaps

- Demand Gen cold context-pack is still about `2.6s`; payload and warm runtime
  are inside budget, but cold path should be improved if it stays visible in
  browser/Codex proof.
- Full BDOS-class Ads optimizer is not done. Remaining areas include Keyword
  Planner enrichment, forecast/audience size, budget pacing, impression share
  usage, change-history reasoning, apply previews, human confirmation and audit.
- Command Center/dashboard is moving toward a usable marketer cockpit, but Goal
  001 remains active until the goal file's API/dashboard/skills/evals/safety
  requirements are all verified.
- Knowledge base/source-map work exists, but the long-term knowledge compiler
  and memory layer are not complete. Do not replace that with prompt stuffing.

## Next Best Slice

Continue with Goal 001 in this order unless live state shows a stronger blocker:

1. Improve the next marketer-facing cockpit surface that still repeats or hides
   useful decisions.
2. Continue Ads optimizer read contracts toward safe, review-only decisions.
3. Add or strengthen non-interactive skill evals only when they test real
   product usefulness, not just schema compliance.
4. Keep `docs/PROGRESS.md` compact; archive older entries instead of appending
   long history here.

## Recovery Pointers

- Active goal: `docs/goals/001-goal.md`.
- Recovery index: `docs/CONTEXT.md`.
- Skill eval ledger: `docs/evals/skill-eval-ledger.md`.
- Marketing source map: `docs/research/wilq-marketing-source-map.md`.
- BDOS-class architecture target:
  `docs/architecture/bdos-class-wilq-operating-system.md`.
- Full pre-compaction progress archive:
  `docs/progress/archive/2026-06-19-progress-ledger.md`.
