from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal, NamedTuple, cast

from wilq.content.planning.runtime_contract import planning_job_stale_after_seconds
from wilq.content.workflow.refresh_preparation_contracts import ContentRefreshPreparationBinding
from wilq.schemas.core import utc_now
from wilq.storage.local_state import DEFAULT_STATE_DB, state_db_path
from wilq.storage.private_paths import prepare_private_store_path
from wilq.storage.schema_versions import (
    ensure_sqlite_schema_version,
    reject_newer_sqlite_schema,
)

PlanningGenerationClaimOutcome = Literal["acquired", "in_flight", "binding_conflict"]
PlanningGenerationClaimFinalStatus = Literal["finished", "failed"]


class PlanningGenerationClaim(NamedTuple):
    outcome: PlanningGenerationClaimOutcome
    claim_version: int


def content_planning_generation_claim_store() -> ContentPlanningGenerationClaimStore:
    return ContentPlanningGenerationClaimStore(state_db_path())


class ContentPlanningGenerationClaimStore:
    """Own durable, process-independent execution claims for planning jobs."""

    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.path = path
        self._clock = clock

    def claim(
        self,
        *,
        work_item_id: str,
        service_card_id: str,
        planning_input_digest: str,
        claim_owner: str,
        refresh_preparation_binding: ContentRefreshPreparationBinding | None = None,
    ) -> PlanningGenerationClaim:
        binding_identity = _refresh_preparation_claim_identity(refresh_preparation_binding)
        claim_key = _planning_generation_claim_key(
            work_item_id,
            service_card_id,
            planning_input_digest,
        )
        now = self._clock()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT status, claimed_at, claim_version,
                       refresh_preparation_authorization_id,
                       refresh_preparation_authorization_digest
                FROM content_planning_generation_claims
                WHERE claim_key = ?
                """,
                (claim_key,),
            ).fetchone()
            if row is not None:
                return _existing_claim(
                    connection,
                    row=row,
                    claim_key=claim_key,
                    claim_owner=claim_owner,
                    binding_identity=binding_identity,
                    now=now,
                )
            return _insert_claim(
                connection,
                claim_key=claim_key,
                work_item_id=work_item_id,
                service_card_id=service_card_id,
                planning_input_digest=planning_input_digest,
                claim_owner=claim_owner,
                binding_identity=binding_identity,
                now=now,
            )

    def finish(
        self,
        *,
        work_item_id: str,
        service_card_id: str,
        planning_input_digest: str,
        claim_owner: str,
        claim_version: int,
        status: PlanningGenerationClaimFinalStatus,
        refresh_preparation_binding: ContentRefreshPreparationBinding | None = None,
    ) -> bool:
        authorization_id, authorization_digest = _refresh_preparation_claim_identity(
            refresh_preparation_binding
        )
        claim_key = _planning_generation_claim_key(
            work_item_id,
            service_card_id,
            planning_input_digest,
        )
        with self._connect() as connection:
            updated = connection.execute(
                """
                UPDATE content_planning_generation_claims
                SET status = ?, updated_at = ?
                WHERE claim_key = ? AND claim_owner = ? AND claim_version = ?
                  AND status = 'claimed'
                  AND refresh_preparation_authorization_id IS ?
                  AND refresh_preparation_authorization_digest IS ?
                """,
                (
                    status,
                    self._clock().isoformat(),
                    claim_key,
                    claim_owner,
                    claim_version,
                    authorization_id,
                    authorization_digest,
                ),
            )
        return updated.rowcount == 1

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
            CREATE TABLE IF NOT EXISTS content_planning_generation_claims (
              claim_key TEXT PRIMARY KEY,
              work_item_id TEXT NOT NULL,
              service_card_id TEXT NOT NULL,
              planning_input_digest TEXT NOT NULL,
              status TEXT NOT NULL CHECK (status IN ('claimed', 'finished', 'failed')),
              claim_owner TEXT NOT NULL,
              claim_version INTEGER NOT NULL DEFAULT 1 CHECK (claim_version >= 1),
              claimed_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE (work_item_id, service_card_id, planning_input_digest)
            )
            """
        )
        _ensure_claim_version_column(connection)
        _ensure_refresh_preparation_binding_columns(connection)
        ensure_sqlite_schema_version(connection)
        return connection


