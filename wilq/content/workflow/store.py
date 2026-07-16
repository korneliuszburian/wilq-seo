from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

from wilq.content.handoff.wordpress import ContentWordPressDraftAuditEnvelope
from wilq.content.handoff.wordpress_execution import (
    ContentWordPressDraftExecutionBoundary,
    ContentWordPressDraftExecutionResult,
)
from wilq.content.quality.review import ContentQualityReview
from wilq.content.review.human import ContentHumanReview
from wilq.content.workflow.codex_revision_commit import (
    codex_completion_state,
    persist_codex_completion,
    prepare_codex_completion,
)
from wilq.content.workflow.planning import (
    ContentPlanningDecision,
    ContentPlanningReviewRequest,
)
from wilq.content.workflow.planning_persistence import record_content_planning_review
from wilq.content.workflow.revision_binding import ContentDraftRevisionBinding
from wilq.content.workflow.revision_persistence import (
    build_stored_draft_revision,
    draft_revision_content_digest,
)
from wilq.content.workflow.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionReviewCommand,
    ContentDraftRevisionReviewResult,
    ContentDraftRevisionState,
    ContentDraftRevisionWriteResult,
)
from wilq.content.workflow.store_measurement import MeasurementStoreMixin
from wilq.content.workflow.store_queries import (
    binding_is_current_and_approved as _binding_is_current_and_approved,
)
from wilq.content.workflow.store_queries import (
    draft_revision_conflict as _draft_revision_conflict,
)
from wilq.content.workflow.store_queries import (
    execution_result_from_adapter_result as _execution_result_from_adapter_result,
)
from wilq.content.workflow.store_queries import (
    latest_draft_revision as _latest_draft_revision,
)
from wilq.content.workflow.store_queries import (
    latest_draft_revision_review as _latest_draft_revision_review,
)
from wilq.content.workflow.store_queries import (
    latest_planning_decision as _latest_planning_decision,
)
from wilq.content.workflow.store_queries import (
    model_json as _model_json,
)
from wilq.content.workflow.store_queries import (
    upsert_action_mutation_audit as _upsert_action_mutation_audit,
)
from wilq.content.workflow.store_queries import (
    upsert_audit_event as _upsert_audit_event,
)
from wilq.content.workflow.store_queries import (
    upsert_wordpress_draft_execution as _upsert_wordpress_draft_execution,
)
from wilq.content.workflow.store_queries import (
    wordpress_revision_apply_claim_key as _wordpress_revision_apply_claim_key,
)
from wilq.content.workflow.store_queries import (
    wordpress_revision_apply_in_progress as _wordpress_revision_apply_in_progress,
)
from wilq.content.workflow.store_revision_review import record_draft_revision_review
from wilq.content.workflow.store_schema import ensure_content_workflow_schema
from wilq.schemas.actions import ActionMutationAuditRecord, AuditEvent, CodexRun
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import DEFAULT_STATE_DB, state_db_path
from wilq.storage.private_paths import prepare_private_store_path

WordPressRevisionApplyClaimResult = Literal[
    "acquired",
    "not_current",
    "in_progress",
    "applied",
    "failed",
]
WordPressRevisionApplyClaimFinalStatus = Literal["applied", "failed"]
WORDPRESS_APPLY_RECONCILIATION_MIN_AGE_SECONDS = 300


def content_workflow_store() -> ContentWorkflowStore:
    return ContentWorkflowStore(state_db_path())


class _StoreConnectionMixin:
    path: Path

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError


class _DraftRevisionStoreMixin(_StoreConnectionMixin):
    def append_draft_revision(
        self,
        command: ContentDraftRevisionAppendCommand,
        *,
        completed_codex_run: CodexRun | None = None,
    ) -> ContentDraftRevisionWriteResult:
        redacted_command = ContentDraftRevisionAppendCommand.model_validate(
            redact_mapping(command.model_dump(mode="json"))
        )
        redacted_completion = prepare_codex_completion(
            redacted_command,
            completed_codex_run,
        )
        content_digest = draft_revision_content_digest(redacted_command)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            completion_state = codex_completion_state(
                connection,
                redacted_completion,
            )
            latest = _latest_draft_revision(connection, redacted_command.work_item_id)
            if _wordpress_revision_apply_in_progress(connection, redacted_command.work_item_id):
                return ContentDraftRevisionWriteResult(
                    status="conflict",
                    conflict=_draft_revision_conflict("apply_in_progress", latest),
                )
            if latest is not None and (
                latest.base_revision_id == redacted_command.base_revision_id
                and latest.content_digest == content_digest
                and latest.created_by == redacted_command.created_by
                and latest.proposal_metadata == redacted_command.proposal_metadata
            ):
                if completion_state == "started":
                    persist_codex_completion(connection, redacted_completion)
                return ContentDraftRevisionWriteResult(
                    status="idempotent",
                    revision=latest,
                )

            if completion_state == "completed":
                raise ValueError("Completed Codex run does not match an idempotent draft revision.")

            current_revision_id = None if latest is None else latest.revision_id
            if redacted_command.base_revision_id != current_revision_id:
                return ContentDraftRevisionWriteResult(
                    status="conflict",
                    conflict=_draft_revision_conflict("stale_base", latest),
                )

            revision = build_stored_draft_revision(
                redacted_command,
                revision_number=1 if latest is None else latest.revision_number + 1,
                content_digest=content_digest,
            )
            redacted_revision = ContentDraftRevision.model_validate(
                redact_mapping(revision.model_dump(mode="json"))
            )
            connection.execute(
                """
                INSERT INTO content_draft_revisions (
                  revision_id,
                  work_item_id,
                  revision_number,
                  base_revision_id,
                  content_digest,
                  created_at,
                  payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    redacted_revision.revision_id,
                    redacted_revision.work_item_id,
                    redacted_revision.revision_number,
                    redacted_revision.base_revision_id,
                    redacted_revision.content_digest,
                    redacted_revision.created_at.isoformat(),
                    _model_json(redacted_revision),
                ),
            )
            persist_codex_completion(connection, redacted_completion)
        return ContentDraftRevisionWriteResult(
            status="created",
            revision=redacted_revision,
        )

    def record_planning_review(
        self,
        work_item_id: str,
        request: ContentPlanningReviewRequest,
        *,
        planning_digest: str,
        service_card_id: str | None,
        human_override_review_required: bool,
    ) -> tuple[Literal["created", "idempotent"], ContentPlanningDecision]:
        with self._connect() as connection:
            return record_content_planning_review(
                connection,
                work_item_id=work_item_id,
                request=request,
                planning_digest=planning_digest,
                service_card_id=service_card_id,
                human_override_review_required=human_override_review_required,
            )

    def load_planning_decisions(self, work_item_id: str) -> list[ContentPlanningDecision]:
        with self._connect() as connection:
            return [
                decision
                for stage in ("scope", "section_map")
                if (decision := _latest_planning_decision(connection, work_item_id, stage))
                is not None
            ]

    def review_draft_revision(
        self,
        command: ContentDraftRevisionReviewCommand,
    ) -> ContentDraftRevisionReviewResult:
        redacted_command = ContentDraftRevisionReviewCommand.model_validate(
            redact_mapping(command.model_dump(mode="json"))
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            return record_draft_revision_review(connection, redacted_command)

    def load_draft_revision_state(self, work_item_id: str) -> ContentDraftRevisionState:
        with self._connect() as connection:
            latest_revision = _latest_draft_revision(connection, work_item_id)
            row = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM content_draft_revisions
                WHERE work_item_id = ?
                """,
                (work_item_id,),
            ).fetchone()
            revision_count = 0 if row is None else cast(int, row["count"])
            latest_review = (
                None
                if latest_revision is None
                else _latest_draft_revision_review(connection, latest_revision.revision_id)
            )
        if latest_revision is None:
            return ContentDraftRevisionState(status="empty", revision_count=0)
        return ContentDraftRevisionState(
            status="unreviewed" if latest_review is None else latest_review.decision,
            latest_revision=latest_revision,
            latest_review=latest_review,
            revision_count=revision_count,
        )

    def list_draft_revisions(self, work_item_id: str) -> list[ContentDraftRevision]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM content_draft_revisions
                WHERE work_item_id = ?
                ORDER BY revision_number ASC
                """,
                (work_item_id,),
            ).fetchall()
        return [
            ContentDraftRevision.model_validate(json.loads(cast(str, row["payload_json"])))
            for row in rows
        ]


class _WordPressApplyStoreMixin(_StoreConnectionMixin):
    def claim_wordpress_revision_apply(
        self,
        binding: ContentDraftRevisionBinding,
        *,
        action_id: str,
        claimed_by: str,
    ) -> WordPressRevisionApplyClaimResult:
        claim_key = _wordpress_revision_apply_claim_key(binding)
        now = utc_now().isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            latest_revision = _latest_draft_revision(connection, binding.work_item_id)
            latest_review = (
                None
                if latest_revision is None
                else _latest_draft_revision_review(
                    connection,
                    latest_revision.revision_id,
                )
            )
            if not _binding_is_current_and_approved(
                binding,
                latest_revision=latest_revision,
                latest_review=latest_review,
            ):
                return "not_current"
            inserted = connection.execute(
                """
                INSERT INTO content_wordpress_revision_apply_claims (
                  claim_key,
                  work_item_id,
                  revision_id,
                  approval_decision_id,
                  action_id,
                  status,
                  claimed_by,
                  claimed_at,
                  updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'claimed', ?, ?, ?)
                ON CONFLICT(claim_key) DO NOTHING
                """,
                (
                    claim_key,
                    binding.work_item_id,
                    binding.revision_id,
                    binding.approval_decision_id,
                    action_id,
                    claimed_by,
                    now,
                    now,
                ),
            )
            if inserted.rowcount == 1:
                started = AuditEvent(
                    id=f"audit_{action_id}_apply_started_{claim_key[:12]}",
                    action_id=action_id,
                    event_type="action_apply_started",
                    event_type_label="Rozpoczęto zapis dokładnej wersji",
                    actor=claimed_by,
                    summary=(
                        "Zarezerwowano jednorazową zgodę przed wywołaniem adaptera "
                        "WordPress. Wynik zapisu nie jest jeszcze znany."
                    ),
                    details={
                        "wordpress_draft_binding": binding.model_dump(mode="json"),
                        "apply_claim_status": "claimed",
                    },
                )
                _upsert_audit_event(connection, started)
                return "acquired"
            row = connection.execute(
                """
                SELECT status
                FROM content_wordpress_revision_apply_claims
                WHERE claim_key = ?
                """,
                (claim_key,),
            ).fetchone()
        if row is None:
            raise RuntimeError("WordPress apply claim disappeared after a unique conflict.")
        status = cast(str, row["status"])
        if status == "claimed":
            return "in_progress"
        if status in {"applied", "failed"}:
            return cast(WordPressRevisionApplyClaimResult, status)
        raise RuntimeError("WordPress apply claim has an unsupported status.")

    def finish_wordpress_revision_apply_claim(
        self,
        binding: ContentDraftRevisionBinding,
        *,
        status: WordPressRevisionApplyClaimFinalStatus,
        audit_event: AuditEvent,
        mutation_audit: ActionMutationAuditRecord,
        adapter_result: dict[str, Any] | None,
    ) -> None:
        claim_key = _wordpress_revision_apply_claim_key(binding)
        execution_result = _execution_result_from_adapter_result(adapter_result)
        if status == "applied" and (
            execution_result is None
            or execution_result.status != "created"
            or not execution_result.wordpress_post_id
        ):
            raise RuntimeError("Applied WordPress claim requires a persisted created draft result.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            _upsert_audit_event(connection, audit_event)
            _upsert_action_mutation_audit(connection, mutation_audit)
            if execution_result is not None:
                _upsert_wordpress_draft_execution(
                    connection,
                    binding.work_item_id,
                    execution_result,
                )
            updated = connection.execute(
                """
                UPDATE content_wordpress_revision_apply_claims
                SET status = ?, updated_at = ?
                WHERE claim_key = ? AND status = 'claimed'
                """,
                (status, utc_now().isoformat(), claim_key),
            )
            if updated.rowcount != 1:
                raise RuntimeError("WordPress apply claim is not active during finalization.")

    def reconcile_wordpress_revision_apply_claim(
        self,
        *,
        work_item_id: str,
        outcome: WordPressRevisionApplyClaimFinalStatus,
        reconciled_by: str,
        notes: str,
        wordpress_post_id: str | None = None,
    ) -> AuditEvent:
        if outcome == "applied" and not wordpress_post_id:
            raise ValueError("Rozstrzygnięcie applied wymaga ID szkicu WordPress.")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT claim_key, revision_id, action_id, claimed_at
                FROM content_wordpress_revision_apply_claims
                WHERE work_item_id = ? AND status = 'claimed'
                ORDER BY claimed_at DESC
                """,
                (work_item_id,),
            ).fetchall()
            if len(rows) != 1:
                raise ValueError(
                    "Reconciliation wymaga dokładnie jednego nierozstrzygniętego apply."
                )
            row = rows[0]
            claim_key = cast(str, row["claim_key"])
            action_id = cast(str, row["action_id"])
            revision_id = cast(str, row["revision_id"])
            claimed_at = datetime.fromisoformat(cast(str, row["claimed_at"]))
            claim_age_seconds = (utc_now() - claimed_at).total_seconds()
            if claim_age_seconds < WORDPRESS_APPLY_RECONCILIATION_MIN_AGE_SECONDS:
                raise ValueError(
                    "Aktywny zapis WordPress nie może być rozstrzygnięty przed końcem "
                    "okna recovery."
                )
            audit = AuditEvent(
                id=f"audit_{action_id}_apply_reconciled_{claim_key[:12]}",
                action_id=action_id,
                event_type="action_apply_reconciled",
                event_type_label="Rozstrzygnięto przerwany zapis WordPress",
                actor=reconciled_by,
                summary=(
                    "Operator rozstrzygnął przerwany zapis na podstawie inspekcji "
                    "WordPress. WILQ nie ponowił zapisu."
                ),
                details={
                    "work_item_id": work_item_id,
                    "revision_id": revision_id,
                    "reconciliation_outcome": outcome,
                    "wordpress_post_id": wordpress_post_id,
                    "notes": notes,
                    "external_write_replayed": False,
                },
            )
            _upsert_audit_event(connection, audit)
            if outcome == "applied":
                _upsert_wordpress_draft_execution(
                    connection,
                    work_item_id,
                    ContentWordPressDraftExecutionResult(
                        status="created",
                        mode="live",
                        boundary=ContentWordPressDraftExecutionBoundary(
                            live_write_enabled=True,
                            live_adapter_configured=True,
                        ),
                        wordpress_post_id=wordpress_post_id,
                        external_write_attempted=True,
                    ),
                )
            updated = connection.execute(
                """
                UPDATE content_wordpress_revision_apply_claims
                SET status = ?, updated_at = ?
                WHERE claim_key = ? AND status = 'claimed'
                """,
                (outcome, utc_now().isoformat(), claim_key),
            )
            if updated.rowcount != 1:
                raise RuntimeError("WordPress apply claim changed during reconciliation.")
        return AuditEvent.model_validate(redact_mapping(audit.model_dump(mode="json")))


