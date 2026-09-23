"""Typed, read-only current material decision for one inventory URL."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.canonical.urls import content_normalized_path
from wilq.content.workflow.material_review import ContentMaterialReviewReadResponse
from wilq.content.workflow.workspace.catalog import (
    ContentInventoryCatalogItem,
    ContentInventoryCatalogResponse,
)

CurrentPageEvidenceStatus = Literal["reviewed_material_current", "blocked"]
CurrentPageEvidenceBlockerCode = Literal[
    "source_catalog_incomplete",
    "source_evidence_drift",
    "source_freshness_blocked",
    "page_absent_from_catalog",
    "page_material_url_only",
    "material_review_missing_or_stale",
]


class CurrentPageEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_type: Literal["current_page_evidence"] = "current_page_evidence"
    status: CurrentPageEvidenceStatus
    decision: str
    work_item_id: str
    page_url: str | None = None
    generation_allowed: Literal[False] = False
    material_meaning_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    current_evidence_ids: list[str] = Field(default_factory=list)
    catalog_evidence_ids: list[str] = Field(default_factory=list)
    blocker_code: CurrentPageEvidenceBlockerCode | None = None
    blocker_owner: str | None = None
    safe_next_step: str

    @model_validator(mode="after")
    def validate_decision_shape(self) -> CurrentPageEvidenceResponse:
        if self.status == "reviewed_material_current":
            if (
                self.material_meaning_digest is None
                or not self.current_evidence_ids
                or not self.catalog_evidence_ids
            ):
                raise ValueError("Current material requires its semantic digest and evidence.")
            if self.blocker_code is not None or self.blocker_owner is not None:
                raise ValueError("Current material cannot carry a blocker.")
        elif (
            self.blocker_code is None
            or self.blocker_owner is None
            or self.material_meaning_digest is not None
        ):
            raise ValueError("Blocked page evidence requires one blocker and no digest.")
        return self


def build_current_page_evidence(
    *,
    work_item_id: str,
    catalog: ContentInventoryCatalogResponse,
    latest_wordpress_evidence_ids: tuple[str, ...],
    wordpress_freshness_state: str | None,
    material_review: ContentMaterialReviewReadResponse | None = None,
) -> CurrentPageEvidenceResponse:
    """Project catalog, connector state, and the existing exact review read."""
    item, blocker = _current_catalog_blocker(
        work_item_id=work_item_id,
        catalog=catalog,
        latest_wordpress_evidence_ids=latest_wordpress_evidence_ids,
        wordpress_freshness_state=wordpress_freshness_state,
    )
    if blocker is not None:
        return blocker
    assert item is not None
    if material_review is None or material_review.status != "approved_current":
        return _blocked(
            work_item_id,
            code="material_review_missing_or_stale",
            decision="Bieżący materiał strony wymaga review albo ponownego sprawdzenia.",
            owner="WILQ content workflow",
            safe_next_step=(
                "Wymagana jest audytowana ActionObject ścieżka do review dokładnego materiału."
            ),
            item=item,
            catalog_evidence_ids=catalog.evidence_ids,
            latest_wordpress_evidence_ids=latest_wordpress_evidence_ids,
        )
    if not _material_review_matches_item(material_review, item, work_item_id):
        return _blocked(
            work_item_id,
            code="material_review_missing_or_stale",
            decision="Review materiału nie jest związany z dokładnym adresem z katalogu.",
            owner="WILQ content workflow",
            safe_next_step=(
                "Wymagana jest audytowana ActionObject ścieżka do review dokładnego materiału."
            ),
            item=item,
            catalog_evidence_ids=catalog.evidence_ids,
            latest_wordpress_evidence_ids=latest_wordpress_evidence_ids,
        )
    observation = material_review.current_observation
    assert observation is not None
    return CurrentPageEvidenceResponse(
        status="reviewed_material_current",
        decision="Materiał strony ma aktualne review dla bieżącego odczytu WordPress.",
        work_item_id=work_item_id,
        page_url=item.url,
        material_meaning_digest=material_review.material_meaning_digest,
        current_evidence_ids=sorted(set(observation.evidence_ids)),
        catalog_evidence_ids=sorted(set(catalog.evidence_ids)),
        safe_next_step=(
            "Przygotuj ActionObject dla tego dokładnego adresu do sprawdzenia przez Wilku."
        ),
    )


def read_current_page_evidence_current(work_item_id: str) -> CurrentPageEvidenceResponse:
    """Resolve current catalog, connector freshness, and exact material review."""
    from wilq.connectors.registry import get_connector_status
    from wilq.content.workflow.material_review import read_content_material_review
    from wilq.content.workflow.store.store import content_workflow_store
    from wilq.content.workflow.workspace.catalog import (
        build_content_inventory_catalog_cached,
        latest_wordpress_vendor_read_evidence_ids,
    )

    catalog = build_content_inventory_catalog_cached()
    evidence_ids = latest_wordpress_vendor_read_evidence_ids()
    connector = get_connector_status("wordpress_ekologus")
    freshness = None if connector is None else connector.freshness.state
    eligibility = build_current_page_evidence(
        work_item_id=work_item_id,
        catalog=catalog,
        latest_wordpress_evidence_ids=evidence_ids,
        wordpress_freshness_state=freshness,
    )
    if eligibility.blocker_code != "material_review_missing_or_stale":
        return eligibility
    review = read_content_material_review(
        work_item_id=work_item_id,
        store=content_workflow_store(),
        catalog_loader=lambda: catalog,
        adapter=None,
    )
    return build_current_page_evidence(
        work_item_id=work_item_id,
        catalog=catalog,
        latest_wordpress_evidence_ids=evidence_ids,
        wordpress_freshness_state=freshness,
        material_review=review,
    )


def _current_catalog_blocker(
    *,
    work_item_id: str,
    catalog: ContentInventoryCatalogResponse,
    latest_wordpress_evidence_ids: tuple[str, ...],
    wordpress_freshness_state: str | None,
) -> tuple[ContentInventoryCatalogItem | None, CurrentPageEvidenceResponse | None]:
    items = [item for item in catalog.items if item.work_item_id == work_item_id]
    item = items[0] if len(items) == 1 else None

    if catalog.status != "ready" or catalog.coverage.status != "complete":
        return item, _blocked(
            work_item_id,
            code="source_catalog_incomplete",
            decision="Nie można potwierdzić pełnego, bieżącego katalogu WordPress.",
            owner="WILQ WordPress connector",
            safe_next_step=(
                "Uzupełnij pełny odczyt katalogu WordPress i ponów sprawdzenie strony."
            ),
            item=item,
            catalog_evidence_ids=catalog.evidence_ids,
            latest_wordpress_evidence_ids=latest_wordpress_evidence_ids,
        )
    if item is None:
        return None, _blocked(
            work_item_id,
            code="page_absent_from_catalog",
            decision="Adres nie występuje dokładnie raz w bieżącym katalogu WordPress.",
            owner="WILQ content workflow",
            safe_next_step="Sprawdź kanoniczny adres strony w pełnym katalogu WordPress.",
            catalog_evidence_ids=catalog.evidence_ids,
            latest_wordpress_evidence_ids=latest_wordpress_evidence_ids,
        )
    if (
        item.source_connector != "wordpress_ekologus"
        or item.evidence_id not in catalog.evidence_ids
    ):
        return item, _blocked(
            work_item_id,
            code="source_catalog_incomplete",
            decision="Katalog nie wiąże strony z jej źródłem WordPress.",
            owner="WILQ WordPress connector",
            safe_next_step=(
                "Uzupełnij pełny odczyt katalogu WordPress i ponów sprawdzenie strony."
            ),
            item=item,
            catalog_evidence_ids=catalog.evidence_ids,
            latest_wordpress_evidence_ids=latest_wordpress_evidence_ids,
        )
    if (
        not latest_wordpress_evidence_ids
        or not catalog.evidence_ids
        or not set(catalog.evidence_ids).issubset(latest_wordpress_evidence_ids)
        or item.evidence_id not in latest_wordpress_evidence_ids
    ):
        return item, _blocked(
            work_item_id,
            code="source_evidence_drift",
            decision="Katalog strony nie odpowiada najnowszemu odczytowi WordPress.",
            owner="WILQ WordPress connector",
            safe_next_step=("Zsynchronizuj katalog z najnowszym odczytem WordPress."),
            item=item,
            catalog_evidence_ids=catalog.evidence_ids,
            latest_wordpress_evidence_ids=latest_wordpress_evidence_ids,
        )
    if wordpress_freshness_state != "fresh":
        return item, _blocked(
            work_item_id,
            code="source_freshness_blocked",
            decision="Odczyt WordPress jest nieświeży albo nie ma potwierdzonej świeżości.",
            owner="WILQ WordPress connector",
            safe_next_step="Odśwież dane WordPress i ponów sprawdzenie tej strony.",
            item=item,
            catalog_evidence_ids=catalog.evidence_ids,
            latest_wordpress_evidence_ids=latest_wordpress_evidence_ids,
        )
    if item.material_status == "url_only":
        return item, _blocked(
            work_item_id,
            code="page_material_url_only",
            decision="Katalog potwierdza adres, ale nie zawiera materiału strony do review.",
            owner="WILQ WordPress connector",
            safe_next_step=("Udostępnij bieżący materiał przez odczyt WordPress."),
            item=item,
            catalog_evidence_ids=catalog.evidence_ids,
            latest_wordpress_evidence_ids=latest_wordpress_evidence_ids,
        )
    return item, None


def _material_review_matches_item(
    material_review: ContentMaterialReviewReadResponse,
    item: ContentInventoryCatalogItem,
    work_item_id: str,
) -> bool:
    preview = material_review.preview
    observation = material_review.current_observation
    canonical_path = content_normalized_path(item.path)
    return (
        material_review.work_item_id == work_item_id
        and preview is not None
        and observation is not None
        and preview.public_url.rstrip("/") == item.url.rstrip("/")
        and preview.canonical_path == canonical_path
        and observation.source_url.rstrip("/") == item.url.rstrip("/")
        and observation.canonical_path == canonical_path
    )


def _blocked(
    work_item_id: str,
    *,
    code: CurrentPageEvidenceBlockerCode,
    decision: str,
    owner: str,
    safe_next_step: str,
    item: ContentInventoryCatalogItem | None = None,
    catalog_evidence_ids: list[str] | tuple[str, ...] = (),
    latest_wordpress_evidence_ids: tuple[str, ...] = (),
) -> CurrentPageEvidenceResponse:
    return CurrentPageEvidenceResponse(
        status="blocked",
        decision=decision,
        work_item_id=work_item_id,
        page_url=item.url if item else None,
        current_evidence_ids=sorted(set(latest_wordpress_evidence_ids)),
        catalog_evidence_ids=sorted(set(catalog_evidence_ids))
        or ([item.evidence_id] if item else []),
        blocker_code=code,
        blocker_owner=owner,
        safe_next_step=safe_next_step,
    )


__all__ = ["CurrentPageEvidenceResponse", "build_current_page_evidence"]
