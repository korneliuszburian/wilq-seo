"""Public server-owned entrypoint for current inventory reconciliation."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from wilq.content.workflow.current_inventory_reconciliation import (
    CurrentInventoryReconciliationBlocked,
    CurrentInventoryScopeResponse,
    build_current_inventory_scope,
)

_ROUTE = "/api/content/inventory/reconciliation"
_ERROR_CODE_PATTERN = r"^[a-z][a-z0-9_]*$"
_CONFLICT_DETAIL = "current_inventory_reconciliation_conflict"
_INCOMPLETE_COVERAGE = "inventory_coverage_incomplete"
_SOURCE_EVIDENCE_MISSING = "inventory_source_evidence_missing"
_SOURCE_FRESHNESS_BLOCKED = {
    "inventory_source_freshness_blocked",
    "inventory_source_freshness_batch_mismatch",
    "inventory_source_run_evidence_mismatch",
    "inventory_source_run_incomplete",
}
_SITEMAP_INTEGRITY_BLOCKED = {
    "inventory_sitemap_count_mismatch",
    "inventory_sitemap_duplicate_url",
    "inventory_sitemap_fact_invalid",
}
_CATALOG_BINDING_BLOCKED = {
    "inventory_catalog_binding_invalid",
    "inventory_catalog_outside_sitemap",
}


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
    }.get(
        detail,
        (
            "WILQ content workflow",
            "Odśwież inwentarz przed ponowną próbą reconciliacji.",
        ),
    )
    if detail in _SOURCE_FRESHNESS_BLOCKED:
        owner = "WILQ WordPress connector"
        safe_next_step = "Odśwież WordPress przez bieżący vendor_read przed kwalifikacją URL-i."
    elif detail in _SITEMAP_INTEGRITY_BLOCKED:
        owner = "WILQ WordPress connector"
        safe_next_step = "Zweryfikuj kompletność i unikalność bieżących rekordów sitemap WordPress."
    elif detail in _CATALOG_BINDING_BLOCKED:
        owner = "WILQ content workflow"
        safe_next_step = "Napraw dokładne powiązanie bieżącego katalogu z sitemap WordPress."
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
    """Return the current read-only sitemap scope, or a typed source blocker."""

    try:
        scope = await asyncio.to_thread(build_current_inventory_scope)
    except CurrentInventoryReconciliationBlocked as blocker:
        return _error_response(
            blocker.detail,
            coverage_status=blocker.coverage_status,
            evidence_ids=blocker.evidence_ids,
        )
    except ValueError:
        return _error_response(_CONFLICT_DETAIL)
    return JSONResponse(status_code=200, content=scope.model_dump(mode="json"))


def register_content_current_inventory_reconciliation_route(router: APIRouter) -> None:
    router.add_api_route(
        _ROUTE,
        reconcile_current_inventory_endpoint,
        methods=["POST"],
        response_model=CurrentInventoryScopeResponse,
        responses={
            200: {"model": CurrentInventoryScopeResponse},
            409: {"model": CurrentInventoryReconciliationErrorResponse},
        },
        tags=["content"],
    )


__all__ = [
    "CurrentInventoryReconciliationErrorResponse",
    "register_content_current_inventory_reconciliation_route",
    "reconcile_current_inventory_endpoint",
]
