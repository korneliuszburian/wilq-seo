from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.knowledge.cards import (
    ContentKnowledgeCard,
    ContentKnowledgeClaimRule,
    ContentKnowledgeProductionDepthReadiness,
    content_knowledge_cards_response,
)
from wilq.content.knowledge.private_source_proposals import (
    PrivateSourceProposal,
    PrivateSourceProposalAudience,
    PrivateSourceProposalFreshnessStatus,
    PrivateSourceProposalPrivacyClass,
    PrivateSourceProposalRetentionDecision,
    PrivateSourceProposalReviewStatus,
    PrivateSourceProposalScope,
    PrivateSourceProposalType,
    ekologus_private_source_proposal_registry,
)
from wilq.content.knowledge.source_facts import (
    ContentKnowledgeLifecycleStatus,
    ContentSourceFact,
    ekologus_source_fact_registry,
)

ServiceProfileGapSeverity = Literal["blocker", "review_required", "thin", "stale"]
ServiceProfileNeededSourceType = Literal[
    "public_site_or_reviewed_internal_service_fact",
    "owner_reviewed_source_fact",
]
ServiceProfileReviewActionMode = Literal["prepare", "review_request"]
ServiceProfileReviewActionPriority = Literal["high", "medium", "low"]
ServiceProfileReviewDecisionOption = Literal["approve", "needs_changes", "stale", "reject"]
ServiceProfileReviewRequirementType = Literal["text", "boolean", "follow_up"]
ServiceProfileApprovalReadinessStatus = Literal[
    "blocked",
    "ready_for_review",
    "ready_for_promotion_request",
]
ServiceProfilePrivateProposalRiskTier = Literal["low", "medium", "high", "unknown"]
ServiceProfilePrivateProposalSupportLevel = Literal[
    "direct", "partial", "background", "conflicting"
]
ServiceProfileReviewActionScope = Literal[
    "general_knowledge_review",
    "public_service_card",
    "coverage_gap",
    "private_service_proposal",
    "private_claim_policy_proposal",
    "private_evidence_policy_proposal",
]


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
    evidence_ids: list[str] = Field(default_factory=list)
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
    service_proposal_count: int
    claim_policy_proposal_count: int
    evidence_requirement_proposal_count: int
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
    source_id: str
    source_type: PrivateSourceProposalType
    privacy_class: PrivateSourceProposalPrivacyClass
    scope: PrivateSourceProposalScope
    target_card_id: str
    target_card_title: str
    source_class_label: str
    source_locator_label: str
    freshness_status: PrivateSourceProposalFreshnessStatus
    review_status: PrivateSourceProposalReviewStatus
    support_level: ServiceProfilePrivateProposalSupportLevel
    risk_tier: ServiceProfilePrivateProposalRiskTier
    data_classes: list[str] = Field(default_factory=list)
    source_block_refs: list[str] = Field(default_factory=list)
    retention_decision: PrivateSourceProposalRetentionDecision
    deletion_path: list[str] = Field(default_factory=list)
    eval_case_ids: list[str] = Field(default_factory=list)
    confidence_label: str
    owner_role: str
    audience: PrivateSourceProposalAudience
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
    needed_source_type: ServiceProfileNeededSourceType
    safe_next_step: str
    example_work_item_ids: list[str] = Field(default_factory=list)


class ContentServiceProfileReviewRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    label: str
    requirement_type: ServiceProfileReviewRequirementType
    required: bool
    blocking_rule: str | None = None


class ContentServiceProfileReviewAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    mode: ServiceProfileReviewActionMode
    review_scope: ServiceProfileReviewActionScope
    priority: ServiceProfileReviewActionPriority
    decision_options: list[ServiceProfileReviewDecisionOption] = Field(default_factory=list)
    review_requirements: list[ContentServiceProfileReviewRequirement] = Field(
        default_factory=list
    )
    label: str
    reason: str
    blocked_write_claim: str
    required_human_role: str
    target_card_id: str | None = None
    gap_id: str | None = None


class ContentServiceProfileReviewActionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_count: int
    review_request_count: int
    prepare_count: int
    public_service_review_count: int
    private_review_count: int
    private_service_review_count: int
    private_policy_review_count: int
    first_review_action_id: str | None = None
    first_review_action_label: str | None = None
    first_review_action_reason: str | None = None
    first_review_action_scope: ServiceProfileReviewActionScope | None = None
    first_review_action_priority: ServiceProfileReviewActionPriority | None = None
    first_review_action_target_card_id: str | None = None
    first_review_action_gap_id: str | None = None
    first_review_required_fields: list[str] = Field(default_factory=list)
    first_review_safe_next_step: str | None = None
    safe_next_step: str


class ContentServiceProfilePrivateReviewValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_count: int
    promotion_allowed_count: int
    blocked_claim_proposal_count: int
    cta_pattern_proposal_count: int
    buyer_trigger_proposal_count: int
    operator_value_score: int = Field(ge=0, le=10)
    value_summary: str
    review_value_points: list[str] = Field(default_factory=list)
    review_questions: list[str] = Field(default_factory=list)


class ContentServiceProfilePrivateReviewQueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    source_id: str
    scope: PrivateSourceProposalScope
    target_card_id: str
    target_card_title: str
    risk_tier: ServiceProfilePrivateProposalRiskTier
    freshness_status: PrivateSourceProposalFreshnessStatus
    audience: PrivateSourceProposalAudience
    review_status: PrivateSourceProposalReviewStatus
    promotion_allowed: bool
    blocked_claim_count: int
    data_classes: list[str] = Field(default_factory=list)
    source_block_refs: list[str] = Field(default_factory=list)
    retention_decision: PrivateSourceProposalRetentionDecision
    deletion_path: list[str] = Field(default_factory=list)
    eval_case_ids: list[str] = Field(default_factory=list)
    source_locator_label: str
    owner_role: str
    redacted: bool
    source_trace_ready: bool
    safe_next_step: str


class ContentServiceProfileReviewQueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str
    review_scope: ServiceProfileReviewActionScope
    priority: ServiceProfileReviewActionPriority
    target_card_id: str | None = None
    target_card_title: str
    decision_options: list[ServiceProfileReviewDecisionOption] = Field(
        default_factory=list
    )


class ContentServiceProfileSourceFactCoverageAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pass_state: bool
    knowledge_status: ContentKnowledgeLifecycleStatus
    ready_for_daily_content: bool
    production_depth_percent: int = Field(ge=0, le=100)
    approved_service_percent: int = Field(ge=0, le=100)
    reviewed_fact_percent: int = Field(ge=0, le=100)
    fact_count: int
    fact_review_counts: dict[str, int] = Field(default_factory=dict)
    fact_scope_counts: dict[str, int] = Field(default_factory=dict)
    fact_connector_counts: dict[str, int] = Field(default_factory=dict)
    service_card_count: int
    coverage_gap_count: int
    review_action_count: int
    first_review_action_id: str | None = None
    first_review_action_label: str | None = None
    private_proposal_count: int
    private_review_required_count: int
    private_review_value: ContentServiceProfilePrivateReviewValue
    private_review_queue: list[ContentServiceProfilePrivateReviewQueueItem] = Field(
        default_factory=list
    )
    review_action_queue: list[ContentServiceProfileReviewQueueItem] = Field(
        default_factory=list
    )
    blockers: list[str] = Field(default_factory=list)
    safe_next_step: str


class ContentServiceProfileApprovalReadinessItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    label: str
    status: ServiceProfileApprovalReadinessStatus
    blocking: bool
    detail: str
    next_step: str
    related_action_id: str | None = None


class ContentServiceProfileApprovalReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ServiceProfileApprovalReadinessStatus
    status_label: str
    can_request_promotion: bool
    mutation_allowed: bool
    production_depth_unlocked: bool
    reviewed_output_required: bool
    approved_current_count: int
    review_required_count: int
    first_action_id: str | None = None
    first_action_label: str | None = None
    blockers: list[str] = Field(default_factory=list)
    checklist: list[ContentServiceProfileApprovalReadinessItem] = Field(
        default_factory=list
    )
    safe_next_step: str


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
    private_review_value: ContentServiceProfilePrivateReviewValue
    private_source_proposals: list[ContentServiceProfilePrivateSourceProposalSection] = Field(
        default_factory=list
    )
    coverage_gaps: list[ContentServiceProfileCoverageGap] = Field(default_factory=list)
    review_action_summary: ContentServiceProfileReviewActionSummary
    review_actions: list[ContentServiceProfileReviewAction] = Field(default_factory=list)
    source_fact_coverage: ContentServiceProfileSourceFactCoverageAudit
    approval_readiness: ContentServiceProfileApprovalReadiness
    technical_trace: ContentServiceProfileTechnicalTrace


