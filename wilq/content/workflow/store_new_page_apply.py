"""Atomic claim ownership for one exact new-page dev-draft attempt."""

from __future__ import annotations

import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Literal, cast

from wilq.content.workflow.new_page_revision_binding import ContentNewPageDraftBinding
from wilq.content.workflow.revisions import ContentDraftRevision, ContentDraftRevisionReview
from wilq.content.workflow.store_queries import (
    latest_draft_revision,
    latest_draft_revision_review,
)
from wilq.content.workflow.store_schema import ensure_content_workflow_schema
from wilq.schemas.core import utc_now
from wilq.storage.local_state import DEFAULT_STATE_DB, state_db_path
from wilq.storage.private_paths import prepare_private_store_path

NewPageRevisionApplyClaimResult = Literal[
    "acquired", "not_current", "in_progress", "applied", "failed"
]


def new_page_apply_claim_store() -> NewPageApplyClaimStore:
    return NewPageApplyClaimStore(state_db_path())


class NewPageApplyClaimStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        prepare_private_store_path(
            self.path,
            normalize_existing_parent=self.path == DEFAULT_STATE_DB,
        )
        connection = sqlite3.connect(self.path)
        self.path.chmod(0o600)
        connection.row_factory = sqlite3.Row
        ensure_content_workflow_schema(connection)
        return connection

    def claim_new_page_revision_apply(
        self,
        binding: ContentNewPageDraftBinding,
        *,
        action_id: str,
        claimed_by: str,
    ) -> NewPageRevisionApplyClaimResult:
        """Reserve one exact reviewed new-page revision before any vendor call."""
        claim_key = _claim_key(binding)
        now = utc_now().isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            revision = latest_draft_revision(connection, binding.work_item_id)
            review = (
                None
                if revision is None
                else latest_draft_revision_review(connection, revision.revision_id)
            )
            if not _binding_is_current_and_approved(binding, revision, review):
                return "not_current"
            inserted = connection.execute(
                """
                INSERT INTO content_new_page_revision_apply_claims (
                  claim_key, work_item_id, revision_id, revision_digest, action_id,
                  status, claimed_by, claimed_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'claimed', ?, ?, ?)
                ON CONFLICT(claim_key) DO NOTHING
                """,
                (
                    claim_key,
                    binding.work_item_id,
                    binding.revision_id,
                    binding.revision_digest,
                    action_id,
                    claimed_by,
                    now,
                    now,
                ),
            )
            if inserted.rowcount == 1:
                return "acquired"
            row = connection.execute(
                "SELECT status FROM content_new_page_revision_apply_claims WHERE claim_key = ?",
                (claim_key,),
            ).fetchone()
        if row is None:
            raise RuntimeError("New-page apply claim disappeared after a unique conflict.")
        status = row["status"]
        if status == "claimed":
            return "in_progress"
        if status in {"applied", "failed"}:
            return cast(Literal["applied", "failed"], status)
        raise RuntimeError("New-page apply claim has an unsupported persisted status.")

    def finish_new_page_revision_apply_claim(
        self,
        binding: ContentNewPageDraftBinding,
        *,
        status: Literal["applied", "failed"],
    ) -> None:
        """Consume a claimed binding after the adapter has a known outcome."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute(
                """
                UPDATE content_new_page_revision_apply_claims
                SET status = ?, updated_at = ?
                WHERE claim_key = ? AND status = 'claimed'
                """,
                (status, utc_now().isoformat(), _claim_key(binding)),
            )
            if updated.rowcount != 1:
                raise RuntimeError("New-page apply claim is not active during finalization.")


def _claim_key(binding: ContentNewPageDraftBinding) -> str:
    return sha256(
        f"{binding.work_item_id}:{binding.revision_id}:{binding.revision_digest}".encode()
    ).hexdigest()


def _binding_is_current_and_approved(
    binding: ContentNewPageDraftBinding,
    revision: ContentDraftRevision | None,
    review: ContentDraftRevisionReview | None,
) -> bool:
    identity = None if revision is None else revision.new_page_document_identity
    return bool(
        revision
        and review
        and revision.document_kind == "new_page"
        and revision.revision_id == binding.revision_id
        and revision.content_digest == binding.revision_digest
        and identity
        and identity.brief_id == binding.brief_id
        and identity.brief_digest == binding.brief_digest
        and identity.foundation_id == binding.foundation_id
        and identity.service_card_id == binding.service_card_id
        and identity.service_card_digest == binding.service_card_digest
        and review.decision == "approved"
        and review.revision_id == binding.revision_id
        and review.revision_digest == binding.revision_digest
    )
