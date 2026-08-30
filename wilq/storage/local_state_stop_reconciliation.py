from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from wilq.codex.stop_reconciliation import (
    LEGACY_STOP_RECONCILIATION_ERROR,
    STOP_RECONCILIATION_EXPECTED_COUNT,
    StopReconciliationDryRunReceipt,
    StopReconciliationManifest,
    StopReconciliationManifestError,
    StopReconciliationReceipt,
    StopReconciliationSourceRow,
    StopReconciliationStorageError,
    validate_stop_reconciliation_apply_identity,
)
from wilq.schemas import AuditEvent, CodexRun
from wilq.security.redaction import redact_mapping
from wilq.storage.model_json import model_json as _model_json
from wilq.storage.schema_versions import (
    SQLITE_SCHEMA_VERSION,
    ensure_sqlite_schema_version,
    reject_newer_sqlite_schema,
)

_CREATE_RECONCILIATION_BATCHES = """
CREATE TABLE IF NOT EXISTS codex_stop_reconciliation_batches (
  batch_id TEXT PRIMARY KEY,
  manifest_sha256 TEXT NOT NULL UNIQUE,
  expected_count INTEGER NOT NULL CHECK (expected_count = 20),
  created_at TEXT NOT NULL
)
"""

_CREATE_LEGACY_STOP_EVENTS = """
CREATE TABLE IF NOT EXISTS codex_stop_events_legacy (
  batch_id TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  source_id TEXT NOT NULL UNIQUE,
  started_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  copied_at TEXT NOT NULL,
  PRIMARY KEY (batch_id, source_id),
  FOREIGN KEY (batch_id) REFERENCES codex_stop_reconciliation_batches (batch_id)
)
"""


def ensure_stop_reconciliation_schema(connection: sqlite3.Connection) -> None:
    connection.execute(_CREATE_RECONCILIATION_BATCHES)
    connection.execute(_CREATE_LEGACY_STOP_EVENTS)


