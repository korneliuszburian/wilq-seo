"""Read-only source-fact candidates bound to the current page KEEP receipt."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.knowledge.cards import ContentKnowledgeCard, ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.workflow.current_page_identity_v2 import (
    CurrentPageIdentityBlockerCode,
    CurrentPageIdentityBlockerOwner,
    CurrentPageIdentityV2Response,
)
from wilq.content.workflow.source_fact_candidate_projection import (
    ContentSourceFactAuthorityBlocker,
    ContentSourceFactAuthorityCandidate,
    ContentSourceFactAuthorityServiceBinding,
    _registry_receipt,
    select_content_source_fact_candidates,
)

_HEX64 = r"^[0-9a-f]{64}$"
ContentSourceFactCandidateV2BlockerCode = CurrentPageIdentityBlockerCode | Literal[
    "approved_source_fact_candidate_missing",
    "service_binding_ambiguous",
    "service_binding_provenance_missing",
    "service_binding_missing",
    "service_card_review_required",
    "source_fact_lineage_missing",
    "source_fact_rejected",
    "source_fact_review_required",
    "source_fact_source_ineligible",
    "source_fact_stale",
]


class ContentSourceFactCandidateV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_fact_id: str = Field(min_length=1, max_length=240)
    fact_digest: str = Field(pattern=_HEX64)
    source_reference_digest: str = Field(pattern=_HEX64)
    source_type: str = Field(min_length=1)
    privacy_class: str = Field(min_length=1)
    freshness_date: str = Field(min_length=1)
    target_card_id: str = Field(min_length=1, max_length=240)
    review_status: Literal["approved"] = "approved"
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    source_connectors: tuple[str, ...] = Field(min_length=1, max_length=64)
    scope: str = Field(min_length=1)
    deterministic_origin: Literal["exact_canonical_path", "exact_service_card_binding"]

    @classmethod
    def from_shared_candidate(
        cls, candidate: ContentSourceFactAuthorityCandidate
    ) -> ContentSourceFactCandidateV2:
        return cls(
            source_fact_id=candidate.source_fact_id,
            fact_digest=candidate.fact_digest,
            source_reference_digest=candidate.source_reference_digest,
            source_type=candidate.source_type,
            privacy_class=candidate.privacy_class,
            freshness_date=candidate.freshness_date,
            target_card_id=candidate.target_card_id,
            review_status="approved",
            evidence_ids=candidate.evidence_ids,
            source_connectors=candidate.source_connectors,
            scope=candidate.scope,
            deterministic_origin=cast(
                Literal["exact_canonical_path", "exact_service_card_binding"],
                candidate.deterministic_origin,
            ),
        )


class ContentSourceFactCandidateV2Projection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    response_type: Literal["content_source_fact_candidates"] = "content_source_fact_candidates"
    contract_version: Literal["content_source_fact_candidates_v2"] = (
        "content_source_fact_candidates_v2"
    )
    status: Literal["eligible", "blocked"]
    work_item_id: str = Field(min_length=1, max_length=240)
    page_url: str | None = None
    canonical_path: str | None = None
    material_meaning_digest: str | None = Field(default=None, pattern=_HEX64)
    receipt_id: str | None = None
    receipt_digest: str | None = Field(default=None, pattern=_HEX64)
    original_evidence_ids: tuple[str, ...] = ()
    apply_evidence_ids: tuple[str, ...] = ()
    current_evidence_ids: tuple[str, ...] = ()
    registry_id: str = Field(min_length=1, max_length=240)
    registry_digest: str = Field(pattern=_HEX64)
    registry_evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=256)
    registry_fact_count: int = Field(ge=0)
    registry_checked_at: datetime
    service_binding: ContentSourceFactAuthorityServiceBinding | None = None
    candidates: tuple[ContentSourceFactCandidateV2, ...] = Field(default=(), max_length=512)
    blocker_code: ContentSourceFactCandidateV2BlockerCode | None = None
    blocker_owner: CurrentPageIdentityBlockerOwner | None = None
    blocker_evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    safe_next_step: str = Field(min_length=1)
    generation_allowed: Literal[False] = False
    source_pack_write_allowed: Literal[False] = False

    @model_validator(mode="after")
    def validate_projection_state(self) -> Self:
        if self.registry_checked_at.tzinfo is None or self.registry_checked_at.utcoffset() is None:
            raise ValueError("Registry checked_at must be timezone-aware.")
        if self.status == "eligible":
            if (
                not self.candidates
                or self.blocker_code is not None
                or self.blocker_owner is not None
                or self.material_meaning_digest is None
                or self.receipt_id is None
                or self.receipt_digest is None
                or self.canonical_path is None
                or self.page_url is None
                or self.service_binding is None
                or self.service_binding.status != "exact_bound"
            ):
                raise ValueError("Eligible source-fact candidates require exact KEEP lineage.")
            if any(
                candidate.deterministic_origin == "exact_service_card_binding"
                for candidate in self.candidates
            ) and (
                self.service_binding.card_id is None
                or self.service_binding.card_status != "approved_current"
                or not self.service_binding.card_evidence_ids
                or not self.service_binding.card_source_connectors
                or self.service_binding.card_freshness is None
            ):
                raise ValueError("Card-scoped candidates require approved card lineage.")
        elif not self.blocker_code or not self.blocker_owner or self.candidates:
            raise ValueError("Blocked source-fact candidates require one blocker and no rows.")
        return self


def build_content_source_fact_candidates_v2_projection(
    *,
    identity: CurrentPageIdentityV2Response,
    facts: tuple[ContentSourceFact, ...] | None = None,
    cards: tuple[ContentKnowledgeCard, ...] | None = None,
    checked_at: datetime | None = None,
) -> ContentSourceFactCandidateV2Projection:
    """Project only approved, evidence-bound facts under exact current identity."""

    current_facts = ekologus_source_facts() if facts is None else facts
    current_cards = ekologus_content_knowledge_cards() if cards is None else cards
    registry = _registry_receipt(current_facts, checked_at)
    common: dict[str, object] = {
        "work_item_id": identity.work_item_id,
        "page_url": identity.page_url,
        "canonical_path": identity.canonical_path,
        "material_meaning_digest": identity.material_meaning_digest,
        "receipt_id": identity.receipt_id,
        "receipt_digest": identity.receipt_digest,
        "original_evidence_ids": tuple(identity.original_evidence_ids),
        "apply_evidence_ids": tuple(identity.apply_evidence_ids),
        "current_evidence_ids": tuple(identity.current_evidence_ids),
        "registry_id": registry.registry_id,
        "registry_digest": registry.registry_digest,
        "registry_evidence_ids": registry.evidence_ids,
        "registry_fact_count": registry.fact_count,
        "registry_checked_at": registry.checked_at,
    }
    if identity.status != "exact_current":
        return _blocked_from_identity(common, identity)
    assert identity.page_url is not None and identity.canonical_path is not None
    eligible, _review_required, binding, blocker = select_content_source_fact_candidates(
        current_facts,
        current_cards,
        page_url=identity.page_url,
        canonical_path=identity.canonical_path,
        binding_evidence_ids=tuple(identity.current_evidence_ids),
    )
    common["service_binding"] = binding
    if blocker is not None:
        return _blocked_for_candidate_seam(common, blocker)
    if not eligible:
        if _review_required:
            blocker, owner = _scoped_candidate_review_blocker(
                _review_required,
                binding.card_evidence_ids,
            )
            return _blocked_for_candidate_seam(
                common,
                blocker,
                owner=owner,
            )
        return _blocked_for_candidate_seam(
            common,
            ContentSourceFactAuthorityBlocker(
                seam="source_fact_review",
                reason="approved_source_fact_candidate_missing",
                evidence_ids=binding.card_evidence_ids,
                next_step="Pozyskaj lub zatwierdź exact source fact dla bieżącego adresu.",
            ),
        )
    return _make_projection(
        common,
        status="eligible",
        candidates=tuple(
            ContentSourceFactCandidateV2.from_shared_candidate(item) for item in eligible
        ),
        safe_next_step="Sprawdź kandydata; osobny ActionObject jest wymagany dla każdego zapisu.",
    )


def _blocked_for_candidate_seam(
    common: Mapping[str, object],
    blocker: ContentSourceFactAuthorityBlocker,
    *,
    owner: CurrentPageIdentityBlockerOwner = "WILQ content workflow",
) -> ContentSourceFactCandidateV2Projection:
    return _make_projection(
        common,
        status="blocked",
        candidates=(),
        blocker_code=cast(ContentSourceFactCandidateV2BlockerCode, blocker.reason),
        blocker_owner=owner,
        blocker_evidence_ids=tuple(
            sorted(set(_common_evidence_ids(common) + blocker.evidence_ids))
        ),
        safe_next_step=blocker.next_step,
    )


def _scoped_candidate_review_blocker(
    candidates: list[ContentSourceFactAuthorityCandidate],
    binding_evidence_ids: tuple[str, ...],
) -> tuple[ContentSourceFactAuthorityBlocker, CurrentPageIdentityBlockerOwner]:
    reasons = {reason for candidate in candidates for reason in candidate.reasons}
    evidence_ids = tuple(
        sorted(
            {
                evidence_id
                for candidate in candidates
                for evidence_id in candidate.evidence_ids
            }
            | set(binding_evidence_ids)
        )
    )
    if reasons & {"source_evidence_missing", "source_connector_missing"}:
        code = "source_fact_lineage_missing"
        owner: CurrentPageIdentityBlockerOwner = "WILQ content workflow"
        next_step = (
            "Uzupełnij evidence i source connector exact source factu, "
            "a następnie ponów odczyt kandydatów."
        )
    elif reasons & {"source_origin_not_credible", "source_privacy_not_eligible"}:
        code = "source_fact_source_ineligible"
        owner = "WILQ content workflow"
        next_step = (
            "WILQ content workflow: zweryfikuj pochodzenie i prywatność źródła, "
            "a następnie zastąp je kwalifikowanym faktem."
        )
    elif "service_card_review_required" in reasons:
        code = "service_card_review_required"
        owner = "Wilku"
        next_step = (
            "Wilku: sprawdź i zatwierdź dokładną kartę usługi "
            "przed ponownym odczytem kandydatów."
        )
    elif any(candidate.review_status == "stale" for candidate in candidates):
        code = "source_fact_stale"
        owner = "WILQ content workflow"
        next_step = "Odśwież źródło i ponownie sprawdź exact source fact."
    elif any(candidate.review_status == "rejected" for candidate in candidates):
        code = "source_fact_rejected"
        owner = "WILQ content workflow"
        next_step = "Zastąp lub ponownie pozyskaj odrzucony source fact."
    else:
        code = "source_fact_review_required"
        owner = "Wilku"
        next_step = (
            "Wilku: sprawdź i zatwierdź exact source fact "
            "przed ponownym odczytem kandydatów."
        )
    return (
        ContentSourceFactAuthorityBlocker(
            seam="source_fact_review",
            reason=code,
            evidence_ids=evidence_ids,
            next_step=next_step,
        ),
        owner,
    )


def _blocked_from_identity(
    common: Mapping[str, object], identity: CurrentPageIdentityV2Response
) -> ContentSourceFactCandidateV2Projection:
    return _make_projection(
        common,
        status="blocked",
        candidates=(),
        blocker_code=identity.blocker_code,
        blocker_owner=identity.blocker_owner,
        blocker_evidence_ids=tuple(
            sorted(
                set(
                    identity.original_evidence_ids
                    + identity.apply_evidence_ids
                    + identity.current_evidence_ids
                )
            )
        ),
        safe_next_step=identity.safe_next_step or "Odśwież exact dane bieżącej strony.",
    )


def _common_evidence_ids(common: Mapping[str, object]) -> tuple[str, ...]:
    evidence_ids: set[str] = set()
    for key in (
        "original_evidence_ids",
        "apply_evidence_ids",
        "current_evidence_ids",
        "registry_evidence_ids",
    ):
        values = common.get(key)
        if isinstance(values, (tuple, list)):
            evidence_ids.update(value for value in values if isinstance(value, str))
    return tuple(sorted(evidence_ids))


def _make_projection(
    common: Mapping[str, object], **fields: object
) -> ContentSourceFactCandidateV2Projection:
    return ContentSourceFactCandidateV2Projection.model_validate(dict(common) | fields)


__all__ = [
    "ContentSourceFactCandidateV2Projection",
    "build_content_source_fact_candidates_v2_projection",
]
