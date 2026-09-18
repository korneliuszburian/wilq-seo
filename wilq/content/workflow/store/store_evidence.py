from __future__ import annotations

import json
import sqlite3
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from wilq.connectors.wordpress.client import _wordpress_draft_value_digest
from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.handoff.wordpress_execution import ContentWordPressDraftExecutionResult
from wilq.content.quality.review import ContentQualityReview
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.documents.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.store.store_queries import (
    upsert_wordpress_draft_execution as _upsert_wordpress_draft_execution,
)
from wilq.content.workflow.store.store_queries import (
    wordpress_revision_apply_claim_key as _wordpress_revision_apply_claim_key,
)
from wilq.schemas.actions import ActionMutationAuditRecord
from wilq.security.redaction import redact_mapping
from wilq.storage.model_json import model_json as _model_json


class ExactWordPressDraftApplyReceipt(BaseModel):
    """One complete, exact WordPress draft apply receipt from persisted evidence."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["applied"] = "applied"
    binding: ContentDraftRevisionBinding
    action_id: str = Field(min_length=1)
    mutation_audit_id: str = Field(min_length=1)
    claim_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    mutation_audit: ActionMutationAuditRecord
    execution_result: ContentWordPressDraftExecutionResult

    @property
    def revision_binding(self) -> ContentDraftRevisionBinding:
        return self.binding

    @property
    def execution(self) -> ContentWordPressDraftExecutionResult:
        return self.execution_result

    @property
    def audit(self) -> ActionMutationAuditRecord:
        return self.mutation_audit


class _EvidenceStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def latest_human_review(self, work_item_id: str) -> ContentHumanReview | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_human_reviews
                WHERE work_item_id = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (work_item_id,),
            ).fetchone()
        if row is None:
            return None
        return ContentHumanReview.model_validate(json.loads(cast(str, row["payload_json"])))

    def save_audit(
        self,
        audit: ContentWordPressDraftAuditEnvelope,
    ) -> ContentWordPressDraftAuditEnvelope:
        redacted = ContentWordPressDraftAuditEnvelope.model_validate(
            redact_mapping(audit.model_dump(mode="json"))
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_workflow_audits (audit_id, human_review_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(audit_id) DO UPDATE SET
                  human_review_id = excluded.human_review_id,
                  payload_json = excluded.payload_json
                """,
                (
                    redacted.audit_id,
                    redacted.human_review_id,
                    _model_json(redacted),
                ),
            )
        return redacted

    def latest_audit_for_review(
        self,
        human_review_id: str,
    ) -> ContentWordPressDraftAuditEnvelope | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_workflow_audits
                WHERE human_review_id = ?
                ORDER BY audit_id DESC
                LIMIT 1
                """,
                (human_review_id,),
            ).fetchone()
        if row is None:
            return None
        return ContentWordPressDraftAuditEnvelope.model_validate(
            json.loads(cast(str, row["payload_json"]))
        )

    def save_quality_review(self, review: ContentQualityReview) -> ContentQualityReview:
        redacted = ContentQualityReview.model_validate(
            redact_mapping(review.model_dump(mode="json"))
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_quality_reviews (review_id, work_item_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(review_id) DO UPDATE SET
                  work_item_id = excluded.work_item_id,
                  payload_json = excluded.payload_json
                """,
                (
                    redacted.review_id,
                    redacted.work_item_id,
                    _model_json(redacted),
                ),
            )
        return redacted

    def latest_quality_review(self, work_item_id: str) -> ContentQualityReview | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_quality_reviews
                WHERE work_item_id = ?
                ORDER BY review_id DESC
                LIMIT 1
                """,
                (work_item_id,),
            ).fetchone()
        if row is None:
            return None
        return ContentQualityReview.model_validate(json.loads(cast(str, row["payload_json"])))

    def save_wordpress_draft_execution(
        self,
        work_item_id: str,
        result: ContentWordPressDraftExecutionResult,
    ) -> ContentWordPressDraftExecutionResult:
        redacted = ContentWordPressDraftExecutionResult.model_validate(
            redact_mapping(result.model_dump(mode="json"))
        )
        with self._connect() as connection:
            _upsert_wordpress_draft_execution(connection, work_item_id, redacted)
        return redacted

    def latest_wordpress_draft_execution(
        self,
        work_item_id: str,
        *,
        handoff_id: str | None = None,
        revision_id: str | None = None,
        revision_digest: str | None = None,
    ) -> ContentWordPressDraftExecutionResult | None:
        binding_values = (handoff_id, revision_id, revision_digest)
        # A caller that starts an exact lookup must provide the complete
        # binding. Never fall back to a work-item-wide legacy execution for a
        # partially specified revision, since that could unlock measurement
        # for a different document.
        if any(value is not None for value in binding_values) and not all(
            value for value in binding_values
        ):
            return None
        with self._connect() as connection:
            if handoff_id and revision_id and revision_digest:
                row = connection.execute(
                    """
                    SELECT payload_json FROM content_wordpress_draft_execution_history
                    WHERE work_item_id = ? AND handoff_id = ? AND revision_id = ?
                      AND revision_digest = ?
                    LIMIT 1
                    """,
                    (work_item_id, handoff_id, revision_id, revision_digest),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT payload_json FROM content_wordpress_draft_executions
                    WHERE work_item_id = ?
                    LIMIT 1
                    """,
                    (work_item_id,),
                ).fetchone()
        if row is None:
            return None
        return ContentWordPressDraftExecutionResult.model_validate(
            json.loads(cast(str, row["payload_json"]))
        )

    def load_exact_wordpress_draft_apply_receipt(
        self,
        binding: ContentDraftRevisionBinding,
        action_id: str,
        mutation_audit_id: str,
    ) -> ExactWordPressDraftApplyReceipt | None:
        """Load one complete apply receipt without URL or legacy fallbacks."""

        if not action_id.strip() or not mutation_audit_id.strip():
            return None
        claim_key = _wordpress_revision_apply_claim_key(binding)
        with self._connect() as connection:
            connection.execute("BEGIN")
            claim = connection.execute(
                """
                SELECT claim_key, work_item_id, revision_id, approval_decision_id,
                       action_id, status
                FROM content_wordpress_revision_apply_claims
                WHERE claim_key = ? AND action_id = ? AND status = 'applied'
                LIMIT 1
                """,
                (claim_key, action_id),
            ).fetchone()
            if claim is None or not _claim_matches_binding(claim, binding, claim_key, action_id):
                return None

            mutation_row = connection.execute(
                """
                SELECT id, action_id, status, payload_json
                FROM action_mutation_audits
                WHERE id = ? AND action_id = ?
                LIMIT 1
                """,
                (mutation_audit_id, action_id),
            ).fetchone()
            if mutation_row is None:
                return None
            mutation_audit = _decode_action_mutation_audit(mutation_row["payload_json"])
            if mutation_audit is None or not _mutation_audit_matches(
                mutation_audit,
                mutation_row,
                binding=binding,
                action_id=action_id,
                mutation_audit_id=mutation_audit_id,
            ):
                return None

            execution_row = connection.execute(
                """
                SELECT payload_json
                FROM content_wordpress_draft_execution_history
                WHERE work_item_id = ? AND handoff_id = ? AND revision_id = ?
                  AND revision_digest = ?
                LIMIT 1
                """,
                (
                    binding.work_item_id,
                    binding.handoff_id,
                    binding.revision_id,
                    binding.content_digest,
                ),
            ).fetchone()
            if execution_row is None:
                return None
            execution = _decode_execution_result(execution_row["payload_json"])
            if execution is None or not _execution_matches_exact_apply(execution, binding):
                return None

        return ExactWordPressDraftApplyReceipt(
            binding=binding,
            action_id=action_id,
            mutation_audit_id=mutation_audit_id,
            claim_key=claim_key,
            mutation_audit=mutation_audit,
            execution_result=execution,
        )


