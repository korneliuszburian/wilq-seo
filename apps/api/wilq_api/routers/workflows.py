from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from wilq.storage.local_state import local_state_store
from wilq.workflows.models import (
    Workflow,
    WorkflowInput,
    WorkflowRun,
    WorkflowRunCreateRequest,
)
from wilq.workflows.registry import list_workflows

router = APIRouter()


@router.get("/api/workflows", response_model=list[Workflow])
def workflows() -> list[Workflow]:
    return list_workflows()


@router.post("/api/workflows/{workflow_id}/runs", response_model=WorkflowRun)
def create_workflow_run(workflow_id: str, request: WorkflowRunCreateRequest) -> WorkflowRun:
    workflow = next(
        (workflow for workflow in list_workflows() if workflow.id == workflow_id),
        None,
    )
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"Unknown workflow: {workflow_id}")
    run = WorkflowRun(
        id=request.id or f"run_{workflow_id}_{uuid4().hex[:10]}",
        workflow_id=workflow_id,
        status="queued",
        scope=_workflow_run_scope(workflow, request.input),
        workspace_work_item_id=_workflow_run_parameter(
            request.input,
            "workspace_work_item_id",
            "work_item_id",
        ),
        input=request.input,
    )
    return local_state_store().save_workflow_run(run)


@router.get("/api/workflow-runs", response_model=list[WorkflowRun])
def workflow_runs() -> list[WorkflowRun]:
    return local_state_store().list_workflow_runs()


@router.get("/api/workflow-runs/{run_id}", response_model=WorkflowRun)
def workflow_run_detail(run_id: str) -> WorkflowRun:
    run = local_state_store().get_workflow_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Unknown workflow run: {run_id}")
    return run


def _workflow_run_scope(workflow: Workflow, workflow_input: WorkflowInput) -> str:
    return (
        _workflow_run_parameter(workflow_input, "scope", "scope_label")
        or workflow.label
    )


def _workflow_run_parameter(workflow_input: WorkflowInput, *keys: str) -> str | None:
    for key in keys:
        value = workflow_input.parameters.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
