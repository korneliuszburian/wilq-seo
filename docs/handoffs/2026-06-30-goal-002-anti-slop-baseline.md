# Goal 002 Anti-Slop Baseline - 2026-06-30

Scope: first Goal 002 engineering baseline before adding new content production
behavior.

This proof does not claim that the repo is clean. It records the current
complexity and quality baseline so the next slices do not add more behavior to
known monoliths.

## Commands

Passed:

- `rtk uv run python scripts/audit_complexity.py --summary --limit 12`
- `rtk uv run python scripts/audit_complexity.py --changed --limit 5`
- `rtk uv run ruff check scripts/audit_complexity.py scripts/goal_001_completion_check.py`
- `rtk git diff --check`

Baseline failures:

- `rtk uv run ruff check . --statistics`
- `rtk uv run mypy wilq apps/api/wilq_api`
- `rtk pnpm fallow:summary`

## Complexity Baseline

- Python files scanned: 147.
- Python non-empty LOC: 81,481.
- Changed files at audit time: 8.
- Frozen growth files changed: 0.

Frozen growth files were clean:

- `apps/api/wilq_api/main.py`
- `apps/dashboard/src/routes/ContentDiagnosticSurface.tsx`
- `tests/test_api_contracts.py`
- `wilq/actions/service.py`
- `wilq/briefing/content_diagnostics.py`
- `wilq/schemas.py`

Largest Python files:

- `tests/test_api_contracts.py`: 18,902 LOC.
- `wilq/briefing/ads_diagnostics.py`: 7,062 LOC.
- `wilq/actions/service.py`: 4,778 LOC.
- `apps/api/wilq_api/main.py`: 4,632 LOC.
- `wilq/schemas.py`: 4,403 LOC.

Largest Python functions:

- `tests/test_api_contracts.py:10373`
  `test_ads_diagnostics_exposes_live_campaign_metric_facts`: 2,910 lines.
- `.agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py:60`
  `main`: 987 lines.
- `tests/test_api_contracts.py:8782`
  `test_google_ads_vendor_read_uses_oauth_and_search_stream`: 748 lines.
- `wilq/briefing/ads_diagnostics.py:5228` `_ads_decision_queue`: 587 lines.
- `tests/test_api_contracts.py:15076`
  `test_content_diagnostics_exposes_query_page_inventory_queue`: 521 lines.

Highest branch-count Python functions:

- `.agents/skills/wilq-ads-doctor/scripts/smoke_skill_contract.py:60`
  `main`: 285 branches.
- `.agents/skills/wilq-merchant-feed-operator/scripts/smoke_skill_contract.py:63`
  `main`: 118 branches.
- `.agents/skills/wilq-localo-operator/scripts/smoke_skill_contract.py:69`
  `main`: 78 branches.
- `.agents/skills/wilq-custom-segments/scripts/smoke_skill_contract.py:52`
  `main`: 72 branches.
- `.agents/skills/wilq-content-strategist/scripts/smoke_skill_contract.py:364`
  `validate_content_action_preview`: 62 branches.

## Quality Baseline

`rtk uv run ruff check . --statistics` currently reports:

- 66 `E501` line-too-long.
- 1 `I001` unsorted imports.
- 1 `UP037` quoted annotation.

`rtk uv run mypy wilq apps/api/wilq_api` currently reports 5 errors:

- `wilq/actions/content_refresh.py:677`
- `wilq/actions/content_refresh.py:679`
- `wilq/actions/content_refresh.py:681`
- `apps/api/wilq_api/main.py:597`
- `apps/api/wilq_api/main.py:598`

All five are `Any | None` passed where `str` is expected.

`rtk pnpm fallow:summary` currently reports:

- dead files: 0.
- dead exports: 0.
- maintainability average: 93.2.
- duplication: 21.0%.
- clone families: 20.
- clone groups: 77.
- duplicated lines: 2,987.
- functions above complexity threshold: 13.

## Decision

Do not add new content production behavior to frozen files. The next code slice
should either reduce risk through extraction or add new content workflow modules
outside the frozen areas.

## Next Action

Move to behavior-preserving extraction or fix the focused mypy errors only if
they block the next extraction slice. Do not start draft generation before
ContentWorkItem, inventory and ContentPreflight v2 are in place.
