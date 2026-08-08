"""Atomic claim ownership for one exact new-page dev-draft attempt."""

from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from wilq.connectors.wordpress.client import WORDPRESS_DEV_HOSTS
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionReview,
)
from wilq.content.workflow.store.store_queries import (
    latest_draft_revision,
    latest_draft_revision_review,
    upsert_action_mutation_audit,
    upsert_audit_event,
)
from wilq.content.workflow.store.store_schema import ensure_content_workflow_schema
from wilq.content.workflow.target.new_page_revision_binding import ContentNewPageDraftBinding
from wilq.schemas.actions import ActionMutationAuditRecord, AuditEvent
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import DEFAULT_STATE_DB, state_db_path
from wilq.storage.private_paths import prepare_private_store_path

NewPageRevisionApplyClaimResult = Literal[
    "acquired", "not_current", "in_progress", "applied", "failed", "uncertain"
]


class NewPageApplyPersistedResult(BaseModel):
    """Allowlisted recovery data from one create-only WordPress response."""

    model_config = ConfigDict(extra="forbid")

    wordpress_post_id: str = Field(min_length=1)
    link: str = ""
    edit_link: str = ""
    status: str = Field(min_length=1)


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
                """
                SELECT status, result_json
                FROM content_new_page_revision_apply_claims
                WHERE claim_key = ?
                """,
                (claim_key,),
            ).fetchone()
        if row is None:
            raise RuntimeError("New-page apply claim disappeared after a unique conflict.")
        status = row["status"]
        if status == "claimed":
            return "in_progress"
        if status == "applied":
            return "applied" if _stored_result(row["result_json"]) is not None else "uncertain"
        if status == "failed":
            return "failed"
        raise RuntimeError("New-page apply claim has an unsupported persisted status.")

    def finish_new_page_revision_apply_claim(
        self,
        binding: ContentNewPageDraftBinding,
        *,
        status: Literal["applied", "failed"],
        audit_event: AuditEvent,
        mutation_audit: ActionMutationAuditRecord,
        adapter_result: dict[str, Any] | None = None,
    ) -> None:
        """Persist the outcome audit and consume the exact claim atomically."""
        persisted_result = _persisted_result(adapter_result)
        result_json = (
            persisted_result.model_dump_json() if persisted_result is not None else None
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            upsert_audit_event(connection, audit_event)
            upsert_action_mutation_audit(connection, mutation_audit)
            updated = connection.execute(
                """
                UPDATE content_new_page_revision_apply_claims
                SET status = ?, result_json = ?, updated_at = ?
                WHERE claim_key = ? AND status = 'claimed'
                """,
                (status, result_json, utc_now().isoformat(), _claim_key(binding)),
            )
            if updated.rowcount != 1:
                row = connection.execute(
                    """
                    SELECT status, result_json FROM content_new_page_revision_apply_claims
                    WHERE claim_key = ?
                    """,
                    (_claim_key(binding),),
                ).fetchone()
                if row is not None and row["status"] == status:
                    if row["result_json"] is None and result_json is not None:
                        connection.execute(
                            """
                            UPDATE content_new_page_revision_apply_claims
                            SET result_json = ?, updated_at = ?
                            WHERE claim_key = ? AND status = ? AND result_json IS NULL
                            """,
                            (
                                result_json,
                                utc_now().isoformat(),
                                _claim_key(binding),
                                status,
                            ),
                        )
                    return
                raise RuntimeError("New-page apply claim is not active during finalization.")

    def result_for_action(self, action_id: str) -> NewPageApplyPersistedResult | None:
        """Recover only the redacted result bound to a completed exact action."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT status, result_json
                FROM content_new_page_revision_apply_claims
                WHERE action_id = ?
                ORDER BY claimed_at DESC
                LIMIT 1
                """,
                (action_id,),
            ).fetchone()
        if row is None or row["status"] != "applied":
            return None
        return _stored_result(row["result_json"])


def _claim_key(binding: ContentNewPageDraftBinding) -> str:
    return sha256(
        f"{binding.work_item_id}:{binding.revision_id}:{binding.revision_digest}".encode()
    ).hexdigest()


def _persisted_result(
    adapter_result: dict[str, Any] | None,
) -> NewPageApplyPersistedResult | None:
    if adapter_result is None:
        return None
    post_id = adapter_result.get("wordpress_post_id")
    status = adapter_result.get("status")
    if not isinstance(post_id, str) or not post_id.strip():
        return None
    if not isinstance(status, str) or not status.strip():
        return None
    allowlisted = {
        "wordpress_post_id": post_id.strip(),
        "link": _safe_dev_url(adapter_result.get("link")),
        "edit_link": _safe_dev_url(adapter_result.get("edit_link")),
        "status": status.strip(),
    }
    return NewPageApplyPersistedResult.model_validate(redact_mapping(allowlisted))


def _stored_result(value: Any) -> NewPageApplyPersistedResult | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return NewPageApplyPersistedResult.model_validate(json.loads(value))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _safe_dev_url(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    parsed = urlparse(value.strip())
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or (parsed.hostname or "").lower() not in WORDPRESS_DEV_HOSTS
    ):
        return ""
    return parsed.geturl()


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
