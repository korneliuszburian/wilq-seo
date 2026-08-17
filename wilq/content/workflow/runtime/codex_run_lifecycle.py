"""The shared lifecycle for persisted Codex turn audit records."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import cast

from wilq.schemas import CodexRun
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import LocalStateStore
from wilq.storage.local_state_runs import supports_run_transaction

LEGACY_SEMANTIC_REVIEW_TIMEOUT_SECONDS = 180.0


def effective_deadline(run: CodexRun) -> datetime:
    return run.deadline_at or (
        run.started_at + timedelta(seconds=LEGACY_SEMANTIC_REVIEW_TIMEOUT_SECONDS)
    )


def runtime_error(code: str, source_codes: list[str]) -> str:
    source = next((item for item in source_codes if item), None)
    return code if source is None else f"{code}:{source}"


def transition_codex_run_if_status(
    store: LocalStateStore,
    run: CodexRun,
    *,
    expected_status: str = "started",
) -> CodexRun | None:
    """Persist a run transition only while its stored status and payload are unchanged."""
    redacted = CodexRun.model_validate(redact_mapping(run.model_dump(mode="json")))
    payload_json = json.dumps(
        redacted.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    with store.run_transaction() as connection:
        current = connection.execute(
            "SELECT payload_json FROM codex_runs WHERE id = ?",
            (redacted.id,),
        ).fetchone()
        if current is None:
            return None
        current_run = CodexRun.model_validate_json(cast(str, current["payload_json"]))
        if current_run.status != expected_status:
            return None
        cursor = connection.execute(
            """
            UPDATE codex_runs
            SET started_at = ?, payload_json = ?
            WHERE id = ? AND payload_json = ?
            """,
            (
                redacted.started_at.isoformat(),
                payload_json,
                redacted.id,
                current["payload_json"],
            ),
        )
        if cursor.rowcount == 0:
            return None
    return redacted


def finish_codex_run(
    store: LocalStateStore,
    run: CodexRun,
    *,
    status: str,
    error: str | None = None,
) -> CodexRun:
    """Terminalize a run through the optimistic transition when available."""
    terminal = terminal_codex_run(run, status=status, error=error)
    if supports_run_transaction(store):
        return transition_codex_run_if_status(store, terminal) or run
    return store.save_codex_run(terminal)


def terminal_codex_run(
    run: CodexRun,
    *,
    status: str,
    error: str | None = None,
) -> CodexRun:
    """Build a terminal run without persisting it."""
    return run.model_copy(update={"status": status, "completed_at": utc_now(), "error": error})


def save_terminal_codex_run(
    store: LocalStateStore,
    run: CodexRun,
    *,
    status: str,
    error: str | None = None,
) -> CodexRun:
    """Persist a terminal run with unconditional upsert semantics."""
    return store.save_codex_run(terminal_codex_run(run, status=status, error=error))

__all__ = [
    "LEGACY_SEMANTIC_REVIEW_TIMEOUT_SECONDS",
    "effective_deadline",
    "finish_codex_run",
    "runtime_error",
    "save_terminal_codex_run",
    "terminal_codex_run",
    "transition_codex_run_if_status",
]
