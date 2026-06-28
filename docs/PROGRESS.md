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
- Generic status routes, Demand Gen, Merchant, GA4, Ads, Content and custom
  segment first-screen labels were tightened to marketer-readable Polish.
- Legacy raw audit summary text is no longer rewritten through string
  replacements; raw historical summaries collapse to a neutral audit note.
- Ahrefs/content public contracts now use `referenced_public_url`; active
  diagnostics, source facts, tactical queue and WordPress draft handoff no
  longer expose or fall back to `target_url`.
- Knowledge operating map now carries API-owned labels for source connectors,
  evidence summaries, missing data and blocked claims, so the Knowledge route
  does not show playbook refusal rules or raw connector IDs on the first screen.
- Knowledge playbooks now expose Polish source rules and output contracts; live
  API proof shows no `Refuse`, `Evidence-backed`, `payload`, `connectora` or
  `query/page` residue in `/api/knowledge/playbooks`.
- UAT packet/result scripts now use marketer-facing Polish route names and
  markdown labels. Live packet proof shows no `Command Center`,
  `Content Planner`, `Ads Doctor`, `dev preview`, `Route`, `Pass` or `Fail`
  residue in the exported UAT packet.
- Ahrefs visible copy now uses `dowody`, `SEO i treści`, `linki zwrotne`,
  `widok Treści` and `organiczne słowa dla URL`; live Ahrefs API/browser proof
  shows no `Ahrefs evidence`, `SEO/content`, `backlinków` or `per URL` residue.
- Custom Segments candidates now expose API-owned preview cards and rejection
  reason labels. The route no longer reads `candidate.payload_preview` for
  marketer-facing segment cards.
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
- `rtk uv run pytest tests/test_api_contracts.py -q -k "ahrefs_diagnostics or content_diagnostics or wordpress_draft or tactical_queue or redaction or legacy_raw_audit_summary" --maxfail=1`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "knowledge_operating_map" --maxfail=1`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "knowledge" --maxfail=1`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "ahrefs_diagnostics" --maxfail=1`
- `rtk uv run pytest tests/test_marketer_uat_packet.py tests/test_marketer_uat_result.py -q --maxfail=1`
- `rtk uv run pytest tests/test_api_contracts.py -q -k "custom_segments" --maxfail=1`
- `rtk pnpm --dir packages/shared-schemas test -- --runInBand`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "custom segments route"`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/KnowledgePanels.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx src/routes/KnowledgePanels.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "knowledge|playbook"`
- `rtk uv run python - <<'PY' ... /api/knowledge/playbooks language residue scan ... PY`
- `rtk uv run python scripts/export_marketer_uat_packet.py --format markdown`
- `rtk env XDG_RUNTIME_DIR=$PWD/.local-lab/xdg-runtime agent-browser eval ... on /ahrefs`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "content route renders condensed selected decision|ahrefs route renders authority context"`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "demand gen route renders readiness contract"`
- `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --pool=threads --poolOptions.threads.singleThread=true --testTimeout=30000 -t "ga4 route renders workflow-specific brief focus"`
- `rtk curl --max-time 60 -sS http://127.0.0.1:8000/api/demand-gen/diagnostics`
- `rtk uv run python - <<'PY' ... /api/ahrefs/diagnostics, /api/content/diagnostics, /api/actions/act_prepare_wordpress_draft_handoff and /api/marketing/tactical-queue public contract scan ... PY`
- `rtk uv run python - <<'PY' ... /api/knowledge/operating-map label-field scan ... PY`
- `rtk env XDG_RUNTIME_DIR=$PWD/.local-lab/xdg-runtime agent-browser get text main` on `/knowledge`
- `rtk curl --max-time 10 -sS -i http://127.0.0.1:8000/api/health`
- `rtk curl --max-time 15 -sS http://127.0.0.1:8000/api/actions/act_prepare_ads_campaign_review_queue`
- `rtk env XDG_RUNTIME_DIR=$PWD/.local-lab/xdg-runtime agent-browser snapshot --compact --depth 6`
- `rtk env XDG_RUNTIME_DIR=$PWD/.local-lab/xdg-runtime agent-browser snapshot --depth 10` on `/ads-doctor/custom-segments`
- `rtk git diff --check`
