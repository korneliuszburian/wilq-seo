from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from wilq.connectors.wordpress.authoring import WordPressAuthoringProfile
from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefBuildResult,
    ContentSalesBriefSeed,
)
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.package import ContentDraftPackage, ContentDraftPackageBuildResult
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationResult,
    StructuredDraftOutput,
)
from wilq.content.enrichment.opportunity import ContentOpportunityEnrichment
from wilq.content.handoff.wordpress import (
    ContentWordPressDraftAuditEnvelope,
    ContentWordPressDraftHandoff,
    ContentWordPressDraftHandoffResult,
)
from wilq.content.handoff.wordpress_authoring import (
    ContentWordPressAuthoringPayloadPreviewResult,
)
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionMode,
    ContentWordPressDraftExecutionResult,
    ContentWordPressDraftSectionOverride,
    ContentWordPressDraftWriteAuthorization,
)
from wilq.content.inventory.records import (
    ContentInventoryDuplicateRisk,
    ContentInventoryRecord,
    ContentInventoryResolution,
)
from wilq.content.knowledge.cards import ContentKnowledgeCardMatch
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
)
from wilq.content.measurement.outcome import (
    ContentMeasurementObservedMetric,
    ContentMeasurementOutcomeInterpretation,
)
from wilq.content.measurement.window import (
    ContentDateRange,
    ContentMeasurementMetric,
    ContentMeasurementWindow,
    ContentMeasurementWindowBlocker,
    ContentMeasurementWindowBuildResult,
)
from wilq.content.preflight.workflow import ContentPreflightVerdict
from wilq.content.quality.review import ContentQualityReview
from wilq.content.quality.revision import ContentRevisionPlan
from wilq.content.quality.revision_apply import ContentRevisionApplication
from wilq.content.review.human import ContentHumanReview, ContentHumanReviewBlocker
from wilq.content.workflow import operator_steps as workflow_steps
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.queue import ContentWorkItemQueueBlocker, ContentWorkItemQueueCandidate
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionDecision,
    ContentDraftRevisionReview,
    ContentDraftRevisionSection,
    ContentDraftRevisionStateStatus,
)
from wilq.schemas import ContentFreshnessAssessment

ContentDraftRevisionPublicConflictCode = Literal[
    "workspace_not_saveable",
    "revision_not_reviewable",
    "apply_in_progress",
    "stale_base",
    "revision_not_found",
    "stale_revision",
    "stale_review",
    "digest_mismatch",
]


class ContentWorkItemPreflightRequest(BaseModel):
    item: ContentWorkItem
    inventory_records: list[ContentInventoryRecord] = Field(default_factory=list)
    duplicate_risk: ContentInventoryDuplicateRisk = "unknown"


class ContentWorkItemPreflightResponse(BaseModel):
    item: ContentWorkItem
    inventory_resolution: ContentInventoryResolution
    preflight_verdict: ContentPreflightVerdict


class ContentWorkItemSalesBriefRequest(BaseModel):
    item: ContentWorkItem
    inventory_records: list[ContentInventoryRecord] = Field(default_factory=list)
    duplicate_risk: ContentInventoryDuplicateRisk = "unknown"
    claim_ledger: ContentClaimLedger
    seed: ContentSalesBriefSeed
    enrichment: ContentOpportunityEnrichment | None = None
    knowledge_match: ContentKnowledgeCardMatch | None = None


class ContentWorkItemSalesBriefResponse(BaseModel):
    item: ContentWorkItem
    inventory_resolution: ContentInventoryResolution
    preflight_verdict: ContentPreflightVerdict
    sales_brief_result: ContentSalesBriefBuildResult


class ContentWorkItemDraftPackageRequest(BaseModel):
    item: ContentWorkItem
    inventory_records: list[ContentInventoryRecord] = Field(default_factory=list)
    duplicate_risk: ContentInventoryDuplicateRisk = "unknown"
    claim_ledger: ContentClaimLedger
    seed: ContentSalesBriefSeed
    enrichment: ContentOpportunityEnrichment | None = None
    knowledge_match: ContentKnowledgeCardMatch | None = None
    sales_brief: ContentSalesBrief | None = None


