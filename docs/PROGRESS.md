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
- WILQ API remains the product brain. Dashboard and Codex skills consume typed
  API contracts, source connectors and WILQ-described evidence.
- Active cleanup removes marketer-facing jargon and working names:
  `Command Center` -> `Centrum pracy`, `Content Planner` -> `Treści` / widok
  treści, `Ads Doctor` -> `Google Ads` / widok Google Ads, `blockery` ->
  `blokady`, `evidence IDs` -> dowody opisane w WILQ.
- Do not preserve deprecated active fields, compatibility aliases or stale
  target/dev/migration semantics when direct migration is feasible.
- Do not mask dirty copy with UI translators, `replaceAll` helpers or local
  dictionaries. Fix typed API/schema/view-model/domain source instead.
- Raw IDs belong only in technical panels, audit detail or trace views, not in
  primary marketer copy.

## Latest Verified State

- Cleanup has moved many Ads, Merchant, GA4, Localo, Ahrefs, Knowledge, Brief
  Workflow, tactical queue and Action Detail labels from dashboard helpers into
  API/domain/shared-schema fields.
- Primary navigation and touched route headings now use marketer-readable Polish
  labels such as `Centrum pracy`, `Treści` and `Google Ads`.
- Touched marketer surfaces avoid raw evidence/action/connector IDs, endpoint
  names, raw enum keys, old dev-site mapping language and English validation
  wording in normal copy.
- Action Detail normal preview renders typed API preview cards only. Raw action
  payloads remain available only behind the collapsed technical detail panel.
- Demand Gen diagnostics now expose typed API preview cards and the dashboard no
  longer builds the primary preview from raw `payload_preview` shape.
- Recent guardrails cover tactical, Ads, Knowledge, action detail, Content
  Planner and marketer-language presentation contracts.

## Active Findings

1. Keep `PLAN.md`, `PLANS.md`, `docs/PROGRESS.md` and
   `docs/goals/001-goal.md` short and aligned. History belongs in git and proof
   artifacts.
2. Remove scattered raw fallback paths in registry/workflow and knowledge
   routes by adding API/schema/view-model labels.
3. Continue moving repeated metric, dimension, source, blocker and evidence
   naming into API/domain labels. Pure numeric formatting can stay in UI.

## Proof

Recent focused proof used during the cleanup:

- `rtk uv run python scripts/marketer_language_guard.py`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "merchant_diagnostics or marketing_brief or ahrefs_diagnostics or content_diagnostics or actions" --maxfail=1`
- `rtk pnpm --dir apps/dashboard typecheck`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "demand_gen" --maxfail=1`
- `rtk pnpm --dir packages/shared-schemas test -- --runInBand`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "demand gen route renders readiness contract"`
- `rtk curl --max-time 60 -sS http://127.0.0.1:8000/api/demand-gen/diagnostics`
- `rtk curl --max-time 10 -sS -i http://127.0.0.1:8000/api/health`
- `rtk curl --max-time 15 -sS http://127.0.0.1:8000/api/actions/act_prepare_ads_campaign_review_queue`
- `rtk env XDG_RUNTIME_DIR=$PWD/.local-lab/xdg-runtime agent-browser snapshot --compact --depth 6`
- `rtk git diff --check`
