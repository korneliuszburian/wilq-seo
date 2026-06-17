# Workflow Orchestration

Workflow primitives live in `wilq/workflows/models.py`:

- Workflow
- WorkflowRun
- WorkflowStep
- WorkflowInput
- WorkflowOutput
- WorkflowEvidence
- WorkflowActionObject

Initial registry lives in `wilq/workflows/registry.py`.

Workflows run against WILQ API, record evidence IDs, action IDs, connector status and errors, and must be visible in the dashboard.

Local run state:

- `wilq/storage/local_state.py` stores workflow runs in SQLite.
- Default DB location is `.local-lab/state/wilq.sqlite3`.
- `WILQ_STATE_DB` overrides the DB path for tests or isolated local runs.
- Workflow run payloads are redacted before storage.

API surface:

- `GET /api/workflows`: workflow definitions.
- `POST /api/workflows/{workflow_id}/runs`: create a queued persisted run.
- `GET /api/workflow-runs`: list persisted workflow runs.
- `GET /api/workflow-runs/{run_id}`: fetch a persisted workflow run.
