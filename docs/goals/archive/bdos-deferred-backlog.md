# Deferred BDOS-Class Backlog

Status: archived backlog, not the active Goal 001 queue.
Last updated: 2026-06-24.

This file preserves important work that should not be lost while Goal 001 stays
small and demo-focused. Move an item back into `docs/goals/001-goal.md` only
when it becomes the next active slice or directly unblocks the Ekologus demo.

## Product Bar

BDOS-class WILQ means an agency-grade marketing operating system:

- many accounts/clients managed from one place,
- Google Ads, GA4, GSC, Merchant, Ahrefs, Localo/GBP, WordPress and social
  evidence joined into decisions,
- Polish marketer workflows that turn metrics into concrete actions,
- safe write paths with `dry_run -> preview -> confirm -> audit`,
- expert knowledge condensed into structured rules/cards,
- Codex skills and subagents using typed WILQ API contracts,
- no invented metrics, no prompt-only business logic and no unsafe apply.

## Deferred Workstreams

1. **Multi-client and agency operations**
   - Client/account registry, per-client configuration and credential source
     labels without leaking secrets.
   - Per-account folders for briefs, audit history, reports, mutation logs and
     client business context.
   - Cross-account daily check, monthly review, alerting and role/permission
     model.
   - Agency branding for reports and labels after Ekologus works deeply.

2. **Google Ads optimizer depth**
   - Approved/live Keyword Planner enrichment and forecast/audience-size reads.
   - Change-history rows plus before/after performance windows for change
     impact review.
   - Derived KPI contracts for CPA, ROAS, profit, budget pacing and wasted
     budget that include currency, attribution window, margin and target
     guardrails.
   - Search-term safety: keyword match context, 90-day safety check, negative
     keyword payload preview and apply audit.
   - Recommendations review and reranking with safe apply only after preview,
     confirm and audit.
   - Custom segment and campaign builder apply path with payload preview,
     SafetyLimits and partial-failure handling.

3. **Merchant and product performance**
   - Historical price snapshots with real price changes.
   - Before/after product performance windows joined across Merchant, Ads and
     GA4 item facts.
   - Product-level ROAS/profitability only after matching product performance,
     cost, revenue and margin contracts exist.
   - Richer sample product previews when vendor APIs expose safe product IDs,
     titles, issue context and candidate supplemental-feed fields.
   - Feed writes remain blocked until product data mutation contracts, dry-run,
     preview, confirm and audit exist.

4. **GA4, attribution and ecommerce diagnostics**
   - Attribution and conversion-drop verdicts only after history, source/cost
     and conversion context exist.
   - Landing/source/campaign quality decisions joined with Ads, GSC and
     WordPress inventory.
   - Ecommerce/item diagnostics joined with Merchant and Ads product state.
   - Tracking-quality workflow that separates measurement blockers from
     marketing performance claims.

5. **GSC, Ahrefs, WordPress and content intelligence**
   - Fresh Ahrefs gap reads and stronger cross-source scoring.
   - Content decay, cannibalization, near-top opportunity and duplicate/canonical
     contracts.
   - Target-site migration fields for new pages: target URL, page type, source
     URL, canonical source, rewrite status and review state.
   - Content generation pipeline: evidence pack, intent cluster, brief,
     draft/rewrite preview and review ActionObject.
   - Content output evals that judge usefulness of a brief, not only JSON
     shape.

6. **Localo, GBP and local visibility**
   - Keep current read-only facts for place inventory, rankings, GBP visibility,
     competitor visibility and reviews.
   - Add `local_tasks` only if Localo exposes a side-effect-free read contract.
   - GBP posts, review replies, task apply and visibility uplift claims require
     explicit evidence, preview, validation and audit.
   - Local competitor and review workflows must show blocked claims when
     ranking/uplift evidence is absent.

7. **Social drafting and publishing**
   - Evidence-backed LinkedIn/Facebook drafts from Ads/GSC/GA4/Merchant/content
     facts.
   - Page/org permission contracts, draft preview, confirm and audit before any
     publishing.
   - Publishing stays blocked until social connector permissions and safety
     gates are implemented.

8. **Knowledge compiler and research memory**
   - Source-ingestion contract: source URL/file, author/vendor, date checked,
     claim, domain, confidence, freshness, allowed use, forbidden overclaims and
     linked rule/card IDs.
   - First knowledge batches: Ads optimizer/safety, Merchant feed diagnostics,
     GA4 measurement/ecommerce, GSC/content, Localo/GBP and Ahrefs gap analysis.
   - Promote only high-confidence material into `wilq/expert/**` or
     `wilq/knowledge/**`; raw research stays out of dashboard and skill prompts.
   - Evals must prove selected rules/cards affect a decision or block an unsafe
     claim.
   - Do not add vector DB/memory until source lineage, confidence, freshness and
     rule/card promotion are working.

9. **Codex skills, prompts and subagents**
   - Keep skills as small operator workflows over WILQ API.
   - Dashboard prompt cards must be Polish, skill-specific, evidence-scoped and
     include source connectors, evidence IDs, ActionObject IDs and blocked-claim
     instructions.
   - Run manual and non-interactive eval for every skill after the domain API
     contract is strong enough.
   - Upgrade evals from format/API checks to decision-quality checks.
   - Use subagents for independent audits and disjoint implementation slices;
     merge findings into one typed API/view-model plan before editing shared
     files.

10. **Dashboard, performance and frontend quality**
    - Keep Command Center as decision cockpit, not connector registry or raw
      metric dump.
    - Route-by-route marketer audit for `/command-center`, `/ads-doctor`,
      `/merchant`, `/content-planner`, `/ga4`, `/localo`, `/actions`,
      `/opportunities`, `/knowledge` and `/settings`.
    - Shared route data boundaries so Command Center, brief and drilldowns do
      not independently request and format the same heavy surfaces.
    - Extract large frontend modules only when it improves velocity,
      reviewability, route tests or browser QA.
    - Performance work must be based on fresh latency/duplicate-aggregation
      evidence, not aesthetics.

11. **Release, production and monitoring**
    - Fixture tests assert exact values; live smokes assert contract state,
      freshness, nonempty expected facts and honest blockers.
    - Smaller pre-demo gate: targeted API tests, targeted dashboard route tests,
      touched skill smoke/eval, secret redaction check and one browser
      walkthrough.
    - Production gate: full `scripts/verify.sh`, API health, dashboard build,
      skill smokes/evals, security gate and live read-only connector checks.
    - Operational alerts for stale connectors, missing expected facts, unsafe
      apply attempts and secret leakage.

## Promotion Rule

Do not copy this whole backlog back into Goal 001. Promote one item at a time
only when it has:

- a typed API/view-model owner,
- an evidence source or explicit blocker,
- a focused verification surface,
- a reason it improves the Ekologus demo or the next BDOS-class milestone.