class SqliteStopReconciliationSource:
    """Read exactly the requested legacy run rows without initializing SQLite schema."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read_stop_reconciliation_rows(
        self,
        run_ids: Sequence[str],
    ) -> list[StopReconciliationSourceRow]:
        return _read_source_rows(self.path, run_ids, source_label="source snapshot")


class _StopReconciliationStoreMixin:
    path: Path

    def plan_stop_reconciliation(
        self,
        *,
        manifest: StopReconciliationManifest,
        batch_id: str,
        backup_path: Path,
        expected_count: int,
        expected_manifest_sha256: str,
    ) -> StopReconciliationDryRunReceipt:
        digest = validate_stop_reconciliation_apply_identity(
            manifest,
            batch_id=batch_id,
            expected_count=expected_count,
            expected_manifest_sha256=expected_manifest_sha256,
        )
        backup_rows = _read_verified_backup_rows(self.path, backup_path, manifest)
        try:
            with closing(_connect_read_only(self.path)) as connection:
                _require_supported_schema_version(connection)
                batch_exists = _validate_existing_batch(
                    connection,
                    manifest=manifest,
                    batch_id=batch_id,
                    manifest_digest=digest,
                    backup_rows=backup_rows,
                    schema_may_be_absent=True,
                )
                winners, already, losses = _classify_manifest_runs(
                    connection,
                    backup_rows=backup_rows,
                    batch_id=batch_id,
                    manifest_digest=digest,
                )
        except StopReconciliationManifestError:
            raise
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise StopReconciliationManifestError(
                "Stop reconciliation source state cannot be read"
            ) from exc
        return StopReconciliationDryRunReceipt(
            status="dry_run_partial" if losses else "dry_run_ready",
            batch_id=batch_id,
            manifest_sha256=digest,
            would_copy_count=0 if batch_exists else len(backup_rows),
            already_copied_count=len(backup_rows) if batch_exists else 0,
            would_reconcile_count=len(winners),
            already_reconciled_count=len(already),
            cas_lost_count=len(losses),
            would_reconcile_run_ids=tuple(winners),
            already_reconciled_run_ids=tuple(already),
            cas_lost_run_ids=tuple(losses),
        )

    def apply_stop_reconciliation(
        self,
        *,
        manifest: StopReconciliationManifest,
        batch_id: str,
        backup_path: Path,
        mutation_authorized: bool,
        expected_count: int,
        expected_manifest_sha256: str,
    ) -> StopReconciliationReceipt:
        digest = validate_stop_reconciliation_apply_identity(
            manifest,
            batch_id=batch_id,
            expected_count=expected_count,
            expected_manifest_sha256=expected_manifest_sha256,
        )
        if mutation_authorized is not True:
            raise StopReconciliationManifestError(
                "Stop reconciliation requires explicit mutation authorization"
            )
        backup_rows = _read_verified_backup_rows(self.path, backup_path, manifest)
        try:
            connection = _connect_reconciliation_target(self.path)
        except StopReconciliationManifestError:
            raise
        except (OSError, RuntimeError, sqlite3.Error, ValueError) as exc:
            raise StopReconciliationStorageError(
                "Stop reconciliation storage operation did not start",
                rollback_result="not_started",
            ) from exc
        with closing(connection):
            return _apply_transaction(
                connection,
                manifest=manifest,
                batch_id=batch_id,
                manifest_digest=digest,
                backup_rows=backup_rows,
            )


def _apply_transaction(
    connection: sqlite3.Connection,
    *,
    manifest: StopReconciliationManifest,
    batch_id: str,
    manifest_digest: str,
    backup_rows: list[StopReconciliationSourceRow],
) -> StopReconciliationReceipt:
    transaction_started = False
    try:
        connection.execute("BEGIN IMMEDIATE")
        transaction_started = True
        ensure_stop_reconciliation_schema(connection)
        ensure_sqlite_schema_version(connection)
        batch_exists = _validate_existing_batch(
            connection,
            manifest=manifest,
            batch_id=batch_id,
            manifest_digest=manifest_digest,
            backup_rows=backup_rows,
            schema_may_be_absent=False,
        )
        if not batch_exists:
            _insert_batch_and_legacy_rows(
                connection,
                batch_id=batch_id,
                manifest_digest=manifest_digest,
                backup_rows=backup_rows,
            )
        reconciled, already, losses = _reconcile_manifest_runs(
            connection,
            backup_rows=backup_rows,
            batch_id=batch_id,
            manifest_digest=manifest_digest,
        )
        connection.commit()
    except StopReconciliationManifestError as exc:
        if transaction_started:
            connection.rollback()
        raise StopReconciliationManifestError(
            str(exc),
            rollback_result="rolled_back" if transaction_started else "not_started",
        ) from exc
    except (OSError, sqlite3.Error, ValueError) as exc:
        if transaction_started:
            connection.rollback()
        raise StopReconciliationStorageError(
            "Stop reconciliation storage operation failed",
            rollback_result="rolled_back" if transaction_started else "not_started",
        ) from exc
    return StopReconciliationReceipt(
        status="partial" if losses else "applied",
        batch_id=batch_id,
        manifest_sha256=manifest_digest,
        copied_count=0 if batch_exists else len(backup_rows),
        already_copied_count=len(backup_rows) if batch_exists else 0,
        reconciled_count=len(reconciled),
        already_reconciled_count=len(already),
        cas_lost_count=len(losses),
        reconciled_run_ids=tuple(reconciled),
        already_reconciled_run_ids=tuple(already),
        cas_lost_run_ids=tuple(losses),
    )


def _connect_reconciliation_target(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise StopReconciliationManifestError("Stop reconciliation source state is required")
    connection = sqlite3.connect(path)
    try:
        connection.row_factory = sqlite3.Row
        reject_newer_sqlite_schema(connection)
        _require_supported_schema_version(connection)
        return connection
    except Exception:
        connection.close()
        raise


def _read_verified_backup_rows(
    state_path: Path,
    backup_path: Path,
    manifest: StopReconciliationManifest,
) -> list[StopReconciliationSourceRow]:
    _require_distinct_snapshot(state_path, backup_path)
    rows = _read_source_rows(backup_path, manifest.run_ids, source_label="verified backup")
    rows_by_id = {row.run_id: row for row in rows}
    if len(rows_by_id) != len(rows) or set(rows_by_id) != set(manifest.run_ids):
        raise StopReconciliationManifestError("Verified backup does not match manifest IDs")
    verified: list[StopReconciliationSourceRow] = []
    for run_id in manifest.run_ids:
        row = rows_by_id[run_id]
        if row.payload_sha256 != manifest.payload_digests[run_id]:
            raise StopReconciliationManifestError("Verified backup payload digest differs")
        if row.started_at != manifest.started_at[run_id]:
            raise StopReconciliationManifestError("Verified backup timestamp differs")
        if row.status != "started":
            raise StopReconciliationManifestError("Verified backup run is not started")
        verified.append(row)
    return verified


def _require_supported_schema_version(connection: sqlite3.Connection) -> None:
    row = connection.execute("PRAGMA user_version").fetchone()
    schema_version = int(row[0]) if row is not None else 0
    if schema_version not in {6, 7, SQLITE_SCHEMA_VERSION}:
        raise StopReconciliationManifestError(
            "Stop reconciliation apply requires SQLite schema version 6, 7 or 8"
        )


def _require_distinct_snapshot(state_path: Path, backup_path: Path) -> None:
    if not state_path.is_file():
        raise StopReconciliationManifestError("Stop reconciliation source state is required")
    if not backup_path.is_file():
        raise StopReconciliationManifestError("Verified backup is required")
    try:
        same_file = state_path.samefile(backup_path)
    except OSError as exc:
        raise StopReconciliationManifestError("Verified backup cannot be inspected") from exc
    if same_file:
        raise StopReconciliationManifestError("Verified backup must be a distinct SQLite snapshot")


def _read_source_rows(
    path: Path,
    run_ids: Sequence[str],
    *,
    source_label: str,
) -> list[StopReconciliationSourceRow]:
    if not run_ids or len(set(run_ids)) != len(run_ids):
        raise StopReconciliationManifestError(
            "Stop reconciliation IDs must be non-empty and unique"
        )
    placeholders = ", ".join("?" for _ in run_ids)
    try:
        with closing(_connect_read_only(path)) as connection:
            rows = connection.execute(
                f"""
                SELECT id, started_at, payload_json
                FROM codex_runs
                WHERE id IN ({placeholders})
                """,  # nosec B608 -- placeholders are generated only from a bounded ID count.
                tuple(run_ids),
            ).fetchall()
        return [_source_row(row) for row in rows]
    except StopReconciliationManifestError:
        raise
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise StopReconciliationManifestError(
            f"Stop reconciliation {source_label} cannot be read"
        ) from exc


def _connect_read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise StopReconciliationManifestError("Stop reconciliation SQLite source is missing")
    uri = f"{path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _source_row(row: sqlite3.Row) -> StopReconciliationSourceRow:
    run_id = cast(str, row["id"])
    started_at = cast(str, row["started_at"])
    payload_json = cast(str, row["payload_json"])
    run = CodexRun.model_validate_json(payload_json)
    if run.id != run_id:
        raise StopReconciliationManifestError("Stop reconciliation source run ID differs")
    try:
        persisted_started_at = datetime.fromisoformat(started_at)
    except ValueError as exc:
        raise StopReconciliationManifestError(
            "Stop reconciliation source timestamp is invalid"
        ) from exc
    if (
        persisted_started_at.tzinfo is None
        or persisted_started_at.utcoffset() is None
        or run.started_at != persisted_started_at
    ):
        raise StopReconciliationManifestError(
            "Stop reconciliation source timestamp differs from its payload"
        )
    return StopReconciliationSourceRow(
        run_id=run_id,
        started_at=started_at,
        status=run.status,
        payload_json=payload_json,
        payload_sha256=hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
    )


def _validate_existing_batch(
    connection: sqlite3.Connection,
    *,
    manifest: StopReconciliationManifest,
    batch_id: str,
    manifest_digest: str,
    backup_rows: list[StopReconciliationSourceRow],
    schema_may_be_absent: bool,
) -> bool:
    tables_exist = _reconciliation_tables_exist(connection)
    if not tables_exist:
        if schema_may_be_absent:
            return False
        raise StopReconciliationManifestError("Stop reconciliation schema is unavailable")
    _reject_cross_batch_aliases(
        connection,
        batch_id=batch_id,
        manifest_digest=manifest_digest,
        source_ids=manifest.run_ids,
    )
    header = connection.execute(
        """
        SELECT manifest_sha256, expected_count
        FROM codex_stop_reconciliation_batches
        WHERE batch_id = ?
        """,
        (batch_id,),
    ).fetchone()
    legacy_rows = connection.execute(
        """
        SELECT manifest_sha256, source_id, started_at, payload_json, payload_sha256
        FROM codex_stop_events_legacy
        WHERE batch_id = ?
        ORDER BY source_id
        """,
        (batch_id,),
    ).fetchall()
    if header is None:
        if legacy_rows:
            raise StopReconciliationManifestError("Legacy batch rows have no batch identity")
        return False
    if tuple(header) != (manifest_digest, manifest.expected_count):
        raise StopReconciliationManifestError("Batch identity differs from the manifest")
    expected_by_id = {row.run_id: row for row in backup_rows}
    if {cast(str, row["source_id"]) for row in legacy_rows} != set(expected_by_id):
        raise StopReconciliationManifestError("Existing legacy batch is not exact")
    for legacy in legacy_rows:
        source = expected_by_id[cast(str, legacy["source_id"])]
        if tuple(legacy) != (
            manifest_digest,
            source.run_id,
            source.started_at,
            source.payload_json,
            source.payload_sha256,
        ):
            raise StopReconciliationManifestError(
                "Existing legacy batch row differs from the manifest"
            )
    return True


def _reject_cross_batch_aliases(
    connection: sqlite3.Connection,
    *,
    batch_id: str,
    manifest_digest: str,
    source_ids: Sequence[str],
) -> None:
    digest_owner = connection.execute(
        """
        SELECT batch_id FROM codex_stop_reconciliation_batches
        WHERE manifest_sha256 = ? AND batch_id <> ?
        """,
        (manifest_digest, batch_id),
    ).fetchone()
    if digest_owner is not None:
        raise StopReconciliationManifestError(
            "Manifest digest is already bound to another reconciliation batch"
        )
    placeholders = ", ".join("?" for _ in source_ids)
    source_owner = connection.execute(
        f"""
        SELECT source_id FROM codex_stop_events_legacy
        WHERE source_id IN ({placeholders}) AND batch_id <> ?
        LIMIT 1
        """,  # nosec B608 -- placeholders come from the exact bounded manifest count.
        (*source_ids, batch_id),
    ).fetchone()
    if source_owner is not None:
        raise StopReconciliationManifestError(
            "Manifest source ID is already bound to another reconciliation batch"
        )


def _reconciliation_tables_exist(connection: sqlite3.Connection) -> bool:
    rows = connection.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name IN (?, ?)
        """,
        ("codex_stop_reconciliation_batches", "codex_stop_events_legacy"),
    ).fetchall()
    names = {cast(str, row["name"]) for row in rows}
    expected = {
        "codex_stop_reconciliation_batches",
        "codex_stop_events_legacy",
    }
    if names and names != expected:
        raise StopReconciliationManifestError(
            "Stop reconciliation schema is only partially available"
        )
    return names == expected


