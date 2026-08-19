from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, status
from pydantic import BaseModel

from apps.api.wilq_api.context_models import ContextPackRequest
from wilq.codex.stop_telemetry import StopTelemetryEvent, new_stop_telemetry_event
from wilq.schemas import CodexRun
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
        response_model=StopTelemetryEvent,
        status_code=status.HTTP_201_CREATED,
    )
    def record_stop_telemetry_event() -> StopTelemetryEvent:
        event = new_stop_telemetry_event()
        return local_state_store().append_stop_telemetry_event(event)

    @router.get("/api/codex/runs", response_model=list[CodexRun])
    def codex_runs() -> list[CodexRun]:
        return local_state_store().list_codex_runs()

    return router
