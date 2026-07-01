from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.knowledge.cards import (
    ContentKnowledgeCard,
    ContentKnowledgeClaimRule,
    ContentKnowledgeProductionDepthReadiness,
    content_knowledge_cards_response,
)
from wilq.content.knowledge.private_source_proposals import (
    PrivateSourceProposal,
    ekologus_private_source_proposal_registry,
)
from wilq.content.knowledge.source_facts import (
    ContentKnowledgeLifecycleStatus,
    ekologus_source_fact_registry,
)

ServiceProfileGapSeverity = Literal["blocker", "review_required", "thin", "stale"]
ServiceProfileReviewActionMode = Literal["prepare", "review_request"]


class ContentServiceProfileReviewPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_edit_cards: bool
    can_promote_facts: bool
    can_request_review: bool
    review_required_label: str
    blocked_write_reason: str


class ContentServiceProfileCoverageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_count: int
    service_card_count: int
    seeded_contract_proof_count: int
    source_backed_review_required_count: int
    approved_current_count: int
    stale_count: int
    rejected_count: int
    private_candidate_count: int
    missing_required_area_count: int
    ready_for_daily_content: bool
    status_label: str
    safe_next_step: str


class ContentServiceProfileServiceSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str
    title: str
    status: ContentKnowledgeLifecycleStatus
    status_label: str
    summary: str
    source_fact_ids: list[str] = Field(default_factory=list)
    source_connector_labels: list[str] = Field(default_factory=list)
    source_lineage_labels: list[str] = Field(default_factory=list)
    freshness_label: str
    confidence_label: str
    service_fit_terms: list[str] = Field(default_factory=list)
    buyer_problem_terms: list[str] = Field(default_factory=list)
    buyer_triggers: list[str] = Field(default_factory=list)
    cta_patterns: list[str] = Field(default_factory=list)
    allowed_claims: list[str] = Field(default_factory=list)
    claims_needing_review: list[ContentKnowledgeClaimRule] = Field(default_factory=list)
    forbidden_claims: list[ContentKnowledgeClaimRule] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    usage_notes: list[str] = Field(default_factory=list)
    safe_next_step: str
    review_request_hint: str


class ContentServiceProfilePolicySection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: str
    title: str
    status: ContentKnowledgeLifecycleStatus
    claims_needing_review: list[ContentKnowledgeClaimRule] = Field(default_factory=list)
    forbidden_claims: list[ContentKnowledgeClaimRule] = Field(default_factory=list)
    measurement_sensitive_claims: list[ContentKnowledgeClaimRule] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    safe_next_step: str


class ContentServiceProfilePrivateSourceProposalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_protocol_available: bool
    proposal_count: int
    review_required_count: int
    approved_count: int
    promotion_ready: bool
    promotion_checklist: list[str] = Field(default_factory=list)
    promotion_blocked_reason: str
    proposal_source_labels: list[str] = Field(default_factory=list)
    review_required_proposal_ids: list[str] = Field(default_factory=list)
    redacted: bool
    safe_next_step: str


class ContentServiceProfilePrivateSourceProposalSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    target_card_id: str
    target_card_title: str
    source_class_label: str
    source_locator_label: str
    review_status: str
    support_level: str
    risk_tier: str
    confidence_label: str
    owner_role: str
    redacted: bool
    blocked_claims: list[str] = Field(default_factory=list)
    safe_next_step: str
    promotion_allowed: bool
    blocked_write_claim: str


class ContentServiceProfileCoverageGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gap_id: str
    area: str
    severity: ServiceProfileGapSeverity
    label: str
    reason: str
    needed_source_type: str
    safe_next_step: str
    example_work_item_ids: list[str] = Field(default_factory=list)


class ContentServiceProfileReviewAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    mode: ServiceProfileReviewActionMode
    label: str
    reason: str
    blocked_write_claim: str
    required_human_role: str
    target_card_id: str | None = None
    gap_id: str | None = None


class ContentServiceProfileTechnicalTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    knowledge_card_endpoint: str
    source_fact_count: int
    source_fact_ids: list[str] = Field(default_factory=list)
    private_source_proposal_ids: list[str] = Field(default_factory=list)
    private_source_protocol_doc: str


class ContentServiceProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    workspace_label: str
    generated_at: str
    read_only: bool
    review_policy: ContentServiceProfileReviewPolicy
    production_depth_readiness: ContentKnowledgeProductionDepthReadiness
    coverage_summary: ContentServiceProfileCoverageSummary
    service_sections: list[ContentServiceProfileServiceSection] = Field(default_factory=list)
    claim_policy_sections: list[ContentServiceProfilePolicySection] = Field(default_factory=list)
    evidence_policy_sections: list[ContentServiceProfilePolicySection] = Field(default_factory=list)
    private_source_proposal_summary: ContentServiceProfilePrivateSourceProposalSummary
    private_source_proposals: list[ContentServiceProfilePrivateSourceProposalSection] = Field(
        default_factory=list
    )
    coverage_gaps: list[ContentServiceProfileCoverageGap] = Field(default_factory=list)
    review_actions: list[ContentServiceProfileReviewAction] = Field(default_factory=list)
    technical_trace: ContentServiceProfileTechnicalTrace


def content_service_profile_response() -> ContentServiceProfileResponse:
    knowledge = content_knowledge_cards_response()
    source_fact_registry = ekologus_source_fact_registry()
    private_proposal_registry = ekologus_private_source_proposal_registry()
    cards = knowledge.cards
    service_sections = [_service_section(card) for card in cards if card.card_type == "service"]
    coverage_gaps = _coverage_gaps(cards)
    return ContentServiceProfileResponse(
        workspace_id="ekologus",
        workspace_label="Ekologus",
        generated_at="2026-07-01T00:00:00Z",
        read_only=True,
        review_policy=ContentServiceProfileReviewPolicy(
            can_edit_cards=False,
            can_promote_facts=False,
            can_request_review=True,
            review_required_label=(
                "Wiedza review-required może wspierać analizę i UAT, "
                "ale nie odblokowuje production-depth treści."
            ),
            blocked_write_reason=(
                "Edycja kart i promocja faktów wymagają osobnego ActionObject, "
                "review człowieka i audytu."
            ),
        ),
        production_depth_readiness=knowledge.production_depth_readiness,
        coverage_summary=_coverage_summary(
            cards=cards,
            private_candidate_count=sum(
                1
                for proposal in private_proposal_registry.proposals
                if proposal.source_type == "private_candidate"
            ),
            missing_required_area_count=len(coverage_gaps),
            status_label=knowledge.production_depth_readiness.status_label,
            ready_for_daily_content=knowledge.production_depth_readiness.ready_for_daily_content,
        ),
        service_sections=service_sections,
        claim_policy_sections=[
            _policy_section(card)
            for card in cards
            if card.claims_needing_review
            or card.forbidden_claims
            or card.measurement_sensitive_claims
        ],
        evidence_policy_sections=[
            _policy_section(card)
            for card in cards
            if card.card_type == "evidence_requirement" or card.evidence_requirements
        ],
        private_source_proposal_summary=_private_source_proposal_summary(
            private_proposal_registry.proposals
        ),
        private_source_proposals=_private_source_proposal_sections(
            private_proposal_registry.proposals
        ),
        coverage_gaps=coverage_gaps,
        review_actions=_review_actions(
            coverage_gaps=coverage_gaps,
            private_proposals=private_proposal_registry.proposals,
        ),
        technical_trace=ContentServiceProfileTechnicalTrace(
            knowledge_card_endpoint="/api/content/knowledge-cards",
            source_fact_count=source_fact_registry.fact_count,
            source_fact_ids=[fact.source_id for fact in source_fact_registry.facts],
            private_source_proposal_ids=[
                proposal.proposal_id for proposal in private_proposal_registry.proposals
            ],
            private_source_protocol_doc="docs/architecture/private-source-proposal-protocol.md",
        ),
    )


def _private_source_proposal_sections(
    proposals: list[PrivateSourceProposal],
) -> list[ContentServiceProfilePrivateSourceProposalSection]:
    return [
        ContentServiceProfilePrivateSourceProposalSection(
            proposal_id=proposal.proposal_id,
            target_card_id=proposal.target_card_id,
            target_card_title=proposal.target_card_title,
            source_class_label=proposal.source_class_label,
            source_locator_label=proposal.source_locator_label,
            review_status=proposal.review_status,
            support_level=proposal.support_level,
            risk_tier=proposal.risk_tier,
            confidence_label=_confidence_label(proposal.confidence),
            owner_role=proposal.owner_role,
            redacted=True,
            blocked_claims=proposal.blocked_claims,
            safe_next_step=proposal.safe_next_step,
            promotion_allowed=False,
            blocked_write_claim=(
                "To jest redacted proposal do review; nie promuje source fact ani "
                "knowledge card."
            ),
        )
        for proposal in proposals
    ]


