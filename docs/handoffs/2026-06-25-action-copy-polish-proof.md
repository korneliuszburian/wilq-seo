# 2026-06-25 Action Copy Polish Proof

## Scope

Hardened shared dashboard action copy that was still leaking technical/product
terms into marketer-facing surfaces.

Touched surfaces:

- `/actions`
- action detail route
- shared action cards
- hidden technical payload toggle

This slice does not rename backend schemas, action IDs, enum values or API
contracts. It only changes how existing action data is rendered for the
operator.

## What Changed

- Marketer-facing labels now use `Akcje do walidacji`, `podgląd zmian`,
  `Wykonanie`, `przegląd człowieka` and `Dane techniczne akcji`.
- Raw action data stays behind the technical toggle and no longer exposes raw
  payload keys before the operator opens it.
- Shared action text from API summaries is mapped away from visible Polglish
  such as `ActionObject`, `Apply`, `payload preview`, `review-only`, `pause`,
  `budget scaling`, `evidence` and `inventory`.
- Blocked claims are shown as plain Polish safety statements where the shared
  panel renders them.

## Browser Proof

Proof directory:

```txt
.local-lab/proof/action-copy-polish-20260625/
```

Final text proof:

```txt
.local-lab/proof/action-copy-polish-20260625/actions.final3.text.txt
```

Final accessibility snapshot:

```txt
.local-lab/proof/action-copy-polish-20260625/actions.final3.snapshot.txt
```

Checked leak query:

```bash
rtk rg -n "\bActionObject\b|\bApply\b|\bapply\b|payload preview|podgląd payloadu|review-only|ev_refresh|Klucze:|\bpause\b|budget scaling|\bevidence\b|\binventory\b|claimować|/treści-planner" .local-lab/proof/action-copy-polish-20260625/actions.final3.text.txt
```

Result: no matches.

Screenshot note: `agent-browser screenshot` hit `CDP command timed out:
Page.captureScreenshot` in this WSL session. Text and accessibility snapshot
proof were captured successfully.

## Verification

Passed:

```bash
rtk pnpm --dir apps/dashboard typecheck
rtk pnpm --filter @wilq/dashboard test -- ActionDetailRoute App OpportunitiesRoute --testTimeout=15000
```

Local stack was managed and ready through:

```bash
rtk scripts/local_stack.sh status
```

## Remaining Product Truth

This closes the focused shared action-copy hardening item. It does not close
real marketer UAT, full content production, WordPress draft creation,
publish/apply automation, Ads optimizer, Merchant feed repair or measurement
loop claims.
