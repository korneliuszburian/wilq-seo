from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Literal, cast

from wilq.content.drafts.initial_draft_run import (
    effective_initial_draft_deadline,
    initial_draft_context_digest_for_proposal,
    initial_draft_proposal_context_from_command,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionAppendCommand
from wilq.schemas.actions import CodexRun
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping

CodexCompletionState = Literal["started", "completed"]
_current_initial_draft_context: ContextVar[Callable[[], str] | None] = ContextVar(
    "current_initial_draft_context",
    default=None,
)
_current_editor_draft_context: ContextVar[
    Callable[[], ContentDraftRevisionContext | None] | None
] = ContextVar("current_editor_draft_context", default=None)


@dataclass(frozen=True, slots=True)
class ContentDraftRevisionContext:
    work_item_id: str
    draft_package_id: str
    draft_package_digest: str
    planning_digest: str
    planning_input_digest: str
    service_card_id: str
    inventory_digest: str
    final_canonical_url: str

    @classmethod
    def from_command(
        cls,
        command: ContentDraftRevisionAppendCommand,
    ) -> ContentDraftRevisionContext | None:
        required = (
            command.planning_input_digest,
            command.service_card_id,
            command.inventory_digest,
            command.final_canonical_url,
        )
        if any(value is None for value in required):
            return None
        return cls(
            work_item_id=command.work_item_id,
            draft_package_id=command.draft_package_id,
            draft_package_digest=command.draft_package_digest,
            planning_digest=command.planning_digest,
            planning_input_digest=cast(str, command.planning_input_digest),
            service_card_id=cast(str, command.service_card_id),
            inventory_digest=cast(str, command.inventory_digest),
            final_canonical_url=cast(str, command.final_canonical_url),
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


@contextmanager
def current_editor_draft_context_guard(
    current_context: Callable[[], ContentDraftRevisionContext | None],
) -> Iterator[None]:
    """Bind an editor save to the source context checked during its append."""

    token = _current_editor_draft_context.set(current_context)
    try:
        yield
    finally:
        _current_editor_draft_context.reset(token)


def editor_draft_context_is_current(command: ContentDraftRevisionAppendCommand) -> bool:
    """Check the editor snapshot binding while the append transaction is held."""

    current_context = _current_editor_draft_context.get()
    if current_context is None:
        return True
    expected = ContentDraftRevisionContext.from_command(command)
    return expected is not None and current_context() == expected


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
        if (
            redacted.proposal_id is None
            or redacted.planning_digest != command.planning_digest
            or redacted.planning_input_digest != command.planning_input_digest
        ):
            raise ValueError("Initial draft completion does not match its exact proposal binding.")
        expected_context = initial_draft_context_digest_for_proposal(
            base_revision_id=command.base_revision_id,
            draft_package_id=command.draft_package_id,
            draft_package_digest=command.draft_package_digest,
            final_canonical_url=command.final_canonical_url,
            proposal_context=initial_draft_proposal_context_from_command(
                command,
                proposal_id=redacted.proposal_id,
            ),
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
