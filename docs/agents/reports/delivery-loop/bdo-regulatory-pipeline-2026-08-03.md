# BDO regulatory content pipeline — cumulative packet

Status: `needs review`; this is an owner-facing packet, not human legal approval.

## Fixed point

- Isolated implementation branch: `feat/regulatory-visible-extraction`
- Base used for the current repair slice: `0cea8eeb4aabbe512f17b74921667554d0452e87`
- Current HEAD: `7164e837`
- Subsequent runtime repairs: `1d28b136` (current branch HEAD)
- Latest cohesive commits:
  - `214c944c` — per-constraint regulatory assurance context
  - `adf2e0b3` — semantic reviewer detects editorial/source artifacts
  - `3a4539cf` — queued semantic review is visible before worker preflight
  - `7164e837` — stale semantic runs become terminal after deadline

## Exact live BDO lineage

- Work item: `content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`
- Service: `ekologus_service_bdo_reporting`
- Planning input digest: `9b6440a3d161372d60df91ccc3d5cb25a07a31660fe91beae4924a7188ef2d0b`
- Planning digest: `16514fb2b9cf95dd0389bbbd02bf1d01219634f17138991bf234645eb9434559`
- Proposal: `content_planning_proposal_8d03f0744e4d432ab64fcff8774d7fe0`
- Initial-draft run: `codex_content_initial_draft_8470e329d2ed40a982dbdac9f4d30083`
- Exact revision: `content_revision_6ee42f01b97b4a25814b0665f26e9fab`
- Content digest: `6570099bf08c1f2625de40d2cb6b6fa3118a5f85736e25f000c08fdb4a200f6e`

The revision is `unreviewed`, `publish_ready=false`, and has not been sent to WordPress.

## Evidence state at planning

- WordPress and GSC: `used`; GSC carries exact query rows and evidence IDs.
- GA4: `blocked`, `settling/unverified`; no GA4 values are treated as used planning evidence.
- Google Ads, Ahrefs, Keyword Planner: explicit `missing`; no synthetic metrics are added.
- Merchant, Localo, social: `not_applicable` for this page.
- Regulatory coverage: 8/8 requirements, 12 approved source facts.

## Runtime proof

- Earlier assurance attempts blocked real defects (`overbroad_claim`, `insufficient_source_alignment`).
- The per-constraint assurance run completed and created the exact revision only after those checks passed.
- Focused assurance/source tests: 79 passed before the later semantic-runtime slice; current focused semantic tests: 6 passed, Ruff and complexity audit passed, `git diff --check` passed. Commit `0a2c7925` compacts semantic context while retaining regulatory lineage and adds a payload falsifier.
- A queued semantic POST now becomes visible immediately through GET with the same run ID.
- A stalled semantic run is terminalized as `failed` after the configured deadline; it cannot remain `generating` forever.

## Semantic review state

The first semantic run was `reviewable` with 9 dimensions and no findings, but manual inspection found duplicated source-style paragraphs in the draft. The reviewer prompt now explicitly checks repeated paragraphs, source-attribution narration, and pasted working notes. Fresh API retries are now visible and terminalize instead of becoming zombies, but the current full semantic app-server turn has timed out; no new canonical review has replaced the immutable first review. A transient fresh turn artifact records that timeout under `docs/agents/runs/delivery-loop/bdo-20260803/semantic-fresh-transient.json`. A new retry `codex_content_semantic_review_7824147152d74860b92cd66e4de356ac` was queued, then the local stack was restarted; its worker result still needs verification.

## Runtime configuration blocker

The running API reports `openai_codex` as the only configured connector. Google Ads, Search Console, GA4, Merchant Center, Ahrefs, Localo, both WordPress sites, LinkedIn, and Facebook report missing credentials; Google Sheets is disabled. The source checkout contains a private `.env`, but the isolated worktree running this proof does not, so the runtime cannot see those values. No credential values are copied into this packet. This is an environment handoff blocker, not a content-contract failure.

## Remaining acceptance work

1. Obtain a fresh semantic result for the exact revision after the prompt/runtime repairs (the existing immutable review is pre-prompt-repair and cannot be treated as that proof).
2. Run the behavioral mutation suite for missing requirement answers, scope/exception loss, term/amount/procedure changes, CTA defects, query mismatch, and repetition/source-artifact slop.
3. Export the exact revision, planning proposal/input, source facts/reviews, assurance receipts, semantic request/response, and digests into a reviewable transient run artifact.
4. Obtain separate human review for legal/content accuracy. `reviewable` is not approval.

## Boundaries

No changed path in this slice adds a vendor write, WordPress mutation, publication, deployment, measurement write, or ActionObject apply. The only writes are local immutable workflow/review state and Codex run audit records.

This packet does not prove live vendor freshness, legal approval, publication, SEO outcomes, or lead outcomes.
