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
from wilq.content.workflow.operator_steps import (
    ContentWorkflowOperatorBlocker,
    ContentWorkflowOperatorFacts,
    build_content_workflow_operator_journey,
)
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
    sales_brief_blocker = sales_brief.sales_brief_result.blockers[0:1]
    section_map_blocker = draft_package.draft_package_result.blockers[0:1]
    structured_contract_blocker = (
        structured_generation.structured_generation_result.blockers[0:1]
    )
    signal_quality = None if brief is None else brief.signal_quality
    journey = build_content_workflow_operator_journey(
        ContentWorkflowOperatorFacts(
            sales_brief_present=brief is not None,
            sales_brief_signal_status=(
                None if signal_quality is None else signal_quality.status
            ),
            sales_brief_signal_reason=(
                None if signal_quality is None else signal_quality.reason
            ),
            sales_brief_safe_next_step=(
                signal_quality.safe_next_step
                if signal_quality is not None
                else (
                    sales_brief_blocker[0].next_step
                    if sales_brief_blocker
                    else "Uzupełnij zakres, źródła i bezpieczny brief treści."
                )
            ),
            sales_brief_blocker=(
                None
                if not sales_brief_blocker
                else ContentWorkflowOperatorBlocker(
                    code=sales_brief_blocker[0].code,
                    label=sales_brief_blocker[0].label,
                    reason=sales_brief_blocker[0].reason,
                )
            ),
            section_map_present=draft is not None,
            section_map_blocker=(
                None
                if not section_map_blocker
                else ContentWorkflowOperatorBlocker(
                    code=section_map_blocker[0].code,
                    label=section_map_blocker[0].label,
                    reason=section_map_blocker[0].reason,
                )
            ),
            section_map_safe_next_step=(
                "Sprawdź kolejność sekcji, ich cele i przypisane dowody."
                if draft is not None
                else (
                    section_map_blocker[0].next_step
                    if section_map_blocker
                    else "Najpierw przygotuj bezpieczny plan sekcji."
                )
            ),
            structured_contract_present=(
                structured_generation.structured_generation_result.contract is not None
            ),
            structured_contract_blocker=(
                None
                if not structured_contract_blocker
                else ContentWorkflowOperatorBlocker(
                    code=structured_contract_blocker[0].code,
                    label=structured_contract_blocker[0].label,
                    reason=structured_contract_blocker[0].reason,
                )
            ),
            structured_contract_safe_next_step=(
                structured_contract_blocker[0].next_step
                if structured_contract_blocker
                else "Najpierw przygotuj kontrakt roboczego szkicu."
            ),
        )
    )
    return ContentWorkItemWorkflowSnapshotResponse(
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
        current_step_id=journey.current_step_id,
        operator_steps=journey.steps,
    )