def _planning_generation_claim_key(
    work_item_id: str,
    service_card_id: str,
    planning_input_digest: str,
) -> str:
    payload = json.dumps(
        [work_item_id, service_card_id, planning_input_digest],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _claim_is_stale(claimed_at: str, *, now: datetime) -> bool:
    try:
        timestamp = datetime.fromisoformat(claimed_at)
        age = (now - timestamp).total_seconds()
    except (TypeError, ValueError):
        return True
    return age > planning_job_stale_after_seconds()


def _refresh_preparation_claim_identity(
    binding: ContentRefreshPreparationBinding | None,
) -> tuple[str | None, str | None]:
    if binding is None:
        return None, None
    return binding.authorization_id, binding.authorization_digest


def _claim_matches_binding(
    row: sqlite3.Row,
    binding_identity: tuple[str | None, str | None],
) -> bool:
    return (
        row["refresh_preparation_authorization_id"],
        row["refresh_preparation_authorization_digest"],
    ) == binding_identity


def _existing_claim(
    connection: sqlite3.Connection,
    *,
    row: sqlite3.Row,
    claim_key: str,
    claim_owner: str,
    binding_identity: tuple[str | None, str | None],
    now: datetime,
) -> PlanningGenerationClaim:
    claim_version = int(row["claim_version"])
    is_active = str(row["status"]) == "claimed" and not _claim_is_stale(
        cast(str, row["claimed_at"]), now=now
    )
    if is_active:
        outcome: PlanningGenerationClaimOutcome = (
            "in_flight" if _claim_matches_binding(row, binding_identity) else "binding_conflict"
        )
        return PlanningGenerationClaim(outcome, claim_version)
    next_claim_version = claim_version + 1
    authorization_id, authorization_digest = binding_identity
    updated = connection.execute(
        """
        UPDATE content_planning_generation_claims
        SET status = 'claimed', claim_owner = ?, claim_version = ?,
            refresh_preparation_authorization_id = ?,
            refresh_preparation_authorization_digest = ?,
            claimed_at = ?, updated_at = ?
        WHERE claim_key = ? AND claim_version = ?
        """,
        (
            claim_owner,
            next_claim_version,
            authorization_id,
            authorization_digest,
            now.isoformat(),
            now.isoformat(),
            claim_key,
            claim_version,
        ),
    )
    if updated.rowcount != 1:
        raise RuntimeError("Planning generation claim changed during acquisition.")
    return PlanningGenerationClaim("acquired", next_claim_version)


def _insert_claim(
    connection: sqlite3.Connection,
    *,
    claim_key: str,
    work_item_id: str,
    service_card_id: str,
    planning_input_digest: str,
    claim_owner: str,
    binding_identity: tuple[str | None, str | None],
    now: datetime,
) -> PlanningGenerationClaim:
    authorization_id, authorization_digest = binding_identity
    inserted = connection.execute(
        """
        INSERT INTO content_planning_generation_claims (
          claim_key,
          work_item_id,
          service_card_id,
          planning_input_digest,
          status,
          claim_owner,
          claim_version,
          refresh_preparation_authorization_id,
          refresh_preparation_authorization_digest,
          claimed_at,
          updated_at
        )
        VALUES (?, ?, ?, ?, 'claimed', ?, 1, ?, ?, ?, ?)
        ON CONFLICT(claim_key) DO NOTHING
        """,
        (
            claim_key,
            work_item_id,
            service_card_id,
            planning_input_digest,
            claim_owner,
            authorization_id,
            authorization_digest,
            now.isoformat(),
            now.isoformat(),
        ),
    )
    if inserted.rowcount == 1:
        return PlanningGenerationClaim("acquired", 1)
    row = connection.execute(
        """
        SELECT status, claimed_at, claim_version,
               refresh_preparation_authorization_id,
               refresh_preparation_authorization_digest
        FROM content_planning_generation_claims
        WHERE claim_key = ?
        """,
        (claim_key,),
    ).fetchone()
    if row is None:
        raise RuntimeError("Planning generation claim disappeared during acquisition.")
    return _existing_claim(
        connection,
        row=row,
        claim_key=claim_key,
        claim_owner=claim_owner,
        binding_identity=binding_identity,
        now=now,
    )


def _ensure_claim_version_column(connection: sqlite3.Connection) -> None:
    columns = {
        str(row[1])
        for row in connection.execute(
            "PRAGMA table_info(content_planning_generation_claims)"
        )
    }
    if "claim_version" not in columns:
        connection.execute(
            "ALTER TABLE content_planning_generation_claims "
            "ADD COLUMN claim_version INTEGER NOT NULL DEFAULT 1 "
            "CHECK (claim_version >= 1)"
        )


def _ensure_refresh_preparation_binding_columns(connection: sqlite3.Connection) -> None:
    columns = {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(content_planning_generation_claims)")
    }
    for name in (
        "refresh_preparation_authorization_id",
        "refresh_preparation_authorization_digest",
    ):
        if name not in columns:
            try:
                connection.execute(
                    "ALTER TABLE content_planning_generation_claims "
                    f"ADD COLUMN {name} TEXT"  # nosec B608 -- fixed column names.
                )
            except sqlite3.OperationalError as error:
                if "duplicate column name" not in str(error).lower():
                    raise


def refresh_preparation_binding_columns_present(connection: sqlite3.Connection) -> bool:
    columns = {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(content_planning_generation_claims)")
    }
    return {
        "refresh_preparation_authorization_id",
        "refresh_preparation_authorization_digest",
    }.issubset(columns)


__all__ = [
    "ContentPlanningGenerationClaimStore",
    "PlanningGenerationClaim",
    "PlanningGenerationClaimFinalStatus",
    "PlanningGenerationClaimOutcome",
    "content_planning_generation_claim_store",
    "refresh_preparation_binding_columns_present",
]
