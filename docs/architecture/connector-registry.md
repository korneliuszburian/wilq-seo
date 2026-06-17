# Connector Registry

The connector registry exposes capability and credential state without secret values.

Required connectors:

- `google_ads`
- `google_search_console`
- `google_analytics_4`
- `google_merchant_center`
- `google_sheets` (optional, disabled for current Ekologus operator scope)
- `ahrefs`
- `localo`
- `wordpress_ekologus`
- `wordpress_sklep`
- `linkedin`
- `facebook`
- `openai_codex`

Each connector exposes ID, label, status, configured state, missing credential names, freshness, read/write capabilities, supported actions, rate/cost/risk notes, required env names, and health-check type.

Connector refreshes are durable API runs:

- `status_probe` records local connector readiness from credential-name presence and never calls a vendor API.
- `vendor_read` runs a read-only vendor adapter when one exists and required credential names are configured.
- Google Ads `vendor_read` uses OAuth refresh-token auth and `googleAds:searchStream` to persist only aggregate campaign metrics.
- Google Search Console `vendor_read` uses Search Analytics to persist aggregate site clicks, impressions, CTR and position.
- GA4 `vendor_read` uses Analytics Data API `runReport` to persist aggregate behavior metrics.
- Google Merchant Center `vendor_read` uses Merchant API `aggregateProductStatuses.list` to persist aggregate product status and item-issue counts.
- Google Sheets is currently disabled by product scope. It remains documented as an optional future collaboration/export surface, not a required evidence source.
- Ahrefs `vendor_read` uses Site Explorer `domain-rating` to persist only aggregate domain rating and Ahrefs rank metadata for the configured target.
- WordPress `vendor_read` uses the REST API for `ekologus.pl` and `sklep.ekologus.pl` content inventory, persisting only aggregate post/page counts and latest modification timestamps.
- Every refresh run records evidence IDs, checked credential names, missing credential names, external-call status, vendor-data status, metric summary, summary and errors.
- Redacted scalar `metric_summary` values are also written to the local DuckDB metric store as connector metric facts. The metric store is analytical state, not a raw vendor response cache.
- Refresh runs must not expose secret values, access-pack paths or raw credential files.

Implementation:

- `wilq/connectors/registry.py`
- `wilq/connectors/refresh.py`
- `GET /api/connectors`
- `GET /api/connectors/{connector}/status`
- `POST /api/connectors/{connector}/refresh`
- `GET /api/connectors/refresh-runs`
- `GET /api/connectors/refresh-runs/{run_id}`
- `GET /api/connectors/{connector}/refresh-runs`
- `GET /api/evidence`
- `GET /api/evidence/{evidence_id}`
- `GET /api/metrics/status`
- `GET /api/metrics`

Missing credentials are product state. They must not be hidden, and values must never be returned.

Disabled optional connectors are also product state. They should not create missing-credential noise or block the command center.

Opportunity generation can use connector-status evidence for operational
readiness items, but it must not describe vendor performance until a real
connector refresh has collected vendor data.
