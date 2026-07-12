from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from wilq.content.briefs.sales import ContentSalesBriefSeed
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.enrichment.opportunity import ContentOpportunityEnrichment
from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.inventory.records import ContentInventoryRecord
from wilq.content.knowledge.cards import ContentKnowledgeCardMatch
from wilq.content.knowledge.work_item_service_profile import (
    ContentWorkItemServiceProfileContext,
)
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.contracts import (
    ContentWorkItemDraftPackageResponse,
    ContentWorkItemHumanReviewResponse,
    ContentWorkItemMeasurementWindowResponse,
    ContentWorkItemPreflightResponse,
    ContentWorkItemSalesBriefResponse,
    ContentWorkItemStructuredDraftGenerationResponse,
    ContentWorkItemWordPressDraftHandoffResponse,
    ContentWorkItemWorkflowSnapshotResponse,
)
from wilq.content.workflow.models import ContentWorkItem
from wilq.content.workflow.operator_steps import ContentWorkflowOperatorStep
from wilq.content.workflow.queue import ContentWorkItemQueueCandidate
from wilq.schemas import ContentFreshnessAssessment


@dataclass(frozen=True)
class SnapshotAssemblyCallbacks:
    """Typed seams for each stage of the content workflow snapshot."""

    preflight: Callable[..., ContentWorkItemPreflightResponse]
    sales_brief: Callable[..., ContentWorkItemSalesBriefResponse]
    draft_package: Callable[..., ContentWorkItemDraftPackageResponse]
    structured_generation: Callable[..., ContentWorkItemStructuredDraftGenerationResponse]
    human_review: Callable[..., ContentWorkItemHumanReviewResponse]
    wordpress_handoff: Callable[..., ContentWorkItemWordPressDraftHandoffResponse]
    measurement_window: Callable[..., ContentWorkItemMeasurementWindowResponse]
    operator_steps: Callable[
        [ContentWorkItemWorkflowSnapshotResponse], list[ContentWorkflowOperatorStep]
    ]


def assemble_content_work_item_snapshot(
    *,
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
    claim_ledger: ContentClaimLedger,
    seed: ContentSalesBriefSeed,
    enrichment: ContentOpportunityEnrichment,
    freshness_assessment: ContentFreshnessAssessment,
    candidate: ContentWorkItemQueueCandidate,
    knowledge_match: ContentKnowledgeCardMatch,
    service_profile_context: ContentWorkItemServiceProfileContext,
    measurement_window_id: str,
    callbacks: SnapshotAssemblyCallbacks,
    human_review_record: ContentHumanReview | None = None,
    audit: ContentWordPressDraftAuditEnvelope | None = None,
) -> ContentWorkItemWorkflowSnapshotResponse:
    """Assemble the API-owned snapshot while keeping stage policy in callbacks."""
    preflight = callbacks.preflight(item, inventory_records)
    sales_brief = callbacks.sales_brief(
        item,
        inventory_records,
        claim_ledger,
        seed,
        enrichment,
        knowledge_match,
        measurement_window_id,
    )
    brief = sales_brief.sales_brief_result.brief
    draft_package = callbacks.draft_package(
        item,
        inventory_records,
        claim_ledger,
        seed,
        enrichment,
        knowledge_match,
        measurement_window_id,
        None if brief is None else brief.id,
        brief,
    )
    draft = draft_package.draft_package_result.draft_package
    structured_generation = callbacks.structured_generation(
        item,
        claim_ledger,
        measurement_window_id,
        None if brief is None else brief.id,
        brief,
        draft,
    )
    human_review = callbacks.human_review(
        item,
        claim_ledger,
        measurement_window_id,
        None if brief is None else brief.id,
        draft,
        human_review_record,
    )
    wordpress_handoff = callbacks.wordpress_handoff(
        human_review.reviewed_item,
        draft,
        human_review.review,
        audit,
    )
    measurement_window = callbacks.measurement_window(
        item,
        claim_ledger,
        wordpress_handoff,
        measurement_window_id,
        None if brief is None else brief.id,
        draft,
        human_review,
    )
    snapshot = ContentWorkItemWorkflowSnapshotResponse(
        freshness_assessment=freshness_assessment,
        candidate=candidate,
        service_profile_context=service_profile_context,
        claim_ledger=claim_ledger,
        preflight=preflight,
        sales_brief=sales_brief,
        draft_package=draft_package,
        structured_generation=structured_generation,
        human_review=human_review,
        wordpress_handoff=wordpress_handoff,
        measurement_window=measurement_window,
    )
    snapshot.operator_steps = callbacks.operator_steps(snapshot)
    return snapshot
