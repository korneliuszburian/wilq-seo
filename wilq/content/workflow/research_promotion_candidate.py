"""Read-only options for promoting a reviewed research proposal later."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, Protocol, Self, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.knowledge.cards import ContentKnowledgeCard, ekologus_content_knowledge_cards
from wilq.content.knowledge.source_facts import (
    OFFICIAL_GUIDANCE_TARGET_CARD_ID,
    OFFICIAL_GUIDANCE_TARGET_CARD_TITLE,
    OFFICIAL_GUIDANCE_TARGET_CARD_TYPE,
    ContentSourceFact,
    SourceFactScope,
    ekologus_source_facts,
)
from wilq.content.workflow.decisions.production import (
    ContentProductionClassificationProjection,
    canonical_json_digest,
)
from wilq.content.workflow.delivery_identity import ContentDeliveryIdentityBinding
from wilq.content.workflow.evidence_acquisition_contracts import (
    OfficialGuidanceObservationReceipt,
)
from wilq.content.workflow.evidence_acquisition_coordinator import (
    EvidenceAcquisitionRun,
)
from wilq.content.workflow.official_guidance import resolve_official_guidance_candidate
from wilq.content.workflow.research_proposal import (
    ContentResearchProposalCurrentProjection,
    build_default_evidence_research_coordinator,
)
from wilq.content.workflow.source_fact_candidate_projection import (
    ContentSourceFactAuthorityBlocker,
    ContentSourceFactAuthorityCandidateProjection,
    ContentSourceFactAuthorityRegistryReceipt,
    ContentSourceFactAuthorityServiceBinding,
    build_content_source_fact_authority_candidate_projection,
)

_HEX64 = r"^[0-9a-f]{64}$"
VALID_SOURCE_FACT_SCOPES: tuple[str, ...] = tuple(get_args(SourceFactScope))


class ResearchPromotionRequiredDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    field: Literal["scope", "confidence"]
    allowed_values: tuple[str, ...] = ()
    minimum: float | None = Field(default=None, ge=0, le=1)
    maximum: float | None = Field(default=None, ge=0, le=1)
    reason: str = Field(min_length=1)


class ResearchPromotionPolicySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_card_id: str
    target_card_type: str
    target_card_title: str
    card_status: str | None
    card_freshness: str | None
    card_evidence_ids: tuple[str, ...]
    card_source_connectors: tuple[str, ...]
    allowed_claims: tuple[str, ...]
    blocked_claims: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    policy_source_digest: str = Field(pattern=_HEX64)


class OfficialGuidanceResearchPromotionPolicySnapshot(ResearchPromotionPolicySnapshot):
    """Server-owned claim policy for the explicit official-guidance branch."""

    promotion_kind: Literal["official_guidance"] = "official_guidance"
    policy_version: Literal["official_guidance_policy_v1"] = "official_guidance_policy_v1"
    candidate_id: str = Field(min_length=1, max_length=240)
    candidate_digest: str = Field(pattern=_HEX64)
    candidate_canonical_path: str = Field(min_length=1, max_length=2048)
    candidate_title: str = Field(min_length=1, max_length=600)
    candidate_allowed_claims: tuple[str, ...] = Field(min_length=1, max_length=16)
    candidate_blocked_claims: tuple[str, ...] = ()
    classification_run_id: str = Field(min_length=1, max_length=240)
    classification_decision_set_digest: str = Field(pattern=_HEX64)
    classification_source_row_digest: str = Field(pattern=_HEX64)


class ResearchPromotionCandidateProjection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    response_type: Literal["content_research_promotion_candidate"] = (
        "content_research_promotion_candidate"
    )
    contract_version: Literal["content_research_promotion_candidate_v1"] = (
        "content_research_promotion_candidate_v1"
    )
    status: Literal["ready_for_human_decisions", "blocked"]
    proposal_id: str
    proposal_digest: str | None = Field(default=None, pattern=_HEX64)
    acquisition_run_id: str
    acquisition_run_digest: str | None = Field(default=None, pattern=_HEX64)
    observation_id: str | None
    freshness_date: str | None
    evidence_ids: tuple[str, ...]
    source_url: str | None
    source_connectors: tuple[str, ...]
    identity_binding_id: str | None
    identity_binding_digest: str | None = Field(default=None, pattern=_HEX64)
    classification_run_digest: str | None = Field(default=None, pattern=_HEX64)
    service_binding: ContentSourceFactAuthorityServiceBinding
    registry: ContentSourceFactAuthorityRegistryReceipt
    existing_scope_projection: ContentSourceFactAuthorityCandidateProjection | None = None
    policy: (
        ResearchPromotionPolicySnapshot
        | OfficialGuidanceResearchPromotionPolicySnapshot
        | None
    ) = None
    proposed_claim: str | None
    proposed_scope_text: str | None
    required_human_decisions: tuple[ResearchPromotionRequiredDecision, ...] = ()
    blockers: tuple[ContentSourceFactAuthorityBlocker, ...] = ()
    safe_next_step: str = Field(min_length=1)
    checked_at: datetime

    @model_validator(mode="after")
    def require_state(self) -> Self:
        if self.status == "blocked" and not self.blockers:
            raise ValueError("Blocked promotion candidate requires typed blockers.")
        if self.status == "ready_for_human_decisions" and (
            self.policy is None or not self.required_human_decisions
        ):
            raise ValueError("Promotion candidate requires explicit human decisions.")
        return self


class ResearchPromotionCandidateReader(Protocol):
    def read(self, proposal_id: str) -> ResearchPromotionCandidateProjection: ...


def build_research_promotion_candidate_projection(
    proposal: ContentResearchProposalCurrentProjection | None,
    *,
    acquisition_run: EvidenceAcquisitionRun | None,
    identity: ContentDeliveryIdentityBinding | None,
    classification: ContentProductionClassificationProjection | None,
    facts: tuple[ContentSourceFact, ...] | None = None,
    cards: tuple[ContentKnowledgeCard, ...] | None = None,
    checked_at: datetime | None = None,
) -> ResearchPromotionCandidateProjection:
    checked_at = checked_at or datetime.now(UTC)
    proposal_id = "missing"
    proposal_digest: str | None = None
    acquisition_run_id = "missing"
    acquisition_run_digest: str | None = None
    observation_id = None
    freshness_date = None
    evidence_ids: tuple[str, ...] = ()
    source_url = None
    source_connectors: tuple[str, ...] = ()
    proposed_claim = None
    proposed_scope_text = None
    if proposal is not None:
        proposal_id = proposal.proposal_id
        proposal_digest = proposal.proposal_digest
        proposed = proposal.recorded_proposal
        acquisition_run_id = proposed.acquisition_run_id
        acquisition_run_digest = proposed.acquisition_run_digest or "0" * 64
        observation_id = proposed.observation_id
        freshness_date = (
            acquisition_run.observation.freshness_date
            if acquisition_run is not None and acquisition_run.observation is not None
            else None
        )
        evidence_ids = proposed.evidence_ids
        source_url = proposed.source_url
        source_connectors = proposed.source_connectors
        proposed_claim = proposed.proposed_claim
        proposed_scope_text = proposed.scope
    binding = ContentSourceFactAuthorityServiceBinding(status="missing")
    registry = _registry_projection(facts, checked_at)
    blockers: list[ContentSourceFactAuthorityBlocker] = []
    if proposal is None:
        blockers.append(_blocker("proposal_missing", "Research proposal was not found."))
    elif proposal.current_status != "ready_for_review":
        blockers.extend(
            _blocker(item.code, item.reason) for item in proposal.current_blockers
        )
    elif acquisition_run is not None and acquisition_run.source_intent == "official_primary":
        official = _official_guidance_candidate(
            proposal=proposal,
            acquisition_run=acquisition_run,
            identity=identity,
            classification=classification,
            proposal_id=proposal_id,
            proposal_digest=proposal_digest,
            acquisition_run_id=acquisition_run_id,
            acquisition_run_digest=acquisition_run_digest,
            observation_id=observation_id,
            freshness_date=freshness_date,
            evidence_ids=evidence_ids,
            source_url=source_url,
            source_connectors=source_connectors,
            proposed_claim=proposed_claim,
            proposed_scope_text=proposed_scope_text,
            registry=registry,
            checked_at=checked_at,
        )
        if official is not None:
            return official
        blockers.append(
            _blocker(
                "official_guidance_lineage_invalid",
                (
                    "Official-guidance candidate, observation, identity or classification "
                    "is not exact."
                ),
                evidence_ids=evidence_ids,
                next_step=(
                    "Odśwież official-guidance observation i zwiąż ją z exact identity oraz "
                    "bieżącą klasyfikacją przed promotion."
                ),
            )
        )
    elif acquisition_run is None:
        blockers.append(_blocker("acquisition_run_missing", "Acquisition run is missing."))
    elif identity is None:
        blockers.append(_blocker("identity_binding_missing", "Exact identity binding is missing."))
    elif classification is None:
        blockers.append(_blocker("classification_missing", "Current classification is missing."))
    else:
        exact = build_content_source_fact_authority_candidate_projection(
            identity.binding_id,
            identity=identity,
            classification=classification,
            facts=facts,
            cards=cards,
            checked_at=checked_at,
        )
        binding = exact.service_binding
        if binding.card_id and binding.card_status != "approved_current":
            blockers.append(
                _blocker(
                    "service_card_review_required",
                    "Exact service card lifecycle is not approved_current: "
                    f"{binding.card_status or 'missing'}.",
                    evidence_ids=binding.card_evidence_ids,
                    next_step=(
                        "Sprawdź i zatwierdź exact kartę Service Profile przez człowieka "
                        "przed promocją source factu."
                    ),
                )
            )
        elif exact.status == "blocked":
            blockers.extend(_blocker(item.reason, item.reason) for item in exact.blockers)
        elif binding.status != "exact_bound" or not binding.card_id:
            blockers.append(
                _blocker(
                    "service_binding_missing",
                    "Exact service card binding is unavailable.",
                )
            )
        else:
            card = next(
                (
                    item
                    for item in (cards or ekologus_content_knowledge_cards())
                    if item.id == binding.card_id
                ),
                None,
            )
            if card is None:
                blockers.append(
                    _blocker("service_card_missing", "Exact service card was not found.")
                )
            elif card.lifecycle_status != "approved_current":
                blockers.append(
                    _blocker(
                        "service_card_review_required",
                        "Exact service card lifecycle is not approved_current: "
                        f"{card.lifecycle_status or 'missing'}.",
                    )
                )
            else:
                policy = _policy(card)
                return ResearchPromotionCandidateProjection(
                    status="ready_for_human_decisions",
                    proposal_id=proposal_id,
                    proposal_digest=proposal_digest,
                    acquisition_run_id=acquisition_run_id,
                    acquisition_run_digest=acquisition_run_digest,
                    observation_id=observation_id,
                    freshness_date=freshness_date,
                    evidence_ids=evidence_ids,
                    source_url=source_url,
                    source_connectors=source_connectors,
                    identity_binding_id=identity.binding_id,
                    identity_binding_digest=identity.binding_digest,
                    classification_run_digest=classification.run_digest,
                    service_binding=binding,
                    registry=registry,
                    existing_scope_projection=exact,
                    policy=policy,
                    proposed_claim=proposed_claim,
                    proposed_scope_text=proposed_scope_text,
                    required_human_decisions=(
                        ResearchPromotionRequiredDecision(
                            field="scope",
                            allowed_values=VALID_SOURCE_FACT_SCOPES,
                            reason=(
                                "Researcher scope is not an authoritative "
                                "ContentSourceFact scope."
                            ),
                        ),
                        ResearchPromotionRequiredDecision(
                            field="confidence",
                            minimum=0.0,
                            maximum=1.0,
                            reason=(
                                "Confidence requires an explicit human decision; "
                                "no default is invented."
                            ),
                        ),
                    ),
                    blockers=(),
                    safe_next_step=(
                        "Uzupełnij scope i confidence, potem przejdź osobny "
                        "promotion ActionObject."
                    ),
                    checked_at=checked_at,
                )
    return ResearchPromotionCandidateProjection(
        status="blocked",
        proposal_id=proposal_id,
        proposal_digest=proposal_digest,
        acquisition_run_id=acquisition_run_id,
        acquisition_run_digest=acquisition_run_digest,
        observation_id=observation_id,
        freshness_date=freshness_date,
        evidence_ids=evidence_ids,
        source_url=source_url,
        source_connectors=source_connectors,
        identity_binding_id=None if identity is None else identity.binding_id,
        identity_binding_digest=None if identity is None else identity.binding_digest,
        classification_run_digest=None if classification is None else classification.run_digest,
        service_binding=binding,
        registry=registry,
        proposed_claim=proposed_claim,
        proposed_scope_text=proposed_scope_text,
        blockers=tuple(blockers),
        safe_next_step=(
            blockers[0].next_step
            if blockers
            else "Najpierw usuń blocker exact scope/proposal, bez tworzenia factu."
        ),
        checked_at=checked_at,
    )


def build_default_research_promotion_candidate(
    proposal_id: str,
) -> ResearchPromotionCandidateProjection:
    from wilq.content.workflow.store.store import content_workflow_store

    proposal = build_default_evidence_research_coordinator().read(proposal_id)
    store = content_workflow_store()
    acquisition_run = None
    identity = None
    classification = None
    if proposal is not None:
        acquisition_run = store.get_evidence_acquisition_run(proposal.acquisition_run_id)
        if acquisition_run is not None and acquisition_run.identity_binding_id is not None:
            identity = store.load_content_delivery_identity(acquisition_run.identity_binding_id)
            if identity is not None:
                classification = store.load_production_classification_for_work_item(
                    identity.current_work_item_id
                )
    return build_research_promotion_candidate_projection(
        proposal,
        acquisition_run=acquisition_run,
        identity=identity,
        classification=classification,
    )


def _policy(card: ContentKnowledgeCard) -> ResearchPromotionPolicySnapshot:
    import json
    from hashlib import sha256

    payload = card.model_dump(mode="json")
    digest = sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return ResearchPromotionPolicySnapshot(
        target_card_id=card.id,
        target_card_type=card.card_type,
        target_card_title=card.title,
        card_status=card.lifecycle_status,
        card_freshness=card.freshness,
        card_evidence_ids=tuple(sorted(set(card.evidence_ids))),
        card_source_connectors=tuple(sorted(set(card.source_connectors))),
        allowed_claims=tuple(card.allowed_claims),
        blocked_claims=tuple(item.id for item in card.forbidden_claims),
        evidence_requirements=tuple(card.evidence_requirements),
        policy_source_digest=digest,
    )


def _official_guidance_candidate(
    *,
    proposal: ContentResearchProposalCurrentProjection,
    acquisition_run: EvidenceAcquisitionRun,
    identity: ContentDeliveryIdentityBinding | None,
    classification: ContentProductionClassificationProjection | None,
    proposal_id: str,
    proposal_digest: str | None,
    acquisition_run_id: str,
    acquisition_run_digest: str | None,
    observation_id: str | None,
    freshness_date: str | None,
    evidence_ids: tuple[str, ...],
    source_url: str | None,
    source_connectors: tuple[str, ...],
    proposed_claim: str | None,
    proposed_scope_text: str | None,
    registry: ContentSourceFactAuthorityRegistryReceipt,
    checked_at: datetime,
) -> ResearchPromotionCandidateProjection | None:
    """Build the server-owned official branch without a service-card fallback."""

    del proposal
    candidate_id = acquisition_run.official_guidance_candidate_id
    candidate = None if candidate_id is None else resolve_official_guidance_candidate(candidate_id)
    observation = acquisition_run.observation
    if (
        candidate is None
        or not isinstance(observation, OfficialGuidanceObservationReceipt)
        or acquisition_run.official_guidance_candidate_digest != candidate.candidate_digest
        or observation.candidate_id != candidate.candidate_id
        or observation.candidate_digest != candidate.candidate_digest
        or observation.canonical_path != candidate.canonical_path
        or observation.source_url != candidate.source_url
        or observation.observation_id != observation_id
        or observation.evidence_ids != evidence_ids
        or observation.source_connectors != source_connectors
        or source_url != candidate.source_url
    ):
        return None
    if identity is None or classification is None:
        return None
    if (
        identity.status != "exact_current"
        or identity.final_disposition != "keep"
        or classification.freshness.requires_refresh
        or classification.freshness.state != "fresh"
        or acquisition_run.identity_binding_id is None
        or acquisition_run.identity_binding_digest is None
        or acquisition_run.identity_binding_id != identity.binding_id
        or acquisition_run.identity_binding_digest != identity.binding_digest
        or acquisition_run.current_work_item_id != identity.current_work_item_id
        or acquisition_run.canonical_path != identity.canonical_path
        or acquisition_run.public_url != identity.public_url
        or identity.canonical_path != candidate.canonical_path
        or acquisition_run.classification_run_id != classification.run_id
        or acquisition_run.classification_run_digest != classification.run_digest
        or identity.classification_run_id != classification.run_id
        or identity.classification_run_digest != classification.run_digest
        or identity.classification_decision_set_digest != classification.decision_set_digest
        or identity.classification_source_row_digest != classification.row.source_packet_row_digest
        or classification.row.canonical_path != candidate.canonical_path
    ):
        return None
    policy_payload = {
        "promotion_kind": "official_guidance",
        "policy_version": "official_guidance_policy_v1",
        "candidate_id": candidate.candidate_id,
        "candidate_digest": candidate.candidate_digest,
        "candidate_canonical_path": candidate.canonical_path,
        "candidate_title": candidate.title,
        "candidate_allowed_claims": candidate.allowed_claim_scope,
        "candidate_blocked_claims": candidate.blocked_claims,
        "target_card_id": OFFICIAL_GUIDANCE_TARGET_CARD_ID,
        "target_card_type": OFFICIAL_GUIDANCE_TARGET_CARD_TYPE,
        "target_card_title": OFFICIAL_GUIDANCE_TARGET_CARD_TITLE,
        "allowed_claims": candidate.allowed_claim_scope,
        "blocked_claims": candidate.blocked_claims,
        "evidence_requirements": (
            "exact_official_guidance_observation",
            "human_review",
        ),
    }
    policy = OfficialGuidanceResearchPromotionPolicySnapshot(
        target_card_id=OFFICIAL_GUIDANCE_TARGET_CARD_ID,
        target_card_type=OFFICIAL_GUIDANCE_TARGET_CARD_TYPE,
        target_card_title=OFFICIAL_GUIDANCE_TARGET_CARD_TITLE,
        card_status="approved_current",
        card_freshness="official_guidance_policy_v1",
        card_evidence_ids=tuple(sorted(set(evidence_ids))),
        card_source_connectors=tuple(sorted(set(source_connectors))),
        allowed_claims=tuple(candidate.allowed_claim_scope),
        blocked_claims=tuple(candidate.blocked_claims),
        evidence_requirements=(
            "exact_official_guidance_observation",
            "human_review",
        ),
        policy_source_digest=canonical_json_digest(policy_payload),
        candidate_id=candidate.candidate_id,
        candidate_digest=candidate.candidate_digest,
        candidate_canonical_path=candidate.canonical_path,
        candidate_title=candidate.title,
        candidate_allowed_claims=tuple(candidate.allowed_claim_scope),
        candidate_blocked_claims=tuple(candidate.blocked_claims),
        classification_run_id=classification.run_id,
        classification_decision_set_digest=classification.decision_set_digest,
        classification_source_row_digest=classification.row.source_packet_row_digest,
    )
    if (
        proposal_digest is None
        or acquisition_run_digest is None
        or observation_id is None
        or freshness_date is None
        or proposed_claim is None
        or proposed_scope_text is None
    ):
        return None
    return ResearchPromotionCandidateProjection(
        status="ready_for_human_decisions",
        proposal_id=proposal_id,
        proposal_digest=proposal_digest,
        acquisition_run_id=acquisition_run_id,
        acquisition_run_digest=acquisition_run_digest,
        observation_id=observation_id,
        freshness_date=freshness_date,
        evidence_ids=evidence_ids,
        source_url=source_url,
        source_connectors=source_connectors,
        identity_binding_id=identity.binding_id,
        identity_binding_digest=identity.binding_digest,
        classification_run_digest=classification.run_digest,
        service_binding=ContentSourceFactAuthorityServiceBinding(
            status="exact_bound",
            binding_url=identity.public_url,
        ),
        registry=registry,
        policy=policy,
        proposed_claim=proposed_claim,
        proposed_scope_text=proposed_scope_text,
        required_human_decisions=(
            ResearchPromotionRequiredDecision(
                field="scope",
                allowed_values=("claim_policy",),
                reason=(
                    "Official guidance promotion fixes claim_policy; the reviewer cannot "
                    "change it to a service or regulatory scope."
                ),
            ),
            ResearchPromotionRequiredDecision(
                field="confidence",
                minimum=0.0,
                maximum=1.0,
                reason="Confidence requires an explicit human decision; no default is invented.",
            ),
        ),
        blockers=(),
        safe_next_step=(
            "Sprawdź exact claim, zachowany blocked scope oraz lineage official guidance; "
            "następnie przejdź promotion ActionObject."
        ),
        checked_at=checked_at,
    )


def _registry_projection(
    facts: tuple[ContentSourceFact, ...] | None,
    checked_at: datetime,
) -> ContentSourceFactAuthorityRegistryReceipt:
    from wilq.content.workflow.source_fact_candidate_projection import _registry_receipt

    return _registry_receipt(facts or ekologus_source_facts(), checked_at)


def _blocker(
    code: str,
    reason: str,
    *,
    evidence_ids: tuple[str, ...] = (),
    next_step: str = "Odśwież exact dane i spróbuj ponownie.",
) -> ContentSourceFactAuthorityBlocker:
    return ContentSourceFactAuthorityBlocker(
        seam="research_promotion",
        reason=f"{code}: {reason}",
        evidence_ids=evidence_ids,
        next_step=next_step,
    )


__all__ = [
    "OfficialGuidanceResearchPromotionPolicySnapshot",
    "ResearchPromotionCandidateProjection",
    "ResearchPromotionPolicySnapshot",
    "ResearchPromotionRequiredDecision",
    "VALID_SOURCE_FACT_SCOPES",
    "build_default_research_promotion_candidate",
    "build_research_promotion_candidate_projection",
]
