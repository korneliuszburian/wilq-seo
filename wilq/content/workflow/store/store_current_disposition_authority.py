"""Append-only non-authoritative proposals for current content disposition."""

from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.current_disposition_authority import (
    ContentCurrentDispositionCandidate,
    ContentCurrentDispositionProposal,
    ContentCurrentDispositionReceipt,
    build_current_disposition_proposal,
    build_current_disposition_snapshot,
)
from wilq.storage.model_json import model_json


class ContentCurrentDispositionAuthorityStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_content_current_disposition_proposal(
        self, candidate: ContentCurrentDispositionCandidate
    ) -> ContentCurrentDispositionProposal:
        """Persist only a candidate after exact current-state revalidation."""

        accepted = ContentCurrentDispositionCandidate.model_validate_json(
            candidate.model_dump_json(), strict=True
        )
        snapshot = build_current_disposition_snapshot(self, accepted)
        proposal = build_current_disposition_proposal(snapshot, attempt=accepted.attempt)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_current_disposition_proposals "
                "WHERE action_id = ?",
                (proposal.action_id,),
            ).fetchone()
            if row is not None:
                return ContentCurrentDispositionProposal.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
            connection.execute(
                "INSERT INTO content_current_disposition_proposals "
                "(action_id, proposal_digest, current_work_item_id, payload_json) "
                "VALUES (?, ?, ?, ?)",
                (
                    proposal.action_id,
                    proposal.proposal_digest,
                    proposal.current_work_item_id,
                    model_json(proposal),
                ),
            )
        return proposal

    def load_content_current_disposition_proposal(
        self, action_id: str
    ) -> ContentCurrentDispositionProposal | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_current_disposition_proposals "
                "WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentCurrentDispositionProposal.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def record_content_current_disposition_receipt(
        self, receipt: ContentCurrentDispositionReceipt
    ) -> tuple[str, ContentCurrentDispositionReceipt]:
        accepted = ContentCurrentDispositionReceipt.model_validate_json(
            receipt.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_current_disposition_receipts WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if row is not None:
                stored = ContentCurrentDispositionReceipt.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
                return (
                    (
                        "idempotent"
                        if stored.receipt_digest == accepted.receipt_digest
                        else "conflict"
                    ),
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
                    accepted.authority_snapshot.current_work_item_id,
                    model_json(accepted),
                ),
            )
        return "created", accepted

    def load_content_current_disposition_receipt(
        self, action_id: str
    ) -> ContentCurrentDispositionReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_current_disposition_receipts WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentCurrentDispositionReceipt.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def load_content_current_disposition_receipt_by_id(
        self, receipt_id: str
    ) -> ContentCurrentDispositionReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_current_disposition_receipts "
                "WHERE receipt_id = ?",
                (receipt_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentCurrentDispositionReceipt.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )


__all__ = ["ContentCurrentDispositionAuthorityStoreMixin"]
