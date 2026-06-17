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

Local job orchestration lives in `wilq/jobs/`:

- `models.py`: `ScheduledJob`, `JobRunRequest` and `JobRun`.
- `registry.py`: deterministic job definitions for connector refresh orchestration.
- `scheduler.py`: APScheduler-backed scheduler metadata plus explicit job runner.

Goal 001 does not auto-start a background daemon inside the API process. Jobs are exposed as typed definitions and explicit run endpoints first, so connector refresh work stays reviewable, redacted and testable.

Local run state:

- `wilq/storage/local_state.py` stores workflow runs in SQLite.
- `wilq/storage/local_state.py` stores job runs in SQLite.
- Default DB location is `.local-lab/state/wilq.sqlite3`.
- `WILQ_STATE_DB` overrides the DB path for tests or isolated local runs.
- Workflow and job run payloads are redacted before storage.

API surface:

- `GET /api/workflows`: workflow definitions.
- `POST /api/workflows/{workflow_id}/runs`: create a queued persisted run.
- `GET /api/workflow-runs`: list persisted workflow runs.
- `GET /api/workflow-runs/{run_id}`: fetch a persisted workflow run.
- `GET /api/jobs/status`: scheduler metadata.
- `GET /api/jobs`: job definitions.
- `POST /api/jobs/{job_id}/run`: run a job explicitly.
- `GET /api/job-runs`: list persisted job runs.
- `GET /api/job-runs/{run_id}`: fetch a persisted job run.
