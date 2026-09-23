"""Read-only per-URL current page evidence endpoint."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter

from wilq.connectors.registry import get_connector_status
from wilq.content.workflow.current_page_evidence import (
    CurrentPageEvidenceResponse,
    build_current_page_evidence,
)
from wilq.content.workflow.evidence_acquisition_snapshot import WordPressCurrentPageSnapshotAdapter
from wilq.content.workflow.material_review import (
    CatalogLoader,
    MaterialReaderFactory,
    MaterialReviewStore,
    SelectedItemLoader,
    read_content_material_review,
)
from wilq.content.workflow.store.store import content_workflow_store
from wilq.content.workflow.workspace.catalog import (
    build_content_inventory_catalog_cached,
    latest_wordpress_vendor_read_evidence_ids,
)

StoreFactory = Callable[[], MaterialReviewStore]
AdapterFactory = Callable[[], WordPressCurrentPageSnapshotAdapter]
FreshnessLoader = Callable[[], str | None]
EvidenceIdsLoader = Callable[[], tuple[str, ...]]


def register_content_current_page_evidence_route(
    router: APIRouter,
    *,
    store_factory: StoreFactory | None = None,
    catalog_loader: CatalogLoader = build_content_inventory_catalog_cached,
    selected_item_loader: SelectedItemLoader | None = None,
    adapter_factory: AdapterFactory | None = None,
    material_reader_factory: MaterialReaderFactory | None = None,
    freshness_loader: FreshnessLoader | None = None,
    evidence_ids_loader: EvidenceIdsLoader = latest_wordpress_vendor_read_evidence_ids,
) -> None:
    make_store = store_factory or content_workflow_store
    make_freshness = freshness_loader or _wordpress_freshness_state

    @router.get(
        "/api/content/work-items/{work_item_id}/current-page-evidence",
        response_model=CurrentPageEvidenceResponse,
    )
    def current_page_evidence_endpoint(work_item_id: str) -> CurrentPageEvidenceResponse:
        return read_current_page_evidence(
            work_item_id=work_item_id,
            store_factory=make_store,
            catalog_loader=catalog_loader,
            selected_item_loader=selected_item_loader,
            adapter_factory=adapter_factory,
            material_reader_factory=material_reader_factory,
            freshness_loader=make_freshness,
            evidence_ids_loader=evidence_ids_loader,
        )


def read_current_page_evidence(
    *,
    work_item_id: str,
    store_factory: StoreFactory = content_workflow_store,
    catalog_loader: CatalogLoader = build_content_inventory_catalog_cached,
    selected_item_loader: SelectedItemLoader | None = None,
    adapter_factory: AdapterFactory | None = None,
    material_reader_factory: MaterialReaderFactory | None = None,
    freshness_loader: FreshnessLoader | None = None,
    evidence_ids_loader: EvidenceIdsLoader = latest_wordpress_vendor_read_evidence_ids,
) -> CurrentPageEvidenceResponse:
    """Resolve the same deep current-page evidence view used by its read route."""
    catalog = catalog_loader()
    latest_evidence_ids = evidence_ids_loader()
    freshness_state = (freshness_loader or _wordpress_freshness_state)()
    eligibility = build_current_page_evidence(
        work_item_id=work_item_id,
        catalog=catalog,
        latest_wordpress_evidence_ids=latest_evidence_ids,
        wordpress_freshness_state=freshness_state,
    )
    if eligibility.blocker_code != "material_review_missing_or_stale":
        return eligibility
    current_review = read_content_material_review(
        work_item_id=work_item_id,
        store=store_factory(),
        catalog_loader=lambda: catalog,
        selected_item_loader=selected_item_loader,
        adapter=None if adapter_factory is None else adapter_factory(),
        material_reader_factory=material_reader_factory,
    )
    return build_current_page_evidence(
        work_item_id=work_item_id,
        catalog=catalog,
        latest_wordpress_evidence_ids=latest_evidence_ids,
        wordpress_freshness_state=freshness_state,
        material_review=current_review,
    )


def _wordpress_freshness_state() -> str | None:
    status = get_connector_status("wordpress_ekologus")
    return None if status is None else status.freshness.state


__all__ = ["read_current_page_evidence", "register_content_current_page_evidence_route"]
