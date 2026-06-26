# WILQ Progress Ledger

This is the short recovery ledger. It is not a changelog and must not become an
archive of old broken wording.

Full execution plan: `PLAN.md`
Long-range product plan: `PLANS.md`
Active goal: `docs/goals/001-goal.md`

## Current Readout

Date: 2026-06-26

- WILQ is the system/product.
- Wilku is the human marketer/operator persona.
- Ekologus is the first depth-first workspace/client.
- `ekologus.pl` is the public canonical content home.
- Dev preview hosts are optional design/staging context only when explicitly
  configured for a workflow.
- Existing Ekologus content is preserve-first. A redesign does not imply
  rewriting existing content.
- WILQ API remains the product brain. Dashboard and Codex skills must consume
  typed API contracts, evidence IDs and source connectors.
- Do not preserve outdated fields, old wording or route-local cleanup helpers
  as a compatibility strategy. Migrate touched active consumers directly.

## Canonical Documents

- `PLAN.md` is the current canonical execution plan for cleanup and product
  semantics.
- `docs/goals/001-goal.md` is the active execution goal.
- `PLANS.md` is the longer product roadmap after the cleanup state is accepted.
- Proof artifacts live under `.local-lab/proof/**`; keep detailed scan terms and
  historical transcripts there, not in this ledger.

## Latest Important Facts

- The core marketer path remains:
  `/command-center -> /merchant -> /content-planner -> /ads-doctor -> /ga4`.
- Active content semantics have been corrected toward public/final URL language.
  Removed old review packet script/test artifacts are still visible in git
  status as deletions.
- Command Center, Localo, dashboard fallback labels, context-pack condensation,
  action review-gate condensation, Ads context condensation, secondary route
  condensation, Knowledge, Workflows and Settings have runtime or browser proof
  from the current cleanup goal.
- The latest live API context confirmed WILQ API reachability and connector
  summary `total=12`, `configured=9`, `missing_credentials=2`.
- The current cleanup slice focuses on marketer-facing language, action safety
  wording, stale dev-preview strategy removal and full condensation of active
  operator surfaces.
- Daily/skill context-pack cleanup now avoids stale-field exception lists in the
  API. Audit events in compact operator context expose event type and a plain
  detail pointer; full notes and technical details stay in action detail.
- First-class `ContentPreflight` contract is now started as a typed API layer
  derived from current content diagnostics. It answers preserve/refresh/merge/
  create/block before any future sales brief or draft work; draft and WordPress
  draft remain blocked in this slice.

## Latest Proof Pointers

- WordPress draft handoff contract cleanup:
  `.local-lab/proof/20260626-wordpress-draft-handoff-contract-cleanup/summary.json`.
- Command Center blocked-claim cleanup:
  `.local-lab/proof/20260625-command-center-claim-cleanup/api-context/summary.json`.
- Localo marketer-language cleanup:
  `.local-lab/proof/20260625-localo-language-cleanup/api-context/summary.json`
  and `.local-lab/proof/20260625-localo-language-cleanup/browser/summary-after-wait.json`.
- Dashboard fallback cleanup:
  `.local-lab/proof/20260625-dashboard-fallback-cleanup/browser/fallback-scan-summary.json`.
- Status badge fallback cleanup:
  `.local-lab/proof/20260626-status-badge-fallback-cleanup/browser/summary.json`.
- Ads/Merchant action-language cleanup:
  `.local-lab/proof/20260626-contract-check-language-cleanup/api-context/ads-merchant-string-scan-summary.json`.
- Command Center freshness-language cleanup:
  `.local-lab/proof/20260626-command-center-freshness-language-cleanup/api-context/command-center-string-scan.json`
  and
  `.local-lab/proof/20260626-command-center-freshness-language-cleanup/browser/command-center-browser-scan.json`.
- Content strategist context-pack condensation:
  `.local-lab/proof/20260625-context-pack-condensation/api-context/content-context-pack-final.json`.
- All-skill default context-pack clean scan:
  `.local-lab/proof/20260625-all-skill-context-clean-final-v2/api-context/summary.json`.
- Knowledge route condensation:
  `.local-lab/proof/20260625-knowledge-route-condensation/browser/`.
- Workflows condensation:
  `.local-lab/proof/20260625-workflows-condensation/`.
- Secondary route condensation:
  `.local-lab/proof/20260625-secondary-route-continuation/browser/`.
- Settings access condensation:
  `.local-lab/proof/20260625-route-audit-continuation/browser/settings-after-access-condensation.txt`.
- Action detail language cleanup:
  `.local-lab/proof/20260626-action-detail-language-cleanup/browser/content-action-detail-scan.json`.
- Actions route list cleanup:
  `.local-lab/proof/20260626-actions-route-list-cleanup/browser/actions-playwright-expanded.json`.
