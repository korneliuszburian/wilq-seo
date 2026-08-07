from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.evidence.registry import SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID
from wilq.storage.local_state import state_db_path
from wilq.storage.private_paths import prepare_private_store_path


class ContentPublicSourceReviewCommand(BaseModel):
    """One owner decision about one exact public Service Profile source fact."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    expected_source_fact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_card_id: str = Field(min_length=1)
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1, max_length=200)
    notes: str = Field(min_length=1, max_length=2000)
    source_trace_clear: bool
    blocked_claims_reviewed: bool

    @model_validator(mode="after")
    def require_complete_approval(self) -> ContentPublicSourceReviewCommand:
        if self.decision == "approve" and not all(
            (self.source_trace_clear, self.blocked_claims_reviewed)
        ):
            raise ValueError(
                "Approved public source review requires source trace and claim confirmations."
            )
        return self


class ContentPublicSourceReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_fact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_card_id: str = Field(min_length=1)
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1)
    notes: str = Field(min_length=1)
    source_trace_clear: bool
    blocked_claims_reviewed: bool
    reviewed_at: datetime

    def approved_source_fact(self, candidate: ContentSourceFact) -> ContentSourceFact | None:
        if self.decision != "approve":
            return None
        return candidate.model_copy(
            update={
                "source_id": f"public_source_review_fact_{self.review_id}",
                "review_status": "approved",
                "reviewer": self.reviewer,
                "evidence_ids": [SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
                "usage_notes": [
                    *candidate.usage_notes,
                    (
                        "Publiczne źródło zatwierdzone przez człowieka; "
                        f"source={candidate.source_id}; review={self.review_id}."
                    ),
                ],
            }
        )


class ContentPublicSourceReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["approved", "rejected", "idempotent"]
    review: ContentPublicSourceReview
    approved_source_fact_id: str | None = None
    safe_next_step: str


def public_source_fact_digest(fact: ContentSourceFact) -> str:
    encoded = json.dumps(
        fact.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(encoded.encode("utf-8")).hexdigest()


class PublicSourceReviewStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def record(
        self,
        command: ContentPublicSourceReviewCommand,
        *,
        candidates: tuple[ContentSourceFact, ...],
        now: datetime | None = None,
    ) -> ContentPublicSourceReviewResponse:
        candidate = _reviewable_candidate(candidates, command.source_id)
        digest = public_source_fact_digest(candidate)
        if digest != command.expected_source_fact_digest:
            raise ValueError("public_source_fact_changed")
        if candidate.target_card_id != command.target_card_id:
            raise ValueError("public_source_target_changed")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = _exact_review(connection, command, digest)
            if existing is not None:
                return _response(existing, status="idempotent")
            review = ContentPublicSourceReview(
                review_id=f"public_source_review_{uuid4().hex}",
                source_id=candidate.source_id,
                source_fact_digest=digest,
                target_card_id=candidate.target_card_id,
                decision=command.decision,
                reviewer=command.reviewer,
                notes=command.notes,
                source_trace_clear=command.source_trace_clear,
                blocked_claims_reviewed=command.blocked_claims_reviewed,
                reviewed_at=now or datetime.now(UTC),
            )
            connection.execute(
                """INSERT INTO content_public_source_reviews
                   (review_id, source_id, source_fact_digest, reviewed_at, payload_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    review.review_id,
                    review.source_id,
                    review.source_fact_digest,
                    review.reviewed_at.isoformat(),
                    review.model_dump_json(),
                ),
            )
        return _response(review, status="approved" if review.decision == "approve" else "rejected")

    def approved_source_ids(self, candidates: tuple[ContentSourceFact, ...]) -> set[str]:
        return {
            review.source_id
            for review in self._current_reviews(candidates)
            if review.decision == "approve"
        }

    def approved_source_facts(
        self, candidates: tuple[ContentSourceFact, ...]
    ) -> tuple[ContentSourceFact, ...]:
        candidates_by_id = {candidate.source_id: candidate for candidate in candidates}
        return tuple(
            fact
            for review in self._current_reviews(candidates)
            if (candidate := candidates_by_id.get(review.source_id)) is not None
            if (fact := review.approved_source_fact(candidate)) is not None
        )

    def _current_reviews(
        self, candidates: tuple[ContentSourceFact, ...]
    ) -> list[ContentPublicSourceReview]:
        if not self.path.exists():
            return []
        connection = self._read_connection()
        if connection is None:
            return []
        try:
            if not _table_exists(connection, "content_public_source_reviews"):
                return []
            rows = connection.execute(
                """SELECT payload_json FROM content_public_source_reviews
                   ORDER BY reviewed_at DESC, review_id DESC"""
            ).fetchall()
        finally:
            connection.close()
        candidates_by_id = {candidate.source_id: candidate for candidate in candidates}
        current: dict[str, ContentPublicSourceReview] = {}
        for row in rows:
            review = ContentPublicSourceReview.model_validate_json(row["payload_json"])
            candidate = candidates_by_id.get(review.source_id)
            if (
                candidate is None
                or review.source_fact_digest != public_source_fact_digest(candidate)
            ):
                continue
            current.setdefault(review.source_id, review)
        return list(current.values())

    def _connect(self) -> sqlite3.Connection:
        prepare_private_store_path(self.path, normalize_existing_parent=False)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """CREATE TABLE IF NOT EXISTS content_public_source_reviews (
                 review_id TEXT PRIMARY KEY,
                 source_id TEXT NOT NULL,
                 source_fact_digest TEXT NOT NULL,
                 reviewed_at TEXT NOT NULL,
                 payload_json TEXT NOT NULL
               )"""
        )
        return connection

    def _read_connection(self) -> sqlite3.Connection | None:
        try:
            connection = sqlite3.connect(self.path)
        except sqlite3.OperationalError:
            return None
        connection.row_factory = sqlite3.Row
        return connection


