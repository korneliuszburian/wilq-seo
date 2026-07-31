from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wilq.content.regulatory.policy import (
    ContentRegulatorySourceCandidate,
    regulatory_source_candidates,
)
from wilq.content.regulatory.source_snapshots import (
    ContentRegulatorySourceSnapshot,
    RegulatorySourceSnapshotStore,
)
from wilq.storage.local_state import state_db_path
from wilq.storage.private_paths import prepare_private_store_path

if TYPE_CHECKING:
    from wilq.content.knowledge.source_facts import ContentSourceFact


class ContentRegulatorySourceReviewCommand(BaseModel):
    """One human decision about one exact official-source candidate snapshot."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    expected_source_url: str = Field(min_length=1)
    expected_profile_version: str = Field(min_length=1)
    expected_source_snapshot_id: str = Field(min_length=1)
    expected_source_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewed_fact: str = Field(min_length=20, max_length=2000)
    covered_requirement_ids: list[str] = Field(min_length=1)
    decision: Literal["accepted", "rejected"]
    reviewer: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def require_meaningful_review_fields(self) -> ContentRegulatorySourceReviewCommand:
        if not self.reviewed_fact.strip() or not self.reviewer.strip():
            raise ValueError("Regulatory source review requires a non-empty fact and reviewer.")
        if any(not requirement_id.strip() for requirement_id in self.covered_requirement_ids):
            raise ValueError("Regulatory source review requires non-empty requirement IDs.")
        return self


class ContentRegulatorySourceReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    service_card_ids: list[str] = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    observed_on: str = Field(min_length=1)
    source_snapshot_id: str = Field(min_length=1)
    source_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewed_fact: str = Field(min_length=20)
    covered_requirement_ids: list[str] = Field(min_length=1)
    decision: Literal["accepted", "rejected"]
    reviewer: str = Field(min_length=1)
    reviewed_at: datetime

    def approved_source_fact(self) -> ContentSourceFact | None:
        if self.decision != "accepted":
            return None
        # Import lazily: the effective SourceFact registry projects accepted
        # reviews, so importing it at module load would make that registry
        # circular.
        from wilq.content.knowledge.source_facts import ContentSourceFact

        return ContentSourceFact(
            source_id=f"regulatory_source_fact_{self.review_id}",
            source_type="legal_update",
            privacy_class="commit_safe",
            source_url_or_path=self.source_url,
            extracted_fact=self.reviewed_fact,
            scope="claim_policy",
            freshness_date=self.observed_on,
            confidence=1,
            review_status="approved",
            reviewer=self.reviewer,
            evidence_ids=[f"ev_regulatory_source_review_{self.review_id}"],
            source_connectors=["official_regulatory_review"],
            target_card_id=f"regulatory_{self.profile_id}",
            target_card_type="regulatory_source",
            target_card_title=self.source_title,
            blocked_claims=[
                "Nie traktuj źródła jako indywidualnej porady prawnej ani deklaracji zgodności."
            ],
            evidence_requirements=[
                "Używaj wyłącznie z exact evidence ID i dla przypisanych wymagań regulacyjnych."
            ],
            usage_notes=[
                "Review "
                f"{self.review_id} jest związany ze snapshotem {self.source_snapshot_digest}."
            ],
            official_source=True,
            regulatory_profile_id=self.profile_id,
            regulatory_profile_version=self.profile_version,
            regulatory_requirement_ids=sorted(set(self.covered_requirement_ids)),
            applicable_service_card_ids=sorted(set(self.service_card_ids)),
        )


class ContentRegulatorySourceReviewList(BaseModel):
    """Read-only history of human decisions about official source candidates."""

    model_config = ConfigDict(extra="forbid")

    reviews: list[ContentRegulatorySourceReview] = Field(default_factory=list)


class ContentRegulatorySourceReviewConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal["candidate_changed", "source_snapshot_missing", "source_snapshot_changed"]
    label: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    safe_next_step: str = Field(min_length=1)


class RegulatorySourceReviewStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def record(
        self,
        command: ContentRegulatorySourceReviewCommand,
        *,
        candidates: tuple[ContentRegulatorySourceCandidate, ...] | None = None,
        snapshot_store: RegulatorySourceSnapshotStore | None = None,
        now: datetime | None = None,
    ) -> ContentRegulatorySourceReview:
        candidate = _resolve_candidate(
            command,
            candidates if candidates is not None else regulatory_source_candidates(),
        )
        snapshot = (snapshot_store or RegulatorySourceSnapshotStore(self.path)).get(
            command.expected_source_snapshot_id
        )
        _require_exact_snapshot(candidate, command, snapshot)
        reviewed_at = now or datetime.now(UTC)
        review = ContentRegulatorySourceReview(
            review_id=_review_id(command),
            candidate_id=candidate.candidate_id,
            profile_id=candidate.profile_id,
            profile_version=candidate.profile_version,
            service_card_ids=candidate.service_card_ids,
            source_url=candidate.source_url,
            source_title=candidate.source_title,
            observed_on=snapshot.observed_on,
            source_snapshot_id=snapshot.snapshot_id,
            source_snapshot_digest=snapshot.content_digest,
            reviewed_fact=command.reviewed_fact.strip(),
            covered_requirement_ids=sorted(set(command.covered_requirement_ids)),
            decision=command.decision,
            reviewer=command.reviewer.strip(),
            reviewed_at=reviewed_at,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_regulatory_source_reviews (
                  review_id, candidate_id, decision, reviewed_at, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(review_id) DO NOTHING
                """,
                (
                    review.review_id,
                    review.candidate_id,
                    review.decision,
                    review.reviewed_at.isoformat(),
                    json.dumps(
                        review.model_dump(mode="json"),
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                ),
            )
            row = connection.execute(
                "SELECT payload_json FROM content_regulatory_source_reviews WHERE review_id = ?",
                (review.review_id,),
            ).fetchone()
        if row is None:
            raise RuntimeError("Regulatory source review was not persisted.")
        return ContentRegulatorySourceReview.model_validate(json.loads(row["payload_json"]))

    def list_reviews(self) -> list[ContentRegulatorySourceReview]:
        if not self.path.exists():
            return []
        connection = self._read_connection()
        if connection is None:
            return []
        try:
            with connection:
                if not _table_exists(connection, "content_regulatory_source_reviews"):
                    return []
                rows = connection.execute(
                    "SELECT payload_json FROM content_regulatory_source_reviews "
                    "ORDER BY reviewed_at, review_id"
                ).fetchall()
        finally:
            connection.close()
        return [
            ContentRegulatorySourceReview.model_validate(json.loads(row["payload_json"]))
            for row in rows
        ]

    def approved_source_facts(self) -> tuple[ContentSourceFact, ...]:
        return tuple(
            fact
            for review in self.list_reviews()
            if (fact := review.approved_source_fact()) is not None
        )

    def _connect(self) -> sqlite3.Connection:
        prepare_private_store_path(self.path, normalize_existing_parent=False)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_regulatory_source_reviews (
              review_id TEXT PRIMARY KEY,
              candidate_id TEXT NOT NULL,
              decision TEXT NOT NULL,
              reviewed_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )
        return connection

    def _read_connection(self) -> sqlite3.Connection | None:
        if not self.path.exists():
            return None
        connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection


