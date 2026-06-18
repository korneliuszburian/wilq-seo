# Command Center Second Opinion Brief

Last updated: 2026-06-18.

## Context

WILQ is an API-first Marketing Operating System for Ekologus. The marketer is
Polish, so marketer-facing outputs must be in Polish with Polish diacritics.

The WILQ API is canonical. Dashboard, Codex skills, hooks, workflows, expert
rules, opportunities and actions must use the same API contracts. Codex can
reason and operate, but it must not invent metrics.

Current repo:

```txt
/home/krn/coding/krn/active/wilq-seo
```

Read first:

```txt
AGENTS.md
docs/goals/001-goal.md
docs/handoffs/dashboard-audit-active-slice.md
docs/infra/001.md
docs/architecture/bdos-class-wilq-operating-system.md
docs/research/wilq-marketing-source-map.md
.agents/skills/
apps/dashboard/src/routes/App.tsx
wilq/briefing/
wilq/actions/
wilq/connectors/
```

## Problem To Solve

Command Center currently risks becoming a dump of:

- connector readiness,
- raw evidence IDs,
- raw metric facts,
- GSC query/page rows,
- GA4 landing/source rows,
- Merchant issue rows,
- technical blockers.

That is not useful enough for a marketer. The user expects something closer to
BDOS: a practical operating cockpit where data is condensed into decisions,
safe actions and Codex-assisted workflows.

## Current Data Sources

Configured/live or partially live sources include:

- Google Ads: campaign-level metric facts exist. Search terms, CPA, ROAS,
  recommendations and mutation paths require more explicit read/action
  contracts.
- Google Merchant Center: product/feed facts and issue counts exist.
- Google Search Console: query/page facts exist.
- GA4: landing/source/campaign facts exist; ROAS/revenue/conversion-drop claims
  are blocked unless conversion evidence exists.
- WordPress ekologus.pl/sklep: inventory exists and should prevent duplicate
  content work.
- Ahrefs: aggregate authority/rank context exists; deeper gap workflows need
  richer evidence.
- Localo: API token and org ID are configured, but Localo is blocked until OAuth
  access token yields live local visibility evidence.
- LinkedIn/Facebook: publishing is permission-gated. Drafting can be
  prepare-only from WILQ evidence; publishing cannot be claimed.

## Product Question

Given the available sources and Codex skills, what should WILQ show and do so
that a Polish marketer gets a real advantage?

We need concrete answers to:

1. What exactly should Command Center show on the first screen?
2. What should be removed from Command Center and moved to dedicated routes?
3. How should WILQ condense Ads, GA4, Merchant, GSC, Ahrefs, Localo and
   WordPress facts into decisions?
4. How should Codex skills become the useful operating layer, not just a prompt
   pack?
5. What API contracts are missing for skills to reliably call WILQ and return
   Polish, evidence-backed answers?
6. What should be the next 5 implementation slices, each with acceptance checks?

## Current Working Hypothesis

Command Center should become a decision cockpit, not a data dashboard.

Each top card should answer:

- Co widzę?
- Co to znaczy?
- Co zrobić teraz?
- Czego nie wolno twierdzić?
- Jak Codex może pomóc?

Example card shape:

```txt
Decision: Przejrzyj produkty z problemami w Merchant Center
Why: WILQ sees product/feed issues from Merchant evidence.
Codex action: Run wilq-merchant-feed-operator to prepare a review-safe issue queue.
Evidence: 2-3 sample IDs plus count, not 12 raw IDs in the card.
Blocked claims: approval restored, revenue recovered, automatic feed edit.
CTA: Otwórz Merchant / Uruchom Codex review / Waliduj ActionObject.
```

## Current Concerns

- The UI still over-explains evidence and internal mechanics instead of telling
  the marketer what to do.
- Some sections duplicate intent: operator brief, action plan, tactical queue
  and metric facts all compete for the same first-screen space.
- Raw metric facts and query/page rows are useful for diagnostics but not as
  first-screen decision cards.
- Codex skills exist, but the dashboard does not clearly expose how Codex uses
  WILQ API context to produce better Polish answers than plain Codex.
- The product should not add MCP/server architecture until the REST/API +
  skills loop proves real usefulness.

## Desired Output From Reviewer

Please produce a blunt, implementation-ready recommendation:

1. Ideal Command Center information architecture.
2. Exact first-screen sections and card fields.
3. Which existing sections/components to delete, demote or keep.
4. Codex skill integration model:
   - what prompt/operator action each card should expose,
   - which WILQ endpoint/context pack each skill should call,
   - what output contract should be enforced,
   - how to prove Polish, evidence-backed outputs in non-interactive Codex.
5. Data-to-decision mapping for:
   - Google Ads,
   - GA4,
   - Merchant Center,
   - GSC + WordPress,
   - Ahrefs,
   - Localo,
   - social drafting.
6. Next 5 implementation slices with tests/proof.

Do not recommend generic dashboards, generic LLM advice, or fake metrics.
Everything must be API-backed, evidence-backed, Polish, and safe by default.
