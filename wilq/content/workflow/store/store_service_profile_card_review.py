"""SQLite store seam for Service Profile card review receipts."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from wilq.content.knowledge.service_profile.review_receipts import (
    ContentServiceCardReviewCommand,
    ContentServiceCardReviewReceipt,
    ContentServiceCardReviewRecordResult,
    ContentServiceCardReviewStore,
)
from wilq.content.knowledge.source_facts import ContentSourceFact


class ContentServiceProfileCardReviewStoreMixin:
    path: Path

    def record_content_service_profile_card_review_receipt(
        self,
        command: ContentServiceCardReviewCommand,
        *,
        facts: tuple[ContentSourceFact, ...] | None = None,
        cards: tuple[object, ...] | None = None,
        now: datetime | None = None,
    ) -> ContentServiceCardReviewRecordResult:
        return ContentServiceCardReviewStore(self.path).record(
            command,
            facts=facts,
            cards=cards,
            now=now,
        )

    def load_content_service_profile_card_review_receipt(
        self,
        action_id: str,
    ) -> ContentServiceCardReviewReceipt | None:
        return ContentServiceCardReviewStore(self.path).load(action_id)

    def record_service_profile_card_review_receipt(
        self,
        command: ContentServiceCardReviewCommand,
        *,
        facts: tuple[ContentSourceFact, ...] | None = None,
        cards: tuple[object, ...] | None = None,
        now: datetime | None = None,
    ) -> ContentServiceCardReviewRecordResult:
        return self.record_content_service_profile_card_review_receipt(
            command,
            facts=facts,
            cards=cards,
            now=now,
        )

    def load_service_profile_card_review_receipt(
        self,
        action_id: str,
    ) -> ContentServiceCardReviewReceipt | None:
        return self.load_content_service_profile_card_review_receipt(action_id)


__all__ = ["ContentServiceProfileCardReviewStoreMixin"]
