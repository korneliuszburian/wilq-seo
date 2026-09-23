"""Append-only storage for versioned current page KEEP proposals and receipts."""

from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.current_page_disposition_v2 import (
    CurrentPageDispositionV2Proposal,
    CurrentPageDispositionV2Receipt,
)
from wilq.storage.model_json import model_json


class CurrentPageDispositionV2StoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_current_page_disposition_v2_proposal(
        self, proposal: CurrentPageDispositionV2Proposal
    ) -> CurrentPageDispositionV2Proposal:
        accepted = CurrentPageDispositionV2Proposal.model_validate_json(
            proposal.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_current_disposition_proposals "
                "WHERE action_id = ?",
                (accepted.proposal_id,),
            ).fetchone()
            if row is not None:
                return CurrentPageDispositionV2Proposal.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
            connection.execute(
                "INSERT INTO content_current_disposition_proposals "
                "(action_id, proposal_digest, current_work_item_id, payload_json) "
                "VALUES (?, ?, ?, ?)",
                (
                    accepted.proposal_id,
                    accepted.proposal_digest,
                    accepted.snapshot.work_item_id,
                    model_json(accepted),
                ),
            )
        return accepted

    def load_current_page_disposition_v2_proposal(
        self, proposal_id: str
    ) -> CurrentPageDispositionV2Proposal | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_current_disposition_proposals "
                "WHERE action_id = ?",
                (proposal_id,),
            ).fetchone()
        return (
            None
            if row is None
            else CurrentPageDispositionV2Proposal.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def record_current_page_disposition_v2_receipt(
        self, receipt: CurrentPageDispositionV2Receipt
    ) -> tuple[str, CurrentPageDispositionV2Receipt]:
        accepted = CurrentPageDispositionV2Receipt.model_validate_json(
            receipt.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            proposal_row = connection.execute(
                "SELECT payload_json FROM content_current_disposition_proposals "
                "WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if proposal_row is None:
                raise ValueError("Current page disposition v2 receipt requires a stored proposal.")
            proposal = CurrentPageDispositionV2Proposal.model_validate_json(
                cast(str, proposal_row["payload_json"]), strict=True
            )
            if proposal.snapshot != accepted.snapshot:
                raise ValueError(
                    "Current page disposition v2 receipt snapshot does not match proposal."
                )
            row = connection.execute(
                "SELECT payload_json FROM content_current_disposition_receipts WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if row is not None:
                stored = CurrentPageDispositionV2Receipt.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
                return (
                    "idempotent"
                    if stored.receipt_digest == accepted.receipt_digest
                    else "conflict",
                    stored,
                )
            connection.execute(
                "INSERT INTO content_current_disposition_receipts "
                "(receipt_id, receipt_digest, action_id, current_work_item_id, payload_json) "
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

    def load_current_page_disposition_v2_receipt(
        self, action_id: str
    ) -> CurrentPageDispositionV2Receipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_current_disposition_receipts WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return (
            None
            if row is None
            else CurrentPageDispositionV2Receipt.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def load_current_page_disposition_v2_receipt_by_id(
        self, receipt_id: str
    ) -> CurrentPageDispositionV2Receipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_current_disposition_receipts "
                "WHERE receipt_id = ?",
                (receipt_id,),
            ).fetchone()
        return (
            None
            if row is None
            else CurrentPageDispositionV2Receipt.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def load_latest_current_page_disposition_v2_receipt_for_work_item(
        self, work_item_id: str
    ) -> CurrentPageDispositionV2Receipt | None:
        """Read the newest appended v2 KEEP receipt for one exact work item."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_current_disposition_receipts "
                "WHERE current_work_item_id = ? "
                "AND json_extract(payload_json, '$.schema_version') = ? "
                "ORDER BY rowid DESC LIMIT 1",
                (work_item_id, "wilq_current_page_disposition_receipt_v2"),
            ).fetchone()
        return (
            None
            if row is None
            else CurrentPageDispositionV2Receipt.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )


__all__ = ["CurrentPageDispositionV2StoreMixin"]
