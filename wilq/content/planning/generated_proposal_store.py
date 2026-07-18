from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Literal, cast

from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.schemas import CodexRun
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import DEFAULT_STATE_DB, state_db_path
from wilq.storage.private_paths import prepare_private_store_path
from wilq.storage.schema_versions import (
    ensure_sqlite_schema_version,
    reject_newer_sqlite_schema,
)


def content_planning_proposal_store() -> ContentPlanningProposalStore:
    return ContentPlanningProposalStore(state_db_path())


class ContentPlanningProposalStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def latest(self, work_item_id: str) -> ContentPlanningProposal | None:
        connection = self._read_connection()
        if connection is None:
            return None
        with connection:
            if not _table_exists(connection, "content_planning_proposals"):
                return None
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
        with connection:
            if not _table_exists(connection, "content_planning_proposals"):
                return None
            row = _proposal_row_for_input(
                connection,
                work_item_id,
                service_card_id,
                planning_input_digest,
            )
        return _proposal_from_row(row)

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
