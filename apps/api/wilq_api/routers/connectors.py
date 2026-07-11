from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, BackgroundTasks, HTTPException

from wilq.connectors.refresh import (
    complete_queued_connector_refresh,
    get_connector_refresh_run,
    list_connector_refresh_runs,
    queue_connector_refresh,
    run_connector_refresh,
)
from wilq.connectors.registry import get_connector_status, list_connector_statuses
from wilq.schemas import ConnectorRefreshRequest, ConnectorRefreshRun, ConnectorStatus


def create_connectors_router(clear_api_view_model_caches: Callable[[], None]) -> APIRouter:
    router = APIRouter()

    @router.get("/api/connectors", response_model=list[ConnectorStatus])
    def connectors() -> list[ConnectorStatus]:
        return list_connector_statuses()

    @router.get("/api/connectors/refresh-runs", response_model=list[ConnectorRefreshRun])
    def connector_refresh_runs() -> list[ConnectorRefreshRun]:
        return list_connector_refresh_runs()

    @router.get("/api/connectors/refresh-runs/{run_id}", response_model=ConnectorRefreshRun)
    def connector_refresh_run_detail(run_id: str) -> ConnectorRefreshRun:
        run = get_connector_refresh_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Unknown connector refresh run: {run_id}")
        return run

    @router.get("/api/connectors/{connector}/status", response_model=ConnectorStatus)
    def connector_status_endpoint(connector: str) -> ConnectorStatus:
        status = get_connector_status(connector)
        if status is None:
            raise HTTPException(status_code=404, detail=f"Unknown connector: {connector}")
        return status

    @router.get(
        "/api/connectors/{connector}/refresh-runs",
        response_model=list[ConnectorRefreshRun],
    )
    def connector_refresh_runs_for_connector(connector: str) -> list[ConnectorRefreshRun]:
        if get_connector_status(connector) is None:
            raise HTTPException(status_code=404, detail=f"Unknown connector: {connector}")
        return list_connector_refresh_runs(connector_id=connector)

    @router.post("/api/connectors/{connector}/refresh", response_model=ConnectorRefreshRun)
    def connector_refresh(
        connector: str,
        background_tasks: BackgroundTasks,
        request: ConnectorRefreshRequest | None = None,
    ) -> ConnectorRefreshRun:
        refresh_request = request or ConnectorRefreshRequest()
        if refresh_request.run_async:
            run = queue_connector_refresh(connector, refresh_request)
            if run is not None:
                background_tasks.add_task(
                    complete_queued_connector_refresh,
                    run.id,
                    connector,
                    refresh_request,
                )
                background_tasks.add_task(clear_api_view_model_caches)
        else:
            run = run_connector_refresh(connector, refresh_request)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Unknown connector: {connector}")
        clear_api_view_model_caches()
        return run

    return router
