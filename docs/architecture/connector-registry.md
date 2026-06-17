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

Implementation:

- `wilq/connectors/registry.py`
- `GET /api/connectors`
- `GET /api/connectors/{connector}/status`
- `POST /api/connectors/{connector}/refresh`
- `GET /api/evidence`
- `GET /api/evidence/{evidence_id}`

Missing credentials are product state. They must not be hidden, and values must never be returned.

Opportunity generation can use connector-status evidence for operational
readiness items, but it must not describe vendor performance until a real
connector refresh has collected vendor data.
