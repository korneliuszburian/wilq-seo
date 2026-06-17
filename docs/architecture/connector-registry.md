# Connector Registry

The connector registry exposes capability and credential state without secret values.

Required connectors:

- `google_ads`
- `google_search_console`
- `google_analytics_4`
- `google_merchant_center`
- `google_sheets`
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
- `vendor_read` is allowed as a contract shape, but remains blocked until a connector adapter exists and required credential names are configured.
- Every refresh run records evidence IDs, checked credential names, missing credential names, external-call status, vendor-data status, summary and errors.
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

Missing credentials are product state. They must not be hidden, and values must never be returned.

Opportunity generation can use connector-status evidence for operational
readiness items, but it must not describe vendor performance until a real
connector refresh has collected vendor data.
