"""Receiptless exact identity for a freshly observed current WordPress page."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.canonical.urls import content_is_safe_public_url, content_normalized_path
from wilq.content.workflow.current_page_evidence import (
    CurrentPageEvidenceBlockerCode,
    CurrentPageEvidenceResponse,
    CurrentPageEvidenceStatus,
    current_page_material_is_current,
)
from wilq.content.workflow.decisions.production import canonical_json_digest

_HEX64 = r"^[0-9a-f]{64}$"
CurrentPageIdentityV3BlockerCode = CurrentPageEvidenceBlockerCode | Literal[
    "page_identity_subject_mismatch",
    "page_identity_source_invalid",
    "page_identity_digest_stale",
    "page_evidence_digest_stale",
]


class CurrentPageIdentityV3Response(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    response_type: Literal["current_page_identity"] = "current_page_identity"
    contract_version: Literal["current_page_identity_v3"] = "current_page_identity_v3"
    status: Literal["exact_current", "blocked"]
    work_item_id: str = Field(min_length=1)
    page_url: str | None = None
    canonical_path: str | None = None
    material_meaning_digest: str | None = Field(default=None, pattern=_HEX64)
    identity_id: str | None = None
    identity_digest: str | None = Field(default=None, pattern=_HEX64)
    evidence_digest: str | None = Field(default=None, pattern=_HEX64)
    source_status: CurrentPageEvidenceStatus | None = None
    current_evidence_ids: tuple[str, ...] = ()
    catalog_evidence_ids: tuple[str, ...] = ()
    blocker_code: CurrentPageIdentityV3BlockerCode | None = None
    blocker_owner: str | None = None
    safe_next_step: str = Field(min_length=1)
    generation_allowed: Literal[False] = False

    @model_validator(mode="after")
    def require_exact_or_blocked(self) -> Self:
        for values in (self.current_evidence_ids, self.catalog_evidence_ids):
            if values != tuple(sorted(set(values))) or any(not item.strip() for item in values):
                raise ValueError("Current page identity evidence IDs must be sorted and unique.")
        if self.status == "blocked":
            if (
                not self.blocker_code or not self.blocker_owner or self.identity_id
                or self.identity_digest or self.evidence_digest
            ):
                raise ValueError("Blocked current identity requires one typed blocker.")
            return self
        if (
            not self.page_url
            or not self.canonical_path
            or not self.material_meaning_digest
            or not self.identity_digest
            or not self.evidence_digest
            or not self.identity_id
            or self.source_status not in {"observed_material_current", "reviewed_material_current"}
            or not self.current_evidence_ids
            or not self.catalog_evidence_ids
            or self.blocker_code is not None
            or self.blocker_owner is not None
            or not content_is_safe_public_url(self.page_url)
            or content_normalized_path(self.page_url) != self.canonical_path
            or self.identity_digest != _identity_digest(
                self.work_item_id, self.page_url, self.material_meaning_digest
            )
            or self.identity_id != f"current_page_identity_v3_{self.identity_digest[:24]}"
            or self.evidence_digest != _evidence_digest(
                self.identity_digest,
                self.source_status,
                self.current_evidence_ids,
                self.catalog_evidence_ids,
            )
        ):
            raise ValueError("Exact current identity requires matching URL, digest and evidence.")
        return self


def resolve_current_page_identity_v3(
    work_item_id: str,
    evidence: CurrentPageEvidenceResponse,
    *,
    expected_identity_digest: str | None = None,
    expected_evidence_digest: str | None = None,
) -> CurrentPageIdentityV3Response:
    """Resolve stable material identity and optional exact-read evidence CAS, without writes."""

    current_ids = tuple(sorted(set(evidence.current_evidence_ids)))
    catalog_ids = tuple(sorted(set(evidence.catalog_evidence_ids)))
    if evidence.work_item_id != work_item_id:
        return _blocked(
            work_item_id, "page_identity_subject_mismatch", "WILQ content workflow",
            "Ponów odczyt dokładnego zadania i adresu.", current_ids, catalog_ids,
        )
    if not current_page_material_is_current(evidence):
        return _blocked(
            work_item_id,
            evidence.blocker_code or "page_identity_source_invalid",
            evidence.blocker_owner or "WILQ content workflow",
            evidence.safe_next_step,
            current_ids,
            catalog_ids,
        )
    if (
        not evidence.page_url
        or not content_is_safe_public_url(evidence.page_url)
        or not evidence.material_meaning_digest
        or not current_ids
        or not catalog_ids
    ):
        return _blocked(
            work_item_id, "page_identity_source_invalid", "WILQ content workflow",
            "Ponów dokładny odczyt strony i katalogu WordPress.", current_ids, catalog_ids,
        )
    digest = _identity_digest(work_item_id, evidence.page_url, evidence.material_meaning_digest)
    if expected_identity_digest is not None and expected_identity_digest != digest:
        return _blocked(
            work_item_id, "page_identity_digest_stale", "WILQ content workflow",
            "Odczytaj nową dokładną tożsamość tej strony.", current_ids, catalog_ids,
        )
    evidence_digest = _evidence_digest(digest, evidence.status, current_ids, catalog_ids)
    if expected_evidence_digest is not None and expected_evidence_digest != evidence_digest:
        return _blocked(
            work_item_id, "page_evidence_digest_stale", "WILQ content workflow",
            "Odczytaj nowe dowody dokładnej strony.", current_ids, catalog_ids,
        )
    return CurrentPageIdentityV3Response(
        status="exact_current",
        work_item_id=work_item_id,
        page_url=evidence.page_url,
        canonical_path=content_normalized_path(evidence.page_url),
        material_meaning_digest=evidence.material_meaning_digest,
        identity_id=f"current_page_identity_v3_{digest[:24]}",
        identity_digest=digest,
        evidence_digest=evidence_digest,
        source_status=evidence.status,
        current_evidence_ids=current_ids,
        catalog_evidence_ids=catalog_ids,
        safe_next_step="Sprawdź zatwierdzone źródła twierdzeń dla dokładnej strony.",
    )


def _identity_digest(work_item_id: str, page_url: str, material_digest: str) -> str:
    return canonical_json_digest({
        "schema_version": "wilq_current_page_identity_v3",
        "work_item_id": work_item_id,
        "page_url": page_url,
        "canonical_path": content_normalized_path(page_url),
        "material_meaning_digest": material_digest,
    })


def _evidence_digest(
    identity_digest: str,
    source_status: CurrentPageEvidenceStatus,
    current_ids: tuple[str, ...],
    catalog_ids: tuple[str, ...],
) -> str:
    """Bind one read's lineage; unlike identity, this changes when read IDs rotate."""
    return canonical_json_digest({
        "schema_version": "wilq_current_page_evidence_binding_v3",
        "identity_digest": identity_digest,
        "source_status": source_status,
        "current_evidence_ids": current_ids,
        "catalog_evidence_ids": catalog_ids,
    })


def _blocked(
    work_item_id: str,
    code: CurrentPageIdentityV3BlockerCode,
    owner: str,
    step: str,
    current_ids: tuple[str, ...],
    catalog_ids: tuple[str, ...],
) -> CurrentPageIdentityV3Response:
    return CurrentPageIdentityV3Response(
        status="blocked",
        work_item_id=work_item_id,
        current_evidence_ids=current_ids,
        catalog_evidence_ids=catalog_ids,
        blocker_code=code,
        blocker_owner=owner,
        safe_next_step=step,
    )
