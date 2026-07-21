# Planning panel condensation proof

## Fixed point

- Production commit: `fdbe5dbb`
- Captured: 2026-07-21, managed local stack
- Work item: `content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`

## Outcome

The plan-generation card now keeps the default view focused on the decision: current plan status, five compact source counts, the blocker/next action and one generation action. Source assessments, exact facts, metric comparisons, page assets and GSC query rows remain available behind explicit disclosure controls. No planning request is started by opening or expanding the details.

## Browser proof

- [Desktop full workflow, 1440×900](./desktop-full.png)
- [Mobile full workflow, 390×844](./mobile-full.png)

The mobile full capture shows the plan card reduced to the compact source-count strip plus one disclosure row; the previous always-open source/asset/metric blocks are not in the default flow. Runtime evaluation reported `scrollWidth=390` at `innerWidth=390`; desktop reported no horizontal overflow.

SHA-256:

```text
1fe74e6809d50654a02de6fa4e88d917ebd0ee555f657cb8bf49861bfbb90742  desktop-full.png
5dfeb6dc54029ba01d3db54e36c0375c64a6628027b98f2a2c4d164382208016  mobile-full.png
```

## Focused evidence

- `ContentPlanningGenerationPanel.test.tsx`: 7/7 passed, including the default-closed disclosure assertion.
- Dashboard TypeScript typecheck passed.
- `git diff --check` passed.
- Existing API seam and mutation remain unchanged; this slice only changes rendering hierarchy. No generation, review, revision, handoff or WordPress write was invoked during browser proof.

This is not a claim that the full `/content-workflow` is complete or that the planning proposal is approved.