def _insert_batch_and_legacy_rows(
    connection: sqlite3.Connection,
    *,
    batch_id: str,
    manifest_digest: str,
    backup_rows: list[StopReconciliationSourceRow],
) -> None:
    copied_at = datetime.now(UTC).isoformat()
    connection.execute(
        """
        INSERT INTO codex_stop_reconciliation_batches (
          batch_id, manifest_sha256, expected_count, created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (batch_id, manifest_digest, STOP_RECONCILIATION_EXPECTED_COUNT, copied_at),
    )
    connection.executemany(
        """
        INSERT INTO codex_stop_events_legacy (
          batch_id, manifest_sha256, source_id, started_at,
          payload_json, payload_sha256, copied_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                batch_id,
                manifest_digest,
                row.run_id,
                row.started_at,
                row.payload_json,
                row.payload_sha256,
                copied_at,
            )
            for row in backup_rows
        ],
    )


def _classify_manifest_runs(
    connection: sqlite3.Connection,
    *,
    backup_rows: list[StopReconciliationSourceRow],
    batch_id: str,
    manifest_digest: str,
) -> tuple[list[str], list[str], list[str]]:
    winners: list[str] = []
    already: list[str] = []
    losses: list[str] = []
    for row in backup_rows:
        state = _classify_run(
            connection,
            row=row,
            batch_id=batch_id,
            manifest_digest=manifest_digest,
        )
        {"winner": winners, "already": already, "lost": losses}[state].append(row.run_id)
    return winners, already, losses