- Opportunities list cleanup:
  `.local-lab/proof/20260626-opportunities-list-cleanup/api-context/opportunities-live-summary.json`
  and
  `.local-lab/proof/20260626-opportunities-list-cleanup/browser/browser-proof-status.json`.
- Registry panels condensation:
  `.local-lab/proof/20260626-registry-panels-condensation/summary.json`.
- Knowledge panels language cleanup:
  `.local-lab/proof/20260626-knowledge-panels-language-cleanup/summary.json`.
- Connector access language cleanup:
  `.local-lab/proof/20260626-connector-access-language-cleanup/summary.json`.
- Domain status language cleanup:
  `.local-lab/proof/20260626-domain-status-language-cleanup/summary.json`.
- Action detail draft-label cleanup:
  `.local-lab/proof/20260626-action-detail-draft-label-cleanup/summary.json`.
- Tactical queue metric-language cleanup:
  `.local-lab/proof/20260626-tactical-queue-metric-language-cleanup/summary.json`.
- Knowledge source-type language cleanup:
  `.local-lab/proof/20260626-knowledge-source-type-language-cleanup/summary.json`.
- Content contract version-label cleanup:
  `.local-lab/proof/20260626-content-contract-version-label-cleanup/summary.json`.
- Keyword Planner blocked-access label cleanup:
  `.local-lab/proof/20260626-keyword-planner-blocked-access-label-cleanup/summary.json`.
- Action review-gate safety-language cleanup:
  `.local-lab/proof/20260626-action-review-gate-safety-language-cleanup/summary.json`.
- Content WordPress status language cleanup:
  `.local-lab/proof/20260626-content-wordpress-status-language-cleanup/summary.json`.
- Brief workflow focus-language cleanup:
  `.local-lab/proof/20260626-brief-workflow-focus-language-cleanup/summary.json`.
- Generic surface registry fallback removal:
  `.local-lab/proof/20260626-generic-surface-registry-fallback-removal/summary.json`.
- Content Planner Polish language cleanup:
  `.local-lab/proof/20260626-content-planner-polish-language/browser/content-planner-text.txt`
  and
  `.local-lab/proof/20260626-content-planner-polish-language/content-diagnostics.json`.
- Marketer fixture/backend language cleanup:
  `.local-lab/proof/20260626-marketer-fixture-language-cleanup/summary.json`.
- Ads custom-segment context-pack contract cleanup:
  `.local-lab/proof/20260626-ads-custom-segment-context-pack-contract/summary.json`.
- Marketer language guard self-improvement:
  `.local-lab/proof/20260626-marketer-language-guard-self-improvement/summary.json`.
- Ahrefs capability and Polglish cleanup:
  `.local-lab/proof/20260626-ahrefs-capability-and-polglish-cleanup/summary.json`.

## Latest Verification

- ContentPreflight first contract slice:
  - Added typed backend and shared-schema preflight response.
  - Added `/api/content/preflight`.
  - Added `content_preflight` to content strategist/GSC context packs.
  - Existing-content fixture returns `recommended_mode=refresh`,
    `create_allowed=false`, `draft_allowed=false`,
    `wordpress_draft_allowed=false`, `sales_brief_allowed=true`.
  - No-evidence fixture returns `recommended_mode=block`.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "content_diagnostics_blocks_until_vendor_read or content_diagnostics_exposes_query_page_inventory_queue or codex_context_pack_scopes_content_strategist_payload" --maxfail=1`
    passed: 3 tests.
  - `rtk pnpm --filter @wilq/shared-schemas test -- --runInBand` passed.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
- Context-pack stale-field exception cleanup:
  - Removed active API filters that knew about old dev-preview/mapping field
    names.
  - Updated context-pack tests so compact daily context preserves audit type and
    review outcome without copying raw notes or detail keys.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "context_pack or content_public_url or dev_site or content_action_payload or wordpress_draft_handoff" --maxfail=1`
    passed: 27 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
- Full cleanup verification on 2026-06-26:
  - `scripts/verify.sh` passed end-to-end.
  - Backend pytest: 214 passed.
  - Dashboard Vitest: 52 passed.
  - Playwright dashboard smoke/demo proof: 14 passed.
  - Dashboard production build passed.
  - Non-failing warnings remain: Starlette `httpx` deprecation, `nosec` B105
    warnings in OAuth helper literals, semgrep unavailable, local package not on
    PyPI for audit.