class ContentWorkItemDraftPackageResponse(BaseModel):
    item: ContentWorkItem
    inventory_resolution: ContentInventoryResolution
    preflight_verdict: ContentPreflightVerdict
    sales_brief_result: ContentSalesBriefBuildResult
    draft_package_result: ContentDraftPackageBuildResult


class ContentWorkItemStructuredDraftGenerationRequest(BaseModel):
    item: ContentWorkItem
    sales_brief: ContentSalesBrief | None = None
    claim_ledger: ContentClaimLedger | None = None
    draft_package: ContentDraftPackage | None = None


class ContentWorkItemStructuredDraftGenerationResponse(BaseModel):
    item: ContentWorkItem
    structured_generation_result: StructuredDraftGenerationResult


class ContentWorkItemQualityReviewRequest(BaseModel):
    item: ContentWorkItem
    draft_package: ContentDraftPackage | None = None
    structured_output: StructuredDraftOutput | None = None
    claim_ledger: ContentClaimLedger | None = None
    sales_brief: ContentSalesBrief | None = None
    duplicate_risk: ContentInventoryDuplicateRisk = "clear"


class ContentWorkItemQualityReviewResponse(BaseModel):
    item: ContentWorkItem
    quality_review: ContentQualityReview


class ContentWorkItemRevisionPlanRequest(BaseModel):
    item: ContentWorkItem
    quality_review: ContentQualityReview | None = None


class ContentWorkItemRevisionPlanResponse(BaseModel):
    item: ContentWorkItem
    revision_plan: ContentRevisionPlan


class ContentWorkItemRevisionApplyRequest(BaseModel):
    item: ContentWorkItem
    revision_plan: ContentRevisionPlan | None = None
    draft_output: StructuredDraftOutput | None = None
    updated_quality_review: ContentQualityReview | None = None


class ContentWorkItemRevisionApplyResponse(BaseModel):
    item: ContentWorkItem
    revision_application: ContentRevisionApplication


class ContentWorkItemHumanReviewRequest(BaseModel):
    item: ContentWorkItem
    review: ContentHumanReview | None = None
    draft_package: ContentDraftPackage | None = None
    claim_ledger: ContentClaimLedger | None = None


class ContentWorkItemHumanReviewResponse(BaseModel):
    item: ContentWorkItem
    reviewed_item: ContentWorkItem
    review: ContentHumanReview | None = None
    blockers: list[ContentHumanReviewBlocker] = Field(default_factory=list)
    wordpress_handoff_allowed: bool = False


class ContentWorkItemWordPressDraftHandoffRequest(BaseModel):
    item: ContentWorkItem
    draft_package: ContentDraftPackage | None = None
    human_review: ContentHumanReview | None = None
    audit: ContentWordPressDraftAuditEnvelope | None = None


class ContentWorkItemWordPressDraftHandoffResponse(BaseModel):
    item: ContentWorkItem
    handoff_result: ContentWordPressDraftHandoffResult


class ContentWorkItemWordPressDraftExecutionRequest(BaseModel):
    handoff: ContentWordPressDraftHandoff | None = None
    draft_package: ContentDraftPackage | None = None
    mode: ContentWordPressDraftExecutionMode = "dry_run"
    write_authorization: ContentWordPressDraftWriteAuthorization | None = None
    section_overrides: list[ContentWordPressDraftSectionOverride] = Field(
        default_factory=list
    )


class ContentWorkItemWordPressDraftExecutionResponse(BaseModel):
    execution_result: ContentWordPressDraftExecutionResult


class ContentWordPressDraftWriteReadinessRequirement(BaseModel):
    event_type: str
    label: str
    satisfied: bool = False
    audit_event_id: str | None = None
    actor: str | None = None


class ContentWordPressDraftWriteReadinessBlocker(BaseModel):
    code: str
    label: str
    reason: str
    next_step: str