def _private_source_proposal_summary(
    proposals: list[PrivateSourceProposal],
) -> ContentServiceProfilePrivateSourceProposalSummary:
    review_required = [
        proposal for proposal in proposals if proposal.review_status == "review_required"
    ]
    approved = [proposal for proposal in proposals if proposal.review_status == "approved"]
    if review_required:
        safe_next_step = (
            "Pokaż redacted propozycje Wilkowi i zdecyduj, czy któraś ma stać się "
            "reviewed internal source fact; żadna nie odblokowuje production-depth."
        )
    else:
        safe_next_step = (
            "Użyj protokołu private source proposals dopiero po metadata-only "
            "intake i decyzji ownera."
        )
    return ContentServiceProfilePrivateSourceProposalSummary(
        proposal_protocol_available=True,
        proposal_count=len(proposals),
        review_required_count=len(review_required),
        approved_count=len(approved),
        promotion_ready=False,
        promotion_checklist=[
            "Wilku albo owner potwierdza, że propozycja opisuje realną ofertę Ekologus.",
            "Źródło zostaje streszczone jako redacted/source-safe fact bez raw private text.",
            "Owner wskazuje dozwolone claimy, claimy wymagające review i claimy zakazane.",
            "WILQ zapisuje reviewer, freshness date, confidence i evidence/source lineage.",
            "Focused eval potwierdza, że karta nie odblokowuje legal/product/performance claimów.",
        ],
        promotion_blocked_reason=(
            "Brak zatwierdzenia człowieka i reviewed source fact; Service Profile pokazuje "
            "tylko propozycje review, bez promocji do wiedzy produkcyjnej."
        ),
        proposal_source_labels=_unique(
            proposal.source_locator_label for proposal in proposals
        ),
        review_required_proposal_ids=[
            proposal.proposal_id for proposal in review_required
        ],
        redacted=True,
        safe_next_step=safe_next_step,
    )


def _coverage_summary(
    *,
    cards: list[ContentKnowledgeCard],
    private_candidate_count: int,
    missing_required_area_count: int,
    status_label: str,
    ready_for_daily_content: bool,
) -> ContentServiceProfileCoverageSummary:
    lifecycle_counts = Counter(_lifecycle(card) for card in cards)
    return ContentServiceProfileCoverageSummary(
        card_count=len(cards),
        service_card_count=sum(1 for card in cards if card.card_type == "service"),
        seeded_contract_proof_count=lifecycle_counts["seeded_contract_proof"],
        source_backed_review_required_count=lifecycle_counts["source_backed_review_required"],
        approved_current_count=lifecycle_counts["approved_current"],
        stale_count=lifecycle_counts["stale"],
        rejected_count=lifecycle_counts["rejected"],
        private_candidate_count=private_candidate_count,
        missing_required_area_count=missing_required_area_count,
        ready_for_daily_content=ready_for_daily_content,
        status_label=status_label,
        safe_next_step=(
            "Przejrzyj karty review-required i luki usługowe z Wilkiem przed "
            "użyciem ich jako production-depth."
        ),
    )


def _service_section(card: ContentKnowledgeCard) -> ContentServiceProfileServiceSection:
    status = _lifecycle(card)
    return ContentServiceProfileServiceSection(
        card_id=card.id,
        title=card.title,
        status=status,
        status_label=_status_label(status),
        summary=card.summary,
        source_fact_ids=card.source_fact_ids,
        source_connector_labels=card.source_connectors,
        source_lineage_labels=_redacted_lineage(card.source_lineage),
        freshness_label=card.freshness,
        confidence_label=_confidence_label(card.confidence),
        service_fit_terms=card.service_fit_terms,
        buyer_problem_terms=card.buyer_problem_terms,
        buyer_triggers=card.buyer_triggers,
        cta_patterns=card.cta_patterns,
        allowed_claims=card.allowed_claims,
        claims_needing_review=card.claims_needing_review,
        forbidden_claims=card.forbidden_claims,
        evidence_requirements=card.evidence_requirements,
        usage_notes=card.usage_notes,
        safe_next_step=_safe_next_step(status),
        review_request_hint=(
            "Poproś Wilka/ownera o decyzję: approve, stale, reject albo potrzebne źródło."
        ),
    )


def _policy_section(card: ContentKnowledgeCard) -> ContentServiceProfilePolicySection:
    status = _lifecycle(card)
    return ContentServiceProfilePolicySection(
        card_id=card.id,
        title=card.title,
        status=status,
        claims_needing_review=card.claims_needing_review,
        forbidden_claims=card.forbidden_claims,
        measurement_sensitive_claims=card.measurement_sensitive_claims,
        evidence_requirements=card.evidence_requirements,
        safe_next_step=_safe_next_step(status),
    )


