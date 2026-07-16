from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from wilq.content.briefs.sales import ContentSalesBrief, ContentSalesBriefSeed
from wilq.content.claims.ledger import ContentClaimLedger
from wilq.content.drafts.package import ContentDraftPackage
from wilq.content.enrichment.opportunity import ContentOpportunityEnrichment
from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.inventory.records import ContentInventoryRecord
from wilq.content.knowledge.cards import ContentKnowledgeCardMatch
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.contracts import (
    ContentWorkItemDraftPackageRequest,
    ContentWorkItemDraftPackageResponse,
    ContentWorkItemHumanReviewRequest,
    ContentWorkItemHumanReviewResponse,
    ContentWorkItemMeasurementWindowRequest,
    ContentWorkItemMeasurementWindowResponse,
    ContentWorkItemPreflightRequest,
    ContentWorkItemPreflightResponse,
    ContentWorkItemSalesBriefRequest,
    ContentWorkItemSalesBriefResponse,
    ContentWorkItemStructuredDraftGenerationRequest,
    ContentWorkItemStructuredDraftGenerationResponse,
    ContentWorkItemWordPressDraftHandoffRequest,
    ContentWorkItemWordPressDraftHandoffResponse,
)
from wilq.content.workflow.models import ContentWorkItem


@dataclass(frozen=True)
class SnapshotStageCallbacks:
    preflight: Callable[[ContentWorkItemPreflightRequest], ContentWorkItemPreflightResponse]
    sales_brief: Callable[[ContentWorkItemSalesBriefRequest], ContentWorkItemSalesBriefResponse]
    draft_package: Callable[
        [ContentWorkItemDraftPackageRequest], ContentWorkItemDraftPackageResponse
    ]
    structured_generation: Callable[
        [ContentWorkItemStructuredDraftGenerationRequest],
        ContentWorkItemStructuredDraftGenerationResponse,
    ]
    human_review: Callable[
        [ContentWorkItemHumanReviewRequest], ContentWorkItemHumanReviewResponse
    ]
    wordpress_handoff: Callable[
        [ContentWorkItemWordPressDraftHandoffRequest],
        ContentWorkItemWordPressDraftHandoffResponse,
    ]
    measurement_window: Callable[
        [ContentWorkItemMeasurementWindowRequest], ContentWorkItemMeasurementWindowResponse
    ]


def snapshot_preflight(
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
    *,
    callbacks: SnapshotStageCallbacks,
) -> ContentWorkItemPreflightResponse:
    return callbacks.preflight(
        ContentWorkItemPreflightRequest(
            item=item,
            inventory_records=inventory_records,
            duplicate_risk="clear",
        )
    )


def snapshot_sales_brief(
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
    claim_ledger: ContentClaimLedger,
    seed: ContentSalesBriefSeed,
    enrichment: ContentOpportunityEnrichment,
    knowledge_match: ContentKnowledgeCardMatch,
    measurement_window_id: str,
    *,
    callbacks: SnapshotStageCallbacks,
) -> ContentWorkItemSalesBriefResponse:
    return callbacks.sales_brief(
        ContentWorkItemSalesBriefRequest(
            item=item.model_copy(
                update={
                    "preserve_first_plan_status": "approved",
                    "measurement_window_status": "planned",
                    "measurement_window_id": measurement_window_id,
                }
            ),
            inventory_records=inventory_records,
            duplicate_risk="clear",
            claim_ledger=claim_ledger,
            seed=seed,
            enrichment=enrichment,
            knowledge_match=knowledge_match,
        )
    )


def snapshot_draft_package(
    item: ContentWorkItem,
    inventory_records: list[ContentInventoryRecord],
    claim_ledger: ContentClaimLedger,
    seed: ContentSalesBriefSeed,
    enrichment: ContentOpportunityEnrichment,
    knowledge_match: ContentKnowledgeCardMatch,
    measurement_window_id: str,
    brief_id: str | None,
    brief: ContentSalesBrief | None,
    *,
    callbacks: SnapshotStageCallbacks,
) -> ContentWorkItemDraftPackageResponse:
    return callbacks.draft_package(
        ContentWorkItemDraftPackageRequest(
            item=snapshot_item_ready_for_draft(
                item, claim_ledger, measurement_window_id, brief_id
            ),
            inventory_records=inventory_records,
            duplicate_risk="clear",
            claim_ledger=claim_ledger,
            seed=seed,
            enrichment=enrichment,
            knowledge_match=knowledge_match,
            sales_brief=brief,
        )
    )


