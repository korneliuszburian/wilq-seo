# Operator UAT Findings - 2026-06-24

Scope: simulated marketer walkthrough by the operator, not real Ekologus
marketer feedback. Real marketer UAT remains open.

Proof directory:
`.local-lab/proof/dashboard/marketer-uat-20260624/`

## Route Results

- Command Center: pass after CTA fix. It shows four daily decisions and now
  links directly to `Otwórz Merchant`, `Otwórz Content Planner`, `Otwórz GA4`
  and `Otwórz Ads Doctor`. Before the fix, the same domain routes were labelled
  `Otwórz działanie`, which made the first step feel like an Action detail
  instead of a domain workflow.
- Global navigation: pass after nav fix. The sidebar now exposes the core
  domain workflow links `Merchant`, `Content`, `Ads Doctor` and `GA4` before the
  registry/admin routes, so a marketer can return to the main demo path without
  knowing internal route names.
- Merchant: pass for review-first demo. It clearly separates reported issue
  occurrences from unique products, shows sample product IDs/titles when
  available, and blocks feed write, approval recovery, product ROAS and revenue
  recovery claims.
- Content Planner: pass for strongest current demo value. It exposes GSC/WP
  refresh or merge candidates, target context for `ekologus.dev.proudsite.pl`,
  canonical/duplicate gates, forbidden claims and the new
  `missing_target_inventory` blocker for old-to-new migration candidates.
- Ads Doctor: pass as Ads review cockpit, not optimizer. It shows campaign,
  search-term, recommendation, negative keyword, segment and target guardrail
  queues while blocking CPA/ROAS/wasted-budget/apply claims without target and
  audit contracts.
- GA4: pass as measurement-quality gate. It makes `(not set)` and tracking gaps
  a measurement problem, not a campaign or landing-performance verdict.

## Main Product Finding

The current dashboard gives a real review/planning boost, especially for
Content Planner and Merchant. It is not yet a self-running execution OS. The
largest remaining demo risk is not missing route count; it is whether a real
marketer understands the review-only boundaries and can choose one next action
without developer narration.

## Follow-Up Tasks

- Run the same script with the actual marketer and record pass/fail per route.
- Keep Command Center domain CTAs; do not regress to generic action wording.
- Keep core domain navigation visible before registry routes.
- Continue content depth through old-to-new dev-site mapping, not publish/apply.
- Treat Social, Demand Gen, Knowledge and deeper BDOS automation as deferred
  unless the core demo path regresses.
