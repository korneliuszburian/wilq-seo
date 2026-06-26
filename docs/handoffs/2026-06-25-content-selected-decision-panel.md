# Content Selected Decision Panel - 2026-06-25

## Scope

Added a first-screen Content Planner condensation panel for the selected
content decision. The panel is marketer-facing and sits before the full
operator summary, brief cards and diagnostic proof sections.

## Current proof

- Browser route: `http://127.0.0.1:5173/content-planner`
- Proof folder:
  `.local-lab/proof/content-selected-decision-panel-20260625/`
- Captured files:
  - `content-planner-body.txt`
  - `content-planner-snapshot.txt`
  - `content-planner.png`

## What the panel now shows

- Selected topic: `SEO: odśwież lub scal "zielony ład co to"`.
- Current WILQ API metrics: 8 queries, 44 clicks, 1044 impressions, CTR 2.78%.
- Why it matters: WordPress inventory confirms an existing URL, so WILQ points
  to refresh/merge instead of creating a new page.
- Safe next step: review the public URL decision, preserve/refresh/merge mode
  and optional design preview context before any draft or staging handoff.
- Content direction: H1, H2, FAQ and CTA direction from the ActionObject brief
  preview.
- Evidence/source summary: Google Search Console and WordPress Ekologus, 4
  evidence IDs.
- Blocked claims: lead uplift, revenue impact, ranking guarantee, traffic
  uplift, authority improvement and automatic WordPress publish.
- Later measurement: baseline in GSC/WordPress first, then follow-up windows in
  GSC/GA4 only after any draft/staging/publish path is actually approved.

## Domain semantics

The panel now states the core URL rule explicitly:

- `ekologus.pl` and `sklep.ekologus.pl` are source-of-truth and content
  inventory inputs.
- `ekologus.dev.proudsite.pl` is an optional preview/design context,
  not historical metric evidence.

This matters because most content decisions should preserve, refresh or merge
real public content on `ekologus.pl`. WILQ must not treat the dev site as proof
of historical performance, as a content source, or as a final canonical URL.

## Remaining work

- Real marketer UAT is still required or must be explicitly deferred by owner.
- The route body remains long because detailed traceability still exists below
  the panel; this is acceptable for now because the first decision is condensed.
- Merchant is still the next likely condensation target if dashboard UX work
  continues.