class ContentWordPressDraftWriteReadinessResponse(BaseModel):
    response_type: Literal["wordpress_draft_write_readiness"] = (
        "wordpress_draft_write_readiness"
    )
    contract: Literal["wordpress_draft_write_readiness_v1"] = (
        "wordpress_draft_write_readiness_v1"
    )
    connector: str = "wordpress_ekologus"
    action_id: str = "act_prepare_wordpress_draft_handoff"
    ready: bool = False
    live_write_enabled_by_env: bool = False
    rest_adapter_configured: bool = False
    publish_allowed: Literal[False] = False
    destructive_update_allowed: Literal[False] = False
    required_audit_events: list[ContentWordPressDraftWriteReadinessRequirement] = (
        Field(default_factory=list)
    )
    missing_audit_event_types: list[str] = Field(default_factory=list)
    write_authorization_status: Literal[
        "missing_audit_trace",
        "audit_actor_mismatch",
        "available",
        "blocked_outside_action_apply",
    ] = "missing_audit_trace"
    suggested_write_authorization: ContentWordPressDraftWriteAuthorization | None = None
    blockers: list[ContentWordPressDraftWriteReadinessBlocker] = Field(default_factory=list)
    operator_next_step: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


class ContentWordPressExistingDraftSectionDiff(BaseModel):
    heading: str
    current_summary: str = ""
    proposed_summary: str = ""
    status: Literal["unchanged", "changed", "proposed", "missing_current"]


class ContentWordPressExistingDraftUpdateReadinessResponse(BaseModel):
    response_type: Literal["wordpress_existing_draft_update_readiness"] = (
        "wordpress_existing_draft_update_readiness"
    )
    contract: Literal["wordpress_existing_draft_update_readiness_v1"] = (
        "wordpress_existing_draft_update_readiness_v1"
    )
    connector: str = "wordpress_ekologus"
    action_id: str = "act_prepare_wordpress_existing_draft_update"
    work_item_id: str
    target_post_id: str | None = None
    target_url: str | None = None
    current_state_available: bool = False
    current_section_count: int = 0
    proposed_section_count: int = 0
    section_diff_preview: list[ContentWordPressExistingDraftSectionDiff] = Field(
        default_factory=list
    )
    ready: bool = False
    update_supported: bool = False
    publish_allowed: Literal[False] = False
    destructive_update_allowed: Literal[False] = False
    blockers: list[ContentWordPressDraftWriteReadinessBlocker] = Field(default_factory=list)
    operator_next_step: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


class ContentWordPressDraftReadbackBlocker(BaseModel):
    code: Literal[
        "missing_wordpress_post_id",
        "wordpress_draft_read_failed",
    ]
    label: str
    reason: str
    next_step: str


class ContentWordPressDraftReadback(BaseModel):
    status: Literal["available", "blocked"]
    connector: str = "wordpress_ekologus"
    wordpress_post_id: str | None = None
    post_status: str = ""
    title: str = ""
    link: str = ""
    modified_gmt: str = ""
    content_summary: str = ""
    content_word_count: int | None = None
    acf_field_count: int | None = None
    acf_field_names: list[str] = Field(default_factory=list)
    blockers: list[ContentWordPressDraftReadbackBlocker] = Field(default_factory=list)


