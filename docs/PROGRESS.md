# WILQ Progress Ledger

This is the short recovery ledger. It is not a changelog and must not become an
append-only transcript.

Full current plan: `PLAN.md`
Long-range product plan: `PLANS.md`
Active goal: `docs/goals/001-goal.md`

## Current Readout

Date: 2026-06-28

- WILQ is the system/product.
- Wilku is the human marketer/operator persona.
- Ekologus is the first depth-first workspace/client.
- `ekologus.pl` is the public canonical content home.
- Dev preview hosts are optional design/staging context only when explicitly
  configured. They are not canonical content targets and must not drive content
  decisions by default.
- WILQ API is the product brain. Dashboard and Codex skills consume typed API
  contracts, source connectors and WILQ-described evidence.
- Marketer-facing UI and skill output must use Polish operating language.
- Raw IDs, connector trace, raw payloads and audit details belong only in
  technical detail.
- Dirty copy must be fixed in typed API/schema/view-model/domain source, not
  with React translators or string replacement helpers.
- Do not preserve deprecated active fields, compatibility aliases or stale
  dev-preview/migration semantics when direct migration is feasible.

## Latest Verified State

- Primary navigation and touched route headings use marketer-readable Polish:
  `Centrum pracy`, `Merchant`, `Treści`, `Google Ads`, `GA4`, `Procesy`,
  `Szanse`, `Akcje`, `Baza wiedzy`.
- Touched Ads, Merchant, GA4, Localo, Ahrefs, Knowledge, tactical queue,
  Procesy and action-detail surfaces render API/domain/shared-schema labels
  instead of route-local label dictionaries.
- Action-detail normal preview uses typed API preview cards. Raw action payloads
  stay behind technical detail.
- Content active semantics use public/final URL wording. Active content
  diagnostics/actions no longer expose dev-site placement semantics as product
  logic.
- Treści selected-decision and plan/draft panels render API-owned
  view-models instead of parsing raw action payload previews.
- Merchant, Ads, GA4, Demand Gen, Localo and social touched preview surfaces use
  API-owned preview cards or display labels instead of raw payload shape.
- Knowledge details use API-owned source labels and Polish count forms instead
  of raw connector IDs.
- Procesy cards and run summaries use API/domain source, evidence, action,
  missing-data and blocked-claim summary labels. Fresh `/workflows` loads no
  longer wait on hidden related-action data.
- Shared `StatusBadge` does not own a product-language dictionary; touched
  surfaces pass raw state values plus API/domain visible labels.
- Unknown visible label fallbacks collapse to neutral Polish operator labels
  instead of exposing raw enum keys, snake_case or English values.
- Current proof artifacts live in `.local-lab/proof/`; detailed history lives
  in git commits.

## Active Findings

1. Keep `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and
   `docs/goals/001-goal.md` short and aligned. History belongs in git and proof
   artifacts.
2. Continue raw fallback cleanup in active API/helper modules. Any new visible
   raw fallback must be fixed at typed API/schema/view-model source.
3. Add typed contract/vendor-enum label registries outside the already-cleaned
   Ads diagnostics helper path so unknown read contracts and vendor enums do not
   fall back to raw snake_case or English values in marketer-facing copy.
4. Continue moving repeated metric, dimension, source, blocker and evidence
   naming into API/domain labels. Pure numeric formatting can stay in UI.
5. Remaining active `replace("_", " ")` scan hits are Merchant attribute-key
   normalizers used for equality matching, not visible operator labels; keep
   them out of copy paths.
6. Continue checking compacted context-packs after dashboard/API cleanup; the
   content strategist context currently preserves content preview labels.
7. Real marketer UAT is still required for a usefulness claim unless the owner
   explicitly defers it.

## Latest Accepted Proof

Most recent committed slice:

- `rtk uv run pytest tests/test_api_contracts.py -q -k "workflows_are_decision_backed_operator_contracts or workflow_label_fallbacks_do_not_expose_raw_values or workflow_run_persists_to_local_state_with_redaction" --maxfail=3`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/WorkflowPanels.test.tsx src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "workflow"`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk pnpm --dir packages/shared-schemas test`
- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk git diff --check`
- Browser proof: `.local-lab/proof/workflow-labels-clean.txt`

Recent broad guardrails that remain relevant:

- `rtk uv run python scripts/skill_hygiene_check.py`
- `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q`
- Focused API/dashboard tests named in recent commits.

Do not paste long historical proof lists here. Use git history and
`.local-lab/proof/` when older evidence is needed.
