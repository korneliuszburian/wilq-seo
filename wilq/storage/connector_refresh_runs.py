"""Atomic SQLite queue operations for connector refresh runs."""

from __future__ import annotations

import json
from datetime import UTC
from typing import cast

from wilq.operator_labels import connector_refresh_status_label
from wilq.schemas import (
    AuditEvent,
    ConnectorRefreshRecoveryRejectionCode,
    ConnectorRefreshRun,
    ConnectorRefreshStatus,
    utc_now,
)
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import LocalStateStore
from wilq.storage.local_state_audit import upsert_audit_event
from wilq.storage.local_state_runs import supports_run_transaction

# This fence is captured by the server process at import time and is never
# accepted from a recovery caller. It separates runs that predate this process
# from runs that this process could still own.
_PROCESS_START_FENCE = utc_now()
_CURRENT_PROCESS_CLAIMS: set[str] = set()


def enqueue_connector_refresh_run(
    store: LocalStateStore,
    run: ConnectorRefreshRun,
) -> ConnectorRefreshRun:
    """Insert one queued run per connector under the SQLite write lock."""
    redacted = _redacted_run(run)
    if redacted.status != ConnectorRefreshStatus.queued:
        raise ValueError("Only queued connector refresh runs can be enqueued")
    payload_json = _run_json(redacted)
    with store.run_transaction() as connection:
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
    with store.run_transaction() as connection:
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
        _CURRENT_PROCESS_CLAIMS.add(redacted.id)
    return redacted


def transition_connector_refresh_run_if_current(
    store: LocalStateStore,
    expected_run: ConnectorRefreshRun,
    replacement_run: ConnectorRefreshRun,
) -> ConnectorRefreshRun | None:
    """Replace a run only when its complete serialized payload is unchanged."""
    expected = _redacted_run(expected_run)
    replacement = _redacted_run(replacement_run)
    transitioned = _transition_connector_refresh_run_if_current(
        store,
        expected,
        replacement,
    )
    if transitioned is None:
        return None
    return transitioned[0]


def recover_running_connector_refresh_run(
    store: LocalStateStore,
    expected_run: ConnectorRefreshRun,
) -> tuple[ConnectorRefreshRun, AuditEvent] | None:
    """Interrupt one orphaned pre-process running run with an atomic audit."""
    expected = _redacted_run(expected_run)
    if not supports_run_transaction(store):
        return None
    if classify_connector_refresh_recovery_rejection(store, expected.id, expected) is not None:
        return None

    completed_at = utc_now()
    recovered = expected.model_copy(
        update={
            "status": ConnectorRefreshStatus.failed,
            "status_label": connector_refresh_status_label(ConnectorRefreshStatus.failed),
            "completed_at": completed_at,
            "metrics_persisted": False,
            "summary": (
                "Odczyt źródła przerwany po utracie procesu. Stan historycznego "
                "wywołania dostawcy jest niezweryfikowany; sama procedura recovery "
                "nie wykonała wywołania dostawcy ani automatycznego ponowienia."
            ),
            "errors": [*expected.errors, "connector_refresh_interrupted_process_loss"],
        }
    )
    audit = AuditEvent(
        id=f"audit_connector_refresh_process_loss_{expected.id}",
        event_type="connector_refresh_process_loss_recovered",
        actor="wilq_server_process",
        trust_level="local_unverified",
        created_at=completed_at,
        summary=(
            "Przerwano osierocony odczyt źródła po utracie procesu. Stan historycznego "
            "wywołania dostawcy jest niezweryfikowany; sama procedura recovery nie "
            "wykonała wywołania dostawcy ani automatycznego ponowienia."
        ),
        evidence_ids=expected.evidence_ids,
        details={
            "run_id": expected.id,
            "connector_id": expected.connector_id,
            "recovery_reason": "process_loss",
            "interrupted_run_vendor_call_state": "unverified",
            "recovery_vendor_call_attempted": False,
            "retry_scheduled": False,
            "human_approval_recorded": False,
        },
    )
    transitioned = _transition_connector_refresh_run_if_current(
        store,
        expected,
        recovered,
        audit=audit,
    )
    if transitioned is None:
        return None
    persisted_audit = transitioned[1]
    if persisted_audit is None:
        return None
    return transitioned[0], persisted_audit


