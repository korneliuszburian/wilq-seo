from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from wilq.storage.local_state import local_state_store
from wilq.workflows.models import WorkflowRun, WorkflowRunCreateRequest
from wilq.workflows.registry import list_workflows

router = APIRouter()


@router.get("/api/workflows")
def workflows() -> list[dict[str, Any]]:
    return [workflow.model_dump(mode="json") for workflow in list_workflows()]


@router.post("/api/workflows/{workflow_id}/runs", response_model=WorkflowRun)
def create_workflow_run(workflow_id: str, request: WorkflowRunCreateRequest) -> WorkflowRun:
    if workflow_id not in {workflow.id for workflow in list_workflows()}:
        raise HTTPException(status_code=404, detail=f"Unknown workflow: {workflow_id}")
    run = WorkflowRun(
        id=request.id or f"run_{workflow_id}_{uuid4().hex[:10]}",
        workflow_id=workflow_id,
        status="queued",
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
