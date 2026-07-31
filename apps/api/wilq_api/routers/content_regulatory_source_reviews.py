from __future__ import annotations

from fastapi import APIRouter

from wilq.content.regulatory.source_reviews import (
    ContentRegulatorySourceReview,
    ContentRegulatorySourceReviewCommand,
    ContentRegulatorySourceReviewList,
    regulatory_source_review_store,
)


def register_content_regulatory_source_review_routes(router: APIRouter) -> None:
    """Expose the human-only promotion seam for official source candidates.

    This persists a local, append-only review decision. It neither fetches nor
    changes a regulator system and it never creates a content plan by itself.
    """

    @router.get(
        "/api/content/regulatory-source-reviews",
        response_model=ContentRegulatorySourceReviewList,
    )
    def content_regulatory_source_reviews() -> ContentRegulatorySourceReviewList:
        return ContentRegulatorySourceReviewList(
            reviews=regulatory_source_review_store().list_reviews()
        )

    @router.post(
        "/api/content/regulatory-source-reviews",
        response_model=ContentRegulatorySourceReview,
    )
    def content_regulatory_source_review(
        command: ContentRegulatorySourceReviewCommand,
    ) -> ContentRegulatorySourceReview:
        return regulatory_source_review_store().record(command)