class ContentWordPressDraftActivationPacketResponse(BaseModel):
    response_type: Literal["wordpress_draft_activation_packet"] = (
        "wordpress_draft_activation_packet"
    )
    contract: Literal["wordpress_draft_activation_packet_v1"] = (
        "wordpress_draft_activation_packet_v1"
    )
    action_id: str = "act_apply_wordpress_draft_handoff"
    work_item_id: str
    topic: str
    final_canonical_url: str | None = None
    draft_package_ready: bool = False
    draft_package_id: str | None = None
    review_preview_ready: bool = False
    review_preview_status_label: str
    human_review_checklist: list[str] = Field(default_factory=list)
    human_review_ready: bool = False
    audit_ready: bool = False
    handoff_ready: bool = False
    handoff_id: str | None = None
    dry_run_ready: bool = False
    live_write_enabled_by_env: bool = False
    publish_allowed: Literal[False] = False
    destructive_update_allowed: Literal[False] = False
    external_write_attempted: Literal[False] = False
    handoff_blockers: list[str] = Field(default_factory=list)
    execution_blockers: list[str] = Field(default_factory=list)
    activation_missing_step: Literal[
        "draft_package",
        "human_review",
        "audit",
        "handoff",
        "dry_run",
        "ready",
    ] = "draft_package"
    activation_missing_step_label: str
    activation_missing_readiness_labels: list[str] = Field(default_factory=list)
    execution_result: ContentWordPressDraftExecutionResult
    draft_readback: ContentWordPressDraftReadback | None = None
    operator_next_step: str
    next_steps: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


class ContentWorkItemWordPressAuthoringPayloadPreviewRequest(BaseModel):
    handoff: ContentWordPressDraftHandoff | None = None
    draft_package: ContentDraftPackage | None = None
    authoring_profile: WordPressAuthoringProfile | None = None


class ContentWorkItemWordPressAuthoringPayloadPreviewResponse(BaseModel):
    authoring_profile: WordPressAuthoringProfile
    preview_result: ContentWordPressAuthoringPayloadPreviewResult


class ContentWorkItemMeasurementWindowRequest(BaseModel):
    item: ContentWorkItem
    handoff: ContentWordPressDraftHandoff | None = None
    baseline_period: ContentDateRange
    observation_period: ContentDateRange
    allowed_metrics: list[ContentMeasurementMetric] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)


class ContentWorkItemMeasurementWindowResponse(BaseModel):
    item: ContentWorkItem
    updated_item: ContentWorkItem
    measurement_window_result: ContentMeasurementWindowBuildResult
    outcome_blockers: list[ContentMeasurementWindowBlocker] = Field(default_factory=list)


class ContentWorkItemMeasurementOutcomeRequest(BaseModel):
    window: ContentMeasurementWindow
    observed_metrics: list[ContentMeasurementObservedMetric] = Field(default_factory=list)
    as_of: date


class ContentWorkItemMeasurementOutcomeResponse(BaseModel):
    outcome: ContentMeasurementOutcomeInterpretation


class ContentDraftRevisionWorkspace(BaseModel):
    status: ContentDraftRevisionStateStatus
    latest_revision: ContentDraftRevision | None = None
    latest_review: ContentDraftRevisionReview | None = None
    revision_count: int = Field(ge=0)
    context_current: bool
    editor_title: str
    editor_sections: list[ContentDraftRevisionSection] = Field(default_factory=list)
    can_save: bool
    can_review: bool
    safe_next_step: str

    @model_validator(mode="after")
    def require_consistent_revision_state(self) -> ContentDraftRevisionWorkspace:
        if self.can_save and self.can_review:
            raise ValueError("Revision workspace cannot save and review at the same time.")
        if self.can_review and (
            self.status not in {"unreviewed", "deferred"} or not self.context_current
        ):
            raise ValueError("Only an unreviewed or deferred revision can be reviewed.")
        if self.status == "empty":
            if self.latest_revision is not None or self.latest_review is not None:
                raise ValueError("Empty revision workspace cannot expose a revision or review.")
            if self.revision_count != 0:
                raise ValueError("Empty revision workspace must have revision_count=0.")
            if not self.context_current:
                raise ValueError("Empty revision workspace has no stale persisted context.")
            return self
        if self.latest_revision is None or self.revision_count < 1:
            raise ValueError("Non-empty revision workspace requires a latest revision.")
        if self.context_current:
            if self.editor_title != self.latest_revision.title:
                raise ValueError("Revision workspace editor title must resume the latest revision.")
            if self.editor_sections != self.latest_revision.sections:
                raise ValueError(
                    "Revision workspace editor sections must resume the latest revision."
                )
        if self.status == "unreviewed":
            if self.latest_review is not None:
                raise ValueError("Unreviewed revision workspace cannot expose a review.")
            return self
        if self.latest_review is None:
            raise ValueError("Reviewed revision workspace requires the latest review.")
        if self.latest_review.revision_id != self.latest_revision.revision_id:
            raise ValueError("Revision review must target the latest revision.")
        if self.latest_review.revision_digest != self.latest_revision.content_digest:
            raise ValueError("Revision review digest must match the latest revision.")
        if self.latest_review.decision != self.status:
            raise ValueError("Revision workspace status must match its latest review decision.")
        return self