def snapshot_structured_generation(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    measurement_window_id: str,
    brief_id: str | None,
    brief: ContentSalesBrief | None,
    draft: ContentDraftPackage | None,
    *,
    callbacks: SnapshotStageCallbacks,
) -> ContentWorkItemStructuredDraftGenerationResponse:
    return callbacks.structured_generation(
        ContentWorkItemStructuredDraftGenerationRequest(
            item=snapshot_item_ready_for_draft(
                item, claim_ledger, measurement_window_id, brief_id, draft
            ),
            sales_brief=brief,
            claim_ledger=claim_ledger,
            draft_package=draft,
        )
    )


def snapshot_human_review(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    measurement_window_id: str,
    brief_id: str | None,
    draft: ContentDraftPackage | None,
    human_review_record: ContentHumanReview | None,
    *,
    callbacks: SnapshotStageCallbacks,
) -> ContentWorkItemHumanReviewResponse:
    return callbacks.human_review(
        ContentWorkItemHumanReviewRequest(
            item=snapshot_item_ready_for_handoff(
                item, claim_ledger, measurement_window_id, brief_id, draft
            ),
            review=human_review_record,
            draft_package=draft,
            claim_ledger=claim_ledger,
        )
    )


def snapshot_wordpress_handoff(
    item: ContentWorkItem,
    draft: ContentDraftPackage | None,
    human_review: ContentHumanReview | None,
    audit: ContentWordPressDraftAuditEnvelope | None,
    *,
    callbacks: SnapshotStageCallbacks,
) -> ContentWorkItemWordPressDraftHandoffResponse:
    return callbacks.wordpress_handoff(
        ContentWorkItemWordPressDraftHandoffRequest(
            item=item,
            draft_package=draft,
            human_review=human_review,
            audit=audit,
        )
    )


def snapshot_measurement_window(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    wordpress_handoff: ContentWorkItemWordPressDraftHandoffResponse,
    measurement_window_id: str,
    brief_id: str | None,
    draft: ContentDraftPackage | None,
    human_review: ContentWorkItemHumanReviewResponse,
    *,
    callbacks: SnapshotStageCallbacks,
) -> ContentWorkItemMeasurementWindowResponse:
    return callbacks.measurement_window(
        ContentWorkItemMeasurementWindowRequest(
            item=snapshot_item_ready_for_measurement(
                item,
                claim_ledger,
                measurement_window_id,
                brief_id,
                draft,
                human_review,
            ),
            handoff=wordpress_handoff.handoff_result.handoff,
        )
    )


def snapshot_item_ready_for_draft(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    measurement_window_id: str,
    brief_id: str | None,
    draft: ContentDraftPackage | None = None,
) -> ContentWorkItem:
    update: dict[str, object] = {
        "preflight_status": "draft_allowed",
        "preserve_first_plan_status": "approved",
        "sales_brief_status": "approved",
        "sales_brief_id": brief_id,
        "claim_ledger_status": "approved",
        "claim_ledger_id": claim_ledger.id,
        "measurement_window_status": "planned",
        "measurement_window_id": measurement_window_id,
    }
    if draft is not None:
        update.update({"draft_package_status": "ready", "draft_package_id": draft.id})
    return item.model_copy(update=update)


def snapshot_item_ready_for_handoff(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    measurement_window_id: str,
    brief_id: str | None,
    draft: ContentDraftPackage | None,
) -> ContentWorkItem:
    return snapshot_item_ready_for_draft(
        item, claim_ledger, measurement_window_id, brief_id, draft
    ).model_copy(update={"preflight_status": "handoff_allowed"})


def snapshot_item_ready_for_measurement(
    item: ContentWorkItem,
    claim_ledger: ContentClaimLedger,
    measurement_window_id: str,
    brief_id: str | None,
    draft: ContentDraftPackage | None,
    human_review: ContentWorkItemHumanReviewResponse,
) -> ContentWorkItem:
    return snapshot_item_ready_for_handoff(
        item, claim_ledger, measurement_window_id, brief_id, draft
    ).model_copy(
        update={
            "human_review_status": human_review.reviewed_item.human_review_status,
            "human_review_id": human_review.reviewed_item.human_review_id,
            "audit_status": "missing",
            "audit_id": None,
            "measurement_window_status": "missing",
            "measurement_window_id": None,
        }
    )
