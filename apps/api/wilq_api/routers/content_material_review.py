"""Public preview/review/readback routes for current WordPress material."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from wilq.content.workflow.evidence_acquisition_snapshot import WordPressCurrentPageSnapshotAdapter
from wilq.content.workflow.material_review import (
    CatalogLoader,
    Clock,
    ContentMaterialReviewCommand,
    ContentMaterialReviewPreviewResponse,
    ContentMaterialReviewReadResponse,
    ContentMaterialReviewResponse,
    MaterialReaderFactory,
    MaterialReviewConflictError,
    MaterialReviewNotFoundError,
    MaterialReviewStore,
    build_content_material_review_preview,
    build_content_material_review_receipt,
    read_content_material_review,
    revalidate_content_material_review_preview,
)
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.workspace.catalog import build_content_inventory_catalog_cached
from wilq.schemas import ContentDecisionItem
from wilq.schemas.core import utc_now

SelectedItemLoader = Callable[[str], ContentDecisionItem | None]
StoreFactory = Callable[[], MaterialReviewStore]
AdapterFactory = Callable[[], WordPressCurrentPageSnapshotAdapter]


def register_content_material_review_routes(
    router: APIRouter,
    *,
    store_factory: StoreFactory | None = None,
    catalog_loader: CatalogLoader = build_content_inventory_catalog_cached,
    selected_item_loader: SelectedItemLoader | None = None,
    adapter_factory: AdapterFactory | None = None,
    material_reader_factory: MaterialReaderFactory | None = None,
    clock: Clock = utc_now,
) -> None:
    """Register the public material review lifecycle.

    Factories are explicit ports so route/service tests can isolate the SQLite
    store and current-page reader without changing production connector policy.
    """

    make_store = store_factory or content_workflow_store
    make_selected = selected_item_loader or _selected_item_loader

    preview_path = "/api/content/work-items/{work_item_id}/material-review/preview"
    review_path = "/api/content/work-items/{work_item_id}/material-review"

    @router.post(
        preview_path,
        response_model=ContentMaterialReviewPreviewResponse,
    )
    def material_review_preview_endpoint(
        work_item_id: str,
    ) -> ContentMaterialReviewPreviewResponse:
        return _preview_endpoint(
            work_item_id,
            store_factory=make_store,
            catalog_loader=catalog_loader,
            selected_item_loader=make_selected,
            adapter_factory=adapter_factory,
            material_reader_factory=material_reader_factory,
            clock=clock,
        )

    @router.post(
        review_path,
        response_model=ContentMaterialReviewResponse,
        responses={409: {"model": ContentMaterialReviewResponse}},
    )
    def material_review_endpoint(
        work_item_id: str,
        request: ContentMaterialReviewCommand,
    ) -> ContentMaterialReviewResponse | JSONResponse:
        return _review_endpoint(
            work_item_id,
            request,
            store_factory=make_store,
            catalog_loader=catalog_loader,
            selected_item_loader=make_selected,
            adapter_factory=adapter_factory,
            material_reader_factory=material_reader_factory,
            clock=clock,
        )

    @router.get(
        review_path,
        response_model=ContentMaterialReviewReadResponse,
    )
    def material_review_read_endpoint(work_item_id: str) -> ContentMaterialReviewReadResponse:
        return _read_endpoint(
            work_item_id,
            store_factory=make_store,
            catalog_loader=catalog_loader,
            selected_item_loader=make_selected,
            adapter_factory=adapter_factory,
            material_reader_factory=material_reader_factory,
            clock=clock,
        )


def _preview_endpoint(
    work_item_id: str,
    *,
    store_factory: StoreFactory,
    catalog_loader: CatalogLoader,
    selected_item_loader: SelectedItemLoader,
    adapter_factory: AdapterFactory | None,
    material_reader_factory: MaterialReaderFactory | None,
    clock: Clock,
) -> ContentMaterialReviewPreviewResponse:
    try:
        preview = build_content_material_review_preview(
            work_item_id=work_item_id,
            catalog_loader=catalog_loader,
            selected_item_loader=selected_item_loader,
            adapter=_build_adapter(adapter_factory),
            material_reader_factory=material_reader_factory,
            clock=clock,
        )
        stored = store_factory().record_content_material_review_preview(preview)
    except MaterialReviewNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (MaterialReviewConflictError, RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if stored.status == "conflict":
        raise HTTPException(status_code=409, detail="content_material_review_preview_conflict")
    return ContentMaterialReviewPreviewResponse(preview=stored.preview)


def _review_endpoint(
    work_item_id: str,
    request: ContentMaterialReviewCommand,
    *,
    store_factory: StoreFactory,
    catalog_loader: CatalogLoader,
    selected_item_loader: SelectedItemLoader,
    adapter_factory: AdapterFactory | None,
    material_reader_factory: MaterialReaderFactory | None,
    clock: Clock,
) -> ContentMaterialReviewResponse | JSONResponse:
    store = store_factory()
    preview = store.load_content_material_review_preview(request.preview_id)
    if (
        preview is None
        or preview.preview_digest != request.preview_digest
        or preview.work_item_id != work_item_id
    ):
        raise HTTPException(status_code=409, detail="content_material_review_preview_mismatch")
    try:
        revalidate_content_material_review_preview(
            work_item_id=work_item_id,
            preview=preview,
            catalog_loader=catalog_loader,
            selected_item_loader=selected_item_loader,
            adapter=_build_adapter(adapter_factory),
            material_reader_factory=material_reader_factory,
            clock=clock,
        )
        receipt = build_content_material_review_receipt(
            work_item_id=work_item_id,
            command=request,
            reviewed_at=clock(),
        )
        stored = store.record_content_material_review(receipt)
        current = _read_endpoint_result(
            work_item_id,
            store=store,
            catalog_loader=catalog_loader,
            selected_item_loader=selected_item_loader,
            adapter_factory=adapter_factory,
            material_reader_factory=material_reader_factory,
            clock=clock,
        )
    except (MaterialReviewConflictError, RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    response = ContentMaterialReviewResponse(
        status=stored.status,
        review=stored.review,
        current=current,
    )
    if stored.status == "conflict":
        return JSONResponse(status_code=409, content=response.model_dump(mode="json"))
    return response


def _read_endpoint(
    work_item_id: str,
    *,
    store_factory: StoreFactory,
    catalog_loader: CatalogLoader,
    selected_item_loader: SelectedItemLoader,
    adapter_factory: AdapterFactory | None,
    material_reader_factory: MaterialReaderFactory | None,
    clock: Clock,
) -> ContentMaterialReviewReadResponse:
    return _read_endpoint_result(
        work_item_id,
        store=store_factory(),
        catalog_loader=catalog_loader,
        selected_item_loader=selected_item_loader,
        adapter_factory=adapter_factory,
        material_reader_factory=material_reader_factory,
        clock=clock,
    )


def _read_endpoint_result(
    work_item_id: str,
    *,
    store: MaterialReviewStore,
    catalog_loader: CatalogLoader,
    selected_item_loader: SelectedItemLoader,
    adapter_factory: AdapterFactory | None,
    material_reader_factory: MaterialReaderFactory | None,
    clock: Clock,
) -> ContentMaterialReviewReadResponse:
    return read_content_material_review(
        work_item_id=work_item_id,
        store=store,
        catalog_loader=catalog_loader,
        selected_item_loader=selected_item_loader,
        adapter=_build_adapter(adapter_factory),
        material_reader_factory=material_reader_factory,
        clock=clock,
    )


def _build_adapter(
    adapter_factory: AdapterFactory | None,
) -> WordPressCurrentPageSnapshotAdapter | None:
    return None if adapter_factory is None else adapter_factory()


def _selected_item_loader(work_item_id: str) -> ContentDecisionItem | None:
    from wilq.content.workflow.decisions.inventory_binding import inventory_decision_for_work_item

    return inventory_decision_for_work_item(
        work_item_id,
        read_material=True,
        include_all_metric_facts=True,
    )


__all__ = ["register_content_material_review_routes"]
