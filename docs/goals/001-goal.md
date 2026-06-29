# Goal 001 - Clean Product Semantics And Marketer Cockpit

Status: active

Date: 2026-06-28

## Objective

Clean WILQ's active product semantics and marketer-facing surfaces before
starting the next product layer.

This goal does not finish the full WILQ Marketing Operating System. It makes
the current review cockpit coherent, condensed and usable enough that Wilku can
inspect it without reading technical internals.

## Identity

- WILQ = system/product.
- Wilku = human marketer/operator persona.
- Ekologus = first depth-first workspace/client.
- `ekologus.pl` = public canonical content home.
- Dev preview hosts = optional design/staging context only when explicitly
  configured.

## Product Rules

- Brak dowodu w WILQ -> brak rekomendacji.
- Brak źródła danych -> brak rekomendacji.
- Brak sprawdzenia treści przed pisaniem -> brak pisania.
- Brak briefu sprzedażowego -> brak szkicu.
- Brak sprawdzenia ryzykownych obietnic -> brak języka gotowego do publikacji.
- Brak sprawdzenia przez człowieka -> brak przekazania szkicu do WordPress.
- Brak audytu -> brak zapisu zmian.
- Brak okna pomiarowego -> brak twierdzeń o sukcesie albo porażce.
- Brak logiki biznesowej w promptach albo opisach skilli.
- Brak translatorów React/UI, helperów `replaceAll` i słowników w route'ach
  dla semantyki produktu.
- Brak aliasów zgodności i przestarzałych aktywnych pól, gdy bezpośrednia
  migracja jest wykonalna.
- Usuń stare semantyki target/dev/migration z aktywnych kontraktów.
- Brudny tekst widoczny dla marketera naprawiaj w źródłowym kontrakcie API,
  schemacie, view-modelu albo warstwie domenowej.
- Raw IDs may appear in technical panels, audit detail and trace views only.
- Every repeated issue becomes a typed API/schema/view-model field or a test
  guard.

## Current Cleanup Vocabulary

Use `PLAN.md` as the canonical visible-language source.

Preferred visible terms include:

- `Centrum pracy`
- `Treści`
- `Google Ads`
- `akcja do sprawdzenia`
- `podgląd zmian`
- `zapis zmian`
- `zatwierdzenie zmian`
- `blokada`
- `dowody`
- `źródła danych`
- `co zrobić dalej`
- `czego nie wolno obiecać`

Forbidden primary-surface terms include:

- `Command Center`
- `Content Planner`
- `Ads Doctor`
- `payload`
- `evidence IDs`
- `blockery`
- raw connector/debug wording
- legacy dev-preview placement wording
- migration-map or mapping-review wording

Technical route slugs, schema fields, enum values, connector IDs, evidence IDs,
action IDs and audit fields may stay in technical contracts or drawers.

## Current State

- Active docs agree on the current product model: WILQ is the system, Wilku is
  the human operator persona, Ekologus is the first workspace, and
  `ekologus.pl` remains the canonical content home.
- Dev-preview and migration-era assumptions are guarded in active content
  diagnostics, context packs, skill contracts and dashboard smoke tests.
- Primary dashboard and skill surfaces use Polish operator copy and API/domain
  labels for decisions, evidence summaries, sources, blockers and next steps.
  Raw IDs, payloads, connector trace and audit detail remain behind technical
  detail.
- Connector status is live and current for the core proof: GSC, GA4, Merchant,
  Google Ads, Ahrefs, Localo and WordPress are configured and fresh. LinkedIn
  and Facebook are optional missing-credential social connectors; Google Sheets
  is disabled by current scope.
- JS workspace dependencies are current as of 2026-06-29. Google Ads minor API
  releases are tracked as explicit WILQ read/review contracts, not endpoint
  churn.
- Fallow is wired as the changed-file audit gate. Current full health shows
  historical dashboard hotspots, but no high-confidence current refactoring
  target blocks this cleanup goal.
- Machine guardrails cover marketer language, context-pack language, content URL
  semantics, raw visible copy, schema label hydration, active goal count and
  Goal 001 completion status.
- Durable UAT handoff lives at
  `docs/handoffs/2026-06-29-marketer-uat-ready.md`. Goal 001 remains active
  until real marketer UAT is recorded or the owner explicitly defers it.

