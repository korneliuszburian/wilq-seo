"""Public server-owned entrypoint for current inventory reconciliation."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from wilq.content.workflow.current_inventory_reconciliation import (
    CurrentInventoryReconciliationResult,
    reconcile_current_authoring_inventory,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationValidationError,
)

_ROUTE = "/api/content/inventory/reconciliation"
_ERROR_CODE_PATTERN = r"^[a-z][a-z0-9_]*$"
_INVALID_DETAIL = "current_inventory_reconciliation_invalid"
_CONFLICT_DETAIL = "current_inventory_reconciliation_conflict"


class CurrentInventoryReconciliationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str = Field(pattern=_ERROR_CODE_PATTERN)


def _error_response(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=CurrentInventoryReconciliationErrorResponse(detail=detail).model_dump(
            mode="json"
        ),
    )


async def reconcile_current_inventory_endpoint() -> (
    CurrentInventoryReconciliationResult | JSONResponse
):
    """Reconcile the server's current catalog without caller-owned input."""

    try:
        return await asyncio.to_thread(reconcile_current_authoring_inventory)
    except ContentProductionClassificationValidationError:
        return _error_response(_INVALID_DETAIL)
    except ValueError:
        return _error_response(_CONFLICT_DETAIL)


def register_content_current_inventory_reconciliation_route(router: APIRouter) -> None:
    router.add_api_route(
        _ROUTE,
        reconcile_current_inventory_endpoint,
        methods=["POST"],
        response_model=CurrentInventoryReconciliationResult,
        responses={409: {"model": CurrentInventoryReconciliationErrorResponse}},
        tags=["content"],
    )


__all__ = [
    "CurrentInventoryReconciliationErrorResponse",
    "register_content_current_inventory_reconciliation_route",
    "reconcile_current_inventory_endpoint",
]
