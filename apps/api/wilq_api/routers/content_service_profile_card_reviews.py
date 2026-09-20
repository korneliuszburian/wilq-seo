from __future__ import annotations

from fastapi import APIRouter, HTTPException

from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.knowledge.service_profile.review_receipts import (
    ContentServiceCardReviewCommand,
    ContentServiceCardReviewReceipt,
    ContentServiceCardReviewResponse,
)
from wilq.content.workflow.store.store import content_workflow_store


def register_content_service_profile_card_review_routes(router: APIRouter) -> None:
    @router.post(
        "/api/content/service-profile/card-reviews",
        response_model=ContentServiceCardReviewResponse,
        responses={409: {"description": "Exact card review changed or conflicts."}},
    )
    def record_service_profile_card_review(
        request: ContentServiceCardReviewCommand,
    ) -> ContentServiceCardReviewResponse:
        try:
            result = content_workflow_store().record_content_service_profile_card_review_receipt(
                request
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        ekologus_content_knowledge_cards.cache_clear()
        decision_status = (
            "approved"
            if result.receipt.decision == "approve"
            else "rejected"
            if result.receipt.decision == "reject"
            else result.receipt.decision
        )
        return ContentServiceCardReviewResponse(
            status="idempotent" if result.status == "idempotent" else decision_status,
            receipt=result.receipt,
            safe_next_step=(
                "Karta jest approved-current; odśwież exact candidates przed dalszym wyborem."
                if result.receipt.decision == "approve"
                else "Karta pozostaje zablokowana do kolejnego exact review."
            ),
        )

    @router.get(
        "/api/content/service-profile/card-reviews/{action_id}",
        response_model=ContentServiceCardReviewReceipt,
    )
    def read_service_profile_card_review(action_id: str) -> ContentServiceCardReviewReceipt:
        receipt = content_workflow_store().load_content_service_profile_card_review_receipt(
            action_id
        )
        if receipt is None:
            raise HTTPException(status_code=404, detail="service_profile_card_review_not_found")
        return receipt


__all__ = ["register_content_service_profile_card_review_routes"]