def _reconcile_manifest_runs(
    connection: sqlite3.Connection,
    *,
    backup_rows: list[StopReconciliationSourceRow],
    batch_id: str,
    manifest_digest: str,
) -> tuple[list[str], list[str], list[str]]:
    reconciled: list[str] = []
    already: list[str] = []
    losses: list[str] = []
    for row in backup_rows:
        state = _classify_run(
            connection,
            row=row,
            batch_id=batch_id,
            manifest_digest=manifest_digest,
        )
        if state == "already":
            already.append(row.run_id)
            continue
        if state == "lost":
            losses.append(row.run_id)
            continue
        updated = connection.execute(
            """
            UPDATE codex_runs
            SET payload_json = ?
            WHERE id = ? AND started_at = ? AND payload_json = ?
            """,
            (
                _reconciled_payload(row.payload_json),
                row.run_id,
                row.started_at,
                row.payload_json,
            ),
        )
        if updated.rowcount != 1:
            losses.append(row.run_id)
            continue
        _insert_reconciliation_audit(
            connection,
            batch_id=batch_id,
            run_id=row.run_id,
            manifest_digest=manifest_digest,
        )
        reconciled.append(row.run_id)
    return reconciled, already, losses


def _classify_run(
    connection: sqlite3.Connection,
    *,
    row: StopReconciliationSourceRow,
    batch_id: str,
    manifest_digest: str,
) -> Literal["winner", "already", "lost"]:
    current = connection.execute(
        "SELECT started_at, payload_json FROM codex_runs WHERE id = ?",
        (row.run_id,),
    ).fetchone()
    if current is None:
        return "lost"
    current_started_at = cast(str, current["started_at"])
    current_payload = cast(str, current["payload_json"])
    if _already_reconciled(
        connection,
        batch_id=batch_id,
        row=row,
        manifest_digest=manifest_digest,
        current_started_at=current_started_at,
        current_payload=current_payload,
    ):
        return "already"
    if current_started_at != row.started_at or current_payload != row.payload_json:
        return "lost"
    current_run = CodexRun.model_validate_json(current_payload)
    return "winner" if current_run.status == "started" else "lost"


