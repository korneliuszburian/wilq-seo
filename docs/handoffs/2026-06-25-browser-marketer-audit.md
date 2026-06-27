# Browser Marketer Audit - 2026-06-25

Superseded note, 2026-06-27: Content Planner notes in this audit predate the
product correction that `ekologus.pl` is the public canonical content home and
dev preview hosts are optional design/staging context only. Treat any
`target-site`, `migration`, mapping-map or staging-handoff wording below as
historical audit language, not current implementation guidance.

Scope: objective pass through the core demo route with `agent-browser`:

`/command-center -> /merchant -> /content-planner -> /ads-doctor -> /ga4`

Proof directory:

`.local-lab/proof/browser-marketer-audit-20260625/`

This audit checks marketer usefulness and information density. It does not
replace real marketer UAT.

## Browser Evidence Summary

| Route | Body chars | Lines | Headings | Cards/sections | Scroll height | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `/command-center` | 4,351 | 155 | 7 | 6 | 2,280 | Usable first screen |
| `/merchant` | 18,982 | 348 | 21 | 19 | 9,392 | Useful but too much drilldown |
| `/content-planner` | 43,079 | 612 | 19 | 17 | 14,368 | Strong value, overloaded |
| `/ads-doctor` | 60,163 | 1,082 | 29 | 43 | 22,714 | Too dense for unassisted demo |
| `/ga4` | 9,490 | 269 | 15 | 13 | 5,936 | Clearest diagnostic route |

Viewport during audit: 1440x1000.

## Direct Verdict

Command Center is the only route that currently feels like a marketer cockpit.
It gives clear daily decisions, domain CTAs and blocked-claim boundaries.

The domain routes are evidence-rich, but they still behave too much like
auditable diagnostic ledgers. That is valuable for AI-engineering operators and
for proof, but it creates scanning cost for a marketer. The product risk is not
"does it render"; it is "can the marketer find the next action before reading
three layers of contracts and blockers".

## What To Show The Marketer

Show only this path:

1. `Command Center`: pick one daily decision.
2. `Merchant`: show that feed issues are review queues, not automatic fixes.
3. `Content Planner`: show one BDO or Zielony Lad refresh/merge decision with
   target-site mapping blockers.
4. `Ads Doctor`: show the "Najpierw sprawdź w Ads" strip, not the full page.
5. `GA4`: show `(not set)` as measurement QA, not campaign blame.

Do not walk the marketer through every card on Ads, Content or Merchant. That
will make the system look heavy even though the underlying evidence is useful.

## Route Findings

### Command Center

Status: `usable`.

What works:

- It states the primary next step.
- Four daily decisions are understandable.
- CTAs go to the right domain routes.
- Guardrails are visible without becoming the whole page.

What still adds noise:

- Repeated "Codex prompt" strips may be useful for the operator, but they are
  secondary for a marketer. They should be collapsed if the marketer does not
  actively use Codex from the dashboard.
- The bottom source summary is fine as a footer, not as a decision surface.

### Merchant

Status: `useful but too much drilldown`.

What works:

- The first Merchant card correctly explains that report occurrences are not
  unique products.
- Sample product IDs/titles are helpful because they make the feed issue real.
- The page blocks approval recovery, revenue recovery and feed writes.

What is too much:

- It mixes issue review, Ads product-state mapping, price-impact readiness,
  sample readiness, product performance readiness and proof sections on one
  long page.
- The repeated "Podglad review / Kontrakt / Zakres / Apply/API" blocks are
  operator proof, not marketer decision material.

Recommended cut for demo:

- First screen: one "Co sprawdzic teraz" queue with 3 items max.
- Keep product samples inline only for the selected queue item.
- Move contract/payload/proof sections behind a technical drawer.

### Content Planner

Status: `strongest value, overloaded`.

What works:

- It is the strongest route for Ekologus because it connects GSC, WordPress,
  Ahrefs and the new-site target context.
- It correctly prevents create/publish claims before mapping and duplicate
  review.
- BDO/Zielony Lad refresh/merge decisions are easy to explain as marketing work.

What is too much:

- 43k characters and 14 viewport heights is too much for a content planning
  session.
- The page shows full Ahrefs review, multiple content decisions, migration
  blockers, draft readiness, staging preview and measurement preview together.
- Target-site gate text repeats the same blocker in several forms:
  migration candidate missing, candidate not confirmed, alternatives missing,
  manual mapping required.

Recommended cut for demo:

- Add a "Dzisiejszy brief do review" top panel with one selected decision:
  BDO or Zielony Lad.
- Keep only: source URL, target candidates, decision type, H1/H2/FAQ/CTA,
  missing evidence, forbidden claims, next human input.
- Collapse Ahrefs gaps, full mapping map, staging handoff and measurement plan
  below "Szczegoly techniczne".

### Ads Doctor

Status: `too dense for unassisted demo`.

What works:

- It is honest: no CPA/ROAS/wasted-budget/apply claims without contracts.
- It has a useful "Najpierw sprawdz w Ads" strip.
- It separates ready review areas from blocked conclusions.

What is too much:

- 60k characters, 29 headings, 43 sections/cards and 22 viewport heights.
- The useful start strip appears after a long readiness explanation and many
  ready/blocked cards.
- The same blocked concepts repeat many times: CPA, ROAS, wasted budget,
  budget changes, recommendations, exclusions, Keyword Planner, change history.

Recommended cut for demo:

- Move "Najpierw sprawdz w Ads" above the full ready/blocked matrix.
- Limit first screen to 3 review tasks:
  campaign triage, search terms, recommendations/budget.
- Put the full blocked-claims matrix and action previews behind a proof drawer.

### GA4

Status: `clearest diagnostic route`.

What works:

- It clearly teaches that `(not set)` is measurement QA, not campaign blame.
- It is short enough compared with Ads/Content.
- It blocks ROAS/revenue/profitability without being too abstract.

What is too much:

- It repeats per-row metric tiles for each `(not set)` item.
- Raw values like `0.019608` engagement are not marketer-friendly.

Recommended cut for demo:

- Show the three measurement problems as one grouped issue first.
- Format engagement as a percentage everywhere.
- Keep row-level details available only after selecting a row.

## Priority Tasks From This Audit

1. `P0 demo UX`: Move Ads "Najpierw sprawdz w Ads" to the top of Ads Doctor
   and make it the primary first-screen surface.
2. `P0 content UX`: Add a single selected content decision panel at the top of
   Content Planner for BDO/Zielony Lad, with the rest collapsed.
3. `P1 merchant UX`: Collapse Merchant contract/payload/proof blocks behind a
   technical details drawer.
4. `P1 GA4 UX`: Group `(not set)` rows into one measurement QA block and hide
   row metric tiles until drilldown.
5. `P1 operator UX`: Collapse Codex prompt strips unless the marketer explicitly
   uses them during UAT.

## What Not To Do

- Do not add another route.
- Do not add more evals before fixing first-screen density.
- Do not hide blocked claims completely; move them behind progressive
  disclosure.
- Do not claim Ads optimizer, feed repair, publishing, uplift, CPA/ROAS or
  revenue recovery.
