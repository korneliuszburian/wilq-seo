"""Read-only, exact-row source-fact candidate projection.

This module scopes reviewed facts to one current S1 identity. It never creates
an authority proposal or receipt; human selection remains a separate
ActionObject lifecycle.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from wilq.content.canonical.urls import content_normalized_path, content_normalized_url
from wilq.content.knowledge.cards import (
    ContentKnowledgeCard,
    ekologus_content_knowledge_cards,
)
from wilq.content.knowledge.matching_surface import service_card_has_binding_provenance
from wilq.content.knowledge.source_facts import ContentSourceFact, ekologus_source_facts
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationProjection,
    canonical_json_digest,
)
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.source_pack_binding import (
    APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
    SOURCE_FACT_REGISTRY_ID,
    source_fact_registry_digest,
)
from wilq.evidence.registry import SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID

_HEX64 = r"^[0-9a-f]{64}$"
_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"
_CREDIBLE_SOURCE_TYPES = {
    "public_site",
    "reviewed_internal",
    "legal_update",
    "connector_metric",
    "uat_feedback",
}
_CandidateOrigin = Literal[
    "exact_canonical_path",
    "exact_service_card_binding",
    "current_page_snapshot",
    "research_packet",
]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class ContentSourceFactAuthorityBlocker(_FrozenModel):
    seam: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=512)
    next_step: str = Field(min_length=1)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_blocker_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _optional_sorted_ids(value, "Blocker evidence IDs")


def _nonzero_digest(value: str) -> str:
    if value == "0" * 64:
        raise ValueError("Candidate digest cannot be zero.")
    return value


def _sorted_ids(value: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = tuple(item.strip() for item in value)
    if (
        any(not item for item in normalized)
        or any(not re.fullmatch(_SAFE_IDENTIFIER, item) for item in normalized)
        or len(normalized) != len(set(normalized))
        or normalized != tuple(sorted(normalized))
    ):
        raise ValueError(f"{label} must be sorted, unique and non-blank.")
    return normalized


def _optional_sorted_ids(value: tuple[str, ...], label: str) -> tuple[str, ...]:
    return _sorted_ids(value, label) if value else value


def _fact_digest(fact: ContentSourceFact) -> str:
    return canonical_json_digest(fact.model_dump(mode="json"))


def _source_reference_digest(fact: ContentSourceFact) -> str:
    return canonical_json_digest(
        {
            "source_type": fact.source_type,
            "privacy_class": fact.privacy_class,
            "source_url_or_path": fact.source_url_or_path,
        }
    )


class ContentSourceFactAuthorityCandidate(_FrozenModel):
    """One deterministic, non-authoritative candidate exposed for human selection."""

    source_fact_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    fact_digest: str = Field(pattern=_HEX64)
    source_reference_digest: str = Field(pattern=_HEX64)
    source_type: str = Field(min_length=1)
    privacy_class: str = Field(min_length=1)
    freshness_date: str = Field(min_length=1)
    target_card_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    review_status: Literal[
        "approved", "review_required", "unreviewed", "stale", "rejected"
    ]
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    source_connectors: tuple[str, ...] = Field(default=(), max_length=64)
    scope: str = Field(min_length=1)
    deterministic_origin: _CandidateOrigin
    selectable: bool
    reasons: tuple[str, ...] = Field(default=(), max_length=16)

    @field_validator("fact_digest", "source_reference_digest")
    @classmethod
    def require_nonzero_candidate_digests(cls, value: str) -> str:
        return _nonzero_digest(value)

    @field_validator("evidence_ids", "source_connectors")
    @classmethod
    def require_sorted_candidate_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _optional_sorted_ids(value, "Candidate IDs")

    @field_validator("reasons")
    @classmethod
    def require_candidate_reasons(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not reason.strip() for reason in value):
            raise ValueError("Candidate reasons must be non-blank.")
        return value


class ContentSourceFactAuthorityServiceBinding(_FrozenModel):
    """Exact card/path binding used to scope candidates; never a selection."""

    status: Literal["exact_bound", "ambiguous", "missing"]
    card_id: str | None = None
    card_status: str | None = None
    card_evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    card_source_connectors: tuple[str, ...] = Field(default=(), max_length=64)
    card_freshness: str | None = None
    binding_url: str | None = None

    @field_validator("card_evidence_ids", "card_source_connectors")
    @classmethod
    def require_sorted_binding_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _optional_sorted_ids(value, "Service binding IDs")


class ContentSourceFactAuthorityRegistryReceipt(_FrozenModel):
    """Read-time registry receipt; it does not authorize any row."""

    registry_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    registry_digest: str = Field(pattern=_HEX64)
    evidence_ids: tuple[str, ...] = Field(default=(), max_length=256)
    fact_count: int = Field(ge=0)
    checked_at: datetime

    @field_validator("registry_digest")
    @classmethod
    def require_nonzero_registry_receipt(cls, value: str) -> str:
        return _nonzero_digest(value)

    @field_validator("evidence_ids")
    @classmethod
    def require_sorted_registry_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _optional_sorted_ids(value, "Registry evidence IDs")

    @field_validator("checked_at")
    @classmethod
    def require_aware_registry_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Registry checked_at must be timezone-aware.")
        return value.astimezone(UTC)


class ContentSourceFactAuthorityCandidateProjection(_FrozenModel):
    """Read-only exact-row candidate projection; no proposal or receipt is created."""

    response_type: Literal["content_source_fact_authority_candidates"] = (
        "content_source_fact_authority_candidates"
    )
    contract_version: Literal["content_source_fact_authority_candidates_v1"] = (
        "content_source_fact_authority_candidates_v1"
    )
    status: Literal["eligible", "evidence_acquisition_needed", "blocked"]
    identity_binding_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    identity_binding_digest: str | None = Field(default=None, pattern=_HEX64)
    current_work_item_id: str | None = None
    canonical_path: str | None = None
    public_url: str | None = None
    classification_run_id: str | None = None
    classification_run_digest: str | None = Field(default=None, pattern=_HEX64)
    classification_decision_set_digest: str | None = Field(default=None, pattern=_HEX64)
    classification_source_row_digest: str | None = Field(default=None, pattern=_HEX64)
    service_binding: ContentSourceFactAuthorityServiceBinding
    registry: ContentSourceFactAuthorityRegistryReceipt
    eligible_candidates: tuple[ContentSourceFactAuthorityCandidate, ...] = ()
    review_required_candidates: tuple[ContentSourceFactAuthorityCandidate, ...] = ()
    acquisition_status: Literal["not_needed", "needed"]
    acquisition_source_kind: str = Field(min_length=1)
    acquisition_reason: str = Field(min_length=1)
    blockers: tuple[ContentSourceFactAuthorityBlocker, ...] = ()
    safe_next_step: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_projection_state(self) -> Self:
        if (
            self.status == "eligible"
            and (
                not self.eligible_candidates
                or self.blockers
                or self.acquisition_status != "not_needed"
            )
        ):
            raise ValueError("Eligible candidate projection has an inconsistent state.")
        if self.status == "evidence_acquisition_needed" and self.acquisition_status != "needed":
            raise ValueError("Evidence acquisition state must be marked needed.")
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked candidate projection requires typed blockers.")
        return self


def _candidate_blocker(
    seam: str,
    reason: str,
    evidence_ids: tuple[str, ...] = (),
    next_step: str = "Odśwież exact dane i przygotuj nowy preview.",
) -> ContentSourceFactAuthorityBlocker:
    return ContentSourceFactAuthorityBlocker(
        seam=seam,
        reason=reason,
        evidence_ids=tuple(sorted(set(evidence_ids))),
        next_step=next_step,
    )


def _registry_receipt(
    facts: tuple[ContentSourceFact, ...], checked_at: datetime | None
) -> ContentSourceFactAuthorityRegistryReceipt:
    return ContentSourceFactAuthorityRegistryReceipt(
        registry_id=SOURCE_FACT_REGISTRY_ID,
        registry_digest=source_fact_registry_digest(facts),
        evidence_ids=tuple(
            sorted(
                {
                    APPROVED_SOURCE_MATERIALS_EVIDENCE_ID,
                    SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID,
                }
            )
        ),
        fact_count=len(facts),
        checked_at=checked_at or datetime.now(UTC),
    )


def _blocked_projection(
    identity_binding_id: str,
    registry: ContentSourceFactAuthorityRegistryReceipt,
    blocker: ContentSourceFactAuthorityBlocker,
    *,
    identity: ContentDeliveryIdentityBinding | None,
    classification: ContentProductionClassificationProjection | None,
    service_binding: ContentSourceFactAuthorityServiceBinding | None = None,
) -> ContentSourceFactAuthorityCandidateProjection:
    return ContentSourceFactAuthorityCandidateProjection(
        status="blocked",
        identity_binding_id=identity_binding_id,
        identity_binding_digest=None if identity is None else identity.binding_digest,
        current_work_item_id=None if identity is None else identity.current_work_item_id,
        canonical_path=None if identity is None else identity.canonical_path,
        public_url=None if identity is None else identity.public_url,
        classification_run_id=None if classification is None else classification.run_id,
        classification_run_digest=None if classification is None else classification.run_digest,
        classification_decision_set_digest=(
            None if classification is None else classification.decision_set_digest
        ),
        classification_source_row_digest=(
            None if classification is None else classification.row.source_packet_row_digest
        ),
        service_binding=service_binding
        or ContentSourceFactAuthorityServiceBinding(status="missing"),
        registry=registry,
        acquisition_status="needed",
        acquisition_source_kind="current_page_or_research_packet",
        acquisition_reason="Najpierw zwiąż exact S1 i źródło faktu.",
        blockers=(blocker,),
        safe_next_step=blocker.next_step,
    )


def _exact_input_blocker(
    identity_binding_id: str,
    identity: ContentDeliveryIdentityBinding | None,
    classification: ContentProductionClassificationProjection | None,
) -> ContentSourceFactAuthorityBlocker | None:
    if identity is None:
        return _candidate_blocker(
            "s1_identity",
            "identity_binding_missing",
            next_step="Najpierw zapisz exact S1 identity binding.",
        )
    if identity.binding_id != identity_binding_id:
        return _candidate_blocker(
            "s1_identity",
            "identity_binding_id_mismatch",
            identity.inventory_evidence_ids,
            "Użyj dokładnie tego identity bindingu, którego dotyczy żądanie.",
        )
    if identity.status != "exact_current":
        return _candidate_blocker(
            "s1_identity",
            "identity_binding_not_exact_current",
            identity.inventory_evidence_ids,
            "Usuń typed blocker S1 i odśwież kandydatów.",
        )
    if classification is None:
        return _candidate_blocker(
            "classification",
            "classification_current_missing",
            identity.inventory_evidence_ids,
            "Wskaż bieżącą klasyfikację dla exact work itemu.",
        )
    if classification.freshness.requires_refresh or classification.freshness.state != "fresh":
        return _candidate_blocker(
            "classification",
            "classification_stale",
            classification.row.primary_evidence_ids,
            "Odśwież bieżącą klasyfikację przed wyborem source factów.",
        )
    if (
        classification.run_id != identity.classification_run_id
        or classification.run_digest != identity.classification_run_digest
        or classification.decision_set_digest != identity.classification_decision_set_digest
    ):
        return _candidate_blocker(
            "classification",
            "classification_identity_drift",
            classification.row.primary_evidence_ids,
            "Użyj identity i classification z tego samego exact runu.",
        )
    row = classification.row
    if (
        row.current_work_item_id != identity.current_work_item_id
        or row.canonical_path != identity.canonical_path
        or row.public_url != identity.public_url
        or row.source_packet_row_digest != identity.classification_source_row_digest
    ):
        return _candidate_blocker(
            "classification",
            "classification_source_row_digest_mismatch",
            row.primary_evidence_ids,
            "Ponownie zwiąż work item, path, URL i source-row digest.",
        )
    if identity.final_disposition != "keep":
        return _candidate_blocker(
            "current_disposition",
            "disposition_not_keep",
            identity.inventory_evidence_ids,
            "Source facts dla produkcji wybieraj wyłącznie dla bieżącego keep.",
        )
    return None


def _service_binding(
    identity: ContentDeliveryIdentityBinding,
    facts: tuple[ContentSourceFact, ...],
    cards: tuple[ContentKnowledgeCard, ...],
) -> tuple[
    ContentSourceFactAuthorityServiceBinding,
    ContentKnowledgeCard | None,
    tuple[ContentSourceFact, ...],
    ContentSourceFactAuthorityBlocker | None,
]:
    exact_cards = tuple(
        card
        for card in cards
        if card.card_type == "service"
        and any(
            _same_exact_public_url(identity.public_url, url)
            for url in card.service_binding_urls
        )
    )
    path_facts = tuple(
        fact
        for fact in facts
        if any(
            content_normalized_path(path).casefold() == identity.canonical_path.casefold()
            for path in fact.applicable_canonical_paths
        )
    )
    if len(exact_cards) > 1:
        return (
            ContentSourceFactAuthorityServiceBinding(
                status="ambiguous", binding_url=identity.public_url
            ),
            None,
            path_facts,
            _candidate_blocker(
                "service_binding",
                "service_binding_ambiguous",
                tuple(e for card in exact_cards for e in card.evidence_ids),
                "Wybierz jedną exact kartę usługi przed source-fact review.",
            ),
        )
    card = exact_cards[0] if exact_cards else None
    if card is not None and not service_card_has_binding_provenance(card):
        binding = ContentSourceFactAuthorityServiceBinding(
            status="missing",
            card_id=card.id,
            card_status=card.lifecycle_status,
            card_evidence_ids=tuple(sorted(set(card.evidence_ids))),
            card_source_connectors=tuple(sorted(set(card.source_connectors))),
            card_freshness=card.freshness,
            binding_url=identity.public_url,
        )
        return (
            binding,
            card,
            path_facts,
            _candidate_blocker(
                "service_binding",
                "service_binding_provenance_missing",
                tuple(card.evidence_ids),
                "Uzupełnij evidence, connector i freshness exact karty usługi.",
            ),
        )
    if card is None and not path_facts:
        return (
            ContentSourceFactAuthorityServiceBinding(
                status="missing", binding_url=identity.public_url
            ),
            None,
            path_facts,
            _candidate_blocker(
                "service_binding",
                "service_binding_missing",
                identity.inventory_evidence_ids,
                "Pozyskaj exact service/page scope przed wyborem source factów.",
            ),
        )
    return (
        ContentSourceFactAuthorityServiceBinding(
            status="exact_bound",
            card_id=None if card is None else card.id,
            card_status=None if card is None else card.lifecycle_status,
            card_evidence_ids=()
            if card is None
            else tuple(sorted(set(card.evidence_ids))),
            card_source_connectors=()
            if card is None
            else tuple(sorted(set(card.source_connectors))),
            card_freshness=None if card is None else card.freshness,
            binding_url=identity.public_url,
        ),
        card,
        path_facts,
        None,
    )


def _scoped_candidates(
    facts: tuple[ContentSourceFact, ...],
    *,
    identity: ContentDeliveryIdentityBinding,
    card: ContentKnowledgeCard | None,
) -> tuple[list[ContentSourceFactAuthorityCandidate], list[ContentSourceFactAuthorityCandidate]]:
    scoped: dict[str, tuple[ContentSourceFact, _CandidateOrigin]] = {}
    for fact in facts:
        origin: _CandidateOrigin | None = None
        if any(
            content_normalized_path(path).casefold() == identity.canonical_path.casefold()
            for path in fact.applicable_canonical_paths
        ):
            origin = "exact_canonical_path"
        elif card is not None and (
            fact.source_id in card.source_fact_ids
            or fact.target_card_id == card.id
            or card.id in fact.applicable_service_card_ids
        ):
            origin = "exact_service_card_binding"
        if origin is not None:
            scoped.setdefault(fact.source_id, (fact, origin))

    eligible: list[ContentSourceFactAuthorityCandidate] = []
    review_required: list[ContentSourceFactAuthorityCandidate] = []
    for fact, origin in sorted(scoped.values(), key=lambda item: item[0].source_id):
        reasons: list[str] = []
        if fact.source_type not in _CREDIBLE_SOURCE_TYPES:
            reasons.append("source_origin_not_credible")
        if fact.review_status != "approved":
            reasons.append("source_fact_not_approved")
        if not fact.evidence_ids:
            reasons.append("source_evidence_missing")
        if not fact.source_connectors:
            reasons.append("source_connector_missing")
        if fact.privacy_class not in {"commit_safe", "private_local", "redacted_only"}:
            reasons.append("source_privacy_not_eligible")
        if card is not None and card.lifecycle_status != "approved_current":
            reasons.append("service_card_review_required")
        candidate = ContentSourceFactAuthorityCandidate(
            source_fact_id=fact.source_id,
            fact_digest=_fact_digest(fact),
            source_reference_digest=_source_reference_digest(fact),
            source_type=fact.source_type,
            privacy_class=fact.privacy_class,
            freshness_date=fact.freshness_date,
            target_card_id=fact.target_card_id,
            review_status=fact.review_status,
            evidence_ids=tuple(sorted(set(fact.evidence_ids))),
            source_connectors=tuple(sorted(set(fact.source_connectors))),
            scope=fact.scope,
            deterministic_origin=origin,
            selectable=not reasons,
            reasons=tuple(reasons),
        )
        (eligible if candidate.selectable else review_required).append(candidate)
    return eligible, review_required


def build_content_source_fact_authority_candidate_projection(
    identity_binding_id: str,
    *,
    identity: ContentDeliveryIdentityBinding | None,
    classification: ContentProductionClassificationProjection | None,
    facts: tuple[ContentSourceFact, ...] | None = None,
    cards: tuple[ContentKnowledgeCard, ...] | None = None,
    checked_at: datetime | None = None,
) -> ContentSourceFactAuthorityCandidateProjection:
    """Project exact-row candidates without creating a proposal or receipt."""

    current_facts = ekologus_source_facts() if facts is None else facts
    current_cards = ekologus_content_knowledge_cards() if cards is None else cards
    registry = _registry_receipt(current_facts, checked_at)
    blocker = _exact_input_blocker(identity_binding_id, identity, classification)
    if blocker is not None:
        return _blocked_projection(
            identity_binding_id,
            registry,
            blocker,
            identity=identity,
            classification=classification,
        )
    assert identity is not None
    assert classification is not None
    binding, card, _path_facts, blocker = _service_binding(
        identity, current_facts, current_cards
    )
    if blocker is not None:
        return _blocked_projection(
            identity_binding_id,
            registry,
            blocker,
            identity=identity,
            classification=classification,
            service_binding=binding,
        )
    eligible, review_required = _scoped_candidates(
        current_facts, identity=identity, card=card
    )
    common = {
        "identity_binding_id": identity_binding_id,
        "identity_binding_digest": identity.binding_digest,
        "current_work_item_id": identity.current_work_item_id,
        "canonical_path": identity.canonical_path,
        "public_url": identity.public_url,
        "classification_run_id": classification.run_id,
        "classification_run_digest": classification.run_digest,
        "classification_decision_set_digest": classification.decision_set_digest,
        "classification_source_row_digest": classification.row.source_packet_row_digest,
        "service_binding": binding,
        "registry": registry,
    }
    if eligible:
        return ContentSourceFactAuthorityCandidateProjection.model_validate(
            {
                **common,
                "status": "eligible",
                "eligible_candidates": tuple(eligible),
                "review_required_candidates": tuple(review_required),
                "acquisition_status": "not_needed",
                "acquisition_source_kind": "existing_authoritative_source_fact",
                "acquisition_reason": (
                    "Exact approved source facts are available for human selection."
                ),
                "safe_next_step": (
                    "Wybierz kandydatów i uruchom osobny ActionObject source-fact authority."
                ),
            }
        )
    evidence_ids = tuple(
        sorted({evidence for item in review_required for evidence in item.evidence_ids})
    )
    blocker = _candidate_blocker(
        "source_fact_review",
        "source_fact_not_approved" if review_required else "source_fact_candidate_missing",
        evidence_ids or binding.card_evidence_ids,
        "Pozyskaj lub zatwierdź exact source fact z bieżącego/reviewowanego źródła.",
    )
    return ContentSourceFactAuthorityCandidateProjection.model_validate(
        {
            **common,
            "status": "evidence_acquisition_needed",
            "eligible_candidates": (),
            "review_required_candidates": tuple(review_required),
            "acquisition_status": "needed",
            "acquisition_source_kind": (
                "owner_reviewed_source_fact"
                if review_required
                else "current_page_or_research_packet"
            ),
            "acquisition_reason": (
                "Istnieją scoped fakty, ale wymagają review/evidence."
                if review_required
                else "Brakuje factu z exact bieżącego lub reviewowanego źródła."
            ),
            "blockers": (blocker,),
            "safe_next_step": blocker.next_step,
        }
    )


def _same_exact_public_url(left: str, right: str) -> bool:
    left_normalized = content_normalized_url(left)
    right_normalized = content_normalized_url(right)
    return bool(left_normalized and left_normalized == right_normalized)


__all__ = [
    "ContentSourceFactAuthorityCandidate",
    "ContentSourceFactAuthorityCandidateProjection",
    "ContentSourceFactAuthorityRegistryReceipt",
    "ContentSourceFactAuthorityServiceBinding",
    "build_content_source_fact_authority_candidate_projection",
]