- Ahrefs capability and Polglish cleanup:
  - WILQ remains valid as the product/system name. The cleanup targets
    unnecessary English and internal wording in visible/operator copy.
  - Visible phrases like `brakujące credentiale`, `credential names`,
    `gotowość connectora` and `awarię connectora` were replaced with plain
    Polish access/source wording where they were shown to the operator.
  - Added structured Ahrefs expert capabilities so the Ahrefs skill context
    pack exposes SEO gap review capability through typed rules, not prompt
    workaround text.
  - Updated the Ahrefs context-pack contract test to enforce full condensation:
    full diagnostics keep gap records, while the Codex context-pack carries the
    record count and full endpoint pointer.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "command_center or ahrefs or codex_context_pack_scopes_ads_doctor_payload" --maxfail=1`
    passed: 28 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 -t "connector status renders|localo route renders workflow-specific blockers and clean metric labels|social route renders workflow-specific blockers|Command Center" --testTimeout=15000`
    passed: 3 tests, 17 skipped.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
  - `rtk git diff --check -- apps/api/wilq_api/main.py wilq/briefing/command_center.py wilq/briefing/ahrefs_diagnostics.py apps/dashboard/src/routes/OperatingRouteSurfaces.tsx scripts/marketer_language_guard.py wilq/expert/seo/ahrefs_capabilities.yaml tests/test_api_contracts.py`
    passed.
- Marketer language guard self-improvement:
  - `scripts/marketer_language_guard.py` now blocks newly found visible
    regressions: `Blockery`, `Metric facts`, `GSC clicks`,
    `content opportunities`, `post candidates`, `LinkedIn credentials` and old
    adapter wording.
  - WILQ remains allowed as the system/product name. The guard does not
    blanket-ban `WILQ API`, `source_connectors` or `missing_credentials`
    because those are still valid technical contract terms in skill/API
    surfaces.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
- Ads custom-segment context-pack contract cleanup:
  - `act_prepare_custom_segments_from_search_terms` context-pack compaction now
    keeps one compacted `payload_preview` row for the existing
    `custom_segment_change_preview_v1` contract.
  - Removed the stale compaction check for unused
    `custom_segment_payload_preview_v1` wording instead of preserving an alias.
  - `rtk uv run python -m py_compile apps/api/wilq_api/main.py` passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "codex_context_pack_scopes_ads_doctor_payload or codex_context_pack_scopes_custom_segments_payload" --maxfail=1`
    passed: 2 tests.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "marketing_brief or command_center or localo or ads" --maxfail=1`
    passed.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
- Marketer fixture/backend language cleanup:
  - WILQ remains the product/system name. The cleanup targets unnecessary
    English and technical visible wording, not the WILQ brand.
  - Dashboard fixture and backend brief copy was cleaned for visible terms like
    `Social Publisher`, `Blockery`, `Metric facts`, `GSC clicks`,
    `content opportunities`, `WILQ API`, adapter/connector wording and raw
    access wording where the marketer does not need contract details.
  - Technical contract fields such as `missing_credentials`,
    `checked_credentials`, `source_connectors` and metric fact names were not
    renamed mechanically.
  - `rtk uv run python -m py_compile wilq/briefing/localo_diagnostics.py wilq/briefing/marketing_brief.py wilq/briefing/command_center.py wilq/briefing/ads_diagnostics.py`
    passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "marketing_brief or command_center or localo" --maxfail=1`
    passed: 32 tests.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q --maxfail=1`
    passed: 5 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx src/routes/CommandCenterRoute.test.tsx src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1 -t "connector status renders|workflow route renders persisted workflow runs|localo route renders workflow-specific blockers and clean metric labels|social route renders workflow-specific blockers|Command Center|content" --testTimeout=15000`
    passed: 8 tests, 17 skipped, 1 file skipped.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - The broad Ads-inclusive API subset blocker found during this slice was
    fixed in the Ads custom-segment context-pack cleanup above.
- WordPress draft handoff contract cleanup:
  - Active content/WordPress handoff naming was migrated from
    `staging_*` / `wordpress_staging_*` to `wordpress_draft_handoff_*` /
    `wordpress_draft_*` in the backend payload, context-pack compaction,
    dashboard renderers, content strategist smoke contract and content tests.
  - Touched dashboard domain surfaces now use `WILQ` / data-in-WILQ language
    instead of visible `WILQ API` wording where the marketer does not need API
    boundary language.
  - `rtk uv run python -m py_compile apps/api/wilq_api/main.py wilq/actions/content_refresh.py wilq/actions/service.py wilq/briefing/content_diagnostics.py .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py`
    passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "content" --maxfail=1`
    passed: 13 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ContentDiagnosticSurface.test.ts src/routes/ActionDetailRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 18 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - Scoped stale-term scan over touched active sources returned no hits for
    `staging_handoff`, `wordpress_staging`, `staging_draft`,
    `WordPressStaging`, `contentStaging`, generic Focus/Safety Gate registry
    labels, `migration-map` or `mapping-review`.
  - Live WILQ API/browser proof was not refreshed in this slice because the
    current session reports WILQ API unreachable.
