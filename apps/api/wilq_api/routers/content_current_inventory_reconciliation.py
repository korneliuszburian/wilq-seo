"""Public server-owned entrypoint for current inventory reconciliation."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from wilq.content.workflow.current_inventory_reconciliation import (
    CurrentInventoryReconciliationBlocked,
    preflight_current_inventory_reconciliation,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationValidationError,
)

_ROUTE = "/api/content/inventory/reconciliation"
_ERROR_CODE_PATTERN = r"^[a-z][a-z0-9_]*$"
_INVALID_DETAIL = "current_inventory_reconciliation_invalid"
_CONFLICT_DETAIL = "current_inventory_reconciliation_conflict"
_INCOMPLETE_COVERAGE = "inventory_coverage_incomplete"
_ELIGIBLE_SCOPE_POLICY_UNAVAILABLE = "current_eligible_scope_policy_unavailable"
_SOURCE_EVIDENCE_MISSING = "inventory_source_evidence_missing"


class CurrentInventoryReconciliationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str = Field(pattern=_ERROR_CODE_PATTERN)
    owner: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)
    coverage_status: str = Field(min_length=1)
    evidence_ids: list[str]


def _error_response(
    detail: str,
    *,
    coverage_status: str = "unknown",
    evidence_ids: list[str] | None = None,
) -> JSONResponse:
    owner, safe_next_step = {
        _INCOMPLETE_COVERAGE: (
            "WILQ WordPress connector",
            "Zweryfikuj kompletność bieżącego odczytu publicznej mapy witryny WordPress.",
        ),
        _SOURCE_EVIDENCE_MISSING: (
            "WILQ WordPress connector",
            "Ukończ bieżący odczyt vendor_read WordPress z identyfikatorami dowodów.",
        ),
        _ELIGIBLE_SCOPE_POLICY_UNAVAILABLE: (
            "WILQ content workflow",
            "Zaimplementuj dokładną politykę bieżącego zakresu kwalifikującego "
            "z kompletnego katalogu.",
        ),
    }.get(
        detail,
        (
            "WILQ content workflow",
            "Odśwież inwentarz przed ponowną próbą reconciliacji.",
        ),
    )
    return JSONResponse(
        status_code=409,
        content=CurrentInventoryReconciliationErrorResponse(
            detail=detail,
            owner=owner,
            safe_next_step=safe_next_step,
            coverage_status=coverage_status,
            evidence_ids=evidence_ids or [],
        ).model_dump(mode="json"),
    )


async def reconcile_current_inventory_endpoint() -> JSONResponse:
    """Return the typed blocker before any reconciliation write can run."""

    try:
        await asyncio.to_thread(preflight_current_inventory_reconciliation)
    except CurrentInventoryReconciliationBlocked as blocker:
        return _error_response(
            blocker.detail,
            coverage_status=blocker.coverage_status,
            evidence_ids=blocker.evidence_ids,
        )
    except ContentProductionClassificationValidationError:
        return _error_response(_INVALID_DETAIL)
    except ValueError:
        return _error_response(_CONFLICT_DETAIL)
    return _error_response(_CONFLICT_DETAIL)


def register_content_current_inventory_reconciliation_route(router: APIRouter) -> None:
    router.add_api_route(
        _ROUTE,
        reconcile_current_inventory_endpoint,
        methods=["POST"],
        status_code=409,
        responses={409: {"model": CurrentInventoryReconciliationErrorResponse}},
        tags=["content"],
    )


__all__ = [
    "CurrentInventoryReconciliationErrorResponse",
    "register_content_current_inventory_reconciliation_route",
    "reconcile_current_inventory_endpoint",
]
