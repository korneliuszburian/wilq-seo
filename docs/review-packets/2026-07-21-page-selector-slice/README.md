# Page selector slice proof

## Fixed point

- Production commit: `eaec193f9c1bd81a80da912184ddb0a1e7d0a727`
- Captured: 2026-07-21, local managed stack (`127.0.0.1:8000` / `127.0.0.1:5173`)
- Work item: `content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`
- URL: `/content-workflow?work_item_id=content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`

## Result

The workflow now exposes exactly one page selector labelled `Strona`. It combines the queue candidates and the full WordPress inventory, deduplicated by `work_item_id`; the live BDO page exposed 858 options. The former “Zmień stronę lub otwórz pełny inventory” panel and its second page-selection mechanism are gone.

The selector was exercised against a real inventory item (`content_work_item_inventory_0454c020b0ddbad0062b3d08`). The route changed to that item and the page title changed to `Informacja o opakowaniach i odpadach opakowaniowych oraz o opłacie produktowej - Ekologus`, proving the same public selection seam loads a non-queue page.

## Browser proof

| Viewport | Screenshot | Result |
| --- | --- | --- |
| 1440×900 | [desktop](./desktop-1440x900.png) | URL, WordPress title, service, one `Strona` selector and 858-page availability are visible; `scrollWidth=1440`. |
| 390×844 | [mobile](./mobile-390x844.png) | Same single selector and context remain usable without horizontal overflow; `scrollWidth=390`. |

SHA-256:

```text
da1c36de0672a3fa5545cc1af561f4ed96e5899bccb1a5d1d83d1b330458a093  desktop-1440x900.png
97cf8c53bcfad7765e3064d4ca355581acba215d7a71517e287b8fb0819aebd1  mobile-390x844.png
```

## Safety

The browser session issued read-only GET requests for queue, inventory, snapshot and related workflow context. No POST, PUT, PATCH or DELETE, generation, review, handoff or WordPress write was observed. Focused Vitest coverage for page discovery/selection passed (3 tests), dashboard TypeScript typecheck passed, and `git diff --check` passed. The broader legacy surface suite still contains pre-existing assertions for removed UI copy; those are outside this selector slice and were not silently rewritten.