- Ads/Merchant action-language cleanup:
  - `rtk uv run python -m py_compile wilq/briefing/ads_diagnostics.py wilq/briefing/merchant_diagnostics.py wilq/actions/google_ads/negative_keywords.py wilq/actions/google_ads/custom_segments.py wilq/actions/google_ads/search_term_ngrams.py`
    passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "ads_diagnostics or merchant_diagnostics" --maxfail=1`
    passed: 10 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "ads doctor route renders live metric-backed diagnostics|custom segments route renders dedicated validation contract" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 2 tests.
- Command Center freshness-language cleanup:
  - `rtk uv run python -m py_compile wilq/briefing/command_center.py`
    passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "command_center" --maxfail=1`
    passed: 18 tests.
  - `agent-browser` snapshot scan for `/command-center` passed.
- Skill language cleanup:
  - Stale mixed-language scans over WILQ skill instructions and output contracts
    returned no hits.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
- Action detail language cleanup:
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionDetailRoute.test.tsx -t "content brief and WordPress" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test.
  - Browser scan for `/actions/act_prepare_content_refresh_queue` returned no
    stale action/detail wording hits.
- Connector access language cleanup:
  - Command Center now says `źródła danych`, not `connectorów`, in the source
    health summary.
  - Settings access details now summarize missing access/configuration counts
    without exposing connector IDs, credential variable names or raw source
    labels in the expanded card.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/RegistryPanels.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 3 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "connector status renders" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test; startup/collection remained slow, but the route assertion
    completed.
  - Stale visible-copy scan over the touched sources returned no component hits;
    remaining raw strings are fixture inputs or negative assertions.
  - `rtk git diff --check` passed.
- Domain status language cleanup:
  - Ads Doctor, Ahrefs, Merchant and GA4 connector status labels now render
    `brakuje dostępu` instead of credential wording.
  - Social Publisher empty state now asks to `uzupełnij dostęp LinkedIn/Facebook`
    instead of configuring credentials.
  - Active route source scan returned no visible component hits for stale
    credential wording; the only remaining hit was a negative test assertion.
  - `rtk git diff --check` passed.
  - Focused `App.test.tsx -t "social route renders workflow-specific blockers"`
    did not collect tests and failed in Vitest worker transform/fetch for
    `OperatingRouteSurfaces.tsx`; do not count it as route proof.
- Action detail draft-label cleanup:
  - Action detail preview cards now use `Materiały do posta social`,
    `Tytuł szkicu`, `Przekazanie do WordPress`, `Blokady przekazania` and
    `gotowość systemu` instead of draft/staging/API wording.
  - Stale-label scan over `DetailPanels.tsx` and `ActionDetailRoute.test.tsx`
    returned no hits for the removed visible strings.
  - `rtk git diff --check` passed.
  - Focused `ActionDetailRoute.test.tsx -t "social draft evidence inputs|content brief and WordPress"`
    failed: one action-detail route assertion did not find the heading, and one
    case timed out. Treat this as missing runtime proof for this slice.
- Tactical queue metric-language cleanup:
  - Tactical queue first-screen copy now says `metryki z WILQ API` instead of
    `metric facts`.
  - Empty-state blocker now says `Potrzebne są metryki z WILQ API`.
  - Source scan over Tactical Queue returned no production `metric facts` hits;
    remaining hits are fixture input or negative assertions.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/TacticalQueuePanel.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test.
  - `rtk git diff --check` passed.
- Knowledge source-type language cleanup:
  - Knowledge cards now render `marketing_playbook` source type as `zasada pracy`
    instead of `playbook marketingowy`.
  - Added focused card-list coverage and test cleanup in
    `KnowledgePanels.test.tsx`.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/KnowledgePanels.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 3 tests.
  - Source scan returned no active `playbook marketingowy`/visible playbook
    label hits; the remaining hit is a negative assertion.
  - `rtk git diff --check` passed.
- Content contract version-label cleanup:
  - Content contract labels now hide internal `_v1` suffixes for draft
    generation, URL preflight and WordPress draft preview/write labels.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 3 tests.
  - Label scan over `contentLabels.ts` and the focused test found no visible
    ` v1` label strings; remaining hits are enum inputs in tests.
  - `rtk git diff --check` passed.
- Keyword Planner blocked-access label cleanup:
  - Keyword Planner action detail now renders `Zablokowany dostęp` instead of
    `Blokowane API`.
  - Source scan over `DetailPanels.tsx` and `ActionDetailRoute.test.tsx`
    returned no stale `Blokowane API` hits.
  - `rtk git diff --check` passed.
  - Focused `ActionDetailRoute.test.tsx -t "Keyword Planner access blocker"`
    failed before reaching the expected detail heading; do not count it as
    route proof for this slice.
