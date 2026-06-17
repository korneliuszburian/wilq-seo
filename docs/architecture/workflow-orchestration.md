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

