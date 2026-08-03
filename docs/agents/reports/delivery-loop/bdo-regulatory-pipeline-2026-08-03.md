# BDO regulatory content pipeline — cumulative packet

Status: `needs review`; this is an owner-facing packet, not human legal approval.

## Fixed point

- Isolated implementation branch: `feat/regulatory-visible-extraction`
- Base used for the current repair slice: `0cea8eeb4aabbe512f17b74921667554d0452e87`
- Current HEAD: `00bb3337`
- Latest cohesive commits:
  - `214c944c` — per-constraint regulatory assurance context
  - `adf2e0b3` — semantic reviewer detects editorial/source artifacts
  - `3a4539cf` — queued semantic review is visible before worker preflight
  - `7164e837` — stale semantic runs become terminal after deadline
  - `102e89cd` — classify commerce sitemap maps and exclude them from editorial catalog
  - `cf7c4e1b` — run independent draft-assurance checks concurrently and allow a bounded 15-minute run
  - `7e2dbea7` — treat dev editorial maps as eligible and legacy shop/sorbent URLs as commerce-only audit inventory
  - `9ec01b0a` — make semantic reviewer failure-mode mapping explicit
  - `00bb3337` — add deterministic CTA, query-intent, repetition and source-note guards

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
- Focused sitemap tests: 4 passed; focused semantic API/guard tests include the deterministic quality guard falsifier. Ruff, complexity audit and `git diff --check` pass for the changed paths. One unrelated polling fixture still assumes an old timeout-store stub and is not claimed as green.
- A queued semantic POST now becomes visible immediately through GET with the same run ID.
- A stalled semantic run is terminalized as `failed` after the configured deadline; it cannot remain `generating` forever.

## Semantic review state

The fresh semantic run for the exact revision is `content_semantic_review_8d2c19d3daa6406596d772b3c67b7237`, status `reviewable`, with 9 dimensions and 0 findings. Its request/response is retained in `docs/agents/runs/delivery-loop/bdo-20260803/semantic-review-fresh.json`. Human review remains required; `reviewable` is not legal or publication approval.

## Runtime configuration

The running API reports 9/12 configured connectors: Google Ads, Search Console, GA4, Merchant Center, Ahrefs, Localo, both WordPress sites and Codex. LinkedIn and Facebook remain unconfigured; Google Sheets is disabled. No credential values are copied into this packet.

## Remaining acceptance work

1. Re-run the behavioral mutation suite for missing requirement answers, scope/exception loss, term/amount/procedure changes, CTA defects, query mismatch, and repetition/source-artifact slop after the deterministic guards; any remaining model-only misses stay open rather than being presented as passing.
2. Export exact revision, planning proposal/input, source facts/reviews, assurance receipts, semantic request/response, and digests into a reviewable transient run artifact.
3. Obtain separate human review for legal/content accuracy. `reviewable` is not approval.

## Boundaries

No changed path in this slice adds a vendor write, WordPress mutation, publication, deployment, measurement write, or ActionObject apply. The only writes are local immutable workflow/review state and Codex run audit records.

This packet does not prove live vendor freshness, legal approval, publication, SEO outcomes, or lead outcomes.
