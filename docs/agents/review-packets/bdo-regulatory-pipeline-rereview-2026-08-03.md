# Cumulative re-review prompt — WILQ BDO content pipeline

Review the exact fixed point:

```text
Base: 0cea8eeb4aabbe512f17b74921667554d0452e87
HEAD: c72a6246
Packet wrapper: 73cd37b4 (documentation only)
Branch: feat/regulatory-visible-extraction
```

Do not review this as a generic prompt experiment. Treat WILQ as an API-first
marketing operating system. The acceptance target is one exact, regulatorily
grounded BDO chain:

```text
fresh connector reads
  -> exact planning input and proposal
  -> independent per-requirement draft assurance
  -> immutable draft revision
  -> advisory semantic review
  -> human review required
```

The chain must remain read-only with respect to WordPress and vendors. No
`ActionObject.apply`, publication, deployment or measurement write may be
introduced or inferred from a successful review.

## Exact live evidence

- Work item: `content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`
- Service: `ekologus_service_bdo_reporting`
- Planning input digest: `bcde37bf6ed6068287a70a6b13847bc5d24d8cffeda0206b8eef29572a78f26b`
- Proposal: `content_planning_proposal_2f1047ef9c2c4f7fb00c7191ae5b4436`
- Revision: `content_revision_6b801326be75414186dc4f9f79b05139`
- Revision digest: `d13459d19d50b52e31a9809d8e395b0c25e4275a94db422af56c60d9f191289e`

The transient proof artifacts are under
`docs/agents/runs/delivery-loop/bdo-20260803/` and are evidence only; they do
not represent human approval.

## Required checks

1. Verify the changed-path ledger for the fixed point and identify any
   out-of-scope vendor, WordPress, publication, deployment, measurement or
   ActionObject execution boundary.
2. Verify that production and dev sitemap policies keep product/catalog,
   `sklep.ekologus.pl`, `/sorbent*`, `/sklep*` and `/shop*` out of editorial
   candidates while retaining them as audit inventory. Verify dev service and
   content maps remain eligible.
3. Verify exact planning/revision/proposal digests and source lineage. Missing,
   settling or unverified connector data must remain typed blockers, never
   synthetic metrics.
4. Verify independent assurance: one check per regulatory requirement,
   fail-closed output validation, no substring-only override of missing scope or
   exceptions, and no append after a failed assurance result.
5. Verify semantic review target binding and deterministic guards. The
   behavioral suite must catch all seven controlled mutations:
   missing requirement answer, scope/exception loss, term/procedure change,
   missing CTA, query mismatch, repetition and source-style slop.
6. Verify the fresh unmutated semantic turn is `reviewable` with zero findings,
   while `publish_ready=false`, `human_review_required=true` and
   `action_object_created=false` remain true.
7. Verify the focused gate evidence: semantic API and polling tests, sitemap
   tests, Ruff, complexity audit and `git diff --check`.

## Verdict format

Return `ACCEPT` only if every required check is directly proven at HEAD. For
`REPAIR`, report only concrete reproducible findings with exact path,
reproduction, marketer impact, smallest repair and falsifier. Keep proof gaps
and the absence of human/legal approval separate from production findings.

This packet does not claim live legal correctness, human approval, publication,
SEO outcomes or lead outcomes.
