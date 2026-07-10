# Cleanup rebaseline — 2026-07-10

## Fresh evidence

- Worktree clean at `106c567` before this audit slice.
- WILQ metrics API: DuckDB, 95,644 metric facts, 4,469 refresh runs.
- Content queue: blocked; 1 actionable candidate of the required 3.
- Public `ekologus.pl` and dev `ekologus.dev.proudsite.pl` are distinct roles.
  Existing tests block dev URLs as SEO canonicals.
- Complexity still concentrates in Ads diagnostics (6,430 LOC), action service
  (5,989), Ads contract tests (4,971) and content-workflow API (1,425).

## Reconciled c9h9 work

| Bead | Status now | Remaining proof/gap |
| --- | --- | --- |
| `b4kg` schemas | complete | Compatibility facade and domain leaves are in code; do not reopen. |
| `50wa` API mega-test | continue | Extracted leaves exist; finish only from current complexity/test-theatre evidence. |
| `ho41` content workflow | continue | First view is lighter and typed; route remains oversized and existing-draft update is intentionally prepare-only. |
| `jnra` action service | continue | Domain constructors moved, but service remains 5,989 LOC. |
| `kgvy` Ads diagnostics | continue | Several builders moved, but diagnostics remains 6,430 LOC. |
| `pidl` dashboard mega-test | continue | Needs current, route-focused test boundary audit. |
| `0q74` skill smoke harness | continue | Eval evidence is fresh, but scripts remain hotspot-sized. |

## Product priority

The next product proof is not canonical configuration: it is whether a marketer
can act on the single public-page content workbench in 30 seconds with current
signals, blocker and safe dev-draft step. The queue's Ahrefs-only item remains
a business/content decision without a confirmed target, not a public/dev URL
configuration failure.

## Next audit actions

1. Capture a current desktop and mobile `/content-workflow` proof packet and
   record a usefulness score with the live queue state.
2. Reconcile each remaining open c9h9 child in Beads against this ledger;
   close or rewrite stale descriptions before implementation.
3. Select the next implementation slice only after those two checks.
