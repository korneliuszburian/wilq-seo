# Scope-before-generation proof

## Fixed point

- Production commit: `ff145369`
- Work item: `content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`
- Route: `/content-workflow`

## Outcome

When the API reports `scope_current=false`, the planning card no longer offers `Wygeneruj aktualny plan`. It shows one explicit gate: `Najpierw zapisz aktualną decyzję zakresu`. This prevents generation from competing with or bypassing the current human scope decision. Once the scope decision is current, the existing generation seam remains unchanged.

## Browser proof

- [Desktop full workflow](./desktop-full.png)
- [Mobile full workflow](./mobile-full.png)

The live BDO snapshot showed the scope gate, no generation button, and no horizontal overflow (`scrollWidth=390`, `innerWidth=390` on mobile). The browser proof performed read-only GETs only.

SHA-256:

```text
f02bcfe502d8b69cc372245e568cb7385e058bfc28f2f2c843dca5e5bee86c0b  desktop-full.png
574b36f289792766230f41256091acddcecfd0ee333ae6eb5b9c84d6f31f7857  mobile-full.png
```

## Focused evidence

- `ContentPlanningGenerationPanel.test.tsx`: 8/8 passed, including stale-scope generation denial.
- Dashboard TypeScript typecheck passed.
- `git diff --check` passed.
- No API, Codex, revision, review, handoff or WordPress behavior changed.

This is a gate on an existing UI action, not an approval of the plan or content.
