from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Literal, cast

from wilq.content.drafts.initial_draft_run import (
    effective_initial_draft_deadline,
    initial_draft_context_digest,
)
from wilq.content.workflow.revisions import ContentDraftRevisionAppendCommand
from wilq.schemas.actions import CodexRun
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping

CodexCompletionState = Literal["started", "completed"]
_current_initial_draft_context: ContextVar[Callable[[], str] | None] = ContextVar(
    "current_initial_draft_context",
    default=None,
)


@contextmanager
def current_initial_draft_context_guard(
    current_context: Callable[[], str],
) -> Iterator[None]:
    """Bind the source context check to one atomic draft-revision append."""

    token = _current_initial_draft_context.set(current_context)
    try:
        yield
    finally:
        _current_initial_draft_context.reset(token)


def assert_initial_draft_current_context(
    connection: sqlite3.Connection,
    *,
    work_item_id: str,
    run: CodexRun | None,
) -> None:
    """Reject a new initial-draft completion outside the current source context.

    The store invokes this after ``BEGIN IMMEDIATE``. An exact completed replay
    remains idempotent even if the source has advanced in the meantime.
    """

    if run is None or run.hook != "content_initial_full_draft":
        return
    row = connection.execute(
        "SELECT payload_json FROM codex_runs WHERE id = ?", (run.id,)
    ).fetchone()
    if row is not None and CodexRun.model_validate_json(row["payload_json"]) == run:
        return
    current_context = _current_initial_draft_context.get()
    if (
        current_context is not None
        and current_context() != run.initial_draft_context_digest
    ):
        raise ValueError("stale_initial_draft_context")


def prepare_codex_completion(
    command: ContentDraftRevisionAppendCommand,
    completed_run: CodexRun | None,
) -> CodexRun | None:
    metadata = command.proposal_metadata
    if metadata is None:
        if completed_run is not None:
            raise ValueError("Codex completion requires proposal metadata.")
        return None
    if command.correction_reason == "official_source_lineage_rebase":
        if completed_run is not None:
            raise ValueError("Official-source lineage rebase cannot attach a Codex completion.")
        return None
    if completed_run is None:
        raise ValueError("Codex proposal append requires its completed run.")
    redacted = CodexRun.model_validate(redact_mapping(completed_run.model_dump(mode="json")))
    if redacted.hook == "content_initial_full_draft":
        expected_context = initial_draft_context_digest(
            base_revision_id=command.base_revision_id,
            draft_package_id=command.draft_package_id,
            draft_package_digest=command.draft_package_digest,
            final_canonical_url=command.final_canonical_url,
            service_card_id=command.service_card_id,
            proposal_id=redacted.proposal_id or "",
            planning_digest=command.planning_digest,
            planning_input_digest=command.planning_input_digest or "",
        )
        if redacted.initial_draft_context_digest not in {None, expected_context}:
            raise ValueError("Initial draft context changed before append.")
        redacted = redacted.model_copy(update={"initial_draft_context_digest": expected_context})
    if metadata.codex_run_id != redacted.id:
        raise ValueError("Proposal metadata must reference the completed Codex run.")
    if redacted.status != "completed" or redacted.completed_at is None:
        raise ValueError("Codex proposal append requires a completed terminal run.")
    if redacted.error is not None:
        raise ValueError("Completed Codex proposal run cannot carry an error.")
    return redacted


def codex_completion_state(
    connection: sqlite3.Connection,
    completed_run: CodexRun | None,
) -> CodexCompletionState | None:
    if completed_run is None:
        return None
    row = connection.execute(
        "SELECT payload_json FROM codex_runs WHERE id = ?", (completed_run.id,)
    ).fetchone()
    if row is None:
        raise ValueError("Codex proposal run must be persisted as started before append.")
    stored_run = CodexRun.model_validate(json.loads(cast(str, row["payload_json"])))
    if (
        stored_run.hook == "content_initial_full_draft"
        and stored_run.initial_draft_context_digest
        != completed_run.initial_draft_context_digest
    ):
        raise ValueError("initial_draft_context_changed")
    if stored_run == completed_run:
        return "completed"
    if (
        stored_run.hook == "content_initial_full_draft"
        and completed_run.status == "completed"
        and utc_now() >= effective_initial_draft_deadline(stored_run)
    ):
        raise ValueError("initial_draft_deadline_expired")
    expected_started = completed_run.model_copy(
        update={"status": "started", "completed_at": None, "error": None}
    )
    if stored_run != expected_started:
        raise ValueError("Persisted Codex run does not match the proposal completion.")
    return "started"


def persist_codex_completion(
    connection: sqlite3.Connection,
    completed_run: CodexRun | None,
) -> None:
    if completed_run is None:
        return
    payload_json = json.dumps(
        completed_run.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    cursor = connection.execute(
        "UPDATE codex_runs SET started_at = ?, payload_json = ? WHERE id = ?",
        (completed_run.started_at.isoformat(), payload_json, completed_run.id),
    )
    if cursor.rowcount != 1:
        raise RuntimeError("Codex proposal run disappeared during atomic append.")