def public_source_review_store() -> PublicSourceReviewStore:
    return PublicSourceReviewStore(state_db_path())


def _reviewable_candidate(
    candidates: tuple[ContentSourceFact, ...], source_id: str
) -> ContentSourceFact:
    candidate = next((fact for fact in candidates if fact.source_id == source_id), None)
    if candidate is None:
        raise ValueError("public_source_fact_not_found")
    if not (
        candidate.source_type == "public_site"
        and candidate.privacy_class == "commit_safe"
        and candidate.review_status == "review_required"
    ):
        raise ValueError("public_source_fact_not_reviewable")
    return candidate


def _exact_review(
    connection: sqlite3.Connection,
    command: ContentPublicSourceReviewCommand,
    digest: str,
) -> ContentPublicSourceReview | None:
    row = connection.execute(
        """SELECT payload_json FROM content_public_source_reviews
           WHERE source_id = ? AND source_fact_digest = ?
           ORDER BY reviewed_at DESC, review_id DESC LIMIT 1""",
        (command.source_id, digest),
    ).fetchone()
    if row is None:
        return None
    review = ContentPublicSourceReview.model_validate_json(row["payload_json"])
    expected = ContentPublicSourceReview(
        review_id=review.review_id,
        source_id=command.source_id,
        source_fact_digest=digest,
        target_card_id=command.target_card_id,
        decision=command.decision,
        reviewer=command.reviewer,
        notes=command.notes,
        source_trace_clear=command.source_trace_clear,
        blocked_claims_reviewed=command.blocked_claims_reviewed,
        reviewed_at=review.reviewed_at,
    )
    if review.model_dump(exclude={"review_id", "reviewed_at"}) != expected.model_dump(
        exclude={"review_id", "reviewed_at"}
    ):
        raise ValueError("public_source_review_conflict")
    return review


def _response(
    review: ContentPublicSourceReview,
    *,
    status: Literal["approved", "rejected", "idempotent"],
) -> ContentPublicSourceReviewResponse:
    approved_fact_id = (
        f"public_source_review_fact_{review.review_id}"
        if review.decision == "approve"
        else None
    )
    return ContentPublicSourceReviewResponse(
        status=status,
        review=review,
        approved_source_fact_id=approved_fact_id,
        safe_next_step=(
            "Odśwież exact planning input; karta usługi może teraz użyć "
            "zatwierdzonego publicznego source factu."
            if review.decision == "approve"
            else "Nie używaj tej publicznej propozycji w planie; przygotuj poprawione źródło."
        ),
    )


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone() is not None


__all__ = [
    "ContentPublicSourceReview",
    "ContentPublicSourceReviewCommand",
    "ContentPublicSourceReviewResponse",
    "PublicSourceReviewStore",
    "public_source_fact_digest",
    "public_source_review_store",
]