class _ReviewStoreMixin(_StoreConnectionMixin):
    def save_human_review(self, review: ContentHumanReview) -> ContentHumanReview:
        redacted = ContentHumanReview.model_validate(redact_mapping(review.model_dump(mode="json")))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_human_reviews (id, work_item_id, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  work_item_id = excluded.work_item_id,
                  payload_json = excluded.payload_json
                """,
                (
                    redacted.id,
                    redacted.work_item_id,
                    _model_json(redacted),
                ),
            )
        return redacted

    def latest_human_review(self, work_item_id: str) -> ContentHumanReview | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM content_human_reviews
                WHERE work_item_id = ?
                ORDER BY id DESC
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
            connection.execute(
                """
                INSERT INTO content_wordpress_draft_executions (work_item_id, payload_json)
                VALUES (?, ?)
                ON CONFLICT(work_item_id) DO UPDATE SET
                  payload_json = excluded.payload_json
                """,
                (
                    work_item_id,
                    _model_json(redacted),
                ),
            )
        return redacted

    def latest_wordpress_draft_execution(
        self,
        work_item_id: str,
    ) -> ContentWordPressDraftExecutionResult | None:
        with self._connect() as connection:
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


class ContentWorkflowStore(
    _DraftRevisionStoreMixin,
    _WordPressApplyStoreMixin,
    _ReviewStoreMixin,
    MeasurementStoreMixin,
):
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
