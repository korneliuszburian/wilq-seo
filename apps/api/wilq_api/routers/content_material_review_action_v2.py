"""Public local preview/read seam for ActionObject-owned material approval."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from wilq.content.workflow.current_material_text import (
    CurrentMaterialTextBlocked,
    CurrentMaterialTextExact,
    read_exact_current_material_text,
)
from wilq.content.workflow.evidence_acquisition_snapshot import WordPressCurrentPageSnapshotAdapter
from wilq.content.workflow.material_review import (
    CatalogLoader,
    Clock,
    ContentMaterialReviewPreview,
    MaterialReaderFactory,
    MaterialReviewConflictError,
    MaterialReviewNotFoundError,
)
from wilq.content.workflow.material_review_action_v2 import (
    build_current_material_review_action_preview_v2,
    load_current_material_review_action_v2,
    parse_material_review_action_preview,
)
from wilq.content.workflow.store.store import ContentWorkflowStore, content_workflow_store
from wilq.content.workflow.workspace.catalog import build_content_inventory_catalog_cached
from wilq.schemas import ActionObject, ContentDecisionItem
from wilq.schemas.core import utc_now


class MaterialReviewActionReadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    response_type: Literal["content_material_review_action_v2"] = (
        "content_material_review_action_v2"
    )
    status: Literal["preview_ready"] = "preview_ready"
    action_id: str
    action: ActionObject
    preview: ContentMaterialReviewPreview
    external_write_attempted: Literal[False] = False
    generation_allowed: Literal[False] = False


class MaterialReviewActionBlockedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    response_type: Literal["content_material_review_action_v2"] = (
        "content_material_review_action_v2"
    )
    status: Literal["blocked"] = "blocked"
    work_item_id: str
    blocker_code: Literal[
        "material_review_work_item_missing",
        "material_review_source_stale",
        "material_review_context_invalid",
        "material_review_source_unavailable",
    ]
    blocker_owner: Literal["WILQ content workflow", "WILQ WordPress connector"]
    evidence_ids: list[str] = Field(default_factory=list)
    safe_next_step: str
    external_write_attempted: Literal[False] = False
    generation_allowed: Literal[False] = False


StoreFactory = Callable[[], ContentWorkflowStore]
SelectedItemLoader = Callable[[str], ContentDecisionItem | None]
AdapterFactory = Callable[[], WordPressCurrentPageSnapshotAdapter]


def register_content_material_review_action_v2_routes(
    router: APIRouter,
    *,
    store_factory: StoreFactory | None = None,
    catalog_loader: CatalogLoader = build_content_inventory_catalog_cached,
    selected_item_loader: SelectedItemLoader | None = None,
    adapter_factory: AdapterFactory | None = None,
    material_reader_factory: MaterialReaderFactory | None = None,
    clock: Clock = utc_now,
) -> None:
    make_store = store_factory or (lambda: content_workflow_store())
    make_selected = selected_item_loader or _selected_item_loader

    @router.post(
        "/api/content/work-items/{work_item_id}/material-review-action/preview",
        response_model=MaterialReviewActionReadResponse,
        responses={409: {"model": MaterialReviewActionBlockedResponse}},
    )
    def preview_action(
        work_item_id: str,
    ) -> MaterialReviewActionReadResponse | JSONResponse:
        try:
            action = build_current_material_review_action_preview_v2(
                work_item_id,
                store=make_store(),
                catalog_loader=catalog_loader,
                selected_item_loader=make_selected,
                adapter=_build_adapter(adapter_factory),
                material_reader_factory=material_reader_factory,
                clock=clock,
            )
        except (MaterialReviewNotFoundError, ValueError, RuntimeError) as error:
            blocked = _blocked_material_review_action(work_item_id, error)
            return JSONResponse(status_code=409, content=blocked.model_dump(mode="json"))
        preview = parse_material_review_action_preview(action.payload["material_review_preview"])
        return MaterialReviewActionReadResponse(
            action_id=action.id,
            action=action,
            preview=preview,
        )

    @router.get(
        "/api/content/work-items/{work_item_id}/material-review-action/{action_id}",
        response_model=MaterialReviewActionReadResponse,
    )
    def read_action(work_item_id: str, action_id: str) -> MaterialReviewActionReadResponse:
        action = load_current_material_review_action_v2(action_id, store=make_store())
        if action is None:
            raise HTTPException(status_code=404, detail="material_review_action_not_found")
        preview = parse_material_review_action_preview(action.payload["material_review_preview"])
        if preview.work_item_id != work_item_id:
            raise HTTPException(status_code=404, detail="material_review_action_not_found")
        return MaterialReviewActionReadResponse(
            action_id=action.id,
            action=action,
            preview=preview,
        )

    @router.get(
        "/api/content/work-items/{work_item_id}/material-review-action/{action_id}/text",
        response_model=CurrentMaterialTextExact,
        responses={409: {"model": CurrentMaterialTextBlocked}},
    )
    def read_action_text(
        work_item_id: str, action_id: str
    ) -> CurrentMaterialTextExact | JSONResponse:
        adapter = _build_adapter(adapter_factory) or WordPressCurrentPageSnapshotAdapter(
            material_reader=(
                material_reader_factory() if material_reader_factory is not None else None
            ),
            clock=clock,
        )
        result = read_exact_current_material_text(
            work_item_id=work_item_id,
            action_id=action_id,
            store=make_store(),
            adapter=adapter,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="material_review_action_not_found")
        if isinstance(result, CurrentMaterialTextBlocked):
            return JSONResponse(status_code=409, content=result.model_dump(mode="json"))
        return result


def _build_adapter(
    factory: AdapterFactory | None,
) -> WordPressCurrentPageSnapshotAdapter | None:
    return None if factory is None else factory()


def _blocked_material_review_action(
    work_item_id: str, error: MaterialReviewNotFoundError | ValueError | RuntimeError
) -> MaterialReviewActionBlockedResponse:
    if isinstance(error, MaterialReviewNotFoundError):
        return MaterialReviewActionBlockedResponse(
            work_item_id=work_item_id,
            blocker_code="material_review_work_item_missing",
            blocker_owner="WILQ content workflow",
            safe_next_step="Odczytaj katalog i wybierz istniejącą stronę do review.",
        )
    if isinstance(error, MaterialReviewConflictError) and "observation_stale" in str(error):
        return MaterialReviewActionBlockedResponse(
            work_item_id=work_item_id,
            blocker_code="material_review_source_stale",
            blocker_owner="WILQ WordPress connector",
            safe_next_step="Odśwież dokładny odczyt materiału tej strony z WordPress.",
        )
    if isinstance(error, RuntimeError):
        return MaterialReviewActionBlockedResponse(
            work_item_id=work_item_id,
            blocker_code="material_review_source_unavailable",
            blocker_owner="WILQ WordPress connector",
            safe_next_step="Ponów odczyt źródła WordPress dla tego URL-a.",
        )
    return MaterialReviewActionBlockedResponse(
        work_item_id=work_item_id,
        blocker_code="material_review_context_invalid",
        blocker_owner="WILQ content workflow",
        safe_next_step="Przygotuj nowe preview dokładnego materiału tej strony.",
    )


def _selected_item_loader(work_item_id: str) -> ContentDecisionItem | None:
    from wilq.content.workflow.decisions.inventory_binding import inventory_decision_for_work_item

    return inventory_decision_for_work_item(
        work_item_id,
        read_material=True,
        include_all_metric_facts=True,
    )


__all__ = ["register_content_material_review_action_v2_routes"]