- Action review-gate safety-language cleanup:
  - Action review gate now renders `Ostatni zapis bezpieczeństwa`,
    `Ślad bezpieczeństwa`, `Czy próbowano zapisu` and
    `brak bezpiecznej ścieżki zapisu w zewnętrznym systemie` instead of
    default audit/adapter/mutation wording.
  - Preview, confirm and impact result panels now use `Ślad bezpieczeństwa`
    instead of `Zdarzenie audytu`.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ActionObjectPanels.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test.
  - Stale wording scan over `ActionObjectPanels.tsx`,
    `ActionObjectPanels.test.tsx` and `App.test.tsx` found old terms only in
    negative assertions.
  - `rtk git diff --check -- apps/dashboard/src/routes/ActionObjectPanels.tsx apps/dashboard/src/routes/ActionObjectPanels.test.tsx apps/dashboard/src/routes/App.test.tsx`
    passed.
  - Focused `App.test.tsx -t "merchant route renders dedicated feed diagnostics"`
    failed before reaching the action safety panel because the route test did
    not find heading `Merchant Center`; do not count it as proof for this slice.
- Content WordPress status language cleanup:
  - Added a shared `contentWordPressPostStatusLabel` so WordPress status
    `draft` renders as `szkic` before it reaches Content Planner or Action
    Detail cards.
  - Content Planner no longer renders `wersja robocza istniejącej treści /
    draft`; tests now expect `wersja robocza istniejącej treści / szkic`.
  - Action Detail WordPress cards now use `Szkic WordPress do sprawdzenia` and
    `Przekazanie` instead of staging-facing labels.
  - `scripts/marketer_language_guard.py` now blocks raw ` / draft`,
    raw draft-status copy and visible staging labels in active surfaces.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 4 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run python -m py_compile scripts/marketer_language_guard.py`
    passed.
  - `rtk git diff --check -- apps/dashboard/src/lib/contentLabels.ts apps/dashboard/src/routes/ContentDiagnosticSurface.tsx apps/dashboard/src/routes/DetailPanels.tsx apps/dashboard/src/routes/ContentDiagnosticSurface.test.ts apps/dashboard/src/routes/App.test.tsx scripts/marketer_language_guard.py`
    passed.
- Brief workflow focus-language cleanup:
  - Brief workflow config no longer exposes `Local Visibility Focus`,
    `Social Publishing Focus`, `Content Growth Focus`, `Feed/Product Focus` or
    generic `Safety Gate` headings.
  - Route config now uses `Lokalna widoczność do sprawdzenia`,
    `Publikacje social do sprawdzenia`, `Priorytety treści do sprawdzenia`,
    `Feed i produkty do sprawdzenia` and `Brama bezpieczeństwa...` labels.
  - Added `BriefWorkflowSurface.test.tsx` to guard the config against returning
    generic Focus/Safety Gate labels.
  - `scripts/marketer_language_guard.py` now blocks those visible headings in
    active surfaces.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/BriefWorkflowSurface.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk git diff --check -- apps/dashboard/src/routes/BriefWorkflowSurface.tsx apps/dashboard/src/routes/BriefWorkflowSurface.test.tsx apps/dashboard/src/routes/App.test.tsx scripts/marketer_language_guard.py`
    passed.
- Generic surface registry fallback removal:
  - Removed the dead generic registry fallback branch from `GenericSurface`
    instead of renaming its headings.
  - Removed disabled registry queries and unused ExpertRule filtering helpers
    from `GenericSurface`.
  - Added `GenericSurface.test.tsx` to prove compact fallback routes do not
    render `Evidence Registry`, `Connector Refresh Runs`, `Connector Status`,
    `Opportunities`, `Actions` or `Expert Rules`.
  - `scripts/marketer_language_guard.py` now blocks registry fallback headings
    in active surfaces.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/GenericSurface.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk git diff --check -- apps/dashboard/src/routes/GenericSurface.tsx apps/dashboard/src/routes/GenericSurface.test.tsx scripts/marketer_language_guard.py`
    passed.
  - Focused `App.test.tsx -t "legacy operating routes do not fall back to registry dumps"`
    was interrupted after a worker timeout fetching `RegistryPanels.tsx`; no
    tests were collected, so it is not proof for this slice.
- Actions route list cleanup:
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/App.test.tsx -t "actions route starts from marketer-facing actions instead of registry dumps" --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 1 test.
  - Runtime proof for expanded `/actions` list returned no stale action-list
    wording hits.
- Opportunities list cleanup:
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/OpportunitiesRoute.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 2 tests.
  - Live API proof for `/api/opportunities` returned 5 decisions with evidence
    and source counts.
  - Browser proof for `/opportunities` was not completed because both browser
    tools hung while waiting for the route render in this session.
- Registry panels condensation:
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/RegistryPanels.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 2 tests.
  - Evidence and source-read lists no longer print raw source/run identifiers or
    raw metric key-value summaries in the card view.
- Knowledge panels language cleanup:
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/KnowledgePanels.test.tsx --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 2 tests.
  - Visible knowledge-panel wording now uses plain Polish for rules and actions
    instead of internal workflow labels.
- Localo metric-label cleanup:
  - `rtk uv run pytest tests/test_api_contracts.py -k "localo_diagnostics" -q`
    passed: 4 tests.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/components/MetricFactChips.test.tsx src/routes/App.test.tsx -t "MetricFactChips|localo route renders workflow-specific blockers and clean metric labels" --reporter=verbose --testTimeout=30000`
    passed: 2 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
  - Browser proof for `/localo`:
    `.local-lab/proof/20260626-localo-metric-label-cleanup/browser/summary.json`
    has zero hits for `metryka WILQ`, raw Localo contract IDs and stale
    dimension wording, while confirming the visible labels `Zmiany konkurencji`,
    `obszar=widoczność konkurencji` and `zakres=aktywne miejsca`.
