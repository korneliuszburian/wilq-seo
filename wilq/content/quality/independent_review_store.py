"""Append-only-ish SQLite storage for independent advisory review runs."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from wilq.content.quality.independent_review_contracts import (
    ContentIndependentFindingDispositionRequest,
    ContentIndependentReviewFinding,
    ContentIndependentReviewRun,
)
from wilq.schemas.core import utc_now
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import DEFAULT_STATE_DB, state_db_path
from wilq.storage.private_paths import prepare_private_store_path
from wilq.storage.schema_versions import reject_newer_sqlite_schema


class IndependentReviewStorageActivationRequired(RuntimeError):
    pass


class IndependentReviewConflict(RuntimeError):
    pass


class IndependentReviewNotFound(IndependentReviewConflict):
    pass


@dataclass(frozen=True, slots=True)
class IndependentReviewDispositionResult:
    status: Literal["recorded", "idempotent"]
    run: ContentIndependentReviewRun
    finding: ContentIndependentReviewFinding


class ContentIndependentReviewStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write_ready(self) -> bool:
        if self.path != DEFAULT_STATE_DB:
            return True
        connection = self._read_connection()
        if connection is None:
            return False
        with connection:
            return all(
                _table_exists(connection, table)
                for table in ("content_semantic_reviews", "content_independent_review_runs")
            )

    def for_revision(
        self,
        work_item_id: str,
        revision_id: str,
        revision_digest: str,
    ) -> list[ContentIndependentReviewRun]:
        connection = self._read_connection()
        if connection is None:
            return []
        with connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM content_independent_review_runs
                WHERE work_item_id = ? AND revision_id = ? AND revision_digest = ?
                ORDER BY created_at ASC, run_id ASC
                """,
                (work_item_id, revision_id, revision_digest),
            ).fetchall()
        return [_run_from_row(row) for row in rows]

    def for_run(self, run_id: str) -> ContentIndependentReviewRun | None:
        connection = self._read_connection()
        if connection is None:
            return None
        with connection:
            row = connection.execute(
                "SELECT payload_json FROM content_independent_review_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return None if row is None else _run_from_row(row)

    def save_run(self, run: ContentIndependentReviewRun) -> Literal["created", "idempotent"]:
        safe_run = ContentIndependentReviewRun.model_validate(
            redact_mapping(run.model_dump(mode="json"))
        )
        payload_json = safe_run.model_dump_json()
        with self._write_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT payload_json FROM content_independent_review_runs WHERE run_id = ?",
                (safe_run.run_id,),
            ).fetchone()
            if existing is not None:
                stored = _run_from_row(existing)
                if _same_run_core(stored, safe_run):
                    return "idempotent"
                raise IndependentReviewConflict("Independent review run ID already exists.")
            role_existing = connection.execute(
                """
                SELECT run_id
                FROM content_independent_review_runs
                WHERE work_item_id = ? AND revision_id = ? AND revision_digest = ? AND role = ?
                """,
                (
                    safe_run.work_item_id,
                    safe_run.revision_id,
                    safe_run.revision_digest,
                    safe_run.role,
                ),
            ).fetchone()
            if role_existing is not None:
                raise IndependentReviewConflict(
                    "One exact revision can have only one run per independent role."
                )
            connection.execute(
                """
                INSERT INTO content_independent_review_runs (
                  run_id, work_item_id, revision_id, revision_digest, role,
                  created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    safe_run.run_id,
                    safe_run.work_item_id,
                    safe_run.revision_id,
                    safe_run.revision_digest,
                    safe_run.role,
                    safe_run.created_at.isoformat(),
                    payload_json,
                ),
            )
        return "created"

    def record_disposition(
        self,
        *,
        work_item_id: str,
        revision_id: str,
        run_id: str,
        finding_id: str,
        request: ContentIndependentFindingDispositionRequest,
    ) -> IndependentReviewDispositionResult:
        with self._write_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_independent_review_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                raise IndependentReviewNotFound("Independent review run was not found.")
            run = _run_from_row(row)
            if run.work_item_id != work_item_id or run.revision_id != revision_id:
                raise IndependentReviewConflict("Disposition identity does not match the run.")
            if run.revision_digest != request.expected_revision_digest:
                raise IndependentReviewConflict("Disposition digest does not match the run.")
            finding = next(
                (item for item in run.findings if item.finding_id == finding_id),
                None,
            )
            if finding is None:
                raise IndependentReviewNotFound("Independent review finding was not found.")
            if finding.disposition is not None:
                if _same_disposition(finding, request):
                    return IndependentReviewDispositionResult("idempotent", run, finding)
                raise IndependentReviewConflict("Finding disposition is immutable once recorded.")
            if not set(request.evidence_ids).issubset(set(run.evidence_ids)):
                raise IndependentReviewConflict(
                    "Disposition evidence must belong to the exact run evidence set."
                )
            updated_finding = finding.model_copy(
                update={
                    "disposition": request.disposition,
                    "disposition_reason": request.reason.strip(),
                    "disposition_evidence_ids": list(dict.fromkeys(request.evidence_ids)),
                    "disposed_by": request.disposed_by.strip(),
                    "disposed_at": utc_now(),
                }
            )
            updated_run = run.model_copy(
                update={
                    "findings": [
                        updated_finding if item.finding_id == finding_id else item
                        for item in run.findings
                    ]
                }
            )
            safe_updated_run = ContentIndependentReviewRun.model_validate(
                redact_mapping(updated_run.model_dump(mode="json"))
            )
            connection.execute(
                "UPDATE content_independent_review_runs SET payload_json = ? WHERE run_id = ?",
                (safe_updated_run.model_dump_json(), run_id),
            )
        persisted_finding = next(
            item for item in safe_updated_run.findings if item.finding_id == finding_id
        )
        return IndependentReviewDispositionResult("recorded", safe_updated_run, persisted_finding)

    def _write_connection(self) -> sqlite3.Connection:
        prepare_private_store_path(
            self.path,
            normalize_existing_parent=self.path == DEFAULT_STATE_DB,
        )
        connection = sqlite3.connect(self.path)
        self.path.chmod(0o600)
        connection.row_factory = sqlite3.Row
        reject_newer_sqlite_schema(connection)
        if self.path == DEFAULT_STATE_DB and not all(
            _table_exists(connection, table)
            for table in ("content_semantic_reviews", "content_independent_review_runs")
        ):
            connection.close()
            raise IndependentReviewStorageActivationRequired(
                "Independent-review storage requires an approved maintenance window."
            )
        connection.execute(_CREATE_TABLE)
        return connection

    def _read_connection(self) -> sqlite3.Connection | None:
        if not self.path.exists():
            return None
        connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        reject_newer_sqlite_schema(connection)
        if not _table_exists(connection, "content_independent_review_runs"):
            connection.close()
            return None
        return connection


def _same_disposition(
    finding: ContentIndependentReviewFinding,
    request: ContentIndependentFindingDispositionRequest,
) -> bool:
    safe_request = redact_mapping(
        {
            "reason": request.reason,
            "disposed_by": request.disposed_by,
        }
    )
    return (
        finding.disposition == request.disposition
        and finding.disposition_reason == str(safe_request["reason"]).strip()
        and finding.disposed_by == str(safe_request["disposed_by"]).strip()
        and finding.disposition_evidence_ids == list(dict.fromkeys(request.evidence_ids))
    )


def _same_run_core(
    stored: ContentIndependentReviewRun,
    candidate: ContentIndependentReviewRun,
) -> bool:
    def without_disposition(run: ContentIndependentReviewRun) -> dict[str, object]:
        payload = run.model_dump(mode="json")
        for finding in payload["findings"]:
            for key in (
                "disposition",
                "disposition_reason",
                "disposition_evidence_ids",
                "disposed_by",
                "disposed_at",
            ):
                finding[key] = (
                    None
                    if key
                    in {"disposition", "disposition_reason", "disposed_by", "disposed_at"}
                    else []
                )
        return payload

    return without_disposition(stored) == without_disposition(candidate)


def _run_from_row(row: sqlite3.Row) -> ContentIndependentReviewRun:
    return ContentIndependentReviewRun.model_validate_json(cast(str, row["payload_json"]))


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone()
        is not None
    )


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS content_independent_review_runs (
  run_id TEXT PRIMARY KEY,
  work_item_id TEXT NOT NULL,
  revision_id TEXT NOT NULL,
  revision_digest TEXT NOT NULL,
  role TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  UNIQUE (work_item_id, revision_id, revision_digest, role)
)
"""


def content_independent_review_store() -> ContentIndependentReviewStore:
    return ContentIndependentReviewStore(state_db_path())


__all__ = [
    "ContentIndependentReviewStore",
    "IndependentReviewConflict",
    "IndependentReviewDispositionResult",
    "IndependentReviewNotFound",
    "IndependentReviewStorageActivationRequired",
    "content_independent_review_store",
]
