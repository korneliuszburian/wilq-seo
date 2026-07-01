# GA4 Traffic Quality Proof

Date: 2026-07-01
Skill: `wilq-ga4-analyst`
API base: `http://127.0.0.1:8000`

## Status

WILQ API is reachable and GA4 diagnostics are API-backed.

- API health: `ok`
- Dashboard: `http://127.0.0.1:5173/command-center`
- GA4 connector: `configured`
- GA4 freshness: `fresh`
- Latest GA4 refresh: `refresh_google_analytics_4_5ebc4ba1c966`
- Latest GA4 refresh completed at: `2026-07-01T19:01:32Z`
- GA4 vendor range: `2026-06-03` to `2026-06-30`
- Latest WordPress Ekologus refresh: `refresh_wordpress_ekologus_691cbe6ab27d`
- WordPress refresh completed at: `2026-07-01T19:03:28Z`
- WordPress inventory objects: `16`

The local `curl` call to WordPress timed out at 120 seconds, but the API
refresh run completed successfully in the backend and persisted evidence.

## Dowody

Primary evidence IDs from WILQ API:

- `ev_refresh_refresh_google_analytics_4_5ebc4ba1c966`
- `ev_refresh_refresh_google_analytics_4_33a4b3fda0db`
- `ev_refresh_refresh_wordpress_ekologus_691cbe6ab27d`
- `ev_connector_google_analytics_4_status`

Source connectors:

- `google_analytics_4`
- `wordpress_ekologus`

Skill smoke:

- Command: `rtk uv run python .agents/skills/wilq-ga4-analyst/scripts/smoke_skill_contract.py --api-base http://127.0.0.1:8000`
- Result: passed
- Action validation: `act_review_ga4_tracking_quality` returned `valid=true`

## Kolejka Decyzji GA4

WILQ GA4 diagnostics returned four decision items.

### 1. `ga4_decision_tq_ga4_not_set_google_organic`

- Type: measurement problem / `fix_measurement`
- Status: blocked
- Landing page: `(not set)`
- Source/medium: `google / organic`
- Campaign: `(organic)`
- Active users: `73`
- Engagement rate: `2.15%`
- Interpretation: do not judge campaign, SEO or landing page from this row.
  First check landing page attribution, source/medium, UTM and report setup.

### 2. `ga4_decision_tq_ga4_not_set_not_set`

- Type: measurement problem / `fix_measurement`
- Status: blocked
- Landing page: `(not set)`
- Source/medium: `(not set)`
- Campaign: `(not set)`
- Active users: `179`
- Engagement rate: `0%`
- Interpretation: this is primarily a measurement/attribution gap, not a
  marketing verdict.

### 3. `ga4_decision_tq_ga4_unknown_google_cpc`

- Type: traffic quality review / `review_traffic_quality`
- Status: ready
- Landing page: `/`
- Source/medium: `google / cpc`
- Campaign: `(2026) Ekologus Ogólna`
- Active users: `49`
- Engagement rate: `75.58%`
- WordPress match: confirmed
- Interpretation: review campaign message and home-page intent fit. Do not infer
  ROAS, revenue or conversion quality without separate cost/conversion evidence.

### 4. `ga4_decision_tq_ga4_rewolucja_w_decyzjach_o_warunkach_zabudowy_co_zm_google_cpc`

- Type: traffic quality review / `review_traffic_quality`
- Status: ready
- Landing page: `/rewolucja-w-decyzjach-o-warunkach-zabudowy-co-zmienia-sie-od-2026/`
- Source/medium: `google / cpc`
- Campaign: `(2026) Ekologus Ogólna`
- Active users: `25`
- Engagement rate: `43.33%`
- WordPress match: confirmed
- Interpretation: review whether the ad promise and landing-page intent match.
  Do not infer ROAS, revenue or conversion quality without separate
  cost/conversion evidence.

## Diagnosis

Measurement problem:

- The two `(not set)` rows are blocked.
- They should lead to tracking/reporting review, not campaign or SEO blame.

Marketing review candidate:

- The two `google / cpc` rows have confirmed landing pages and behavior metrics.
- They can support traffic-quality and message-fit review.
- They cannot support return-on-ad-spend, revenue, profitability or conversion
  conclusions on their own.

## Blocked Claims

The GA4 skill/API contract blocks conclusions about:

- `zwrot z reklam`
- `przychód`
- `opłacalność`
- `spadek konwersji`
- `współczynnik konwersji`
- `ocena atrybucji`
- `diagnoza lejka`
- `naprawiony pomiar`
- `wdrożona konfiguracja konwersji`
- `zapis w GA4`

## Next Safe Step

Use `act_review_ga4_tracking_quality` as a prepare-mode review action. Start
with the two measurement blockers, then review the two `google / cpc` landing
page/message-fit candidates.

No GA4 write or campaign change is approved by this proof.
