# Compact workflow state proof

Fixed point: `5d669672c535114a5c7ff5ce1ba278a20d2af2a3`

This slice changes only the marketer-facing task map. The five API-owned step
buttons remain available for navigation, but the duplicate heading, selected
step title, status prose, and repeated “next safe step” panel were removed. The
hero remains the single place that explains the current action and blocker.

## Browser proof

- URL: `http://127.0.0.1:5173/content-workflow?work_item_id=content_work_item_content_decision_https___www_ekologus_pl_bdo_co_musi_wiedziec_przedsiebiorca`
- `desktop.png`: 1440×900, scroll top; compact `Stan pracy` rail is visible above the scope panel.
- `mobile.png`: 390×844, scroll top; no horizontal overflow (`scrollWidth=390`).
- Live BDO API context: 181 GSC impressions, 0 clicks, missing exact GA4, 4 detected `the_content` sections, bound BDO service.

## Contract boundary

No API, snapshot, planning, revision, Codex, review, handoff, or WordPress
behavior changed. The map still disables steps according to the API-owned
`canOpen` state and preserves the existing selected-step navigation.

## Focused signals

- Dashboard typecheck: passed.
- `git diff --check`: passed.
- Browser desktop/mobile proof: passed; desktop width 1440, mobile width 390.

The broad legacy `ContentWorkflowSurface` test file still contains unrelated
stale fixture assertions (for example a missing legacy GA4 test node); those
are not used as a blanket pass claim for this UI-only slice.
