# Context → text proof

Fixed point: `27948d3894e2dd3002f9c270b57a1abf619a291d`

The marketer-facing workflow now presents four states:

1. **Kontekst** — page, service, current evidence and one scope decision;
2. **Tekst** — the HTML authoring workspace;
3. **Review** — human review of an exact revision;
4. **Odbiór opcjonalny** — optional WordPress/dev handoff after approval.

The API still retains `section_map` as a system-owned readiness state. It is
not shown as a marketer step. When the API reports it as current, the dashboard
opens the text state. Plan source counts are behind an explicit details control;
the plan gate still requires a current saved scope and does not run generation
on view load.

## Browser proof

URL:

`http://127.0.0.1:5173/content-workflow?work_item_id=content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`

After snapshot load, both `1440×900` and `390×844` reported:

```text
1 Kontekst
2 Tekst
3 Review
4 Odbiór opcjonalny
horizontal overflow: 0
```

Artifacts:

```text
desktop.png  sha256: 28ecff50d6dc6dd0342aeba647324b9fa63995221eab4841e0aa48df1f7dbef1
mobile.png   sha256: fce7bf0c83229376d44f9923ffda8f9ea5ab704c83d3b0da007a30fa6b85efd4
```

The browser proof was read-only. No planning generation, revision save,
review, handoff or WordPress write was executed. WILQ API context at proof:
12 connectors total, 9 configured, 2 missing credentials.

## Focused proof

`src/routes/ContentWorkflowTaskMap.test.tsx` verifies that `section_map` is
not rendered as a marketer step and that the visible rail has four states.
Generation-panel focused tests also verify the source details disclosure and
scope gate.

