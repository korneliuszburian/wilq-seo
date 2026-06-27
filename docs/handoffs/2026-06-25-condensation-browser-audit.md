# WILQ condensation browser audit - 2026-06-25

Superseded note, 2026-06-27: Content Planner notes in this audit predate the
product correction that `ekologus.pl` is the public canonical content home and
dev preview hosts are optional design/staging context only. Treat any
`target migration`, mapping-state or staging-handoff wording below as
historical audit language, not current implementation guidance.

Scope:

- Fresh local WILQ API proof after stack start.
- Fresh `agent-browser` walkthrough of the core demo path:
  `/command-center`, `/merchant`, `/content-planner`, `/ads-doctor`, `/ga4`.
- Goal: identify what must be condensed so a marketer can decide what to do
  without reading raw diagnostics.

Runtime proof:

- Stack start: `rtk scripts/local_stack.sh start`
- API health: `GET /api/health` returned `{"status":"ok","service":"wilq-api"}`.
- Command Center API: `GET /api/dashboard/command-center` returned
  `primary_next_step="Najpierw otwórz /merchant i przejrzyj kolejkę problemów feedu."`,
  `blocker_count=2`, `tactical_item_count=24`.
- Endpoint timings during audit:
  - Merchant diagnostics: HTTP 200, about 7.95s.
  - Content diagnostics: HTTP 200, about 7.66s.
  - Ads diagnostics: HTTP 200, about 2.12s.
  - GA4 diagnostics: HTTP 200, about 6.66s.

Proof artifacts:

- `.local-lab/proof/condensation-browser-audit-20260625/command-center.text.txt`
- `.local-lab/proof/condensation-browser-audit-20260625/merchant.text.txt`
- `.local-lab/proof/condensation-browser-audit-20260625/content-planner.text.txt`
- `.local-lab/proof/condensation-browser-audit-20260625/ads-doctor.text.txt`
- `.local-lab/proof/condensation-browser-audit-20260625/ga4.text.txt`
- Matching `.snapshot.txt`, `.open.txt` and `.wait.txt` files are in the same
  directory.

Note: full-page screenshot capture timed out on long routes. Text and snapshot
proof were captured after API load and are enough for this condensation audit;
do not use this handoff as visual pixel proof.

## Route measurements

| Route | Text size | Snapshot lines | Headings | Interactive refs | Readout |
| --- | ---: | ---: | ---: | ---: | --- |
| Command Center | 4,550 chars | 27 | 7 | 19 | Best condensed start screen. |
| Merchant | 19,388 chars | 59 | 21 | 32 | Useful, but too much review/proof detail after first decision. |
| Content Planner | 16,723 chars | 76 | 21 | 42 | High value, but needs a selected decision/brief first. |
| Ads Doctor | 61,885 chars | 201 | 54 | 90 | Too dense; primary target for condensation. |
| GA4 | 9,752 chars | 46 | 15 | 24 | Clearest diagnostic route; keep pattern. |

## Current API-backed marketer readout

Command Center already answers the first question well:

- First next step: open Merchant and review the feed issue queue.
- It shows 4 decisions, 2 blockers and 7 source groups.
- It gives marketer copy before technical detail.

Merchant:

- Shows 10,776 products, 19 problems and 7 evidence items.
- The first queue item is understandable: `landing_page_error / n:link`.
- It correctly says issue occurrences are not unique product count.
- Problem: review payload/contract/action sections appear too early and repeat
  the same apply-blocked story many times.

Content Planner:

- Shows 10 query/URL pairs, 11 GSC-to-WP matches and 19 Ahrefs-to-WP overlaps.
- The top item is strong: Zielony Lad refresh/merge with 666 impressions,
  24 clicks, CTR 3.60% and average position 1.4.
- It correctly treats target migration as review, not publish.
- Problem: a marketer needs one selected brief/review item first; Ahrefs,
  mapping, staging and measurement details should sit below a condensed first
  decision.

Ads Doctor:

- Shows 98 clicks, 2,303 impressions, 160.46 PLN cost, 2 conversions,
  18 campaigns, 50 search terms, 4 recommendations and 5 budgets.
- It correctly blocks CPA, ROAS, wasted-budget, scaling, budget change,
  recommendation apply and campaign mutation claims.
- Problem: the route is still a diagnostic wall: 61k text chars, 54 headings,
  90 interactive refs and repeated ActionObject review panels. The existing
  "Najpierw sprawdź w Ads" strip is useful, but the first-screen hierarchy is
  still not condensed enough.

GA4:

- Shows measurement issues first and clearly separates `(not set)` from
  campaign/landing blame.
- Shows 79 active users, 420 events and 1.96% engagement for the first
  `(not set)` row.
- Correctly blocks conversion rate, ROAS, revenue and profitability claims.
- This is the best model for other diagnostic routes: problem first, why it
  matters, safe next step, blocked claims, then technical details.

## Condensation tasks

1. Ads Doctor must get a real top condensed decision panel:
   - one primary decision,
   - why it matters,
   - safe next action,
   - blocked claims,
   - missing inputs,
   - evidence summary,
   - measurement/impact plan.
   The full campaign/search-term/recommendation/action matrices should move
   below collapsible sections.

2. Content Planner should start with one selected content review item:
   - likely Zielony Lad or BDO refresh/merge,
   - source evidence,
   - target mapping state,
   - H1/H2/FAQ/CTA direction,
   - missing evidence,
   - blocked claims,
   - mapping review action.
   Ahrefs, migration, staging and measurement details should remain available
   but not lead the screen.

3. Merchant should keep the first queue item and product/problem counts, then
   collapse repeated contract/payload/apply-blocked sections behind technical
   details.

4. GA4 should be the reference pattern for diagnostic condensation. Keep
   measurement issues first and continue formatting engagement as readable
   percentages.

5. Command Center should stay the first screen. Do not replace it with registry
   views. It already gives the correct daily path.

## Product rule extracted

Every marketer-facing route needs one condensed decision surface before details:

```text
decision -> why it matters -> safe next action -> blocked claims -> evidence summary -> missing inputs -> measurement plan
```

Raw evidence IDs, ActionObject IDs, payload keys, connector internals and
technical contracts remain required for traceability, but should be detail-level
material unless the marketer explicitly opens the technical drawer.
