# Python Runtime And Test Standards

This is the current standard for senior cleanup work under Beads epic
`wilq-seo-c9h9`. It is intentionally short. Product behavior belongs in typed
WILQ API/domain modules, not in giant compatibility files, skill prose or
dashboard copy.

## Runtime Modules

- One module owns one domain concept: connector read, action safety, content
  workflow, knowledge lifecycle, Ads diagnostics, Merchant diagnostics, source
  health or storage.
- Frozen files are compatibility surfaces only: `wilq/schemas/__init__.py`,
  `wilq/actions/service.py`, `tests/test_api_contracts.py`,
  `wilq/briefing/content_diagnostics.py` and `apps/api/wilq_api/main.py`.
- New behavior must land in a domain module first. A frozen file may only
  re-export, route to or delete compatibility code during an extraction slice.
- Route handlers stay thin. They call domain services and return named typed
  response models.
- Connector modules must keep vendor reads redacted and read-only unless a
  write goes through ActionObject validation, preview, review, confirmation and
  audit.
- Repeated nested shapes should get named type aliases or small Pydantic/
  dataclass contracts instead of copy-pasted dictionaries.

## Tests

- Tests prove behavior: evidence/source requirements, blocked unsafe claims,
  freshness handling, ActionObject safety, redaction, Polish operator labels or
  API response contracts.
- Tests must not preserve dead routes, raw implementation wording or dashboard
  card layout unless that text is the product contract.
- A test body over 100 lines needs a split plan or a reason in the related
  Bead. Giant fixtures belong in focused factories named by domain behavior.
- `tests/test_api_contracts.py` is not a place for new assertions. Move new
  domain coverage into focused files under `tests/content`, `tests/connectors`,
  `tests/actions` or a narrow `tests/api_contracts/<domain>.py` module.
- Focused pytest subsets are preferred for slices; full verification is still
  required before goal completion.

## Complexity Gate

Use:

```bash
rtk uv run python scripts/audit_complexity.py --changed --summary --limit 12
```

The clean target is no changed frozen files and no changed-code budget
violations. During extraction work, `--allow-frozen` or
`--allow-budget-violations` may be used only when the Bead names the exact
temporary slice and the diff moves toward smaller domain modules. Do not use
those flags to hide new product behavior in a monolith.

## First Split Order

1. Remove stale route and placeholder truth from active dashboard/docs/tests.
2. Split `tests/test_api_contracts.py` by domain.
3. Split the `wilq/schemas/` package into domain schema modules with compatibility
   exports.
4. Split `wilq/actions/service.py` after schema boundaries are clear.
5. Split Ads diagnostics after shared contracts and tests are smaller.