def content_service_profile_response() -> ContentServiceProfileResponse:
    knowledge = content_knowledge_cards_response()
    source_fact_registry = ekologus_source_fact_registry()
    private_proposal_registry = ekologus_private_source_proposal_registry()
    cards = knowledge.cards
    source_facts = list(source_fact_registry.facts)
    service_sections = [_service_section(card) for card in cards if card.card_type == "service"]
    coverage_gaps = _coverage_gaps(cards)
    private_proposals = private_proposal_registry.proposals
    review_actions = _review_actions(
        cards=cards,
        coverage_gaps=coverage_gaps,
        private_proposals=private_proposals,
    )
    review_action_summary = _review_action_summary(
        review_actions=review_actions,
    )
    coverage_summary = _coverage_summary(
        cards=cards,
        private_candidate_count=private_proposal_registry.proposal_count,
        missing_required_area_count=len(coverage_gaps),
        status_label=knowledge.production_depth_readiness.status_label,
        ready_for_daily_content=knowledge.production_depth_readiness.ready_for_daily_content,
    )
    source_fact_coverage = _source_fact_coverage_audit(
        source_facts=source_facts,
        service_sections=service_sections,
        private_proposals=private_proposals,
        coverage_summary=coverage_summary,
        production_depth_readiness=knowledge.production_depth_readiness,
        coverage_gaps=coverage_gaps,
        review_action_summary=review_action_summary,
        review_actions=review_actions,
    )
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
                "Edycja kart i promocja faktów wymagają osobnej zatwierdzonej "
                "akcji, review człowieka i audytu."
            ),
        ),
        production_depth_readiness=knowledge.production_depth_readiness,
        coverage_summary=coverage_summary,
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
            private_proposals
        ),
        private_review_value=source_fact_coverage.private_review_value,
        private_source_proposals=_private_source_proposal_sections(
            private_proposals
        ),
        coverage_gaps=coverage_gaps,
        review_action_summary=review_action_summary,
        review_actions=review_actions,
        source_fact_coverage=source_fact_coverage,
        approval_readiness=_approval_readiness(
            coverage_summary=coverage_summary,
            review_action_summary=review_action_summary,
            private_proposals=private_proposals,
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


def _approval_readiness(
    *,
    coverage_summary: ContentServiceProfileCoverageSummary,
    review_action_summary: ContentServiceProfileReviewActionSummary,
    private_proposals: list[PrivateSourceProposal],
) -> ContentServiceProfileApprovalReadiness:
    approved_current_count = coverage_summary.approved_current_count
    review_required_count = coverage_summary.source_backed_review_required_count
    private_pending_count = sum(
        1
        for proposal in private_proposals
        if proposal.retention_decision == "pending_owner_decision"
        or proposal.review_status == "review_required"
    )
    checklist = [
        ContentServiceProfileApprovalReadinessItem(
            code="public_service_review",
            label="Publiczne karty usług sprawdzone przez człowieka",
            status=(
                "ready_for_review"
                if review_action_summary.public_service_review_count
                else "blocked"
            ),
            blocking=approved_current_count == 0,
            detail=(
                f"{review_action_summary.public_service_review_count} publicznych kart "
                "czeka na decyzję review; żadna nie jest jeszcze zatwierdzona jako "
                "wiedza do finalnych treści."
                if approved_current_count == 0
                else f"{approved_current_count} kart ma status zatwierdzonej wiedzy."
            ),
            next_step=(
                "Zacznij od pierwszej publicznej karty usługi i zapisz decyzję: "
                "zatwierdź, popraw, oznacz jako nieaktualne albo odrzuć."
            ),
            related_action_id=review_action_summary.first_review_action_id,
        ),
        ContentServiceProfileApprovalReadinessItem(
            code="source_trace_review",
            label="Ślad źródłowy i zablokowane twierdzenia sprawdzone",
            status=(
                "ready_for_review"
                if review_action_summary.first_review_required_fields
                else "blocked"
            ),
            blocking=True,
            detail=(
                "Review musi potwierdzić czytelny ślad źródłowy, zablokowane "
                "twierdzenia, notatkę review i decyzję człowieka."
            ),
            next_step=(
                "Użyj pól review z Service Profile zamiast ręcznie zgadywać, "
                "co Wilku ma podpisać."
            ),
            related_action_id=review_action_summary.first_review_action_id,
        ),
        ContentServiceProfileApprovalReadinessItem(
            code="private_source_governance",
            label="Prywatne propozycje ekologus-ai mają decyzję ownera",
            status="blocked" if private_pending_count else "ready_for_review",
            blocking=private_pending_count > 0,
            detail=(
                f"{private_pending_count} prywatnych propozycji nadal wymaga decyzji "
                "review, retencji albo aktualności; nie może odblokować finalnych "
                "treści."
            )
            if private_pending_count
            else "Prywatne propozycje nie blokują obecnej ścieżki review.",
            next_step=(
                "Dla prywatnych propozycji potwierdź klasy danych, bloki źródła, "
                "aktualność, odbiorców, retencję, ścieżkę usunięcia i bramki ewaluacji."
            ),
        ),
        ContentServiceProfileApprovalReadinessItem(
            code="promotion_request_packet",
            label="Osobny wniosek o zatwierdzenie jest gotowy do przygotowania",
            status="blocked",
            blocking=True,
            detail=(
                "WILQ nie ma jeszcze zatwierdzonego wyniku review, więc nie wolno "
                "przygotować wniosku jako gotowego do promocji wiedzy."
            ),
            next_step=(
                "Najpierw zapisz wynik rozmowy review skryptem "
                "record_service_profile_review_result.py; dopiero raport ready może "
                "zasilić osobny wniosek."
            ),
        ),
    ]
    blockers = [item.label for item in checklist if item.blocking]
    can_request_promotion = not blockers and approved_current_count > 0
    return ContentServiceProfileApprovalReadiness(
        status="ready_for_promotion_request" if can_request_promotion else "blocked",
        status_label=(
            "wniosek o zatwierdzenie można przygotować"
            if can_request_promotion
            else "wniosek o zatwierdzenie zablokowany"
        ),
        can_request_promotion=can_request_promotion,
        mutation_allowed=False,
        production_depth_unlocked=False,
        reviewed_output_required=True,
        approved_current_count=approved_current_count,
        review_required_count=review_required_count,
        first_action_id=review_action_summary.first_review_action_id,
        first_action_label=review_action_summary.first_review_action_label,
        blockers=blockers,
        checklist=checklist,
        safe_next_step=(
            "Przeprowadź review pierwszej karty Service Profile i zapisz wynik "
            "review; WILQ nadal nie zmieni kart ani source facts bez osobnej "
            "audytowanej ścieżki."
        ),
    )


def _source_fact_coverage_knowledge_status(status: str) -> ContentKnowledgeLifecycleStatus:
    if status == "production_depth":
        return "approved_current"
    return cast(ContentKnowledgeLifecycleStatus, status)


def _source_fact_coverage_audit(
    *,
    source_facts: list[ContentSourceFact],
    service_sections: list[ContentServiceProfileServiceSection],
    private_proposals: list[PrivateSourceProposal],
    coverage_summary: ContentServiceProfileCoverageSummary,
    production_depth_readiness: ContentKnowledgeProductionDepthReadiness,
    coverage_gaps: list[ContentServiceProfileCoverageGap],
    review_action_summary: ContentServiceProfileReviewActionSummary,
    review_actions: list[ContentServiceProfileReviewAction],
) -> ContentServiceProfileSourceFactCoverageAudit:
    fact_review_counts = Counter(fact.review_status for fact in source_facts)
    fact_scope_counts = Counter(fact.scope for fact in source_facts)
    fact_connector_counts = Counter(
        connector for fact in source_facts for connector in fact.source_connectors
    )
    approved_service_count = sum(
        1 for section in service_sections if section.status == "approved_current"
    )
    private_review_queue = _private_review_queue(private_proposals)
    private_review_value = _private_review_value_summary(
        facts=source_facts,
        private_review_queue=private_review_queue,
    )
    review_action_queue = _review_action_queue(
        review_actions=review_actions,
        service_sections=service_sections,
        private_proposals=private_proposals,
        first_review_action_id=review_action_summary.first_review_action_id,
    )
    blockers = [
        *production_depth_readiness.blocker_labels,
        *(gap.reason for gap in coverage_gaps),
    ]
    pass_state = bool(source_facts) and bool(review_actions) and not any(
        proposal.promotion_allowed for proposal in private_review_queue
    )
    return ContentServiceProfileSourceFactCoverageAudit(
        pass_state=pass_state,
        knowledge_status=_source_fact_coverage_knowledge_status(
            production_depth_readiness.status
        ),
        ready_for_daily_content=production_depth_readiness.ready_for_daily_content,
        production_depth_percent=_percent(
            production_depth_readiness.production_depth_card_count,
            max(coverage_summary.service_card_count, 1),
        ),
        approved_service_percent=_percent(
            approved_service_count,
            max(len(service_sections), 1),
        ),
        reviewed_fact_percent=_percent(
            fact_review_counts["approved"],
            max(len(source_facts), 1),
        ),
        fact_count=len(source_facts),
        fact_review_counts=dict(sorted(fact_review_counts.items())),
        fact_scope_counts=dict(sorted(fact_scope_counts.items())),
        fact_connector_counts=dict(sorted(fact_connector_counts.items())),
        service_card_count=coverage_summary.service_card_count,
        coverage_gap_count=len(coverage_gaps),
        review_action_count=review_action_summary.total_count,
        first_review_action_id=review_action_summary.first_review_action_id,
        first_review_action_label=review_action_summary.first_review_action_label,
        private_proposal_count=len(private_proposals),
        private_review_required_count=(
            sum(1 for proposal in private_proposals if proposal.review_status == "review_required")
        ),
        private_review_value=private_review_value,
        private_review_queue=private_review_queue,
        review_action_queue=review_action_queue,
        blockers=blockers,
        safe_next_step=coverage_summary.safe_next_step,
    )


def _private_review_queue(
    proposals: list[PrivateSourceProposal],
) -> list[ContentServiceProfilePrivateReviewQueueItem]:
    queue = [
        ContentServiceProfilePrivateReviewQueueItem(
            proposal_id=proposal.proposal_id,
            source_id=proposal.source_id,
            scope=proposal.scope,
            target_card_id=proposal.target_card_id,
            target_card_title=proposal.target_card_title,
            risk_tier=proposal.risk_tier,
            freshness_status=proposal.freshness_status,
            audience=proposal.audience,
            review_status=proposal.review_status,
            promotion_allowed=False,
            blocked_claim_count=len(proposal.blocked_claims),
            data_classes=proposal.data_classes,
            source_block_refs=proposal.source_block_refs,
            retention_decision=proposal.retention_decision,
            deletion_path=proposal.deletion_path,
            eval_case_ids=proposal.eval_case_ids,
            source_locator_label=proposal.source_locator_label,
            owner_role=proposal.owner_role,
            redacted=True,
            source_trace_ready=bool(
                proposal.source_block_refs and proposal.eval_case_ids
            ),
            safe_next_step=proposal.safe_next_step,
        )
        for proposal in proposals
    ]
    return sorted(
        queue,
        key=lambda item: (
            _risk_order(item.risk_tier),
            _source_scope_order(item.scope),
            item.target_card_title,
        ),
    )


def _private_review_value_summary(
    *,
    facts: list[ContentSourceFact],
    private_review_queue: list[ContentServiceProfilePrivateReviewQueueItem],
) -> ContentServiceProfilePrivateReviewValue:
    private_source_ids = {item.source_id for item in private_review_queue}
    private_facts = [fact for fact in facts if fact.source_id in private_source_ids]
    proposal_count = len(private_review_queue)
    blocked_claim_proposal_count = sum(
        1 for item in private_review_queue if item.blocked_claim_count > 0
    )
    cta_pattern_proposal_count = sum(1 for fact in private_facts if fact.cta_patterns)
    buyer_trigger_proposal_count = sum(
        1
        for fact in private_facts
        if fact.buyer_triggers or fact.buyer_problem_terms
    )
    promotion_allowed_count = sum(
        1 for item in private_review_queue if item.promotion_allowed
    )
    review_value_points: list[str] = []
    review_questions: list[str] = []
    if cta_pattern_proposal_count:
        review_value_points.append(
            "Prywatne propozycje dodają CTA albo kierunek rozmowy do oceny przez Wilka."
        )
        review_questions.append(
            "Czy proponowane CTA brzmi jak realny następny krok Ekologus, a nie obietnica wyniku?"
        )
    if buyer_trigger_proposal_count:
        review_value_points.append(
            "Prywatne propozycje doprecyzowują problemy i triggery kupującego."
        )
        review_questions.append(
            "Czy opisany problem kupującego faktycznie pasuje do rozmów z klientami Ekologus?"
        )
    if blocked_claim_proposal_count:
        review_value_points.append(
            "Każda propozycja niesie jawne zablokowane twierdzenia, więc może pomagać "
            "w Claim Ledgerze bez luzowania bezpieczeństwa."
        )
        review_questions.append(
            "Czy zablokowane twierdzenia są kompletne, szczególnie dla prawa, "
            "kar, zgodności i efektów?"
        )
    if promotion_allowed_count == 0 and proposal_count:
        review_value_points.append(
            "Żadna prywatna propozycja nie może wejść do production-depth bez review człowieka."
        )
        review_questions.append(
            "Które propozycje odrzucić, oznaczyć jako nieaktualne albo zostawić "
            "tylko jako tło do UAT?"
        )
    operator_value_score = 0
    if proposal_count:
        operator_value_score += 2
    if cta_pattern_proposal_count:
        operator_value_score += 2
    if buyer_trigger_proposal_count:
        operator_value_score += 2
    if blocked_claim_proposal_count == proposal_count and proposal_count:
        operator_value_score += 2
    if promotion_allowed_count == 0:
        operator_value_score += 1
    return ContentServiceProfilePrivateReviewValue(
        proposal_count=proposal_count,
        promotion_allowed_count=promotion_allowed_count,
        blocked_claim_proposal_count=blocked_claim_proposal_count,
        cta_pattern_proposal_count=cta_pattern_proposal_count,
        buyer_trigger_proposal_count=buyer_trigger_proposal_count,
        operator_value_score=min(operator_value_score, 9),
        value_summary=(
            "Prywatne propozycje ekologus-ai dają materiał do review i mogą poprawić "
            "konkretność Service Profile, ale nie odblokowują production-depth, "
            "publikacji ani gotowych twierdzeń bez decyzji człowieka."
        ),
        review_value_points=review_value_points,
        review_questions=review_questions,
    )


def _review_action_queue(
    *,
    review_actions: list[ContentServiceProfileReviewAction],
    service_sections: list[ContentServiceProfileServiceSection],
    private_proposals: list[PrivateSourceProposal],
    first_review_action_id: str | None,
) -> list[ContentServiceProfileReviewQueueItem]:
    title_by_card_id = _target_title_lookup(service_sections, private_proposals)
    queue = [
        ContentServiceProfileReviewQueueItem(
            action_id=action.action_id,
            review_scope=action.review_scope,
            priority=action.priority,
            target_card_id=action.target_card_id,
            target_card_title=(
                title_by_card_id.get(action.target_card_id or "")
                or action.target_card_id
                or "ogólny przegląd wiedzy"
            ),
            decision_options=action.decision_options,
        )
        for action in review_actions
    ]
    queue = sorted(
        queue,
        key=lambda item: (
            _priority_order(item.priority),
            _review_scope_order(item.review_scope),
            item.target_card_title,
            item.action_id,
        ),
    )
    if not first_review_action_id:
        return queue
    first_items = [item for item in queue if item.action_id == first_review_action_id]
    if not first_items:
        return queue
    return [
        first_items[0],
        *(item for item in queue if item.action_id != first_review_action_id),
    ]


def _target_title_lookup(
    service_sections: list[ContentServiceProfileServiceSection],
    private_proposals: list[PrivateSourceProposal],
) -> dict[str, str]:
    lookup = {section.card_id: section.title for section in service_sections}
    lookup.update(
        {
            proposal.target_card_id: proposal.target_card_title
            for proposal in private_proposals
        }
    )
    return lookup


def _private_source_proposal_sections(
    proposals: list[PrivateSourceProposal],
) -> list[ContentServiceProfilePrivateSourceProposalSection]:
    return [
        ContentServiceProfilePrivateSourceProposalSection(
            proposal_id=proposal.proposal_id,
            source_id=proposal.source_id,
            source_type=proposal.source_type,
            privacy_class=proposal.privacy_class,
            scope=proposal.scope,
            target_card_id=proposal.target_card_id,
            target_card_title=proposal.target_card_title,
            source_class_label=proposal.source_class_label,
            source_locator_label=proposal.source_locator_label,
            freshness_status=proposal.freshness_status,
            review_status=proposal.review_status,
            support_level=proposal.support_level,
            risk_tier=proposal.risk_tier,
            data_classes=proposal.data_classes,
            source_block_refs=proposal.source_block_refs,
            retention_decision=proposal.retention_decision,
            deletion_path=proposal.deletion_path,
            eval_case_ids=proposal.eval_case_ids,
            confidence_label=_confidence_label(proposal.confidence),
            owner_role=proposal.owner_role,
            audience=proposal.audience,
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
    scope_counts = Counter(proposal.scope for proposal in proposals)
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
        service_proposal_count=scope_counts["service"],
        claim_policy_proposal_count=scope_counts["claim_policy"],
        evidence_requirement_proposal_count=scope_counts["evidence_requirement"],
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
        evidence_ids=card.evidence_ids,
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
    cards: list[ContentKnowledgeCard],
    coverage_gaps: list[ContentServiceProfileCoverageGap],
    private_proposals: list[PrivateSourceProposal],
) -> list[ContentServiceProfileReviewAction]:
    decision_options = _review_decision_options()
    review_requirements = _review_requirements()
    private_review_requirements = _private_review_requirements()
    actions = [
        ContentServiceProfileReviewAction(
            action_id="service_profile_request_knowledge_review",
            mode="review_request",
            review_scope="general_knowledge_review",
            priority="medium",
            decision_options=decision_options,
            review_requirements=review_requirements,
            label="Poproś o review wiedzy usługowej",
            reason=(
                "Karty review-required nie mogą odblokować production-depth "
                "bez decyzji człowieka."
            ),
            blocked_write_claim="To nie zapisuje zmian w kartach wiedzy.",
            required_human_role="Wilku albo owner wiedzy Ekologus",
        )
    ]
    for card in cards:
        if (
            card.card_type == "service"
            and _lifecycle(card) == "source_backed_review_required"
            and "public_site" in card.source_connectors
        ):
            actions.append(
                ContentServiceProfileReviewAction(
                    action_id=f"service_profile_review_card_{card.id}",
                    mode="review_request",
                    review_scope="public_service_card",
                    priority="medium",
                    decision_options=decision_options,
                    review_requirements=review_requirements,
                    label=f"Sprawdź kartę usługi: {card.title}",
                    reason=(
                        "Karta ma publiczne źródło, ale wymaga decyzji człowieka "
                        "zanim stanie się approved-current."
                    ),
                    blocked_write_claim=(
                        "To nie promuje source fact ani knowledge card; "
                        "potrzebna jest osobna zatwierdzona akcja i audyt."
                    ),
                    required_human_role="Wilku albo owner wiedzy Ekologus",
                    target_card_id=card.id,
                )
            )
    for gap in coverage_gaps:
        actions.append(
            ContentServiceProfileReviewAction(
                action_id=f"service_profile_review_{gap.gap_id}",
                mode="prepare",
                review_scope="coverage_gap",
                priority="high" if gap.severity == "blocker" else "medium",
                decision_options=decision_options,
                review_requirements=review_requirements,
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
                review_scope=_private_review_action_scope(proposal),
                priority=_private_review_action_priority(proposal),
                decision_options=decision_options,
                review_requirements=private_review_requirements,
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


def _review_decision_options() -> list[ServiceProfileReviewDecisionOption]:
    return ["approve", "needs_changes", "stale", "reject"]


def _review_requirements() -> list[ContentServiceProfileReviewRequirement]:
    return [
        ContentServiceProfileReviewRequirement(
            field="action_id",
            label="action ID z live Service Profile",
            requirement_type="text",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="target_card_id",
            label="target card ID zgodny z action_id",
            requirement_type="text",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="decision",
            label="decyzja review",
            requirement_type="text",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="source_trace_clear",
            label="czy ślad źródłowy jest czytelny",
            requirement_type="boolean",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="blocked_claims_reviewed",
            label="czy claimy zablokowane zostały sprawdzone",
            requirement_type="boolean",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="notes",
            label="notatki review",
            requirement_type="text",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="follow_up_beads",
            label="follow-up Beads",
            requirement_type="follow_up",
            required=False,
            blocking_rule=(
                "Wymagane, gdy decision != approve albo source_trace_clear/"
                "blocked_claims_reviewed nie są true."
            ),
        ),
    ]


def _private_review_requirements() -> list[ContentServiceProfileReviewRequirement]:
    return [
        *_review_requirements(),
        ContentServiceProfileReviewRequirement(
            field="data_classes_confirmed",
            label="czy klasy danych prywatnego źródła są poprawne",
            requirement_type="boolean",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="source_block_refs_confirmed",
            label="czy source block refs są wystarczające do śladu źródłowego",
            requirement_type="boolean",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="freshness_status_confirmed",
            label="czy aktualność prywatnego źródła została potwierdzona",
            requirement_type="boolean",
            required=True,
            blocking_rule=(
                "Nie wolno promować prywatnej propozycji, gdy freshness_status "
                "nie został potwierdzony przez ownera/reviewera."
            ),
        ),
        ContentServiceProfileReviewRequirement(
            field="audience_scope_confirmed",
            label="czy zakres dostępu/audience prywatnego źródła jest poprawny",
            requirement_type="boolean",
            required=True,
            blocking_rule=(
                "Nie wolno promować prywatnej propozycji, gdy audience/scope "
                "nie został potwierdzony dla użycia marketingowego."
            ),
        ),
        ContentServiceProfileReviewRequirement(
            field="retention_decision_confirmed",
            label="czy decyzja retencji została podjęta albo świadomie zablokowana",
            requirement_type="boolean",
            required=True,
            blocking_rule=(
                "Nie wolno promować prywatnej propozycji, gdy retention_decision "
                "pozostaje pending_owner_decision bez świadomej decyzji ownera."
            ),
        ),
        ContentServiceProfileReviewRequirement(
            field="deletion_path_confirmed",
            label="czy ścieżka usunięcia/odrzucenia proposal jest jasna",
            requirement_type="boolean",
            required=True,
        ),
        ContentServiceProfileReviewRequirement(
            field="eval_gates_confirmed",
            label="czy eval gates blokujące unsafe claimy są wskazane",
            requirement_type="boolean",
            required=True,
        ),
    ]


def _private_review_action_scope(
    proposal: PrivateSourceProposal,
) -> ServiceProfileReviewActionScope:
    if proposal.scope == "service":
        return "private_service_proposal"
    if proposal.scope == "evidence_requirement":
        return "private_evidence_policy_proposal"
    return "private_claim_policy_proposal"


def _private_review_action_priority(
    proposal: PrivateSourceProposal,
) -> ServiceProfileReviewActionPriority:
    if proposal.scope in {"claim_policy", "evidence_requirement"}:
        return "high"
    return "medium"


def _review_action_summary(
    *,
    review_actions: list[ContentServiceProfileReviewAction],
) -> ContentServiceProfileReviewActionSummary:
    first_review_action = _first_review_action(review_actions)
    private_actions = [
        action
        for action in review_actions
        if action.review_scope
        in {
            "private_service_proposal",
            "private_claim_policy_proposal",
            "private_evidence_policy_proposal",
        }
    ]
    public_service_actions = [
        action
        for action in review_actions
        if action.review_scope == "public_service_card"
    ]
    private_service_actions = [
        action
        for action in private_actions
        if action.review_scope == "private_service_proposal"
    ]
    private_policy_actions = [
        action
        for action in private_actions
        if action.review_scope
        in {"private_claim_policy_proposal", "private_evidence_policy_proposal"}
    ]
    return ContentServiceProfileReviewActionSummary(
        total_count=len(review_actions),
        review_request_count=sum(
            1 for action in review_actions if action.mode == "review_request"
        ),
        prepare_count=sum(1 for action in review_actions if action.mode == "prepare"),
        public_service_review_count=len(public_service_actions),
        private_review_count=len(private_actions),
        private_service_review_count=len(private_service_actions),
        private_policy_review_count=len(private_policy_actions),
        first_review_action_id=first_review_action.action_id
        if first_review_action is not None
        else None,
        first_review_action_label=first_review_action.label
        if first_review_action is not None
        else None,
        first_review_action_reason=first_review_action.reason
        if first_review_action is not None
        else None,
        first_review_action_scope=first_review_action.review_scope
        if first_review_action is not None
        else None,
        first_review_action_priority=first_review_action.priority
        if first_review_action is not None
        else None,
        first_review_action_target_card_id=first_review_action.target_card_id
        if first_review_action is not None
        else None,
        first_review_action_gap_id=first_review_action.gap_id
        if first_review_action is not None
        else None,
        first_review_required_fields=_required_review_fields(first_review_action)
        if first_review_action is not None
        else [],
        first_review_safe_next_step=_first_review_safe_next_step(first_review_action)
        if first_review_action is not None
        else None,
        safe_next_step=(
            "Najpierw przejrzyj publiczne karty usług, potem prywatne propozycje "
            "service i claim-policy; żadna akcja review nie promuje faktów bez "
            "osobnego prepare-only preview i audytu."
        ),
    )


def _first_review_action(
    review_actions: list[ContentServiceProfileReviewAction],
) -> ContentServiceProfileReviewAction | None:
    priority_order: dict[ServiceProfileReviewActionPriority, int] = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }
    scope_order: dict[ServiceProfileReviewActionScope, int] = {
        "public_service_card": 0,
        "private_service_proposal": 1,
        "private_claim_policy_proposal": 2,
        "private_evidence_policy_proposal": 3,
        "coverage_gap": 4,
        "general_knowledge_review": 5,
    }
    candidates = [
        action for action in review_actions if action.mode == "review_request"
    ] or review_actions
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda action: (
            scope_order[action.review_scope],
            priority_order[action.priority],
            action.label,
            action.action_id,
        ),
    )[0]


def _required_review_fields(action: ContentServiceProfileReviewAction) -> list[str]:
    return [
        requirement.field
        for requirement in action.review_requirements
        if requirement.required
    ]


def _first_review_safe_next_step(
    action: ContentServiceProfileReviewAction,
) -> str:
    if action.review_scope == "public_service_card":
        return (
            "Weź tę publiczną kartę jako pierwszą: sprawdź źródło, zablokowane "
            "claimy i dopiero potem zdecyduj approve/needs_changes/stale/reject."
        )
    if action.review_scope == "private_service_proposal":
        return (
            "Pokaż redacted propozycję Wilkowi jako pytanie UAT; nie promuj jej "
            "do source fact bez potwierdzenia klas danych, aktualności i retencji."
        )
    if action.review_scope in {
        "private_claim_policy_proposal",
        "private_evidence_policy_proposal",
    }:
        return (
            "Sprawdź najpierw claim-policy/evidence-policy, bo od tego zależy, "
            "czego WILQ nie może powiedzieć w treściach."
        )
    if action.review_scope == "coverage_gap":
        return "Najpierw znajdź źródło dla luki, potem dopiero przygotuj kartę review."
    return "Zbierz decyzję review człowieka przed jakąkolwiek promocją wiedzy."


def _percent(value: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((value / total) * 100)


def _risk_order(value: ServiceProfilePrivateProposalRiskTier) -> int:
    return {"high": 0, "medium": 1, "low": 2, "unknown": 3}[value]


def _priority_order(value: ServiceProfileReviewActionPriority) -> int:
    return {"high": 0, "medium": 1, "low": 2}[value]


def _source_scope_order(value: PrivateSourceProposalScope) -> int:
    return {
        "claim_policy": 0,
        "evidence_requirement": 1,
        "service": 2,
        "buyer_problem": 3,
        "cta": 4,
        "metric_signal": 5,
    }[value]


def _review_scope_order(value: ServiceProfileReviewActionScope) -> int:
    return {
        "private_claim_policy_proposal": 0,
        "private_evidence_policy_proposal": 1,
        "public_service_card": 2,
        "private_service_proposal": 3,
        "coverage_gap": 4,
        "general_knowledge_review": 5,
    }[value]


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