- Candidate-language cleanup:
  - Active dashboard/API source scan returned no hits for stale visible
    `kandydat*`, legacy dry-run, migration-map, mapping-review or `target_site`
    wording in active marketer-facing sources.
  - `rtk uv run python -m py_compile wilq/briefing/ads_diagnostics.py wilq/actions/content_refresh.py wilq/schemas.py`
    passed.
  - Live WILQ API diagnostics/context proof under
    `.local-lab/proof/20260626-candidate-language-cleanup/api-context/`
    scanned clean for stale candidate/dev/migration wording across Ads,
    Content, Merchant and custom-segments context output.
  - Focused dashboard vitest attempts for touched routes did not reach test
    collection and timed out in the worker fetch/transform phase; do not count
    them as proof.
  - `agent-browser` snapshot attempts hit `Resource temporarily unavailable`;
    do not count browser proof for this slice until the daemon is healthy.
- Marketer language guard:
  - Added `scripts/marketer_language_guard.py` and wired it into
    `scripts/quality.sh` so repeated stale marketer-facing wording becomes a
    fast shared guardrail instead of a chat-only correction.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed after the Merchant
    skill output contract wording cleanup.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
- Skill/eval gate language cleanup:
  - `scripts/verify.sh` now checks the current output labels
    `Akcje do sprawdzenia` and `Sprawdzenie w WILQ` instead of old action
    candidate wording.
  - `scripts/codex_skill_eval.sh` no longer prompts for old action-candidate
    wording or visible ActionObject IDs.
  - `docs/evals/cases/wilq-skill-eval-cases.json` now expects
    `do sprawdzenia w WILQ` in affected skill cases.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
  - `rtk bash -n scripts/verify.sh scripts/codex_skill_eval.sh scripts/quality.sh`
    passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py scripts/skill_hygiene_check.py`
    passed.
- Campaign/custom-segment skill wording cleanup:
  - `wilq-campaign-builder` eval prompt now asks for a campaign proposal and
    `Sprawdzenie w WILQ`, not old candidate/validation wording.
  - `wilq-custom-segments` output contract now describes `Segment do
    sprawdzenia` and proposals from the API contract, not marketer-facing
    candidates.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
  - `rtk rg -n "kandydata|kandydat|kandydaci|kandydatów|kandydatem|Kandydat" docs/evals/cases/wilq-skill-eval-cases.json .agents/skills scripts/verify.sh scripts/codex_skill_eval.sh`
    returned no active hits.
- Codex eval prompt cleanup:
  - Ads eval markers now use `zapis zmian rekomendacji`, not old execution
    wording.
  - `scripts/codex_skill_eval.sh` now asks for `sprawdzenie w WILQ` instead of
    old validation wording in the operator prompt.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
  - `rtk rg -n "wykonanie rekomendacji|gdy walidacja przejdzie|walidacja przejdzie|Walidacja|tylko do sprawdzenia|Dry-run|dry-run|ActionObject IDs|ActionObjecty" docs/evals/cases/wilq-skill-eval-cases.json .agents/skills scripts/verify.sh scripts/codex_skill_eval.sh tests/test_codex_skill_eval_cases.py`
    returned no active hits.
- Content strategist smoke guard cleanup:
  - The content strategist smoke no longer keeps old URL placement names as
    literal sentinels. It now asserts the current content URL allowlist:
    `source_public_url`, `final_canonical_url`, `intended_final_url`,
    `preview_url`.
  - `rtk uv run python -m py_compile .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py`
    passed.
  - `rtk uv run --extra dev ruff check .agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py`
    passed.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
  - `rtk rg -n "target_site|mapping_review|migration_candidate|current_migration_candidate_url|wykonanie rekomendacji|gdy walidacja przejdzie|walidacja przejdzie|ActionObject IDs|ActionObjecty|kandydat" docs/evals/cases/wilq-skill-eval-cases.json .agents/skills scripts/verify.sh scripts/codex_skill_eval.sh tests/test_codex_skill_eval_cases.py`
    returned no active hits.
  - Live `wilq-content-strategist` smoke against `/api/codex/context-pack`
    timed out. `scripts/local_stack.sh status` and `/api/health` were ready, so
    do not count live content context-pack proof for this slice.
- Marketer language guard expansion:
  - `scripts/marketer_language_guard.py` now also scans active eval/prompt
    contract files: `docs/evals/cases/wilq-skill-eval-cases.json`,
    `scripts/codex_skill_eval.sh`, `scripts/verify.sh` and
    `tests/test_codex_skill_eval_cases.py`.
  - The guard now catches the recurring action-candidate, old validation,
    old recommendation execution and old URL-placement phrases that already
    appeared during this cleanup.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run python -m py_compile scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
- Command Center and action-language browser cleanup:
  - Browser text proof for `/command-center` showed no stale candidate/dev
    wording, but did show `akcję WILQ` in the Ads next step.
  - Command Center, Content Planner preview copy, Ads action count labels and
    Ads business-context next step now use `sprawdzenie w WILQ`,
    `zatwierdzenie w WILQ` and `akcje do sprawdzenia` instead of `akcja WILQ`.
  - `wilq/briefing/ads_diagnostics.py` now says the write path requires
    separate WILQ review, preview, confirmation and audit instead of a separate
    WILQ action.
  - `scripts/marketer_language_guard.py` now blocks `akcja WILQ` variants in
    active scanned sources.
  - `rtk uv run python -m py_compile wilq/briefing/ads_diagnostics.py` passed.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run python -m py_compile scripts/marketer_language_guard.py` passed.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/CommandCenterRoute.test.tsx src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    did not fully pass: `ContentDiagnosticSurface.test.ts` passed 2 tests, but
    `CommandCenterRoute.test.tsx` timed out in the vitest worker while fetching
    `lucide-react`.
  - Follow-up `agent-browser open /command-center` failed with `Resource
    temporarily unavailable`; do not count post-change browser proof for this
    slice.
