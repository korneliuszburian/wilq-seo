from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from wilq.connectors.wordpress.authoring import WordPressAuthoringProfile
from wilq.content.briefs.sales import (
    ContentSalesBrief,
    ContentSalesBriefBuildResult,
    ContentSalesBriefSeed,
)
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.openai_runtime import (
    OpenAIStructuredDraftRuntimeMode,
    OpenAIStructuredDraftRuntimeResult,
)
from wilq.content.drafts.package import ContentDraftPackage, ContentDraftPackageBuildResult
from wilq.content.drafts.preview import StructuredDraftPreviewResult
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftGenerationResult,
    StructuredDraftOutput,
)
from wilq.content.drafts.variants import ContentDraftVariantsResult
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


class ContentWorkItemDraftVariantsRequest(BaseModel):
    item: ContentWorkItem
    sales_brief: ContentSalesBrief | None = None
    claim_ledger: ContentClaimLedger | None = None
    draft_package: ContentDraftPackage | None = None


class ContentWorkItemDraftVariantsResponse(BaseModel):
    item: ContentWorkItem
    draft_variants_result: ContentDraftVariantsResult


class ContentWorkItemStructuredDraftRuntimeRequest(BaseModel):
    contract: StructuredDraftGenerationContract | None = None
    model: str | None = None
    mode: OpenAIStructuredDraftRuntimeMode = "dry_run"


class ContentWorkItemStructuredDraftRuntimeResponse(BaseModel):
    runtime_result: OpenAIStructuredDraftRuntimeResult


class ContentWorkItemStructuredDraftPreviewRequest(BaseModel):
    contract: StructuredDraftGenerationContract | None = None
    output: StructuredDraftOutput | None = None


class ContentWorkItemStructuredDraftPreviewResponse(BaseModel):
    preview_result: StructuredDraftPreviewResult


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


class ContentWorkItemWorkflowSnapshotResponse(BaseModel):
    response_type: Literal["workflow_snapshot"] = "workflow_snapshot"
    claim_ledger: ContentClaimLedger
    preflight: ContentWorkItemPreflightResponse
    sales_brief: ContentWorkItemSalesBriefResponse
    draft_package: ContentWorkItemDraftPackageResponse
    structured_generation: ContentWorkItemStructuredDraftGenerationResponse
    human_review: ContentWorkItemHumanReviewResponse
    wordpress_handoff: ContentWorkItemWordPressDraftHandoffResponse
    measurement_window: ContentWorkItemMeasurementWindowResponse
    operator_steps: list[workflow_steps.ContentWorkflowOperatorStep] = Field(
        default_factory=list
    )


class ContentWorkItemBlockedSnapshotResponse(BaseModel):
    response_type: Literal["blocked_snapshot"] = "blocked_snapshot"
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


ContentWorkItemSnapshotResponse = (
    ContentWorkItemWorkflowSnapshotResponse | ContentWorkItemBlockedSnapshotResponse
)


class ContentWorkItemSnapshotHumanReviewRequest(BaseModel):
    review: ContentHumanReview


class ContentWorkItemSnapshotAuditRequest(BaseModel):
    audit: ContentWordPressDraftAuditEnvelope