class ContentDraftRevisionSaveRequest(BaseModel):
    base_revision_id: str | None = None
    title: str = Field(min_length=1)
    sections: list[ContentDraftRevisionSection] = Field(min_length=1)
    created_by: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_visible_draft_fields(self) -> ContentDraftRevisionSaveRequest:
        if not self.title.strip():
            raise ValueError("Draft revision requires a visible title.")
        if not self.created_by.strip():
            raise ValueError("Draft revision requires a visible creator identifier.")
        return self


class ContentDraftRevisionReviewRequest(BaseModel):
    expected_revision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewed_by: str = Field(min_length=1)
    decision: ContentDraftRevisionDecision
    notes: str = ""
    checked_items: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_review_evidence(self) -> ContentDraftRevisionReviewRequest:
        if not self.reviewed_by.strip():
            raise ValueError("Revision review requires a visible reviewer identifier.")
        if any(not item.strip() for item in self.checked_items):
            raise ValueError("Revision review checked_items cannot contain blank values.")
        if any(not evidence_id.strip() for evidence_id in self.evidence_ids):
            raise ValueError("Revision review evidence_ids cannot contain blank values.")
        if self.decision == "approved":
            if not any(item.strip() for item in self.checked_items):
                raise ValueError("Approved revision review requires checked_items.")
            if not any(evidence_id.strip() for evidence_id in self.evidence_ids):
                raise ValueError("Approved revision review requires evidence_ids.")
        elif not self.notes.strip():
            raise ValueError(f"{self.decision} revision review requires notes.")
        return self


class ContentDraftRevisionSaveResponse(BaseModel):
    status: Literal["created", "idempotent"]
    revision: ContentDraftRevision
    workspace: ContentDraftRevisionWorkspace


class ContentDraftRevisionReviewResponse(BaseModel):
    status: Literal["recorded", "idempotent"]
    review: ContentDraftRevisionReview
    workspace: ContentDraftRevisionWorkspace


class ContentDraftRevisionConflictResponse(BaseModel):
    status: Literal["conflict"] = "conflict"
    code: ContentDraftRevisionPublicConflictCode
    current_revision_id: str | None = None
    current_digest: str | None = Field(default=None, min_length=64, max_length=64)
    safe_next_step: str


class ContentStructuredGenerationReadinessBlocker(BaseModel):
    code: str
    label: str
    reason: str
    next_step: str


class ContentStructuredGenerationReadiness(BaseModel):
    status: Literal["ready", "blocked"]
    editable_section_headings: list[str] = Field(default_factory=list)
    blockers: list[ContentStructuredGenerationReadinessBlocker] = Field(
        default_factory=list
    )
    safe_next_step: str
    publish_ready: Literal[False] = False

    @model_validator(mode="after")
    def require_fail_closed_state(self) -> ContentStructuredGenerationReadiness:
        headings = [heading.strip() for heading in self.editable_section_headings]
        if any(not heading for heading in headings):
            raise ValueError("Editable section headings cannot contain blank values.")
        if len(set(headings)) != len(headings):
            raise ValueError("Editable section headings must be unique.")
        if self.status == "ready":
            if not headings or self.blockers:
                raise ValueError(
                    "Ready structured generation requires headings and no blockers."
                )
        elif headings or not self.blockers:
            raise ValueError(
                "Blocked structured generation requires blockers and no headings."
            )
        return self