def _claim_matches_binding(
    row: sqlite3.Row,
    binding: ContentDraftRevisionBinding,
    claim_key: str,
    action_id: str,
) -> bool:
    return bool(
        row["claim_key"] == claim_key
        and row["work_item_id"] == binding.work_item_id
        and row["revision_id"] == binding.revision_id
        and row["approval_decision_id"] == binding.approval_decision_id
        and row["action_id"] == action_id
        and row["status"] == "applied"
    )


def _decode_action_mutation_audit(value: object) -> ActionMutationAuditRecord | None:
    try:
        return ActionMutationAuditRecord.model_validate(json.loads(cast(str, value)))
    except (TypeError, ValueError):
        return None


def _mutation_audit_matches(
    audit: ActionMutationAuditRecord,
    row: sqlite3.Row,
    *,
    binding: ContentDraftRevisionBinding,
    action_id: str,
    mutation_audit_id: str,
) -> bool:
    return bool(
        row["id"] == mutation_audit_id
        and row["action_id"] == action_id
        and row["status"] == "applied"
        and audit.id == mutation_audit_id
        and audit.action_id == action_id
        and audit.status == "applied"
        and audit.connector == "wordpress_ekologus"
        and audit.adapter_reached
        and audit.external_write_attempted
        and audit.mutation_attempted
        and audit.wordpress_draft_binding == binding
        and audit.new_page_draft_binding is None
    )


