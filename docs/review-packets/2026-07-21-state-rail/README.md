# State rail proof — section map is system state

Fixed point: `5243fe33049d03c9322f1185f09222f2673e5770`

The marketer-facing `/content-workflow` rail now exposes four states:

1. Zakres
2. Tekst
3. Review
4. Dev preview

The API still owns `section_map` and its readiness contract. The dashboard no
longer presents that generated map as a separate marketer step. If the API
reports `section_map` as the current system state, the marketer surface opens
the text state instead.

## Runtime proof

URL:

`http://127.0.0.1:5173/content-workflow?work_item_id=content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`

Desktop `1440x900`, after snapshot load:

```text
buttons: 1 Zakres, 2 Tekst, 3 Review, 4 Dev preview
horizontal overflow: 0
```

Mobile `390x844`, after snapshot load:

```text
buttons: 1 Zakres, 2 Tekst, 3 Review, 4 Dev preview
horizontal overflow: 0
```

Artifacts:

```text
desktop.png  sha256: 29f51db1b7436ba913f1f132bc0ea8b44fc205632451a77a6610ffddad420cd6
mobile.png   sha256: 97cf8c53bcfad7765e3064d4ca355581acba215d7a71517e287b8fb0819aebd1
```

The browser proof was read-only. No planning generation, revision save,
review, handoff, or WordPress write was executed. WILQ API context at proof:
12 connectors total, 9 configured, 2 missing credentials.

## Focused falsifier

`src/routes/ContentWorkflowTaskMap.test.tsx` verifies that a generated
`section_map` does not render as a marketer step and that the visible rail has
four states.

