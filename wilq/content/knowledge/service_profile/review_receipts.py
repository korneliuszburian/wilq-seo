"""Append-only receipts for exact Service Profile card review decisions."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from wilq.content.knowledge.source_facts import (
    ContentSourceFact,
    ekologus_source_facts,
)
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.source_pack_binding import source_fact_registry_digest
from wilq.schemas.core import utc_now
from wilq.storage.local_state import state_db_path
from wilq.storage.model_json import model_json
from wilq.storage.private_paths import prepare_private_store_path
from wilq.storage.schema_versions import reject_newer_sqlite_schema

_HEX64 = r"^[0-9a-f]{64}$"
_SAFE_IDENTIFIER = r"^[a-z][a-z0-9_-]{0,239}$"
_ZERO_DIGEST = "0" * 64

ContentServiceCardReviewDecision = Literal[
    "approve",
    "needs_changes",
    "stale",
    "reject",
]


def service_profile_card_review_action_id(card_id: str) -> str:
    """Return the only action ID that may review ``card_id``."""

    return f"service_profile_review_card_{card_id}"


def service_profile_source_fact_digest(fact: ContentSourceFact) -> str:
    """Digest one complete source fact, including its typed lineage."""

    return canonical_json_digest(fact.model_dump(mode="json"))


def service_profile_source_set_digest(
    source_fact_ids: tuple[str, ...],
    source_fact_digests: tuple[str, ...],
) -> str:
    """Digest the exact sorted source-fact ID and digest sets."""

    return canonical_json_digest(
        {
            "source_fact_ids": source_fact_ids,
            "source_fact_digests": source_fact_digests,
        }
    )


# Kept as a readable compatibility name for review-session tooling.  The
# value is intentionally the exact source-fact set digest, not a prose/source
# URL digest that could drift while the facts remain the same.
service_profile_source_reference_digest = service_profile_source_set_digest


def _sorted_unique(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    normalized = tuple(value.strip() for value in values)
    if (
        any(not value for value in normalized)
        or len(normalized) != len(set(normalized))
        or normalized != tuple(sorted(normalized))
    ):
        raise ValueError(f"{label} must be sorted, unique and non-blank.")
    return normalized


def _reviewer_or_notes(value: str, *, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must be non-blank.")
    return normalized


class ContentServiceCardReviewCommand(BaseModel):
    """One human decision over one exact, live Service Profile card."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    action_id: str = Field(min_length=1, max_length=280)
    card_id: str = Field(
        min_length=1,
        max_length=240,
        pattern=_SAFE_IDENTIFIER,
        validation_alias=AliasChoices("card_id", "target_card_id"),
    )
    source_fact_registry_digest: str = Field(pattern=_HEX64)
    source_fact_ids: tuple[str, ...] = ()
    source_fact_digests: tuple[str, ...] = ()
    source_set_digest: str | None = Field(
        default=None,
        pattern=_HEX64,
        validation_alias=AliasChoices("source_set_digest", "source_reference_digest"),
    )
    decision: ContentServiceCardReviewDecision
    source_trace_clear: bool
    blocked_claims_reviewed: bool
    reviewer: str = Field(min_length=1, max_length=200)
    notes: str = Field(min_length=1, max_length=2000)

    @field_validator("source_fact_ids")
    @classmethod
    def validate_source_fact_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique(value, label="Source fact IDs") if value else value

    @field_validator("source_fact_digests")
    @classmethod
    def validate_source_fact_digests(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(
            len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            for digest in value
        ):
            raise ValueError("Source fact digests must be lowercase SHA-256 values.")
        return _sorted_unique(value, label="Source fact digests") if value else value

    @field_validator("reviewer")
    @classmethod
    def validate_reviewer(cls, value: str) -> str:
        return _reviewer_or_notes(value, label="Reviewer")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str) -> str:
        return _reviewer_or_notes(value, label="Review notes")

    @model_validator(mode="after")
    def validate_review(self) -> ContentServiceCardReviewCommand:
        if self.action_id != service_profile_card_review_action_id(self.card_id):
            raise ValueError("Service Profile card review action does not bind the card.")
        if self.source_fact_digests and len(self.source_fact_ids) != len(self.source_fact_digests):
            raise ValueError("Source fact IDs and digests must have equal lengths.")
        if self.source_set_digest is None and not self.source_fact_digests:
            raise ValueError("Review requires source fact digests or a source set digest.")
        if self.source_set_digest is not None and self.source_fact_digests:
            expected = service_profile_source_set_digest(
                self.source_fact_ids,
                self.source_fact_digests,
            )
            if self.source_set_digest != expected:
                raise ValueError("Source fact set digest does not match the submitted set.")
        if self.decision == "approve" and not (
            self.source_trace_clear and self.blocked_claims_reviewed
        ):
            raise ValueError(
                "Approved Service Profile card review requires source trace and "
                "blocked-claim confirmations."
            )
        return self


