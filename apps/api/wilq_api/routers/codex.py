from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from apps.api.wilq_api.context_models import ContextPackRequest
from wilq.codex.run_history import (
    CODEX_RUN_HISTORY_DEFAULT_LIMIT,
    CODEX_RUN_HISTORY_MAX_LIMIT,
    InvalidCodexRunHistoryCursor,
)
from wilq.codex.stop_telemetry import (
    StopTelemetryIntakeAccepted,
    StopTelemetryReceipt,
    StopTelemetryUnavailable,
    intake_stop_telemetry,
    read_stop_telemetry_health,
)
from wilq.schemas import CodexRun, CodexRunHistoryPage, CodexRunNotFound
from wilq.storage.local_state import local_state_store


class CodexRunPublicWriteRetired(BaseModel):
    type: Literal["deprecated_write_blocked"] = "deprecated_write_blocked"
    code: Literal["codex_run_public_write_retired"] = "codex_run_public_write_retired"
    successor: Literal["/api/codex/telemetry/stop-events"] = (
        "/api/codex/telemetry/stop-events"
    )


def create_codex_router(
    build_context_pack: Callable[[ContextPackRequest | None], dict[str, Any]],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/codex/context")
    def codex_context() -> dict[str, Any]:
        return build_context_pack(None)

    @router.post("/api/codex/context-pack")
    def codex_context_pack(request: ContextPackRequest) -> dict[str, Any]:
        return build_context_pack(request)

    @router.post(
        "/api/codex/runs",
        response_model=CodexRunPublicWriteRetired,
        status_code=status.HTTP_410_GONE,
    )
    def retire_public_codex_run_write() -> CodexRunPublicWriteRetired:
        return CodexRunPublicWriteRetired()

    @router.post(
        "/api/codex/telemetry/stop-events",
        response_model=StopTelemetryIntakeAccepted,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {"model": StopTelemetryUnavailable}
        },
    )
    def record_stop_telemetry_event() -> StopTelemetryIntakeAccepted | JSONResponse:
        result = intake_stop_telemetry(local_state_store())
        if isinstance(result, StopTelemetryUnavailable):
            return _stop_telemetry_unavailable_response(result)
        return result

    @router.get(
        "/api/codex/telemetry/health",
        response_model=StopTelemetryReceipt,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {"model": StopTelemetryUnavailable}
        },
    )
    def stop_telemetry_health() -> StopTelemetryReceipt | JSONResponse:
        result = read_stop_telemetry_health(local_state_store())
        if isinstance(result, StopTelemetryUnavailable):
            return _stop_telemetry_unavailable_response(result)
        return result

    @router.get("/api/codex/run-history", response_model=CodexRunHistoryPage)
    def codex_run_history(
        limit: Annotated[
            int,
            Query(ge=1, le=CODEX_RUN_HISTORY_MAX_LIMIT),
        ] = CODEX_RUN_HISTORY_DEFAULT_LIMIT,
        cursor: str | None = None,
    ) -> CodexRunHistoryPage | JSONResponse:
        try:
            return local_state_store().list_codex_run_history(limit=limit, cursor=cursor)
        except InvalidCodexRunHistoryCursor:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "Nieprawidłowy kursor historii uruchomień Codex."},
            )

    @router.get(
        "/api/codex/runs/{run_id}",
        response_model=CodexRun,
        responses={status.HTTP_404_NOT_FOUND: {"model": CodexRunNotFound}},
    )
    def codex_run_detail(run_id: str) -> CodexRun | JSONResponse:
        run = local_state_store().get_codex_run(run_id)
        if run is None:
            error = CodexRunNotFound(run_id=run_id)
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error.model_dump(mode="json"),
            )
        return run

    @router.get("/api/codex/runs", response_model=list[CodexRun])
    def codex_runs(response: Response) -> list[CodexRun]:
        response.headers["Deprecation"] = "true"
        return local_state_store().list_codex_runs()

    return router


def _stop_telemetry_unavailable_response(
    error: StopTelemetryUnavailable,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error.model_dump(mode="json"),
    )
