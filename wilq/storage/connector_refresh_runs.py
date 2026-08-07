"""Atomic SQLite queue operations for connector refresh runs."""

from __future__ import annotations

import json
from typing import cast

from wilq.schemas import ConnectorRefreshRun, ConnectorRefreshStatus
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import LocalStateStore


def enqueue_connector_refresh_run(
    store: LocalStateStore,
    run: ConnectorRefreshRun,
) -> ConnectorRefreshRun:
    """Insert one queued run per connector under the SQLite write lock."""
    redacted = _redacted_run(run)
    if redacted.status != ConnectorRefreshStatus.queued:
        raise ValueError("Only queued connector refresh runs can be enqueued")
    payload_json = _run_json(redacted)
    with store._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT payload_json FROM connector_refresh_runs
            WHERE connector_id = ? AND status IN ('queued', 'running')
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
            (redacted.connector_id,),
        ).fetchone()
        if row is not None:
            return ConnectorRefreshRun.model_validate_json(cast(str, row["payload_json"]))
        connection.execute(
            """
            INSERT INTO connector_refresh_runs (
              id, connector_id, status, updated_at, payload_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                redacted.id,
                redacted.connector_id,
                redacted.status,
                redacted.started_at.isoformat(),
                payload_json,
            ),
        )
    return redacted


def claim_queued_connector_refresh_run(
    store: LocalStateStore,
    run: ConnectorRefreshRun,
) -> ConnectorRefreshRun | None:
    """Atomically move a queued run to running for exactly one worker."""
    redacted = _redacted_run(run)
    if redacted.status != ConnectorRefreshStatus.running:
        raise ValueError("A connector refresh claim must transition to running")
    payload_json = _run_json(redacted)
    updated_at = redacted.completed_at or redacted.started_at
    with store._connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """
            UPDATE connector_refresh_runs
            SET status = ?, updated_at = ?, payload_json = ?
            WHERE id = ? AND connector_id = ? AND status = 'queued'
            """,
            (
                redacted.status,
                updated_at.isoformat(),
                payload_json,
                redacted.id,
                redacted.connector_id,
            ),
        )
        if cursor.rowcount != 1:
            return None
    return redacted


def _redacted_run(run: ConnectorRefreshRun) -> ConnectorRefreshRun:
    return ConnectorRefreshRun.model_validate(redact_mapping(run.model_dump(mode="json")))


def _run_json(run: ConnectorRefreshRun) -> str:
    return json.dumps(run.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