# Existing review-session code used the longer name while this seam was being
# introduced.  Keep the alias so old clients fail only on stale data, not on a
# harmless import rename.
ContentServiceProfileCardReviewCommand = ContentServiceCardReviewCommand


class ContentServiceCardReviewReceipt(BaseModel):
    """Immutable, lineage-bound human decision for one Service Profile card."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str = Field(min_length=1, max_length=300)
    receipt_digest: str = Field(pattern=_HEX64)
    action_id: str = Field(min_length=1, max_length=280)
    card_id: str = Field(min_length=1, max_length=240, pattern=_SAFE_IDENTIFIER)
    source_fact_registry_digest: str = Field(pattern=_HEX64)
    source_fact_ids: tuple[str, ...] = ()
    source_fact_digests: tuple[str, ...] = ()
    source_set_digest: str = Field(pattern=_HEX64)
    source_reference_digest: str = Field(pattern=_HEX64)
    decision: ContentServiceCardReviewDecision
    source_trace_clear: bool
    blocked_claims_reviewed: bool
    reviewer: str = Field(min_length=1, max_length=200)
    notes: str = Field(min_length=1, max_length=2000)
    reviewed_at: datetime

    @field_validator("source_fact_ids")
    @classmethod
    def validate_receipt_source_fact_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _sorted_unique(value, label="Receipt source fact IDs") if value else value

    @field_validator("source_fact_digests")
    @classmethod
    def validate_receipt_source_fact_digests(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(
            len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            for digest in value
        ):
            raise ValueError("Receipt source fact digests must be lowercase SHA-256 values.")
        return _sorted_unique(value, label="Receipt source fact digests") if value else value

    @field_validator("reviewed_at")
    @classmethod
    def validate_reviewed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Review time must be timezone-aware.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_receipt(self) -> ContentServiceCardReviewReceipt:
        if self.action_id != service_profile_card_review_action_id(self.card_id):
            raise ValueError("Stored Service Profile card review action does not bind the card.")
        if len(self.source_fact_ids) != len(self.source_fact_digests):
            raise ValueError("Receipt source fact IDs and digests must have equal lengths.")
        if self.source_set_digest != service_profile_source_set_digest(
            self.source_fact_ids,
            self.source_fact_digests,
        ):
            raise ValueError("Stored Service Profile source set digest is invalid.")
        if self.source_reference_digest != self.source_set_digest:
            raise ValueError("Stored Service Profile source reference digest is invalid.")
        if self.receipt_digest != _ZERO_DIGEST and self.receipt_digest != (
            service_profile_receipt_digest(self)
        ):
            raise ValueError("Stored Service Profile receipt digest is invalid.")
        return self


class ContentServiceCardReviewRecordResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["created", "idempotent"]
    receipt: ContentServiceCardReviewReceipt


class ContentServiceCardReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["approved", "needs_changes", "stale", "rejected", "idempotent"]
    receipt: ContentServiceCardReviewReceipt
    safe_next_step: str


def service_profile_receipt_digest(receipt: ContentServiceCardReviewReceipt) -> str:
    payload = receipt.model_dump(mode="json", exclude={"receipt_digest"})
    return canonical_json_digest(payload)


class ContentServiceCardReviewStore:
    """SQLite append-only ledger for Service Profile card review receipts."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def record(
        self,
        command: ContentServiceCardReviewCommand,
        *,
        facts: tuple[ContentSourceFact, ...] | None = None,
        cards: tuple[object, ...] | None = None,
        now: datetime | None = None,
    ) -> ContentServiceCardReviewRecordResult:
        accepted = ContentServiceCardReviewCommand.model_validate(
            command.model_dump(mode="python")
        )
        current_facts = ekologus_source_facts() if facts is None else facts
        card, card_facts = _exact_live_card_facts(
            accepted.card_id,
            current_facts,
            cards=cards,
        )
        del card
        expected_registry_digest = source_fact_registry_digest(current_facts)
        expected_ids, expected_digests = _source_set(card_facts)
        expected_set_digest = service_profile_source_set_digest(
            expected_ids,
            expected_digests,
        )
        if accepted.source_fact_registry_digest != expected_registry_digest:
            raise ValueError("service_profile_source_registry_changed")
        if accepted.source_fact_ids != expected_ids:
            raise ValueError("service_profile_card_source_facts_changed")
        if accepted.source_fact_digests and accepted.source_fact_digests != expected_digests:
            raise ValueError("service_profile_card_source_fact_digests_changed")
        if (
            accepted.source_set_digest is not None
            and accepted.source_set_digest != expected_set_digest
        ):
            raise ValueError("service_profile_card_source_set_changed")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_row = connection.execute(
                """
                SELECT *
                FROM content_service_profile_card_review_receipts
                WHERE action_id = ?
                  AND source_fact_registry_digest = ?
                  AND source_set_digest = ?
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (accepted.action_id, expected_registry_digest, expected_set_digest),
            ).fetchone()
            if existing_row is not None:
                existing = _receipt_from_row(existing_row)
                if _receipt_matches_command(existing, accepted):
                    return ContentServiceCardReviewRecordResult(
                        status="idempotent",
                        receipt=existing,
                    )
                raise ValueError("service_profile_card_review_conflict")

            reviewed_at = now or utc_now()
            provisional = ContentServiceCardReviewReceipt(
                receipt_id=f"service_profile_card_review_receipt_{uuid4().hex}",
                receipt_digest=_ZERO_DIGEST,
                action_id=accepted.action_id,
                card_id=accepted.card_id,
                source_fact_registry_digest=expected_registry_digest,
                source_fact_ids=expected_ids,
                source_fact_digests=expected_digests,
                source_set_digest=expected_set_digest,
                source_reference_digest=expected_set_digest,
                decision=accepted.decision,
                source_trace_clear=accepted.source_trace_clear,
                blocked_claims_reviewed=accepted.blocked_claims_reviewed,
                reviewer=accepted.reviewer,
                notes=accepted.notes,
                reviewed_at=reviewed_at,
            )
            receipt = provisional.model_copy(
                update={"receipt_digest": service_profile_receipt_digest(provisional)}
            )
            connection.execute(
                """
                INSERT INTO content_service_profile_card_review_receipts (
                  receipt_id, receipt_digest, action_id, card_id,
                  source_fact_registry_digest, source_set_digest,
                  decision, reviewer, reviewed_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt.receipt_id,
                    receipt.receipt_digest,
                    receipt.action_id,
                    receipt.card_id,
                    receipt.source_fact_registry_digest,
                    receipt.source_set_digest,
                    receipt.decision,
                    receipt.reviewer,
                    receipt.reviewed_at.isoformat(),
                    model_json(receipt),
                ),
            )
        return ContentServiceCardReviewRecordResult(status="created", receipt=receipt)

    def load(self, action_id: str) -> ContentServiceCardReviewReceipt | None:
        connection = self._read_connection()
        if connection is None:
            return None
        try:
            if not _table_exists(connection, "content_service_profile_card_review_receipts"):
                return None
            row = connection.execute(
                """
                SELECT *
                FROM content_service_profile_card_review_receipts
                WHERE action_id = ?
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (action_id,),
            ).fetchone()
        finally:
            connection.close()
        return None if row is None else _receipt_from_row(row)

    # Explicit method names make the store seam discoverable to callers that
    # use the receipt vocabulary rather than the generic ``load`` shorthand.
    def record_content_service_card_review_receipt(
        self,
        command: ContentServiceCardReviewCommand,
        *,
        facts: tuple[ContentSourceFact, ...] | None = None,
        cards: tuple[object, ...] | None = None,
        now: datetime | None = None,
    ) -> ContentServiceCardReviewRecordResult:
        return self.record(command, facts=facts, cards=cards, now=now)

    def load_content_service_card_review_receipt(
        self, action_id: str
    ) -> ContentServiceCardReviewReceipt | None:
        return self.load(action_id)

    def _connect(self) -> sqlite3.Connection:
        prepare_private_store_path(self.path, normalize_existing_parent=False)
        connection = sqlite3.connect(self.path)
        self.path.chmod(0o600)
        reject_newer_sqlite_schema(connection)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_service_profile_card_review_receipts (
              receipt_id TEXT PRIMARY KEY,
              receipt_digest TEXT NOT NULL UNIQUE,
              action_id TEXT NOT NULL,
              card_id TEXT NOT NULL,
              source_fact_registry_digest TEXT NOT NULL,
              source_set_digest TEXT NOT NULL,
              decision TEXT NOT NULL CHECK (
                decision IN ('approve', 'needs_changes', 'stale', 'reject')
              ),
              reviewer TEXT NOT NULL,
              reviewed_at TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              UNIQUE (action_id, source_fact_registry_digest, source_set_digest)
            )
            """
        )
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS content_service_profile_card_review_receipts_no_update
            BEFORE UPDATE ON content_service_profile_card_review_receipts
            BEGIN
              SELECT RAISE(ABORT, 'service profile card review receipts are append-only');
            END
            """
        )
        connection.execute(
            """
            CREATE TRIGGER IF NOT EXISTS content_service_profile_card_review_receipts_no_delete
            BEFORE DELETE ON content_service_profile_card_review_receipts
            BEGIN
              SELECT RAISE(ABORT, 'service profile card review receipts are append-only');
            END
            """
        )
        return connection

    def _read_connection(self) -> sqlite3.Connection | None:
        if not self.path.exists():
            return None
        try:
            connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        except sqlite3.OperationalError:
            return None
        reject_newer_sqlite_schema(connection)
        connection.row_factory = sqlite3.Row
        return connection


def service_profile_card_review_store(path: Path | None = None) -> ContentServiceCardReviewStore:
    return ContentServiceCardReviewStore(state_db_path() if path is None else path)


def current_service_profile_card_review_receipt(
    card_id: str,
    card_facts: tuple[ContentSourceFact, ...],
    *,
    current_facts: tuple[ContentSourceFact, ...],
    store: ContentServiceCardReviewStore | None = None,
) -> ContentServiceCardReviewReceipt | None:
    """Return a receipt only when its card and source snapshot are still exact."""

    receipt = (store or service_profile_card_review_store()).load(
        service_profile_card_review_action_id(card_id)
    )
    if receipt is None:
        return None
    source_ids, source_digests = _source_set(card_facts)
    return receipt if all(
        (
            receipt.card_id == card_id,
            receipt.source_fact_registry_digest == source_fact_registry_digest(current_facts),
            receipt.source_fact_ids == source_ids,
            receipt.source_fact_digests == source_digests,
            receipt.source_set_digest == service_profile_source_set_digest(
                source_ids,
                source_digests,
            ),
        )
    ) else None


def _exact_live_card_facts(
    card_id: str,
    facts: tuple[ContentSourceFact, ...],
    *,
    cards: tuple[object, ...] | None,
) -> tuple[object, tuple[ContentSourceFact, ...]]:
    if cards is None:
        from wilq.content.knowledge.cards import ekologus_content_knowledge_cards

        cards = ekologus_content_knowledge_cards()
    card = next(
        (candidate for candidate in cards if getattr(candidate, "id", None) == card_id),
        None,
    )
    if card is None or getattr(card, "card_type", None) != "service":
        raise ValueError("service_profile_card_not_found")
    card_fact_ids = tuple(sorted(getattr(card, "source_fact_ids", ())))
    facts_by_id = {fact.source_id: fact for fact in facts}
    card_facts = tuple(
        facts_by_id[source_id]
        for source_id in card_fact_ids
        if source_id in facts_by_id
    )
    if tuple(fact.source_id for fact in card_facts) != card_fact_ids:
        raise ValueError("service_profile_card_source_facts_changed")
    return card, card_facts


def _source_set(
    facts: tuple[ContentSourceFact, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    pairs = sorted(
        (fact.source_id, service_profile_source_fact_digest(fact))
        for fact in facts
    )
    return tuple(pair[0] for pair in pairs), tuple(sorted(pair[1] for pair in pairs))


def _receipt_matches_command(
    receipt: ContentServiceCardReviewReceipt,
    command: ContentServiceCardReviewCommand,
) -> bool:
    return all(
        (
            receipt.action_id == command.action_id,
            receipt.card_id == command.card_id,
            receipt.source_fact_registry_digest == command.source_fact_registry_digest,
            receipt.source_fact_ids == command.source_fact_ids,
            (
                not command.source_fact_digests
                or receipt.source_fact_digests == command.source_fact_digests
            ),
            command.source_set_digest in (None, receipt.source_set_digest),
            receipt.decision == command.decision,
            receipt.source_trace_clear == command.source_trace_clear,
            receipt.blocked_claims_reviewed == command.blocked_claims_reviewed,
            receipt.reviewer == command.reviewer,
            receipt.notes == command.notes,
        )
    )


def _receipt_from_row(row: sqlite3.Row) -> ContentServiceCardReviewReceipt:
    receipt = ContentServiceCardReviewReceipt.model_validate_json(
        cast(str, row["payload_json"]),
        strict=True,
    )
    expected = (
        receipt.receipt_id,
        receipt.receipt_digest,
        receipt.action_id,
        receipt.card_id,
        receipt.source_fact_registry_digest,
        receipt.source_set_digest,
        receipt.decision,
        receipt.reviewer,
        receipt.reviewed_at.isoformat(),
    )
    stored = tuple(
        row[name]
        for name in (
            "receipt_id",
            "receipt_digest",
            "action_id",
            "card_id",
            "source_fact_registry_digest",
            "source_set_digest",
            "decision",
            "reviewer",
            "reviewed_at",
        )
    )
    if stored != expected:
        raise ValueError("Stored Service Profile receipt scalars do not match payload.")
    return receipt


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (name,),
        ).fetchone()
        is not None
    )


__all__ = [
    "ContentServiceCardReviewCommand",
    "ContentServiceCardReviewDecision",
    "ContentServiceCardReviewReceipt",
    "ContentServiceCardReviewRecordResult",
    "ContentServiceCardReviewResponse",
    "ContentServiceCardReviewStore",
    "ContentServiceProfileCardReviewCommand",
    "current_service_profile_card_review_receipt",
    "service_profile_card_review_action_id",
    "service_profile_card_review_store",
    "service_profile_receipt_digest",
    "service_profile_source_fact_digest",
    "service_profile_source_reference_digest",
    "service_profile_source_set_digest",
]
