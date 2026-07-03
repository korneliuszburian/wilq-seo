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


class ContentWorkItemWordPressDraftExecutionResponse(BaseModel):
    execution_result: ContentWordPressDraftExecutionResult


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