- Action wording guard hardening:
  - Active dashboard/API/skill wording now uses `propozycja w WILQ`,
    `sprawdzenie w WILQ` or `akcje do sprawdzenia` instead of `akcja w WILQ`
    phrasing.
  - Command Center now says `dopasowania WordPress`, not `mapowanie WordPress`.
  - `scripts/marketer_language_guard.py` now blocks `akcja WILQ` and
    `akcja w WILQ` variants across active source and eval/prompt contracts.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile wilq/actions/service.py wilq/briefing/merchant_diagnostics.py wilq/briefing/ga4_diagnostics.py wilq/briefing/tactical_queue.py wilq/briefing/ads_diagnostics.py wilq/briefing/command_center.py scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
  - `rtk uv run python scripts/skill_hygiene_check.py` passed.
  - `rtk uv run --extra dev ruff check scripts/marketer_language_guard.py`
    passed.
- Command Center Polish source-language cleanup:
  - Command Center strict instruction now says `dane źródłowe`, not
    `API/evidence`.
  - Command Center evidence labels now say `Dowody w WILQ`, not `Dowody w API`
    or `WILQ API`.
  - Skill output contracts now say `brakujące dane źródłowe albo dowody`
    instead of `brakujące API/evidence`.
  - `scripts/marketer_language_guard.py` now blocks `API/evidence` and
    `Dowody w API` in active scanned sources.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile wilq/briefing/command_center.py wilq/briefing/marketing_brief.py scripts/marketer_language_guard.py`
    passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "command_center or marketing_brief" --maxfail=1`
    passed: 24 tests.
  - `rtk uv run pytest tests/test_live_contract_smoke.py -q` passed: 3 tests.
  - `rtk uv run pytest tests/test_codex_skill_eval_cases.py -q` passed: 5 tests.
  - Browser proof after `scripts/local_stack.sh restart`:
    `.local-lab/proof/20260626-command-center-polish-language-restarted/browser/command-center-text.txt`
    has no hits for `API/evidence`, `Dowody w API`, `WILQ API`,
    stale action-language, dev-preview or candidate wording.
- Content Planner Polish language cleanup:
  - Content Planner visible copy now says `dane WILQ`, `Szkic`, `punkt
    odniesienia`, `dane po publikacji` and `okna sprawdzenia` instead of
    `WILQ API`, `Draft`, `baseline`, `follow-up` and raw execution wording.
  - Content blocked-claim labels now render `jakość leadów`, `wpływ na
    przychód`, `nowy artykuł bez kontroli spisu treści` and `gwarancja braku
    duplikatów` instead of raw English claims.
  - Content action count now renders Polish plural forms such as `2 akcje`.
  - Live API context for `/api/content/diagnostics` confirmed 3 sections, 5
    decisions, 24 evidence IDs and configured GSC, WordPress, GA4 and Ahrefs
    connectors.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run python -m py_compile wilq/briefing/content_diagnostics.py wilq/briefing/blocked_claim_labels.py`
    passed.
  - `rtk pnpm --dir apps/dashboard exec vitest run src/routes/ContentDiagnosticSurface.test.ts --reporter=verbose --pool=forks --minWorkers=1 --maxWorkers=1`
    passed: 4 tests.
  - Browser proof after `scripts/local_stack.sh restart`:
    `.local-lab/proof/20260626-content-planner-polish-language/browser/content-planner-text.txt`
    has no hits for raw `revenue impact`, `new article without inventory check`,
    `duplicate-free guarantee`, `lead quality`, `2 akcji`, `Draft:`,
    `follow-up`, `baseline`, `credentiali`, `WILQ API`, `target_site`,
    `migration-map` or `mapping-review`.
- Content preflight dashboard gate:
  - Content Planner now reads `/api/content/preflight` and shows a primary
    `Czy można pisać?` panel before the detailed content decision.
  - The panel answers the marketer-facing first question: zachować,
    odświeżyć, scalić, utworzyć or block, plus what remains blocked before a
    draft or WordPress handoff.
  - The dashboard imports `ContentPreflightResponse` from the shared API
    boundary instead of duplicating a local route type.
  - Focused `App.test.tsx -t "content route"` passed: 2 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk git diff --check` passed.
