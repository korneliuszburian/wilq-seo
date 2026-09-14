"""Append-only proposals for exact per-row source-fact authority.

The proposal is deliberately not an approval or a receipt.  It is only the
stable ActionObject input that later canonical review/confirm/apply lifecycle
steps may consume.
"""

from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.source_fact_authority import (
    ContentSourceFactAuthorityPreviewCommand,
    ContentSourceFactAuthorityProposal,
    ContentSourceFactAuthorityReceipt,
    source_fact_authority_action_id,
    source_fact_authority_proposal_digest,
)
from wilq.schemas.core import utc_now
from wilq.storage.model_json import model_json


class ContentSourceFactAuthorityStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_content_source_fact_authority_proposal(
        self,
        command: ContentSourceFactAuthorityPreviewCommand,
    ) -> ContentSourceFactAuthorityProposal:
        """Persist proposal IDs only; S1 and facts are re-read for every preview."""

        accepted = ContentSourceFactAuthorityPreviewCommand.model_validate_json(
            command.model_dump_json(), strict=True
        )
        digest = source_fact_authority_proposal_digest(
            accepted.identity_binding_id, accepted.proposed_source_fact_ids
        )
        proposal = ContentSourceFactAuthorityProposal(
            action_id=source_fact_authority_action_id(
                accepted.identity_binding_id, accepted.proposed_source_fact_ids
            ),
            proposal_digest=digest,
            identity_binding_id=accepted.identity_binding_id,
            proposed_source_fact_ids=accepted.proposed_source_fact_ids,
            prepared_at=utc_now(),
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT payload_json FROM content_source_fact_authority_proposals "
                "WHERE action_id = ?",
                (proposal.action_id,),
            ).fetchone()
            if existing is not None:
                stored = ContentSourceFactAuthorityProposal.model_validate_json(
                    cast(str, existing["payload_json"]), strict=True
                )
                if stored.proposal_digest != proposal.proposal_digest:
                    raise ValueError("Source fact authority proposal conflicts with stored action.")
                return stored
            connection.execute(
                """
                INSERT INTO content_source_fact_authority_proposals (
                  action_id, proposal_digest, identity_binding_id, payload_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    proposal.action_id,
                    proposal.proposal_digest,
                    proposal.identity_binding_id,
                    model_json(proposal),
                ),
            )
        return proposal

    def load_content_source_fact_authority_proposal(
        self, action_id: str
    ) -> ContentSourceFactAuthorityProposal | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_source_fact_authority_proposals "
                "WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentSourceFactAuthorityProposal.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def record_content_source_fact_authority_receipt(
        self, receipt: ContentSourceFactAuthorityReceipt
    ) -> tuple[str, ContentSourceFactAuthorityReceipt]:
        """Append one receipt; an identical action retry returns the original."""

        accepted = ContentSourceFactAuthorityReceipt.model_validate_json(
            receipt.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_source_fact_authority_receipts "
                "WHERE action_id = ?", (accepted.action_id,)
            ).fetchone()
            if row is not None:
                stored = ContentSourceFactAuthorityReceipt.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
                if stored.action_payload_digest != accepted.action_payload_digest:
                    return "conflict", stored
                return "idempotent", stored
            connection.execute(
                """
                INSERT INTO content_source_fact_authority_receipts (
                  receipt_id, receipt_digest, action_id, action_payload_digest,
                  identity_binding_id, current_work_item_id, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    accepted.receipt_id,
                    accepted.receipt_digest,
                    accepted.action_id,
                    accepted.action_payload_digest,
                    accepted.authority_snapshot.identity_binding_id,
                    accepted.authority_snapshot.current_work_item_id,
                    model_json(accepted),
                ),
            )
        return "created", accepted

    def load_content_source_fact_authority_receipt(
        self, action_id: str
    ) -> ContentSourceFactAuthorityReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_source_fact_authority_receipts "
                "WHERE action_id = ?", (action_id,)
            ).fetchone()
        return None if row is None else ContentSourceFactAuthorityReceipt.model_validate_json(
            cast(str, row["payload_json"]), strict=True
        )

    def list_content_source_fact_authority_receipts(
        self,
        *,
        identity_binding_id: str,
        current_work_item_id: str | None = None,
    ) -> list[ContentSourceFactAuthorityReceipt]:
        """Read valid immutable receipts for one exact identity/work item.

        The caller still has to match the selected fact IDs.  This method
        intentionally does not expose an implicit ``latest`` authority.
        """

        query = (
            "SELECT payload_json FROM content_source_fact_authority_receipts "
            "WHERE identity_binding_id = ?"
        )
        parameters: tuple[object, ...] = (identity_binding_id,)
        if current_work_item_id is not None:
            query += " AND current_work_item_id = ?"
            parameters += (current_work_item_id,)
        query += " ORDER BY rowid"
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        receipts: list[ContentSourceFactAuthorityReceipt] = []
        for row in rows:
            try:
                receipts.append(
                    ContentSourceFactAuthorityReceipt.model_validate_json(
                        cast(str, row["payload_json"]), strict=True
                    )
                )
            except Exception:
                # A malformed persisted row is not authority and must never
                # block a separate valid receipt from being read.
                continue
        return receipts

    def load_content_source_fact_authority_receipt_for_identity(
        self,
        identity_binding_id: str,
        current_work_item_id: str,
        source_fact_ids: tuple[str, ...],
    ) -> ContentSourceFactAuthorityReceipt | None:
        """Resolve one receipt by exact identity, work item and fact set.

        The append-only ledger's last receipt is the current row authority.
        Returning it even when the requested fact IDs changed lets
        reconciliation report a typed changed-fact-set blocker instead of
        silently binding an older selection.
        """

        receipts = self.list_content_source_fact_authority_receipts(
            identity_binding_id=identity_binding_id,
            current_work_item_id=current_work_item_id,
        )
        del source_fact_ids
        return receipts[-1] if receipts else None
