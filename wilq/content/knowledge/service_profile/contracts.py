"""Decomposed service_profile contracts implementation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wilq.content.knowledge.cards import (
    ContentKnowledgeClaimRule,
    ContentKnowledgeProductionDepthReadiness,
)
from wilq.content.knowledge.private_source_proposals import (
    PrivateSourceProposalAudience,
    PrivateSourceProposalFreshnessStatus,
    PrivateSourceProposalPrivacyClass,
    PrivateSourceProposalRetentionDecision,
    PrivateSourceProposalReviewStatus,
    PrivateSourceProposalScope,
    PrivateSourceProposalType,
)
from wilq.content.knowledge.source_facts import ContentKnowledgeLifecycleStatus

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
    review_requirements: list[ContentServiceProfileReviewRequirement] = Field(default_factory=list)
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
    decision_options: list[ServiceProfileReviewDecisionOption] = Field(default_factory=list)


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
    review_action_queue: list[ContentServiceProfileReviewQueueItem] = Field(default_factory=list)
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
    checklist: list[ContentServiceProfileApprovalReadinessItem] = Field(default_factory=list)
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