def _resolve_candidate(
    command: ContentRegulatorySourceReviewCommand,
    candidates: tuple[ContentRegulatorySourceCandidate, ...],
) -> ContentRegulatorySourceCandidate:
    candidate = next(
        (item for item in candidates if item.candidate_id == command.candidate_id),
        None,
    )
    if candidate is None:
        raise ValueError("Regulatory source review candidate is no longer available.")
    if (
        candidate.source_url != command.expected_source_url
        or candidate.profile_version != command.expected_profile_version
    ):
        raise ValueError("Regulatory source review candidate changed; read it again before review.")
    if not set(command.covered_requirement_ids).issubset(candidate.requirement_ids):
        raise ValueError(
            "Regulatory source review cannot cover requirements outside its candidate."
        )
    return candidate


def _require_exact_snapshot(
    candidate: ContentRegulatorySourceCandidate,
    command: ContentRegulatorySourceReviewCommand,
    snapshot: ContentRegulatorySourceSnapshot | None,
) -> None:
    if snapshot is None:
        raise ValueError("Regulatory source snapshot is missing; read the official source again.")
    if (
        snapshot.candidate_id != candidate.candidate_id
        or snapshot.profile_id != candidate.profile_id
        or snapshot.profile_version != candidate.profile_version
        or snapshot.source_url != candidate.source_url
        or snapshot.content_digest != command.expected_source_snapshot_digest
    ):
        raise ValueError("Regulatory source snapshot changed; read the official source again.")


def _review_id(command: ContentRegulatorySourceReviewCommand) -> str:
    payload = json.dumps(command.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()[:24]


def regulatory_source_review_store() -> RegulatorySourceReviewStore:
    """The review ledger shares WILQ's private local state location.

    It owns a separate append-only table and never calls a vendor or changes a
    candidate. The effective SourceFact registry reads only accepted rows.
    """

    return RegulatorySourceReviewStore(state_db_path())


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        is not None
    )