## Active Findings

Use these as the next work queue. Do not start future product layers until these
are resolved or explicitly deferred.

1. Keep `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and this file short and
   aligned.
2. Continue raw fallback cleanup in active API/helper modules. Any new visible
   raw fallback must be fixed at typed API/schema/view-model source.
3. Continue typed contract/vendor-enum label registries outside the already
   cleaned Ads campaign status/channel path so unknown read contracts and vendor
   enums do not fall back to raw snake_case or English values in marketer-facing
   copy.
4. Continue moving repeated metric, dimension, source, blocker and evidence
   naming into API/domain labels. Pure numeric formatting can stay in UI.
5. Dashboard still needs focused cleanup for any newly found content/ads
   payload-derived panels.
6. Merchant attribute-key matching now uses canonical comparison keys instead
   of underscore-to-space label normalization. Do not reintroduce generic
   underscore humanization as a compatibility layer.
7. Continue checking compacted context-packs after dashboard/API cleanup. Daily
   and content-strategist context packs have focused tests, and
   `scripts/context_pack_language_guard.py` now guards live compact skill
   contexts across the core skill set in both `verify.sh` and the pre-demo
   gate.
8. Continue focused browser audits when touched routes change or a new visible
   copy risk is found. Any future long blocker/review list must be condensed at
   API/domain source, not trimmed in React.
9. Real marketer UAT is still required for usefulness claims unless explicitly
   deferred by the owner. Use
   `docs/handoffs/2026-06-29-marketer-uat-ready.md` as the current handoff.
   Guard command:
   `rtk uv run python scripts/goal_001_completion_check.py --format markdown`.

## Execution Policy

- Use `rtk` before every shell command.
- Use beads for operational task tracking: run `bd prime` and
  `bd ready --json` after recovery, claim work with `bd update <id> --claim`,
  and do not recreate the same queue as markdown TODOs.
- Use `scripts/local_stack.sh start|status|logs|restart|stop` for the local
  WILQ API/dashboard runtime; do not hand-roll detached API or dashboard
  processes.
- Inspect existing implementation before editing.
- Prefer small verified slices and conventional commits.
- Use subagents for parallel read-only audits or disjoint write scopes.
- Do not let multiple workers edit the same files without explicit ownership.
- After each slice:
  - run focused tests,
  - capture browser/API proof when a marketer route changes,
  - update only current recovery facts,
  - commit and push a coherent green slice.

## Verification

Focused checks:

- Docs-only: `rtk git diff --check`.
- API/schema/action: focused `rtk uv run pytest ...`.
- Dashboard: touched route test plus `rtk pnpm --dir apps/dashboard typecheck`.
- Skill changes: deterministic smoke and targeted eval.
- Marketer copy: `rtk uv run python scripts/marketer_language_guard.py`.
- Browser: `agent-browser` proof for touched marketer routes.

Broad checks:

- `rtk scripts/verify.sh` before cross-surface completion claims.

## Completion Definition

Goal 001 is complete when:

- Active docs agree on the corrected product model and cleaned language.
- Active product paths no longer depend on dev-site migration semantics.
- Primary marketer surfaces no longer show forbidden technical jargon.
- UI translators/string replacement cleanup helpers are removed or proven
  out-of-scope internal utilities.
- Deprecated active fields and compatibility aliases are removed where direct
  migration is feasible.
- Ukierunkowane kontrole API/dashboard/skill przechodzą dla każdego dotkniętego
  zakresu.
- Dowód w przeglądarce potwierdza dotknięte ścieżki marketera.
- Pozostałe historyczne wzmianki są zarchiwizowane albo jawnie śledzone jako
  dług do usunięcia.
- Realny UAT marketera jest zapisany albo jawnie odroczony przez ownera.

Finalny WILQ Marketing Operating System pozostaje późniejszym celem. Nadal
wymaga ContentPreflight, briefu sprzedażowego, rejestru ryzykownych obietnic,
sprawdzenia przez człowieka, przekazania szkicu do WordPress, pomiaru efektu,
profili przestrzeni klienta, cyklu życia wiedzy i bramek bezpiecznego zapisu.
