from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import cast

from wilq.schemas import CodexRun
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import LocalStateStore


def effective_deadline(run: CodexRun, timeout_seconds: float) -> datetime:
    return run.deadline_at or (run.started_at + timedelta(seconds=timeout_seconds))


def runtime_error(code: str, source_codes: list[str]) -> str:
    source = next((item for item in source_codes if item), None)
    return code if source is None else f"{code}:{source}"


def transition_codex_run_if_status(
    store: LocalStateStore,
    run: CodexRun,
    *,
    expected_status: str = "started",
) -> CodexRun | None:
    """Apply a run transition only while its persisted status is unchanged."""
    redacted = CodexRun.model_validate(redact_mapping(run.model_dump(mode="json")))
    payload_json = json.dumps(
        redacted.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    with store._connect() as connection:
        current = connection.execute(
            "SELECT payload_json FROM codex_runs WHERE id = ?",
            (redacted.id,),
        ).fetchone()
        if current is None:
            return None
        current_run = CodexRun.model_validate_json(cast(str, current["payload_json"]))
        if current_run.status != expected_status:
            return None
        connection.execute(
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
        if connection.total_changes == 0:
            return None
    return redacted
