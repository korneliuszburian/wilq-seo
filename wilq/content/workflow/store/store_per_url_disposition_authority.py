"""Append-only proposal and receipt storage for per-URL disposition actions."""

from __future__ import annotations

import sqlite3
from typing import Literal, cast

from wilq.content.workflow.per_url_disposition_authority import (
    PerUrlDispositionProposal,
    PerUrlDispositionReceipt,
)
from wilq.storage.model_json import model_json


def ensure_per_url_disposition_authority_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS content_per_url_disposition_proposals (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id TEXT NOT NULL UNIQUE,
            canonical_path TEXT NOT NULL,
            current_work_item_id TEXT NOT NULL,
            semantic_row_digest TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS content_per_url_disposition_proposals_by_path
        ON content_per_url_disposition_proposals(canonical_path, sequence);

        CREATE TRIGGER IF NOT EXISTS content_per_url_disposition_proposals_no_update
        BEFORE UPDATE ON content_per_url_disposition_proposals
        BEGIN SELECT RAISE(ABORT, 'per-URL disposition proposals are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_per_url_disposition_proposals_no_replace
        BEFORE INSERT ON content_per_url_disposition_proposals
        WHEN EXISTS (
            SELECT 1 FROM content_per_url_disposition_proposals
            WHERE action_id = NEW.action_id
        )
        BEGIN SELECT RAISE(ABORT, 'per-URL disposition proposals are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_per_url_disposition_proposals_no_delete
        BEFORE DELETE ON content_per_url_disposition_proposals
        BEGIN SELECT RAISE(ABORT, 'per-URL disposition proposals are append-only'); END;

        CREATE TABLE IF NOT EXISTS content_per_url_disposition_receipts (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_id TEXT NOT NULL UNIQUE,
            action_id TEXT NOT NULL UNIQUE,
            canonical_path TEXT NOT NULL,
            current_work_item_id TEXT NOT NULL,
            semantic_row_digest TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS content_per_url_disposition_receipts_by_path
        ON content_per_url_disposition_receipts(canonical_path, sequence);

        CREATE TRIGGER IF NOT EXISTS content_per_url_disposition_receipts_no_update
        BEFORE UPDATE ON content_per_url_disposition_receipts
        BEGIN SELECT RAISE(ABORT, 'per-URL disposition receipts are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_per_url_disposition_receipts_no_replace
        BEFORE INSERT ON content_per_url_disposition_receipts
        WHEN EXISTS (
            SELECT 1 FROM content_per_url_disposition_receipts
            WHERE receipt_id = NEW.receipt_id OR action_id = NEW.action_id
        )
        BEGIN SELECT RAISE(ABORT, 'per-URL disposition receipts are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_per_url_disposition_receipts_no_delete
        BEFORE DELETE ON content_per_url_disposition_receipts
        BEGIN SELECT RAISE(ABORT, 'per-URL disposition receipts are append-only'); END;
        """
    )


class PerUrlDispositionAuthorityStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_per_url_disposition_proposal(
        self, proposal: PerUrlDispositionProposal
    ) -> PerUrlDispositionProposal:
        accepted = PerUrlDispositionProposal.model_validate_json(
            proposal.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_per_url_disposition_proposals "
                "WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if row is not None:
                return PerUrlDispositionProposal.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
            connection.execute(
                "INSERT INTO content_per_url_disposition_proposals "
                "(action_id, canonical_path, current_work_item_id, semantic_row_digest, "
                "payload_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    accepted.action_id,
                    accepted.snapshot.canonical_path,
                    accepted.snapshot.current_work_item_id,
                    accepted.snapshot.semantic_row_digest,
                    model_json(accepted),
                ),
            )
        return accepted

    def load_per_url_disposition_proposal(self, action_id: str) -> PerUrlDispositionProposal | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_per_url_disposition_proposals "
                "WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return (
            None
            if row is None
            else PerUrlDispositionProposal.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def record_per_url_disposition_receipt(
        self, receipt: PerUrlDispositionReceipt
    ) -> tuple[Literal["created", "idempotent", "conflict"], PerUrlDispositionReceipt]:
        accepted = PerUrlDispositionReceipt.model_validate_json(
            receipt.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            proposal_row = connection.execute(
                "SELECT payload_json FROM content_per_url_disposition_proposals "
                "WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if proposal_row is None:
                raise ValueError("Per-URL disposition receipt requires a stored proposal.")
            proposal = PerUrlDispositionProposal.model_validate_json(
                cast(str, proposal_row["payload_json"]), strict=True
            )
            if proposal.snapshot != accepted.snapshot:
                raise ValueError("Per-URL disposition receipt snapshot differs from proposal.")
            row = connection.execute(
                "SELECT payload_json FROM content_per_url_disposition_receipts WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if row is not None:
                stored = PerUrlDispositionReceipt.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
                return (
                    "idempotent"
                    if stored.action_payload_digest == accepted.action_payload_digest
                    else "conflict",
                    stored,
                )
            connection.execute(
                "INSERT INTO content_per_url_disposition_receipts "
                "(receipt_id, action_id, canonical_path, current_work_item_id, "
                "semantic_row_digest, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    accepted.receipt_id,
                    accepted.action_id,
                    accepted.snapshot.canonical_path,
                    accepted.snapshot.current_work_item_id,
                    accepted.snapshot.semantic_row_digest,
                    model_json(accepted),
                ),
            )
        return "created", accepted

    def load_per_url_disposition_receipt(self, action_id: str) -> PerUrlDispositionReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_per_url_disposition_receipts WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return (
            None
            if row is None
            else PerUrlDispositionReceipt.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )


__all__ = [
    "PerUrlDispositionAuthorityStoreMixin",
    "ensure_per_url_disposition_authority_schema",
]
