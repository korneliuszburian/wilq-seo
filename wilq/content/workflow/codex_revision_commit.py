from __future__ import annotations

import json
import sqlite3
from typing import Literal, cast

from wilq.content.workflow.revisions import ContentDraftRevisionAppendCommand
from wilq.schemas.actions import CodexRun
from wilq.security.redaction import redact_mapping

CodexCompletionState = Literal["started", "completed"]


def prepare_codex_completion(
    command: ContentDraftRevisionAppendCommand,
    completed_run: CodexRun | None,
) -> CodexRun | None:
    metadata = command.proposal_metadata
    if metadata is None:
        if completed_run is not None:
            raise ValueError("Codex completion requires proposal metadata.")
        return None
    if completed_run is None:
        raise ValueError("Codex proposal append requires its completed run.")
    redacted = CodexRun.model_validate(redact_mapping(completed_run.model_dump(mode="json")))
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
    if stored_run == completed_run:
        return "completed"
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
