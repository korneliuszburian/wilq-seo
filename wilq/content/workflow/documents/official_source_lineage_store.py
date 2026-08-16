from __future__ import annotations

from pathlib import Path

from wilq.content.workflow.documents.codex_revision_commit import prepare_codex_completion
from wilq.content.workflow.documents.revision_persistence import (
    build_stored_draft_revision,
    draft_revision_content_digest,
)
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevisionAppendCommand,
    ContentDraftRevisionWriteResult,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.store.store_queries import (
    draft_revision_conflict,
    latest_draft_revision,
    latest_draft_revision_review,
    wordpress_revision_apply_in_progress,
)
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import state_db_path
from wilq.storage.model_json import model_json


class ContentOfficialSourceLineageStore:
    """Own the atomic, lineage-only append precondition outside the legacy store."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append_rebase(
        self,
        command: ContentDraftRevisionAppendCommand,
        *,
        expected_latest_review_decision_id: str | None,
    ) -> ContentDraftRevisionWriteResult:
        if command.correction_reason != "official_source_lineage_rebase":
            raise ValueError("Official-source lineage store accepts only lineage rebase commands.")
        redacted_command = ContentDraftRevisionAppendCommand.model_validate(
            redact_mapping(command.model_dump(mode="json"))
        )
        prepare_codex_completion(redacted_command, None)
        content_digest = draft_revision_content_digest(redacted_command)
        with ContentWorkflowStore(self.path)._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            latest = latest_draft_revision(connection, redacted_command.work_item_id)
            latest_review = (
                None
                if latest is None
                else latest_draft_revision_review(connection, latest.revision_id)
            )
            if (
                None if latest_review is None else latest_review.decision_id
            ) != expected_latest_review_decision_id:
                return ContentDraftRevisionWriteResult(
                    status="conflict",
                    conflict=draft_revision_conflict("stale_review", latest),
                )
            if wordpress_revision_apply_in_progress(connection, redacted_command.work_item_id):
                return ContentDraftRevisionWriteResult(
                    status="conflict",
                    conflict=draft_revision_conflict("apply_in_progress", latest),
                )
            current_revision_id = None if latest is None else latest.revision_id
            if redacted_command.base_revision_id != current_revision_id:
                return ContentDraftRevisionWriteResult(
                    status="conflict",
                    conflict=draft_revision_conflict("stale_base", latest),
                )
            revision = build_stored_draft_revision(
                redacted_command,
                revision_number=1 if latest is None else latest.revision_number + 1,
                content_digest=content_digest,
            )
            connection.execute(
                """
                INSERT INTO content_draft_revisions (
                  revision_id, work_item_id, revision_number, base_revision_id,
                  content_digest, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    revision.revision_id,
                    revision.work_item_id,
                    revision.revision_number,
                    revision.base_revision_id,
                    revision.content_digest,
                    revision.created_at.isoformat(),
                    model_json(revision),
                ),
            )
        return ContentDraftRevisionWriteResult(status="created", revision=revision)


def content_official_source_lineage_store() -> ContentOfficialSourceLineageStore:
    return ContentOfficialSourceLineageStore(state_db_path())


__all__ = ["ContentOfficialSourceLineageStore", "content_official_source_lineage_store"]