class ContentWorkItemWorkflowSnapshotResponse(BaseModel):
    response_type: Literal["workflow_snapshot"] = "workflow_snapshot"
    freshness_assessment: ContentFreshnessAssessment
    candidate: ContentWorkItemQueueCandidate
    service_profile_context: ContentWorkItemServiceProfileContext = Field(
        default_factory=ContentWorkItemServiceProfileContext.not_evaluated
    )
    claim_ledger: ContentClaimLedger
    preflight: ContentWorkItemPreflightResponse
    sales_brief: ContentWorkItemSalesBriefResponse
    draft_package: ContentWorkItemDraftPackageResponse
    structured_generation: ContentWorkItemStructuredDraftGenerationResponse
    human_review: ContentWorkItemHumanReviewResponse
    wordpress_handoff: ContentWorkItemWordPressDraftHandoffResponse
    measurement_window: ContentWorkItemMeasurementWindowResponse
    revision_workspace: ContentDraftRevisionWorkspace
    current_step_id: workflow_steps.ContentWorkflowOperatorStepId
    operator_steps: workflow_steps.ContentWorkflowOperatorSteps

    @model_validator(mode="after")
    def require_canonical_operator_steps(
        self,
    ) -> ContentWorkItemWorkflowSnapshotResponse:
        workflow_steps.validate_content_workflow_operator_steps(
            current_step_id=self.current_step_id,
            steps=self.operator_steps,
        )
        return self


class ContentWorkItemBrowserWorkflowSnapshotResponse(BaseModel):
    response_type: Literal["workflow_snapshot"] = "workflow_snapshot"
    freshness_assessment: ContentFreshnessAssessment
    candidate: ContentWorkItemQueueCandidate
    service_profile_context: ContentWorkItemServiceProfileContext = Field(
        default_factory=ContentWorkItemServiceProfileContext.not_evaluated
    )
    claim_ledger: ContentClaimLedger
    preflight: ContentWorkItemPreflightResponse
    sales_brief: ContentWorkItemSalesBriefResponse
    draft_package: ContentWorkItemDraftPackageResponse
    structured_generation_readiness: ContentStructuredGenerationReadiness
    human_review: ContentWorkItemHumanReviewResponse
    wordpress_handoff: ContentWorkItemWordPressDraftHandoffResponse
    measurement_window: ContentWorkItemMeasurementWindowResponse
    revision_workspace: ContentDraftRevisionWorkspace
    current_step_id: workflow_steps.ContentWorkflowOperatorStepId
    operator_steps: workflow_steps.ContentWorkflowOperatorSteps

    @model_validator(mode="after")
    def require_canonical_operator_steps(
        self,
    ) -> ContentWorkItemBrowserWorkflowSnapshotResponse:
        workflow_steps.validate_content_workflow_operator_steps(
            current_step_id=self.current_step_id,
            steps=self.operator_steps,
        )
        return self


class ContentWorkItemBlockedSnapshotResponse(BaseModel):
    response_type: Literal["blocked_snapshot"] = "blocked_snapshot"
    freshness_assessment: ContentFreshnessAssessment
    work_item_id: str
    decision_id: str
    title: str
    topic: str
    status_label: str
    reason: str
    safe_next_step: str
    recommended_mode: str
    preflight_status: str
    blockers: list[ContentWorkItemQueueBlocker] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_connectors: list[str] = Field(default_factory=list)
    candidate: ContentWorkItemQueueCandidate
    service_profile_context: ContentWorkItemServiceProfileContext = Field(
        default_factory=ContentWorkItemServiceProfileContext.not_evaluated
    )


ContentWorkItemSnapshotResponse = (
    ContentWorkItemWorkflowSnapshotResponse | ContentWorkItemBlockedSnapshotResponse
)
ContentWorkItemBrowserSnapshotResponse = (
    ContentWorkItemBrowserWorkflowSnapshotResponse | ContentWorkItemBlockedSnapshotResponse
)


class ContentWorkItemSnapshotHumanReviewRequest(BaseModel):
    review: ContentHumanReview


class ContentWorkItemSnapshotAuditRequest(BaseModel):
    audit: ContentWordPressDraftAuditEnvelope