def _coverage_gaps(cards: list[ContentKnowledgeCard]) -> list[ContentServiceProfileCoverageGap]:
    service_terms = {term.lower() for card in cards for term in card.service_fit_terms}
    gaps: list[ContentServiceProfileCoverageGap] = []
    if "operat wodnoprawny" not in service_terms:
        gaps.append(
            ContentServiceProfileCoverageGap(
                gap_id="gap_service_operat_wodnoprawny",
                area="operat wodnoprawny",
                severity="blocker",
                label="Brak bezpośredniej karty usługi dla operatu wodnoprawnego",
                reason=(
                    "WILQ nie powinien dopasowywać szerokiej karty środowiskowej "
                    "do konkretnej usługi bez źródła."
                ),
                needed_source_type="public_site_or_reviewed_internal_service_fact",
                safe_next_step=(
                    "Dodaj publiczny albo reviewed internal source fact i zostaw go "
                    "review-required do decyzji Wilka."
                ),
                example_work_item_ids=["content_work_item_operat_wodnoprawny"],
            )
        )
    if not any(_lifecycle(card) == "approved_current" for card in cards):
        gaps.append(
            ContentServiceProfileCoverageGap(
                gap_id="gap_no_approved_current_cards",
                area="production-depth",
                severity="review_required",
                label="Brak zatwierdzonych production-depth kart usług",
                reason="Obecne karty są seedami albo source-backed review-required.",
                needed_source_type="owner_reviewed_source_fact",
                safe_next_step="Przeprowadź review kart usługowych i zapisz reviewer/freshness.",
            )
        )
    return gaps


def _review_actions(
    *,
    coverage_gaps: list[ContentServiceProfileCoverageGap],
    private_proposals: list[PrivateSourceProposal],
) -> list[ContentServiceProfileReviewAction]:
    actions = [
        ContentServiceProfileReviewAction(
            action_id="service_profile_request_knowledge_review",
            mode="review_request",
            label="Poproś o review wiedzy usługowej",
            reason=(
                "Karty review-required nie mogą odblokować production-depth "
                "bez decyzji człowieka."
            ),
            blocked_write_claim="To nie zapisuje zmian w kartach wiedzy.",
            required_human_role="Wilku albo owner wiedzy Ekologus",
        )
    ]
    for gap in coverage_gaps:
        actions.append(
            ContentServiceProfileReviewAction(
                action_id=f"service_profile_review_{gap.gap_id}",
                mode="prepare",
                label=f"Przygotuj review: {gap.label}",
                reason=gap.reason,
                blocked_write_claim="To jest przygotowanie review, nie edycja knowledge base.",
                required_human_role="Wilku albo owner wiedzy Ekologus",
                gap_id=gap.gap_id,
            )
        )
    for proposal in private_proposals:
        if proposal.review_status != "review_required":
            continue
        actions.append(
            ContentServiceProfileReviewAction(
                action_id=f"service_profile_review_{proposal.proposal_id}",
                mode="review_request",
                label=f"Sprawdź prywatną propozycję: {proposal.target_card_title}",
                reason=(
                    f"{proposal.source_locator_label} jest redacted i review-required; "
                    "może wspierać pytania UAT, ale nie production-depth."
                ),
                blocked_write_claim=(
                    "To nie promuje private proposal do source fact ani knowledge card."
                ),
                required_human_role=proposal.owner_role,
                target_card_id=proposal.target_card_id,
            )
        )
    return actions


def _lifecycle(card: ContentKnowledgeCard) -> ContentKnowledgeLifecycleStatus:
    return card.lifecycle_status or "seeded_contract_proof"


def _status_label(status: ContentKnowledgeLifecycleStatus) -> str:
    return {
        "seeded_contract_proof": "seed kontraktu, nie wiedza produkcyjna",
        "source_backed_review_required": "źródło istnieje, wymagane review",
        "approved_current": "zatwierdzone i aktualne",
        "stale": "wymaga odświeżenia",
        "rejected": "odrzucone, nie używać",
    }[status]


def _safe_next_step(status: ContentKnowledgeLifecycleStatus) -> str:
    if status == "approved_current":
        return "Może wspierać production-depth po sprawdzeniu live evidence dla zadania."
    if status == "stale":
        return "Odśwież źródło i poproś o review przed użyciem."
    if status == "rejected":
        return "Nie używaj w treściach."
    return "Użyj do analizy/UAT, ale poproś o review przed finalnym draftem."


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.8:
        return "wysoka"
    if confidence >= 0.65:
        return "średnia"
    return "niska"


def _redacted_lineage(lineage: list[str]) -> list[str]:
    return [
        item
        for item in lineage
        if item.startswith("https://") or item.startswith("docs/") or item.startswith("wilq/")
    ]


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
