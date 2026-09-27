"""Public async start/readback seam for one current per-URL acceptance wave."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from wilq.content.workflow.current_acceptance import execute_current_acceptance_run
from wilq.content.workflow.current_acceptance_contracts import (
    CurrentAcceptanceAttempt,
    CurrentAcceptanceBlocked,
    CurrentAcceptanceRunRead,
    CurrentAcceptanceSnapshot,
    current_acceptance_scope_coverage_digest,
)
from wilq.content.workflow.current_acceptance_snapshot import build_current_acceptance_snapshot
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.store.store import content_workflow_store

SnapshotLoader = Callable[[], CurrentAcceptanceSnapshot]
StoreFactory = Callable[[], Any]
Worker = Callable[..., None]
_ROUTE = "/api/content/current-acceptance-waves"
_RUN_ROUTE = f"{_ROUTE}/{{run_id}}"
_ERROR_CODE_PATTERN = r"^[a-z][a-z0-9_]*$"


class CurrentAcceptanceStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID


class CurrentAcceptanceErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str = Field(pattern=_ERROR_CODE_PATTERN)
    owner: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)


@dataclass(frozen=True)
class _StartState:
    attempt: CurrentAcceptanceAttempt | None
    snapshot: CurrentAcceptanceSnapshot | None
    dispatch: bool
    error: JSONResponse | None


def register_content_current_acceptance_routes(
    router: APIRouter,
    *,
    snapshot_loader: SnapshotLoader = build_current_acceptance_snapshot,
    store_factory: StoreFactory = content_workflow_store,
    worker: Worker = execute_current_acceptance_run,
) -> None:
    _register_start_route(router, snapshot_loader, store_factory, worker)
    _register_read_route(router, store_factory)


def _register_start_route(
    router: APIRouter,
    snapshot_loader: SnapshotLoader,
    store_factory: StoreFactory,
    worker: Worker,
) -> None:
    @router.post(
        _ROUTE,
        response_model=CurrentAcceptanceRunRead,
        status_code=202,
        responses={
            200: {"model": CurrentAcceptanceRunRead},
            409: {"model": CurrentAcceptanceErrorResponse},
        },
        tags=["content"],
    )
    async def start_current_acceptance_wave(
        request: CurrentAcceptanceStartRequest,
        background_tasks: BackgroundTasks,
    ) -> JSONResponse:
        store = store_factory()
        state = await _prepare_start(str(request.request_id), snapshot_loader, store)
        if state.error is not None:
            return state.error
        if state.attempt is None:
            return _conflict(
                "current_acceptance_attempt_missing",
                "WILQ content workflow",
                "Uruchom kwalifikację z nowym request ID.",
            )
        if state.dispatch and state.snapshot is not None:
            background_tasks.add_task(
                worker,
                state.attempt.run_id,
                state.snapshot,
                store_factory=store_factory,
            )
        return _read_response(store, state.attempt, accepted=True)


def _register_read_route(router: APIRouter, store_factory: StoreFactory) -> None:
    @router.get(
        _RUN_ROUTE,
        response_model=CurrentAcceptanceRunRead,
        responses={404: {"model": CurrentAcceptanceErrorResponse}},
        tags=["content"],
    )
    def read_current_acceptance_wave(
        run_id: str,
    ) -> CurrentAcceptanceRunRead | JSONResponse:
        store = store_factory()
        attempt = store.load_current_acceptance_attempt(run_id)
        if attempt is None:
            return JSONResponse(
                status_code=404,
                content=CurrentAcceptanceErrorResponse(
                    detail="current_acceptance_run_missing",
                    owner="WILQ content workflow",
                    safe_next_step="Uruchom nową kwalifikację z unikalnym request ID.",
                ).model_dump(mode="json"),
            )
        return _read_value(store, attempt)


async def _prepare_start(
    request_id: str,
    snapshot_loader: SnapshotLoader,
    store: Any,
) -> _StartState:
    existing = store.load_current_acceptance_attempt_by_request_id(request_id)
    if existing is not None and existing.status != "queued":
        return _StartState(existing, None, False, None)
    try:
        snapshot = await asyncio.to_thread(snapshot_loader)
    except CurrentAcceptanceBlocked as blocker:
        if existing is not None:
            return _StartState(existing, None, False, None)
        return _StartState(None, None, False, _conflict(
            blocker.code, blocker.owner, blocker.safe_next_step
        ))
    except ValueError:
        if existing is not None:
            return _StartState(existing, None, False, None)
        return _StartState(None, None, False, _conflict(
            "current_acceptance_inventory_blocked",
            "WILQ content workflow",
            "Zweryfikuj bieżący inventory i spróbuj ponownie.",
        ))
    except Exception:
        if existing is not None:
            return _StartState(existing, None, False, None)
        return _StartState(None, None, False, _conflict(
            "current_acceptance_snapshot_unavailable",
            "WILQ content workflow",
            "Sprawdź dostępność bieżącego inventory i źródeł treści.",
        ))
    if existing is not None:
        if snapshot.source_snapshot_digest != existing.source_snapshot_digest:
            return _StartState(existing, None, False, _conflict(
                "current_acceptance_request_id_conflict",
                "WILQ content workflow",
                "Użyj nowego request ID dla zmienionego snapshotu źródeł.",
            ))
        return _StartState(existing, snapshot, True, None)
    attempt = _new_attempt(request_id, snapshot)
    result, stored = store.create_current_acceptance_attempt(attempt)
    if result == "conflict":
        return _StartState(stored, None, False, _conflict(
            "current_acceptance_request_id_conflict",
            "WILQ content workflow",
            "Użyj nowego request ID dla zmienionego snapshotu źródeł.",
        ))
    dispatch = result == "created" or stored.status == "queued"
    return _StartState(stored, snapshot, dispatch, None)


def _new_attempt(
    request_id: str,
    snapshot: CurrentAcceptanceSnapshot,
) -> CurrentAcceptanceAttempt:
    run_id = f"content_current_acceptance_{request_id.replace('-', '')}"
    return CurrentAcceptanceAttempt(
        run_id=run_id,
        request_id=request_id,
        input_digest=canonical_json_digest(
            {"request_id": request_id, "source_snapshot_digest": snapshot.source_snapshot_digest}
        ),
        source_snapshot_digest=snapshot.source_snapshot_digest,
        inventory_evidence_ids=snapshot.scope.inventory_evidence_ids,
        wordpress_evidence_ids=snapshot.wordpress_evidence_ids,
        scope_row_count=len(snapshot.scope.rows),
        scope_row_digest=current_acceptance_scope_coverage_digest(
            (row.canonical_path, row.disposition) for row in snapshot.scope.rows
        ),
        status="queued",
        created_at=snapshot.captured_at,
        updated_at=snapshot.captured_at,
    )


def _read_response(
    store: Any,
    attempt: CurrentAcceptanceAttempt,
    *,
    accepted: bool,
) -> JSONResponse:
    result = _read_value(store, attempt)
    status_code = 202 if accepted and attempt.status in {"queued", "running"} else 200
    return JSONResponse(status_code=status_code, content=result.model_dump(mode="json"))


def _read_value(store: Any, attempt: CurrentAcceptanceAttempt) -> CurrentAcceptanceRunRead:
    wave = None if attempt.wave_id is None else store.load_current_acceptance_wave(attempt.wave_id)
    try:
        return CurrentAcceptanceRunRead(attempt=attempt, wave=wave)
    except ValueError as error:
        raise HTTPException(
            status_code=500,
            detail="current_acceptance_readback_invalid",
        ) from error


def _conflict(detail: str, owner: str, safe_next_step: str) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=CurrentAcceptanceErrorResponse(
            detail=detail,
            owner=owner,
            safe_next_step=safe_next_step,
        ).model_dump(mode="json"),
    )


__all__ = [
    "CurrentAcceptanceErrorResponse",
    "CurrentAcceptanceStartRequest",
    "register_content_current_acceptance_routes",
]
