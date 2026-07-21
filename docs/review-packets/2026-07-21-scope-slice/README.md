# Scope review slice proof

Fixed point: `d398f99e3fd1d20810d9cf7bc15126bb121a935e`

This packet proves the compact `Zakres i cel` surface for the BDO work item. It
does not claim marketer UAT, content quality, generation, review approval, or
WordPress readiness.

## Runtime

- URL: `http://127.0.0.1:5173/content-workflow?work_item_id=content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`
- Desktop proof: 1440×900, `scrollY=737` at the compact scope panel.
- Mobile first viewport: 390×844, `scrollY=0`.
- Mobile scope panel: 390×844, `scrollY=1140`.
- Both viewports report `scrollWidth` equal to the viewport width.

## Observable result

The scope stage now presents one decision area: the selected service, three
high-value planning facts, an on-demand details/source disclosure, a decision,
optional note, and one `Zapisz decyzję` action. The former checklist requiring
the marketer to re-approve page, intent, audience, CTA, and all diagnostic
fields is no longer rendered. Existing-content provenance remains an explicit
checkbox only when the API marks that evidence as required.

The source, revision, generation, review, handoff, and WordPress contracts were
not changed. The save still goes through the existing planning-review API seam
with the existing checked-item lineage (`zakres i CTA`, plus provenance when
explicitly confirmed).

## Artifacts

- `desktop-scope.png` — compact desktop scope panel.
- `mobile-first-viewport.png` — mobile first viewport.
- `mobile-scope.png` — compact mobile scope panel.

## Focused signals

- `pnpm exec vitest run src/routes/ContentPlanningReviewPanel.test.tsx src/routes/ContentWorkflowSurface.test.tsx -t 'records scope review|makes a stale planning decision|planningReviewCheckedItems'`
- `pnpm run typecheck`
- `git diff --check`

The focused tests passed (3 tests); dashboard typecheck passed. The complete
legacy `ContentWorkflowSurface` file still contains unrelated stale assertions
for removed/changed surfaces and was not used as a blanket completion claim.
