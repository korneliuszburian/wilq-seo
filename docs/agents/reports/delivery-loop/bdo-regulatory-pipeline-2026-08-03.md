# BDO regulatory content pipeline — cumulative packet

Status: `needs review`; this is an owner-facing packet, not human legal approval.

## Fixed point

- Isolated implementation branch: `feat/regulatory-visible-extraction`
- Base used for the current repair slice: `0cea8eeb4aabbe512f17b74921667554d0452e87`
- Current HEAD: `c72a6246`
- Latest cohesive commits:
  - `214c944c` — per-constraint regulatory assurance context
  - `adf2e0b3` — semantic reviewer detects editorial/source artifacts
  - `3a4539cf` — queued semantic review is visible before worker preflight
  - `7164e837` — stale semantic runs become terminal after deadline
  - `102e89cd` — classify commerce sitemap maps and exclude them from editorial catalog
  - `cf7c4e1b` — run independent draft-assurance checks concurrently and allow a bounded 15-minute run
  - `7e2dbea7` — treat dev editorial maps as eligible and legacy shop/sorbent URLs as commerce-only audit inventory
  - `9ec01b0a` — make semantic reviewer failure-mode mapping explicit
  - `00bb3337` — add deterministic CTA, repetition and source-note guards
  - `2a958a9b` — bind semantic context targets to the exact revision section IDs
  - `1df3a3e2` — fail closed when regulated sections lose source-fact coverage
  - `a3c2e81a` — keep active semantic polling proof aligned with the current timeout contract
  - `52d23c15` — record the final unmutated semantic turn
  - `9260d8e1` — close the cumulative focused proof gate
  - `68bac70d` — add the bounded cumulative re-review prompt
  - `c72a6246` — align the packet with the final review head
  - `68bac70d` — add the bounded cumulative re-review prompt

## Exact live BDO lineage

- Work item: `content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`
- Service: `ekologus_service_bdo_reporting`
- Planning input digest: `bcde37bf6ed6068287a70a6b13847bc5d24d8cffeda0206b8eef29572a78f26b`
- Planning digest: `0c3515c3ddf720d1bc51ce7d26fbdf2530c7bd62d34e633193c728d093d76f40`
- Proposal: `content_planning_proposal_2f1047ef9c2c4f7fb00c7191ae5b4436`
- Initial-draft run: `codex_content_initial_draft_b5a5b878513748e890949fbf662b341f`
- Exact revision: `content_revision_6b801326be75414186dc4f9f79b05139`
- Content digest: `d13459d19d50b52e31a9809d8e395b0c25e4275a94db422af56c60d9f191289e`

The revision is `unreviewed`, `publish_ready=false`, and has not been sent to WordPress.

## Evidence state at planning

- WordPress and GSC: `used`; GSC carries 8 exact query rows and evidence IDs.
- GA4: `blocked`, `settling/unverified`; no GA4 values are treated as used planning evidence.
- Google Ads, Ahrefs, Keyword Planner: explicit `missing`; no synthetic metrics are added.
- Merchant, Localo, social: `not_applicable` for this page.
- Regulatory coverage: 8/8 requirements, 10 approved source facts in the current planning input.
- Public sitemap audit: 808 URLs total (posts 116, pages 24, products 564, training 17, training-close 2, career 4, category 9, product_cat 72). Product and product-category URLs remain in raw connector evidence but are marked `editorial_eligible=false`. Legacy `/sorbent*`, `/sklep*`, `/shop*` paths and the `sklep.ekologus.pl` host are also commerce-only; the dev sitemap's service/content maps are explicitly editorial while its taxonomy maps remain audit-only. This keeps outdated shop/sorbent inventory visible for audit without allowing it into new-page/editorial decisions.

## Runtime proof

- Earlier assurance attempts blocked real defects (`overbroad_claim`, `insufficient_source_alignment`) and one generated draft failed the deterministic full-name assertion without persisting a revision.
- The current per-constraint assurance run completed in the new bounded parallel executor and created the exact revision only after those checks passed.
- Focused sitemap, semantic API, semantic polling and deterministic guard tests pass together; Ruff, complexity audit and `git diff --check` also pass for the changed paths.
- A queued semantic POST now becomes visible immediately through GET with the same run ID.
- A stalled semantic run is terminalized as `failed` after the configured deadline; it cannot remain `generating` forever.
- The final in-memory behavioral suite uses the exact live revision/proposal/planning digest and 7 controlled mutations. All 7 transport turns completed; every mutation became `needs_changes` with exact revision-section or CTA/whole-document targets. The transient result is retained in `docs/agents/runs/delivery-loop/bdo-20260803/semantic-mutation-suite-final.json` (ignored runtime artifact, not product state).

## Semantic review state

The fresh semantic turn after target binding and deterministic guards is `reviewable` with 9 dimensions and 0 findings for the same exact revision/planning digest. Its transient result is retained in `docs/agents/runs/delivery-loop/bdo-20260803/semantic-review-final.json`; the prior persisted review remains immutable and is not overwritten. Human review remains required; `reviewable` is not legal or publication approval.

## Runtime configuration

The running API reports 9/12 configured connectors: Google Ads, Search Console, GA4, Merchant Center, Ahrefs, Localo, both WordPress sites and Codex. LinkedIn and Facebook remain unconfigured; Google Sheets is disabled. No credential values are copied into this packet.

## Remaining acceptance work

1. Obtain separate human review for legal/content accuracy. `reviewable` is not approval.

## Boundaries

No changed path in this slice adds a vendor write, WordPress mutation, publication, deployment, measurement write, or ActionObject apply. The only writes are local immutable workflow/review state and Codex run audit records.

This packet does not prove live vendor freshness, legal approval, publication, SEO outcomes, or lead outcomes.
