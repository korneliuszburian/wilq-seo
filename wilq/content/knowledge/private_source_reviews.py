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

PrivateSourceRetentionDecision = Literal[
    "retain_while_source_approved",
    "short_window_only",
]


class ContentPrivateSourceReviewCommand(BaseModel):
    """One owner decision about one exact redacted source-fact candidate."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    expected_source_fact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_card_id: str = Field(min_length=1)
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1, max_length=200)
    notes: str = Field(min_length=1, max_length=2000)
    retention_decision: PrivateSourceRetentionDecision
    source_trace_clear: bool
    blocked_claims_reviewed: bool
    data_classes_confirmed: bool
    source_block_refs_confirmed: bool
    freshness_status_confirmed: bool
    audience_scope_confirmed: bool
    deletion_path_confirmed: bool
    eval_gates_confirmed: bool

    @model_validator(mode="after")
    def require_complete_approval(self) -> ContentPrivateSourceReviewCommand:
        if self.decision == "approve" and not all(
            (
                self.source_trace_clear,
                self.blocked_claims_reviewed,
                self.data_classes_confirmed,
                self.source_block_refs_confirmed,
                self.freshness_status_confirmed,
                self.audience_scope_confirmed,
                self.deletion_path_confirmed,
                self.eval_gates_confirmed,
            )
        ):
            raise ValueError(
                "Approved private source review requires every governance confirmation."
            )
        return self


class ContentPrivateSourceReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_fact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_card_id: str = Field(min_length=1)
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1)
    notes: str = Field(min_length=1)
    retention_decision: PrivateSourceRetentionDecision
    source_trace_clear: bool
    blocked_claims_reviewed: bool
    data_classes_confirmed: bool
    source_block_refs_confirmed: bool
    freshness_status_confirmed: bool
    audience_scope_confirmed: bool
    deletion_path_confirmed: bool
    eval_gates_confirmed: bool
    reviewed_at: datetime

    def approved_source_fact(self, candidate: ContentSourceFact) -> ContentSourceFact | None:
        if self.decision != "approve":
            return None
        return ContentSourceFact(
            source_id=f"private_source_review_fact_{self.review_id}",
            source_type="reviewed_internal",
            privacy_class="redacted_only",
            # Do not carry a private path or filename into the approved projection.
            source_url_or_path=f"private-source-review:{self.review_id}",
            extracted_fact=candidate.extracted_fact,
            scope=candidate.scope,
            freshness_date=candidate.freshness_date,
            confidence=candidate.confidence,
            review_status="approved",
            reviewer=self.reviewer,
            evidence_ids=[SERVICE_PROFILE_SOURCE_FACTS_EVIDENCE_ID],
            source_connectors=["reviewed_internal"],
            blocked_claims=candidate.blocked_claims,
            target_card_id=candidate.target_card_id,
            target_card_type=candidate.target_card_type,
            target_card_title=candidate.target_card_title,
            service_fit_terms=candidate.service_fit_terms,
            buyer_problem_terms=candidate.buyer_problem_terms,
            buyer_triggers=candidate.buyer_triggers,
            cta_patterns=candidate.cta_patterns,
            allowed_claims=candidate.allowed_claims,
            evidence_requirements=candidate.evidence_requirements,
            usage_notes=[
                *candidate.usage_notes,
                (
                    "Zatwierdzona przez człowieka redacted propozycja "
                    f"{candidate.source_id}; review={self.review_id}; "
                    f"retencja={self.retention_decision}."
                ),
            ],
        )


class ContentPrivateSourceReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["approved", "rejected", "idempotent"]
    review: ContentPrivateSourceReview
    approved_source_fact_id: str | None = None
    safe_next_step: str


def private_source_fact_digest(fact: ContentSourceFact) -> str:
    payload = json.dumps(
        fact.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(payload.encode("utf-8")).hexdigest()


class PrivateSourceReviewStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def record(
        self,
        command: ContentPrivateSourceReviewCommand,
        *,
        candidates: tuple[ContentSourceFact, ...],
        now: datetime | None = None,
    ) -> ContentPrivateSourceReviewResponse:
        candidate = _reviewable_candidate(candidates, command.source_id)
        actual_digest = private_source_fact_digest(candidate)
        if actual_digest != command.expected_source_fact_digest:
            raise ValueError("private_source_fact_changed")
        if candidate.target_card_id != command.target_card_id:
            raise ValueError("private_source_target_changed")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = _exact_review(connection, command, actual_digest)
            if existing is not None:
                return _response_for_review(existing, status="idempotent")
            review = ContentPrivateSourceReview(
                review_id=f"private_source_review_{uuid4().hex}",
                source_id=candidate.source_id,
                source_fact_digest=actual_digest,
                target_card_id=candidate.target_card_id,
                decision=command.decision,
                reviewer=command.reviewer,
                notes=command.notes,
                retention_decision=command.retention_decision,
                source_trace_clear=command.source_trace_clear,
                blocked_claims_reviewed=command.blocked_claims_reviewed,
                data_classes_confirmed=command.data_classes_confirmed,
                source_block_refs_confirmed=command.source_block_refs_confirmed,
                freshness_status_confirmed=command.freshness_status_confirmed,
                audience_scope_confirmed=command.audience_scope_confirmed,
                deletion_path_confirmed=command.deletion_path_confirmed,
                eval_gates_confirmed=command.eval_gates_confirmed,
                reviewed_at=now or datetime.now(UTC),
            )
            connection.execute(
                """INSERT INTO content_private_source_reviews
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
        if review.decision == "approve":
            return _response_for_review(review, status="approved")
        return _response_for_review(review, status="rejected")

    def approved_source_ids(self, candidates: tuple[ContentSourceFact, ...]) -> set[str]:
        return {
            review.source_id
            for review in self._current_reviews(candidates)
            if review.decision == "approve"
        }

    def approved_source_facts(
        self,
        candidates: tuple[ContentSourceFact, ...],
    ) -> tuple[ContentSourceFact, ...]:
        candidates_by_id = {candidate.source_id: candidate for candidate in candidates}
        return tuple(
            fact
            for review in self._current_reviews(candidates)
            if (candidate := candidates_by_id.get(review.source_id)) is not None
            if (fact := review.approved_source_fact(candidate)) is not None
        )

    def _current_reviews(
        self,
        candidates: tuple[ContentSourceFact, ...],
    ) -> list[ContentPrivateSourceReview]:
        if not self.path.exists():
            return []
        candidates_by_id = {candidate.source_id: candidate for candidate in candidates}
        connection = self._read_connection()
        if connection is None:
            return []
        try:
            if not _table_exists(connection, "content_private_source_reviews"):
                return []
            rows = connection.execute(
                """SELECT payload_json FROM content_private_source_reviews
                   ORDER BY reviewed_at DESC, review_id DESC"""
            ).fetchall()
        finally:
            connection.close()
        current: dict[str, ContentPrivateSourceReview] = {}
        for row in rows:
            review = ContentPrivateSourceReview.model_validate_json(row["payload_json"])
            candidate = candidates_by_id.get(review.source_id)
            if (
                candidate is None
                or review.source_fact_digest != private_source_fact_digest(candidate)
            ):
                continue
            current.setdefault(review.source_id, review)
        return list(current.values())

    def _connect(self) -> sqlite3.Connection:
        prepare_private_store_path(self.path, normalize_existing_parent=False)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """CREATE TABLE IF NOT EXISTS content_private_source_reviews (
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


def private_source_review_store() -> PrivateSourceReviewStore:
    return PrivateSourceReviewStore(state_db_path())


def _reviewable_candidate(
    candidates: tuple[ContentSourceFact, ...],
    source_id: str,
) -> ContentSourceFact:
    candidate = next((fact for fact in candidates if fact.source_id == source_id), None)
    if candidate is None:
        raise ValueError("private_source_fact_not_found")
    if (
        candidate.source_type not in {"private_candidate", "reviewed_internal"}
        or candidate.privacy_class != "redacted_only"
        or candidate.review_status != "review_required"
        or "ekologus_ai_private_source_catalog" not in candidate.source_connectors
    ):
        raise ValueError("private_source_fact_not_reviewable")
    return candidate


def _exact_review(
    connection: sqlite3.Connection,
    command: ContentPrivateSourceReviewCommand,
    digest: str,
) -> ContentPrivateSourceReview | None:
    row = connection.execute(
        """SELECT payload_json FROM content_private_source_reviews
           WHERE source_id = ? AND source_fact_digest = ?
           ORDER BY reviewed_at DESC, review_id DESC LIMIT 1""",
        (command.source_id, digest),
    ).fetchone()
    if row is None:
        return None
    review = ContentPrivateSourceReview.model_validate_json(row["payload_json"])
    if review.model_dump(exclude={"review_id", "reviewed_at"}) != ContentPrivateSourceReview(
        review_id=review.review_id,
        source_id=command.source_id,
        source_fact_digest=digest,
        target_card_id=command.target_card_id,
        decision=command.decision,
        reviewer=command.reviewer,
        notes=command.notes,
        retention_decision=command.retention_decision,
        source_trace_clear=command.source_trace_clear,
        blocked_claims_reviewed=command.blocked_claims_reviewed,
        data_classes_confirmed=command.data_classes_confirmed,
        source_block_refs_confirmed=command.source_block_refs_confirmed,
        freshness_status_confirmed=command.freshness_status_confirmed,
        audience_scope_confirmed=command.audience_scope_confirmed,
        deletion_path_confirmed=command.deletion_path_confirmed,
        eval_gates_confirmed=command.eval_gates_confirmed,
        reviewed_at=review.reviewed_at,
    ).model_dump(exclude={"review_id", "reviewed_at"}):
        raise ValueError("private_source_review_conflict")
    return review


def _response_for_review(
    review: ContentPrivateSourceReview,
    *,
    status: Literal["approved", "rejected", "idempotent"],
) -> ContentPrivateSourceReviewResponse:
    fact_id = (
        f"private_source_review_fact_{review.review_id}"
        if review.decision == "approve"
        else None
    )
    return ContentPrivateSourceReviewResponse(
        status=status,
        review=review,
        approved_source_fact_id=fact_id,
        safe_next_step=(
            "Odśwież exact planning input; karta usługi może teraz użyć zatwierdzonego "
            "redacted source fact."
            if review.decision == "approve"
            else "Nie używaj tej propozycji w planie; przygotuj osobne, poprawione źródło."
        ),
    )


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone() is not None


__all__ = [
    "ContentPrivateSourceReview",
    "ContentPrivateSourceReviewCommand",
    "ContentPrivateSourceReviewResponse",
    "PrivateSourceReviewStore",
    "private_source_fact_digest",
    "private_source_review_store",
]