def _decode_execution_result(value: object) -> ContentWordPressDraftExecutionResult | None:
    try:
        return ContentWordPressDraftExecutionResult.model_validate(json.loads(cast(str, value)))
    except (TypeError, ValueError):
        return None


def _execution_matches_exact_apply(
    execution: ContentWordPressDraftExecutionResult,
    binding: ContentDraftRevisionBinding,
) -> bool:
    if not (
        execution.status == "created"
        and execution.mode == "live"
        and execution.external_write_attempted
        and execution.wordpress_post_id
        and execution.revision_binding == binding
    ):
        return False
    boundary = execution.boundary
    if not (
        boundary.allowed_operation == "create_wordpress_draft"
        and boundary.live_write_enabled
        and boundary.live_adapter_configured
        and boundary.publish_allowed is False
        and boundary.destructive_update_allowed is False
    ):
        return False
    if not (
        execution.endpoint is not None
        and execution.expected_content_digest is not None
        and execution.observed_content_digest is not None
        and execution.expected_content_digest == execution.observed_content_digest
        and execution.expected_title_digest is not None
        and execution.observed_title_digest is not None
        and execution.expected_title_digest == execution.observed_title_digest
    ):
        return False
    if (execution.expected_acf_digest is None) != (execution.observed_acf_digest is None):
        return False
    if (
        execution.expected_acf_digest is not None
        and execution.expected_acf_digest != execution.observed_acf_digest
    ):
        return False
    payload = execution.payload
    if payload is None:
        return False
    if not (
        execution.expected_content_digest
        == _wordpress_draft_value_digest(payload.content_html or payload.content_markdown)
        and execution.expected_title_digest == _wordpress_draft_value_digest(payload.title)
    ):
        return False
    if payload.authoring_mode == "acf_flexible_content" and not (
        execution.expected_acf_digest is not None
        and execution.observed_acf_digest is not None
        and execution.expected_acf_digest == execution.observed_acf_digest
    ):
        return False
    return bool(
        payload.connector == "wordpress_ekologus"
        and payload.post_status == "draft"
        and payload.publish_allowed is False
        and payload.destructive_update_allowed is False
        and payload.final_canonical_url == binding.final_canonical_url
        and execution.endpoint == payload.endpoint_kind
    )


__all__ = ["ExactWordPressDraftApplyReceipt"]