def classify_connector_refresh_recovery_rejection(
    store: LocalStateStore,
    run_id: str,
    expected_run: ConnectorRefreshRun,
) -> ConnectorRefreshRecoveryRejectionCode | None:
    """Classify why a server-owned recovery proof cannot be accepted.

    The classifier only reads state and never changes recovery eligibility. A
    ``None`` result means the exact snapshot is currently eligible; a rejected
    recovery is mapped to a bounded, safe code for the API boundary.
    """
    expected = _redacted_run(expected_run)
    if expected.id != run_id:
        return ConnectorRefreshRecoveryRejectionCode.snapshot_conflict
    if not _is_recoverable_snapshot(expected):
        return ConnectorRefreshRecoveryRejectionCode.snapshot_not_recoverable
    owner_rejection = _current_process_rejection(expected)
    if owner_rejection is not None:
        return owner_rejection
    if not supports_run_transaction(store):
        return ConnectorRefreshRecoveryRejectionCode.snapshot_conflict
    current = store.get_connector_refresh_run(run_id)
    if current is None:
        return ConnectorRefreshRecoveryRejectionCode.snapshot_conflict
    if _run_json(_redacted_run(current)) != _run_json(expected):
        return ConnectorRefreshRecoveryRejectionCode.snapshot_conflict
    return None


def _is_recoverable_snapshot(run: ConnectorRefreshRun) -> bool:
    return (
        run.status == ConnectorRefreshStatus.running
        and run.completed_at is None
        and not run.external_call_attempted
        and not run.vendor_data_collected
        and not run.metrics_persisted
        and not run.metric_summary
    )


def _current_process_rejection(
    run: ConnectorRefreshRun,
) -> ConnectorRefreshRecoveryRejectionCode | None:
    if run.id in _CURRENT_PROCESS_CLAIMS:
        return ConnectorRefreshRecoveryRejectionCode.current_process_claim
    started_at = run.started_at
    if started_at.tzinfo is None or started_at.utcoffset() is None:
        return ConnectorRefreshRecoveryRejectionCode.started_in_current_process
    if started_at.astimezone(UTC) >= _PROCESS_START_FENCE:
        return ConnectorRefreshRecoveryRejectionCode.started_in_current_process
    return None


def _transition_connector_refresh_run_if_current(
    store: LocalStateStore,
    expected: ConnectorRefreshRun,
    replacement: ConnectorRefreshRun,
    *,
    audit: AuditEvent | None = None,
) -> tuple[ConnectorRefreshRun, AuditEvent | None] | None:
    if expected.id != replacement.id or expected.connector_id != replacement.connector_id:
        return None
    expected_payload_json = _run_json(expected)
    replacement_payload_json = _run_json(replacement)
    if not supports_run_transaction(store):
        return None
    with store.run_transaction() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT payload_json FROM connector_refresh_runs
            WHERE id = ? AND connector_id = ? AND status = ?
            """,
            (expected.id, expected.connector_id, expected.status),
        ).fetchone()
        if row is None:
            return None
        current_payload_json = cast(str, row["payload_json"])
        if not _payload_matches_expected(current_payload_json, expected_payload_json):
            return None
        cursor = connection.execute(
            """
            UPDATE connector_refresh_runs
            SET status = ?, updated_at = ?, payload_json = ?
            WHERE id = ? AND connector_id = ? AND status = ? AND payload_json = ?
            """,
            (
                replacement.status,
                (replacement.completed_at or replacement.started_at).isoformat(),
                replacement_payload_json,
                expected.id,
                expected.connector_id,
                expected.status,
                current_payload_json,
            ),
        )
        if cursor.rowcount != 1:
            return None
        persisted_audit = upsert_audit_event(connection, audit) if audit is not None else None
    return replacement, persisted_audit


def _redacted_run(run: ConnectorRefreshRun) -> ConnectorRefreshRun:
    return ConnectorRefreshRun.model_validate(redact_mapping(run.model_dump(mode="json")))


def _payload_matches_expected(payload_json: str, expected_payload_json: str) -> bool:
    try:
        current = _redacted_run(ConnectorRefreshRun.model_validate_json(payload_json))
    except (TypeError, ValueError):
        return False
    return _run_json(current) == expected_payload_json


def _run_json(run: ConnectorRefreshRun) -> str:
    return json.dumps(
        run.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
