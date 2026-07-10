# Action Model

ActionObject is the execution primitive for recommendations and API writes.

Required fields live behind the `wilq/schemas/__init__.py` compatibility façade
and include ID, title, domain, connector, mode, risk, status, evidence IDs,
metrics, diagnosis, reason, payload, validation status, creator, timestamps,
and audit events.

Validation rules:

- Apply fails without evidence IDs.
- Apply fails if the connector is not configured.
- Apply fails if payload is invalid for connector/action type.
- Apply records an audit event.
- High and critical risk writes are blocked in Goal 001.
- Destructive actions are blocked until separately implemented.

Current implementation:

- `wilq/actions/service.py` validates and applies seeded actions.
- `/api/actions/{id}/validate` records validation state.
- `/api/actions/{id}/apply` blocks unvalidated or unsafe actions with an audit event.
