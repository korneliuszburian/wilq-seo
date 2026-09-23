"""Append-only persistence for v2 source-fact authority proposals and receipts."""

from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.source_fact_authority_v2 import (
    ContentSourceFactAuthorityV2Proposal,
    ContentSourceFactAuthorityV2Receipt,
)
from wilq.storage.model_json import model_json
from wilq.storage.schema_versions import reject_newer_sqlite_schema

_SOURCE_FACT_AUTHORITY_V2_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS content_source_fact_authority_v2_proposals (
      action_id TEXT PRIMARY KEY,
      proposal_digest TEXT NOT NULL UNIQUE,
      work_item_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_fact_authority_v2_proposals_no_update
    BEFORE UPDATE ON content_source_fact_authority_v2_proposals
    BEGIN SELECT RAISE(ABORT, 'source fact authority v2 proposals are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_fact_authority_v2_proposals_no_replace
    BEFORE INSERT ON content_source_fact_authority_v2_proposals
    WHEN EXISTS (
      SELECT 1 FROM content_source_fact_authority_v2_proposals
      WHERE action_id = NEW.action_id OR proposal_digest = NEW.proposal_digest
    )
    BEGIN SELECT RAISE(ABORT, 'source fact authority v2 proposals are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_fact_authority_v2_proposals_no_delete
    BEFORE DELETE ON content_source_fact_authority_v2_proposals
    BEGIN SELECT RAISE(ABORT, 'source fact authority v2 proposals are append-only'); END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_source_fact_authority_v2_receipts (
      receipt_id TEXT PRIMARY KEY,
      receipt_digest TEXT NOT NULL UNIQUE,
      action_id TEXT NOT NULL UNIQUE,
      work_item_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_content_source_fact_authority_v2_receipts_work_item
    ON content_source_fact_authority_v2_receipts (work_item_id)
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_fact_authority_v2_receipts_no_update
    BEFORE UPDATE ON content_source_fact_authority_v2_receipts
    BEGIN SELECT RAISE(ABORT, 'source fact authority v2 receipts are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_fact_authority_v2_receipts_no_replace
    BEFORE INSERT ON content_source_fact_authority_v2_receipts
    WHEN EXISTS (
      SELECT 1 FROM content_source_fact_authority_v2_receipts
      WHERE receipt_id = NEW.receipt_id OR receipt_digest = NEW.receipt_digest
         OR action_id = NEW.action_id
    )
    BEGIN SELECT RAISE(ABORT, 'source fact authority v2 receipts are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_fact_authority_v2_receipts_no_delete
    BEFORE DELETE ON content_source_fact_authority_v2_receipts
    BEGIN SELECT RAISE(ABORT, 'source fact authority v2 receipts are append-only'); END
    """,
)


def ensure_source_fact_authority_v2_schema(connection: sqlite3.Connection) -> None:
    """Create append-only v2 tables after rejecting unsupported newer stores."""
    reject_newer_sqlite_schema(connection)
    for statement in _SOURCE_FACT_AUTHORITY_V2_SCHEMA:
        connection.execute(statement)


class SourceFactAuthorityV2StoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_source_fact_authority_v2_proposal(
        self, proposal: ContentSourceFactAuthorityV2Proposal
    ) -> ContentSourceFactAuthorityV2Proposal:
        accepted = ContentSourceFactAuthorityV2Proposal.model_validate_json(
            proposal.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_source_fact_authority_v2_proposals "
                "WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if row is not None:
                return ContentSourceFactAuthorityV2Proposal.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
            connection.execute(
                "INSERT INTO content_source_fact_authority_v2_proposals "
                "(action_id, proposal_digest, work_item_id, payload_json) VALUES (?, ?, ?, ?)",
                (
                    accepted.action_id,
                    accepted.proposal_digest,
                    accepted.snapshot.work_item_id,
                    model_json(accepted),
                ),
            )
        return accepted

    def load_source_fact_authority_v2_proposal(
        self, action_id: str
    ) -> ContentSourceFactAuthorityV2Proposal | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_source_fact_authority_v2_proposals "
                "WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentSourceFactAuthorityV2Proposal.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def record_source_fact_authority_v2_receipt(
        self, receipt: ContentSourceFactAuthorityV2Receipt
    ) -> tuple[str, ContentSourceFactAuthorityV2Receipt]:
        accepted = ContentSourceFactAuthorityV2Receipt.model_validate_json(
            receipt.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            proposal_row = connection.execute(
                "SELECT payload_json FROM content_source_fact_authority_v2_proposals "
                "WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if proposal_row is None:
                raise ValueError("Source fact authority v2 receipt requires a stored proposal.")
            proposal = ContentSourceFactAuthorityV2Proposal.model_validate_json(
                cast(str, proposal_row["payload_json"]), strict=True
            )
            if proposal.snapshot != accepted.snapshot:
                raise ValueError("Source fact authority v2 receipt snapshot differs from proposal.")
            row = connection.execute(
                "SELECT payload_json FROM content_source_fact_authority_v2_receipts "
                "WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if row is not None:
                stored = ContentSourceFactAuthorityV2Receipt.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
                return (
                    "idempotent"
                    if stored.receipt_digest == accepted.receipt_digest
                    else "conflict",
                    stored,
                )
            connection.execute(
                "INSERT INTO content_source_fact_authority_v2_receipts "
                "(receipt_id, receipt_digest, action_id, work_item_id, payload_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    accepted.receipt_id,
                    accepted.receipt_digest,
                    accepted.action_id,
                    accepted.snapshot.work_item_id,
                    model_json(accepted),
                ),
            )
        return "created", accepted

    def load_source_fact_authority_v2_receipt(
        self, action_id: str
    ) -> ContentSourceFactAuthorityV2Receipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_source_fact_authority_v2_receipts "
                "WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentSourceFactAuthorityV2Receipt.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def load_latest_source_fact_authority_v2_receipt_for_work_item(
        self, work_item_id: str
    ) -> ContentSourceFactAuthorityV2Receipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_source_fact_authority_v2_receipts "
                "WHERE work_item_id = ? ORDER BY rowid DESC LIMIT 1",
                (work_item_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentSourceFactAuthorityV2Receipt.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )


__all__ = ["SourceFactAuthorityV2StoreMixin", "ensure_source_fact_authority_v2_schema"]