- Content preflight language cleanup:
  - Browser proof showed `sales brief`, `claimy`, `claimów`, `revenue` and
    `lead uplift` leaking into Content Planner text.
  - The producing API/action sources now say `brief`, `ryzykowne obietnice`,
    `obietnica przychodu` and `wzrost leadów` instead of Polglish wording.
  - Content Planner labels now say `Nie wolno twierdzić` / `Nie wolno obiecać`
    instead of `Zablokowane claimy`.
  - `scripts/marketer_language_guard.py` now blocks `sales brief`,
    `claim review`, `revenue albo lead uplift`, `revenue/lead uplift` and
    `Overlap:` in active scanned sources.
  - Live `/api/content/preflight` after stack restart returned refresh-first
    preflight for `https://www.ekologus.pl/europejski-zielony-lad-co-to-takiego/`
    with `preview_url=null`, `draft_allowed=false`,
    `wordpress_draft_allowed=false`, 4 evidence IDs and 2 source connectors.
  - Browser proof:
    `.local-lab/proof/20260626-content-preflight-language-clean/browser/content-planner-snapshot.txt`
    shows `Czy można pisać?`, `brief odświeżenia`, `ryzykownych obietnic` and
    `Wspólne zapytania`; scan found no `sales brief`, `claimy`, `claimów`,
    `claim review`, `revenue albo lead uplift`, `revenue/lead uplift`,
    `Overlap:`, `target_site`, `migration-map`, `mapping-review`, `Dry-run`,
    `ActionObjecty`, `payload` or `WILQ API`.
  - `rtk uv run python scripts/marketer_language_guard.py` passed.
  - `rtk uv run pytest tests/test_api_contracts.py -q -k "content_preflight or content_action_preview or content_draft" --maxfail=1`
    passed: 2 tests.
  - Focused `App.test.tsx -t "content route"` passed: 2 tests.
  - `rtk pnpm --dir apps/dashboard typecheck` passed.
  - `rtk uv run python -m py_compile wilq/briefing/content_diagnostics.py wilq/actions/content_refresh.py scripts/marketer_language_guard.py`
    passed.
  - `rtk git diff --check` passed.
- Ledger condensation:
  - `docs/PROGRESS.md` was reduced back to a short recovery ledger.
  - `rtk git diff --check` passed after the latest cleanup slices.

## Active Gaps

- `PLAN.md` and `docs/goals/001-goal.md` intentionally contain forbidden wording
  examples as policy. They are not active UI/API copy.
- Some internal contract names are still technical. If they reach the marketer
  surface, migrate the contract or view-model in a focused slice rather than
  adding UI-only masking.
- Explicit debug context can expose more detail than default skill context. It
  must remain operator-only and must not become the normal skill prompt surface.
- Some default skill context-packs are still large by operator standards.
  Continue shrinking only where size comes from raw/debug duplication instead of
  useful decision context.
- Dashboard route vitest/typecheck can exceed current timeout before collecting
  tests on this dirty worktree. Treat that as a test-runtime cleanup task, not a
  product proof.
- `agent-browser` can become temporarily unresponsive in this WSL session. When
  it fails, record it as missing browser proof instead of pretending the route
  was checked.
- Real marketer UAT or explicit owner deferral is still required before claiming
  usefulness as proven.
- Final WILQ is still incomplete. Major missing layers include richer content
  inventory, duplicate/canonical checks, sales brief, claim ledger, human
  review flow, WordPress draft handoff, measurement loop,
  workspace/profile contracts and safe write expansion.

## Next Step

1. Continue active-source cleanup from `PLAN.md`, starting with the next active
   marketer-facing dashboard/API/skill surface that still makes Wilku parse
   technical internals.
2. Do not add route-local masking helpers. Fix the producing API, schema,
   view-model, domain source or skill contract.
3. Use real marketer UAT or owner deferral before claiming the cleanup state is
   accepted.
4. Move to `PLANS.md` product layers only after the cleanup state is accepted or
   the remaining documentation/internal-contract debt is explicitly scheduled.
