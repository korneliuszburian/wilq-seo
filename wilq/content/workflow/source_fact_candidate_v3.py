"""Read-only reviewed source-fact candidates for receiptless exact page identity."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.knowledge.cards import ContentKnowledgeCard, ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.workflow.current_page_identity_v3 import (
    CurrentPageIdentityV3BlockerCode,
    CurrentPageIdentityV3Response,
)
from wilq.content.workflow.source_fact_candidate_projection import (
    ContentSourceFactAuthorityServiceBinding,
    SourceFactCandidateBlockerOwner,
    _registry_receipt,
    scoped_candidate_review_blocker,
    select_content_source_fact_candidates,
)
from wilq.content.workflow.source_fact_candidate_v2 import (
    ContentSourceFactCandidateV2,
    ContentSourceFactCandidateV2BlockerCode,
)

_HEX64 = r"^[0-9a-f]{64}$"
CandidateV3BlockerCode = CurrentPageIdentityV3BlockerCode | ContentSourceFactCandidateV2BlockerCode


class ContentSourceFactCandidateV3Projection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    response_type: Literal["content_source_fact_candidates"] = "content_source_fact_candidates"
    contract_version: Literal["content_source_fact_candidates_v3"] = (
        "content_source_fact_candidates_v3"
    )
    status: Literal["eligible", "blocked"]
    work_item_id: str = Field(min_length=1, max_length=240)
    page_url: str | None = None
    canonical_path: str | None = None
    material_meaning_digest: str | None = Field(default=None, pattern=_HEX64)
    identity_id: str | None = None
    identity_digest: str | None = Field(default=None, pattern=_HEX64)
    evidence_digest: str | None = Field(default=None, pattern=_HEX64)
    current_evidence_ids: tuple[str, ...] = ()
    catalog_evidence_ids: tuple[str, ...] = ()
    registry_id: str = Field(min_length=1, max_length=240)
    registry_digest: str = Field(pattern=_HEX64)
    registry_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    registry_fact_count: int = Field(ge=0)
    registry_checked_at: datetime
    service_binding: ContentSourceFactAuthorityServiceBinding | None = None
    candidates: tuple[ContentSourceFactCandidateV2, ...] = Field(default=(), max_length=512)
    blocker_code: CandidateV3BlockerCode | None = None
    blocker_owner: str | None = None
    blocker_evidence_ids: tuple[str, ...] = ()
    safe_next_step: str = Field(min_length=1)
    generation_allowed: Literal[False] = False
    source_pack_write_allowed: Literal[False] = False

    @model_validator(mode="after")
    def require_exact_candidate_lineage(self) -> Self:
        if self.registry_checked_at.tzinfo is None or self.registry_checked_at.utcoffset() is None:
            raise ValueError("Source-fact registry time must be aware.")
        if self.status == "blocked":
            if not self.blocker_code or not self.blocker_owner or self.candidates:
                raise ValueError("Blocked candidates require one blocker and no facts.")
            return self
        if (
            not self.candidates
            or not self.page_url
            or not self.canonical_path
            or not self.material_meaning_digest
            or not self.identity_id
            or not self.identity_digest
            or not self.evidence_digest
            or not self.current_evidence_ids
            or not self.catalog_evidence_ids
            or self.blocker_code is not None
            or self.blocker_owner is not None
            or self.service_binding is None
            or self.service_binding.status != "exact_bound"
        ):
            raise ValueError("Eligible candidates require exact page, evidence and facts.")
        return self


def build_content_source_fact_candidates_v3_projection(
    *,
    identity: CurrentPageIdentityV3Response,
    facts: tuple[ContentSourceFact, ...] | None = None,
    cards: tuple[ContentKnowledgeCard, ...] | None = None,
    checked_at: datetime | None = None,
) -> ContentSourceFactCandidateV3Projection:
    """Select only approved exact-scope facts; page identity grants no claim approval."""

    current_facts = ekologus_source_facts() if facts is None else facts
    current_cards = ekologus_content_knowledge_cards() if cards is None else cards
    registry = _registry_receipt(current_facts, checked_at)
    common: dict[str, object] = {
        "work_item_id": identity.work_item_id,
        "page_url": identity.page_url,
        "canonical_path": identity.canonical_path,
        "material_meaning_digest": identity.material_meaning_digest,
        "identity_id": identity.identity_id,
        "identity_digest": identity.identity_digest,
        "evidence_digest": identity.evidence_digest,
        "current_evidence_ids": identity.current_evidence_ids,
        "catalog_evidence_ids": identity.catalog_evidence_ids,
        "registry_id": registry.registry_id,
        "registry_digest": registry.registry_digest,
        "registry_evidence_ids": registry.evidence_ids,
        "registry_fact_count": registry.fact_count,
        "registry_checked_at": registry.checked_at,
    }
    if identity.status != "exact_current":
        return _blocked(
            common,
            identity.blocker_code or "page_identity_source_invalid",
            identity.blocker_owner or "WILQ content workflow",
            identity.safe_next_step,
            (),
        )
    assert identity.page_url is not None and identity.canonical_path is not None
    eligible, review_required, binding, blocker = select_content_source_fact_candidates(
        current_facts,
        current_cards,
        page_url=identity.page_url,
        canonical_path=identity.canonical_path,
        binding_evidence_ids=identity.current_evidence_ids,
    )
    common["service_binding"] = binding
    if blocker is not None:
        return _blocked(common, cast(CandidateV3BlockerCode, blocker.reason),
                        "WILQ content workflow", blocker.next_step, blocker.evidence_ids)
    if not eligible:
        if review_required:
            review_blocker, owner = scoped_candidate_review_blocker(
                review_required, binding.card_evidence_ids
            )
            return _blocked(common, cast(CandidateV3BlockerCode, review_blocker.reason),
                            owner, review_blocker.next_step, review_blocker.evidence_ids)
        return _blocked(
            common,
            "approved_source_fact_candidate_missing",
            "WILQ content workflow",
            "Pozyskaj lub zatwierdź exact source fact dla bieżącego adresu.",
            binding.card_evidence_ids,
        )
    return ContentSourceFactCandidateV3Projection.model_validate(common | {
        "status": "eligible",
        "candidates": tuple(
            ContentSourceFactCandidateV2.from_shared_candidate(item) for item in eligible
        ),
        "safe_next_step": "Sprawdź kandydatów; zapis wymaga osobnego ActionObject i review faktów.",
    })


def _blocked(
    common: dict[str, object],
    code: CandidateV3BlockerCode,
    owner: str | SourceFactCandidateBlockerOwner,
    step: str,
    extra_evidence_ids: tuple[str, ...],
) -> ContentSourceFactCandidateV3Projection:
    evidence_ids = set(extra_evidence_ids)
    for name in ("current_evidence_ids", "catalog_evidence_ids", "registry_evidence_ids"):
        values = common.get(name)
        if isinstance(values, tuple):
            evidence_ids.update(value for value in values if isinstance(value, str))
    return ContentSourceFactCandidateV3Projection.model_validate(common | {
        "status": "blocked",
        "blocker_code": code,
        "blocker_owner": owner,
        "blocker_evidence_ids": tuple(sorted(evidence_ids)),
        "safe_next_step": step,
    })
