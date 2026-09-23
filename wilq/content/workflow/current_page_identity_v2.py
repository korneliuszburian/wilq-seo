"""Read-only projection of the current page identity from an approved KEEP receipt."""

from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.canonical.urls import content_normalized_path, content_normalized_url
from wilq.content.workflow.current_page_disposition_v2 import (
    CurrentPageDispositionV2Receipt,
)
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse

CurrentPageIdentityBlockerCode = Literal[
    "source_catalog_incomplete",
    "source_evidence_drift",
    "source_freshness_blocked",
    "page_absent_from_catalog",
    "page_material_url_only",
    "material_review_missing_or_stale",
    "missing_approved_keep_receipt",
    "page_identity_changed",
    "material_meaning_changed",
]
CurrentPageIdentityBlockerOwner = Literal[
    "WILQ content workflow",
    "WILQ WordPress connector",
    "Wilku",
]


class CurrentPageIdentityV2Response(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["exact_current", "blocked"]
    work_item_id: str
    page_url: str | None = None
    normalized_page_url: str | None = None
    canonical_path: str | None = None
    material_meaning_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    receipt_id: str | None = None
    receipt_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    original_evidence_ids: list[str] = Field(default_factory=list)
    apply_evidence_ids: list[str] = Field(default_factory=list)
    current_evidence_ids: list[str] = Field(default_factory=list)
    pending_action_id: str | None = None
    blocker_code: CurrentPageIdentityBlockerCode | None = None
    blocker_owner: CurrentPageIdentityBlockerOwner | None = None
    safe_next_step: str | None = None
    generation_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_status_shape(self) -> CurrentPageIdentityV2Response:
        if self.status == "exact_current":
            if (
                self.page_url is None
                or self.normalized_page_url is None
                or self.canonical_path is None
                or self.material_meaning_digest is None
                or self.receipt_id is None
                or self.receipt_digest is None
            ):
                raise ValueError("Exact current identity requires its URL, meaning and receipt.")
            if self.blocker_code or self.blocker_owner or self.safe_next_step:
                raise ValueError("Exact current identity cannot carry blocker fields.")
            if self.pending_action_id is not None:
                raise ValueError("Exact current identity cannot carry a pending action.")
        elif not self.blocker_code or not self.blocker_owner or not self.safe_next_step:
            raise ValueError("Blocked identity requires exactly one typed blocker and next step.")
        return self


def project_current_page_identity_v2(
    *,
    evidence: CurrentPageEvidenceResponse,
    latest_receipt: CurrentPageDispositionV2Receipt | None,
    pending_action_id: str | None = None,
) -> CurrentPageIdentityV2Response:
    """Grant current identity only when the latest v2 KEEP receipt matches current material."""

    current_ids = sorted(set(evidence.current_evidence_ids + evidence.catalog_evidence_ids))
    receipt = latest_receipt
    if evidence.status == "reviewed_material_current":
        assert evidence.page_url is not None and evidence.material_meaning_digest is not None
        if receipt is not None and not _receipt_matches_page_identity(receipt, evidence):
            return _blocked_current_identity(
                evidence=evidence,
                receipt=receipt,
                current_ids=current_ids,
                pending_action_id=pending_action_id,
                blocker_code="page_identity_changed",
                next_step=(
                    "Wilku: sprawdź i zatwierdź dokładny ActionObject KEEP dla bieżącego URL-a."
                    if pending_action_id is not None
                    else "Zweryfikuj bieżący URL i przygotuj audytowany ActionObject KEEP."
                ),
            )
        if receipt is not None and _receipt_matches_current(receipt, evidence):
            return CurrentPageIdentityV2Response(
                status="exact_current",
                work_item_id=evidence.work_item_id,
                page_url=evidence.page_url,
                normalized_page_url=receipt.snapshot.normalized_page_url,
                canonical_path=receipt.snapshot.canonical_path,
                material_meaning_digest=evidence.material_meaning_digest,
                receipt_id=receipt.receipt_id,
                receipt_digest=receipt.receipt_digest,
                original_evidence_ids=sorted(
                    set(
                        receipt.snapshot.current_evidence_ids
                        + receipt.snapshot.catalog_evidence_ids
                    )
                ),
                apply_evidence_ids=list(receipt.verification_evidence_ids),
                current_evidence_ids=current_ids,
            )
        return _blocked_current_identity(
            evidence=evidence,
            receipt=receipt,
            current_ids=current_ids,
            pending_action_id=pending_action_id,
            blocker_code=(
                "missing_approved_keep_receipt"
                if receipt is None
                else "material_meaning_changed"
            ),
            next_step=(
                "Wilku: sprawdź i zatwierdź dokładny ActionObject KEEP dla bieżącego materiału."
                if pending_action_id is not None
                else "Przygotuj audytowany ActionObject KEEP dla dokładnego bieżącego materiału."
            ),
        )
    return CurrentPageIdentityV2Response(
        status="blocked",
        work_item_id=evidence.work_item_id,
        receipt_id=None if receipt is None else receipt.receipt_id,
        receipt_digest=None if receipt is None else receipt.receipt_digest,
        original_evidence_ids=(
            []
            if receipt is None
            else sorted(
                set(
                    receipt.snapshot.current_evidence_ids
                    + receipt.snapshot.catalog_evidence_ids
                )
            )
        ),
        apply_evidence_ids=([] if receipt is None else list(receipt.verification_evidence_ids)),
        current_evidence_ids=current_ids,
        blocker_code=cast(CurrentPageIdentityBlockerCode, evidence.blocker_code),
        blocker_owner=cast(CurrentPageIdentityBlockerOwner, evidence.blocker_owner),
        safe_next_step=evidence.safe_next_step,
    )


def _receipt_matches_current(
    receipt: CurrentPageDispositionV2Receipt,
    evidence: CurrentPageEvidenceResponse,
) -> bool:
    snapshot = receipt.snapshot
    return (
        receipt.generation_allowed is False
        and snapshot.generation_allowed is False
        and snapshot.disposition == "keep"
        and _receipt_matches_page_identity(receipt, evidence)
        and snapshot.material_meaning_digest == evidence.material_meaning_digest
    )


def _receipt_matches_page_identity(
    receipt: CurrentPageDispositionV2Receipt,
    evidence: CurrentPageEvidenceResponse,
) -> bool:
    snapshot = receipt.snapshot
    page_url = evidence.page_url or ""
    return (
        snapshot.work_item_id == evidence.work_item_id
        and snapshot.page_url == evidence.page_url
        and snapshot.normalized_page_url == content_normalized_url(page_url)
        and snapshot.canonical_path == content_normalized_path(page_url)
    )


def _blocked_current_identity(
    *,
    evidence: CurrentPageEvidenceResponse,
    receipt: CurrentPageDispositionV2Receipt | None,
    current_ids: list[str],
    pending_action_id: str | None,
    blocker_code: CurrentPageIdentityBlockerCode,
    next_step: str,
) -> CurrentPageIdentityV2Response:
    page_url = evidence.page_url
    return CurrentPageIdentityV2Response(
        status="blocked",
        work_item_id=evidence.work_item_id,
        page_url=page_url,
        normalized_page_url=(None if page_url is None else content_normalized_url(page_url)),
        canonical_path=(None if page_url is None else content_normalized_path(page_url)),
        material_meaning_digest=evidence.material_meaning_digest,
        receipt_id=None if receipt is None else receipt.receipt_id,
        receipt_digest=None if receipt is None else receipt.receipt_digest,
        original_evidence_ids=(
            []
            if receipt is None
            else sorted(
                set(receipt.snapshot.current_evidence_ids + receipt.snapshot.catalog_evidence_ids)
            )
        ),
        apply_evidence_ids=([] if receipt is None else list(receipt.verification_evidence_ids)),
        current_evidence_ids=current_ids,
        pending_action_id=pending_action_id,
        blocker_code=blocker_code,
        blocker_owner="Wilku" if pending_action_id is not None else "WILQ content workflow",
        safe_next_step=next_step,
    )


__all__ = [
    "CurrentPageIdentityBlockerCode",
    "CurrentPageIdentityBlockerOwner",
    "CurrentPageIdentityV2Response",
    "project_current_page_identity_v2",
]
