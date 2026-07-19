from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from wilq.content.planning.generated_proposal_contracts import (
    ContentPlanningProposalResponse,
)
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.schemas import CodexRun
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import DEFAULT_STATE_DB, state_db_path
from wilq.storage.private_paths import prepare_private_store_path
from wilq.storage.schema_versions import (
    ensure_sqlite_schema_version,
    reject_newer_sqlite_schema,
)

# Keep the recovery window longer than the bounded Codex planning turn
# (currently 180s) so a slow but still-valid worker cannot be replaced while
# it is running. The grace is deliberately explicit and remains below a
# normal operator retry horizon.
_PLANNING_JOB_STALE_AFTER_SECONDS = 240


def content_planning_proposal_store() -> ContentPlanningProposalStore:
    return ContentPlanningProposalStore(state_db_path())


class ContentPlanningProposalStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def latest(
        self,
        work_item_id: str,
        service_card_id: str | None = None,
    ) -> ContentPlanningProposal | None:
        connection = self._read_connection()
        if connection is None:
            return None
        try:
            with connection:
                if not _table_exists(connection, "content_planning_proposals"):
                    return None
                if service_card_id is None:
                    row = connection.execute(
                        """
                        SELECT payload_json
                        FROM content_planning_proposals
                        WHERE work_item_id = ?
                        ORDER BY proposal_version DESC
                        LIMIT 1
                        """,
                        (work_item_id,),
                    ).fetchone()
                else:
                    row = connection.execute(
                        """
                        SELECT payload_json
                        FROM content_planning_proposals
                        WHERE work_item_id = ? AND service_card_id = ?
                        ORDER BY proposal_version DESC
                        LIMIT 1
                        """,
                        (work_item_id, service_card_id),
                    ).fetchone()
        finally:
            connection.close()
        return _proposal_from_row(row)

    def for_input(
        self,
        work_item_id: str,
        service_card_id: str,
        planning_input_digest: str,
    ) -> ContentPlanningProposal | None:
        connection = self._read_connection()
        if connection is None:
            return None
        try:
            with connection:
                if not _table_exists(connection, "content_planning_proposals"):
                    return None
                row = _proposal_row_for_input(
                    connection,
                    work_item_id,
                    service_card_id,
                    planning_input_digest,
                )
        finally:
            connection.close()
        return _proposal_from_row(row)

    def latest_for_planning_digest(
        self,
        work_item_id: str,
        planning_digest: str,
    ) -> ContentPlanningProposal | None:
        """Read the newest proposal bound to an approved planning workspace."""
        connection = self._read_connection()
        if connection is None:
            return None
        try:
            with connection:
                if not _table_exists(connection, "content_planning_proposals"):
                    return None
                row = connection.execute(
                    """
                    SELECT payload_json
                    FROM content_planning_proposals
                    WHERE work_item_id = ?
                      AND json_extract(payload_json, '$.planning_digest') = ?
                    ORDER BY proposal_version DESC
                    LIMIT 1
                    """,
                    (work_item_id, planning_digest),
                ).fetchone()
        finally:
            connection.close()
        return _proposal_from_row(row)

    def queued_response(
        self,
        work_item_id: str,
        service_card_id: str,
        planning_input_digest: str,
    ) -> ContentPlanningProposalResponse | None:
        """Return the durable in-flight/failed response for an exact input."""
        connection = self._read_connection()
        if connection is None or not _table_exists(connection, "content_planning_generation_jobs"):
            return None
        try:
            with connection:
                row = connection.execute(
                    """
                    SELECT payload_json, status, updated_at
                    FROM content_planning_generation_jobs
                    WHERE work_item_id = ? AND service_card_id = ? AND planning_input_digest = ?
                    LIMIT 1
                    """,
                    (work_item_id, service_card_id, planning_input_digest),
                ).fetchone()
        finally:
            connection.close()
        if row is None or row["status"] not in {"queued", "failed"}:
            return None
        response = ContentPlanningProposalResponse.model_validate(json.loads(row["payload_json"]))
        if row["status"] == "queued" and _job_is_stale(row["updated_at"]):
            # Let the API rebuild the current planning input. The queued
            # payload intentionally has no input summary, so projecting it as
            # a terminal failure would hide the exact digest needed for retry.
            return None
        return response

    def latest_generation_response(
        self,
        work_item_id: str,
    ) -> ContentPlanningProposalResponse | None:
        """Read the newest queued/failed job without rebuilding a snapshot."""
        connection = self._read_connection()
        if connection is None or not _table_exists(connection, "content_planning_generation_jobs"):
            return None
        try:
            with connection:
                row = connection.execute(
                    """
                    SELECT payload_json, status, updated_at
                    FROM content_planning_generation_jobs
                    WHERE work_item_id = ? AND status IN ('queued', 'failed')
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (work_item_id,),
                ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        response = ContentPlanningProposalResponse.model_validate(json.loads(row["payload_json"]))
        if row["status"] == "queued" and _job_is_stale(row["updated_at"]):
            # A stale queue entry is not a terminal model failure. Returning
            # None lets the read route rebuild the exact current input and
            # expose a retryable `not_generated`/`stale` response.
            return None
        return response

    def enqueue(
        self,
        response: ContentPlanningProposalResponse,
    ) -> Literal["queued", "existing"]:
        if response.planning_input_digest is None or response.service_card_id is None:
            raise ValueError("Queued planning requires an exact service and input digest.")
        payload = redact_mapping(response.model_dump(mode="json"))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT status, updated_at FROM content_planning_generation_jobs
                WHERE work_item_id = ? AND service_card_id = ? AND planning_input_digest = ?
                LIMIT 1
                """,
                (response.work_item_id, response.service_card_id, response.planning_input_digest),
            ).fetchone()
            if (
                row is not None
                and row["status"] == "queued"
                and not _job_is_stale(row["updated_at"])
            ):
                return "existing"
            connection.execute(
                """
                INSERT INTO content_planning_generation_jobs (
                  work_item_id, service_card_id, planning_input_digest, status,
                  payload_json, updated_at
                ) VALUES (?, ?, ?, 'queued', ?, CURRENT_TIMESTAMP)
                ON CONFLICT(work_item_id, service_card_id, planning_input_digest)
                DO UPDATE SET status = 'queued', payload_json = excluded.payload_json,
                              updated_at = excluded.updated_at
                """,
                (
                    response.work_item_id,
                    response.service_card_id,
                    response.planning_input_digest,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                ),
            )
        return "queued"

    def enqueue_pending(
        self,
        *,
        work_item_id: str,
        service_card_id: str,
        planning_input_digest: str,
        response: ContentPlanningProposalResponse,
    ) -> Literal["queued", "existing"]:
        """Persist a request before the expensive snapshot is built."""
        payload = redact_mapping(response.model_dump(mode="json"))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT status, updated_at FROM content_planning_generation_jobs
                WHERE work_item_id = ? AND service_card_id = ? AND planning_input_digest = ?
                LIMIT 1
                """,
                (work_item_id, service_card_id, planning_input_digest),
            ).fetchone()
            if (
                row is not None
                and row["status"] == "queued"
                and not _job_is_stale(row["updated_at"])
            ):
                return "existing"
            connection.execute(
                """
                INSERT INTO content_planning_generation_jobs (
                  work_item_id, service_card_id, planning_input_digest, status,
                  payload_json, updated_at
                ) VALUES (?, ?, ?, 'queued', ?, CURRENT_TIMESTAMP)
                ON CONFLICT(work_item_id, service_card_id, planning_input_digest)
                DO UPDATE SET status = 'queued', payload_json = excluded.payload_json,
                              updated_at = excluded.updated_at
                """,
                (
                    work_item_id,
                    service_card_id,
                    planning_input_digest,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                ),
            )
        return "queued"

    def save_terminal_response(self, response: ContentPlanningProposalResponse) -> None:
        if response.service_card_id is None:
            return
        payload = redact_mapping(response.model_dump(mode="json"))
        status = "failed" if response.status in {"failed", "blocked", "stale"} else "finished"
        with self._connect() as connection:
            if response.planning_input_digest is None:
                connection.execute(
                    """
                    UPDATE content_planning_generation_jobs
                    SET status = ?, payload_json = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE work_item_id = ? AND service_card_id = ? AND status = 'queued'
                    """,
                    (
                        status,
                        json.dumps(payload, ensure_ascii=False, sort_keys=True),
                        response.work_item_id,
                        response.service_card_id,
                    ),
                )
            else:
                connection.execute(
                    """
                    UPDATE content_planning_generation_jobs
                    SET status = ?, payload_json = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE work_item_id = ? AND service_card_id = ? AND planning_input_digest = ?
                    """,
                    (
                        status,
                        json.dumps(payload, ensure_ascii=False, sort_keys=True),
                        response.work_item_id,
                        response.service_card_id,
                        response.planning_input_digest,
                    ),
                )

    def save_generated(
        self,
        proposal: ContentPlanningProposal,
        completed_run: CodexRun,
    ) -> tuple[Literal["created", "idempotent"], ContentPlanningProposal]:
        _validate_generated_proposal(proposal, completed_run)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_row = _proposal_row_for_input(
                connection,
                proposal.work_item_id,
                str(proposal.service_card_id),
                str(proposal.planning_input_digest),
            )
            if existing_row is not None:
                existing = _proposal_from_row(existing_row)
                if existing is None:
                    raise RuntimeError("Planning proposal row disappeared during save.")
                return "idempotent", existing
            row = connection.execute(
                """
                SELECT COALESCE(MAX(proposal_version), 0) AS latest_version
                FROM content_planning_proposals
                WHERE work_item_id = ?
                """,
                (proposal.work_item_id,),
            ).fetchone()
            version = 1 if row is None else int(row["latest_version"]) + 1
            versioned = proposal.model_copy(update={"proposal_version": version})
            safe_proposal = ContentPlanningProposal.model_validate(
                redact_mapping(versioned.model_dump(mode="json"))
            )
            safe_run = CodexRun.model_validate(
                redact_mapping(completed_run.model_dump(mode="json"))
            )
            created_at = safe_proposal.created_at or safe_run.completed_at
            if created_at is None:
                raise RuntimeError("Generated planning proposal is missing created_at.")
            connection.execute(
                """
                INSERT INTO codex_runs (id, started_at, payload_json)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  started_at = excluded.started_at,
                  payload_json = excluded.payload_json
                """,
                (
                    safe_run.id,
                    safe_run.started_at.isoformat(),
                    safe_run.model_dump_json(),
                ),
            )
            connection.execute(
                """
                INSERT INTO content_planning_proposals (
                  proposal_id, work_item_id, proposal_version, service_card_id,
                  planning_input_digest, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    safe_proposal.proposal_id,
                    safe_proposal.work_item_id,
                    safe_proposal.proposal_version,
                    safe_proposal.service_card_id,
                    safe_proposal.planning_input_digest,
                    created_at.isoformat(),
                    safe_proposal.model_dump_json(),
                ),
            )
        return "created", safe_proposal

    def _connect(self) -> sqlite3.Connection:
        prepare_private_store_path(
            self.path,
            normalize_existing_parent=self.path == DEFAULT_STATE_DB,
        )
        connection = sqlite3.connect(self.path)
        self.path.chmod(0o600)
        connection.row_factory = sqlite3.Row
        reject_newer_sqlite_schema(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_planning_proposals (
              proposal_id TEXT PRIMARY KEY,
              work_item_id TEXT NOT NULL,
              proposal_version INTEGER NOT NULL CHECK (proposal_version >= 1),
              service_card_id TEXT NOT NULL,
              planning_input_digest TEXT NOT NULL,
              created_at TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              UNIQUE (work_item_id, proposal_version),
              UNIQUE (work_item_id, service_card_id, planning_input_digest)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS codex_runs (
              id TEXT PRIMARY KEY,
              started_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_planning_generation_jobs (
              work_item_id TEXT NOT NULL,
              service_card_id TEXT NOT NULL,
              planning_input_digest TEXT NOT NULL,
              status TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY (work_item_id, service_card_id, planning_input_digest)
            )
            """
        )
        ensure_sqlite_schema_version(connection)
        return connection

    def _read_connection(self) -> sqlite3.Connection | None:
        if not self.path.exists():
            return None
        connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        reject_newer_sqlite_schema(connection)
        return connection


def _proposal_row_for_input(
    connection: sqlite3.Connection,
    work_item_id: str,
    service_card_id: str,
    planning_input_digest: str,
) -> sqlite3.Row | None:
    row = connection.execute(
        """
        SELECT payload_json
        FROM content_planning_proposals
        WHERE work_item_id = ?
          AND service_card_id = ?
          AND planning_input_digest = ?
        LIMIT 1
        """,
        (work_item_id, service_card_id, planning_input_digest),
    ).fetchone()
    return cast(sqlite3.Row | None, row)


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def _job_is_stale(updated_at: str) -> bool:
    try:
        timestamp = datetime.fromisoformat(updated_at).replace(tzinfo=UTC)
    except ValueError:
        return True
    # The planner has a 60-second Codex deadline. Keep only a short grace
    # window so an orphaned worker cannot leave the marketer in `generating`
    # for the old 15-minute interval before a retry becomes possible.
    return (
        datetime.now(UTC) - timestamp
    ).total_seconds() > _PLANNING_JOB_STALE_AFTER_SECONDS


def _proposal_from_row(row: sqlite3.Row | None) -> ContentPlanningProposal | None:
    if row is None:
        return None
    return ContentPlanningProposal.model_validate(json.loads(cast(str, row["payload_json"])))


def _validate_generated_proposal(
    proposal: ContentPlanningProposal,
    completed_run: CodexRun,
) -> None:
    if any(
        value is None
        for value in (
            proposal.proposal_id,
            proposal.codex_run_id,
            proposal.planning_input_digest,
            proposal.created_at,
            proposal.service_card_id,
            completed_run.completed_at,
        )
    ):
        raise ValueError("Generated planning proposal requires immutable binding fields.")
    if proposal.generation_status != "codex_generated":
        raise ValueError("Planning proposal store accepts only Codex-generated proposals.")
    if proposal.codex_run_id != completed_run.id or completed_run.status != "completed":
        raise ValueError("Planning proposal requires its exact completed Codex run.")


__all__ = [
    "ContentPlanningProposalStore",
    "content_planning_proposal_store",
]