def _reconciled_payload(payload_json: str) -> str:
    payload = json.loads(payload_json)
    if not isinstance(payload, dict):
        raise ValueError("Codex run payload must be an object")
    CodexRun.model_validate(payload)
    reconciled = dict(payload)
    reconciled["status"] = "failed"
    reconciled["error"] = LEGACY_STOP_RECONCILIATION_ERROR
    CodexRun.model_validate(reconciled)
    return _model_json(reconciled)


def _insert_reconciliation_audit(
    connection: sqlite3.Connection,
    *,
    batch_id: str,
    run_id: str,
    manifest_digest: str,
) -> None:
    audit = AuditEvent(
        id=_audit_id(batch_id, run_id),
        event_type="codex_stop_reconciled",
        event_type_label="Rozliczono przerwany run Codexa",
        actor="s5_reconciliation",
        created_at=datetime.now(UTC),
        summary="Zakończono przerwany run Codexa przed terminalnym commitem.",
        details={
            "batch_id": batch_id,
            "manifest_digest": manifest_digest,
            "run_id": run_id,
        },
    )
    redacted = AuditEvent.model_validate(redact_mapping(audit.model_dump(mode="json")))
    connection.execute(
        """
        INSERT INTO audit_events (id, action_id, created_at, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (redacted.id, redacted.action_id, redacted.created_at.isoformat(), _model_json(redacted)),
    )


def _already_reconciled(
    connection: sqlite3.Connection,
    *,
    batch_id: str,
    row: StopReconciliationSourceRow,
    manifest_digest: str,
    current_started_at: str,
    current_payload: str,
) -> bool:
    if current_started_at != row.started_at:
        return False
    try:
        if json.loads(current_payload) != json.loads(_reconciled_payload(row.payload_json)):
            return False
    except (TypeError, ValueError):
        return False
    audit_row = connection.execute(
        "SELECT payload_json FROM audit_events WHERE id = ?",
        (_audit_id(batch_id, row.run_id),),
    ).fetchone()
    if audit_row is None:
        return False
    try:
        audit = AuditEvent.model_validate_json(cast(str, audit_row["payload_json"]))
    except ValueError:
        return False
    return bool(
        audit.event_type == "codex_stop_reconciled"
        and audit.details.get("batch_id") == batch_id
        and audit.details.get("run_id") == row.run_id
        and audit.details.get("manifest_digest") == manifest_digest
    )


def _audit_id(batch_id: str, run_id: str) -> str:
    identity = f"{batch_id}\0{run_id}".encode()
    identity_digest = hashlib.sha256(identity).hexdigest()
    return f"audit_codex_stop_reconciled_{identity_digest}"


__all__ = [
    "SqliteStopReconciliationSource",
    "_StopReconciliationStoreMixin",
    "ensure_stop_reconciliation_schema",
]
