"""Append-only proposals for server-owned delivery identity binding actions."""

from __future__ import annotations

import sqlite3
from typing import cast

from wilq.content.workflow.delivery_identity_authority import (
    ContentDeliveryIdentityAuthorityCandidate,
    ContentDeliveryIdentityAuthorityProposal,
    build_delivery_identity_authority_blocked_proposal,
    build_delivery_identity_authority_proposal,
    build_delivery_identity_authority_snapshot,
)
from wilq.storage.model_json import model_json


class ContentDeliveryIdentityAuthorityStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_content_delivery_identity_authority_proposal(
        self, candidate: ContentDeliveryIdentityAuthorityCandidate
    ) -> ContentDeliveryIdentityAuthorityProposal:
        accepted = ContentDeliveryIdentityAuthorityCandidate.model_validate_json(
            candidate.model_dump_json(), strict=True
        )
        try:
            proposal = build_delivery_identity_authority_proposal(
                build_delivery_identity_authority_snapshot(self, accepted)
            )
        except ValueError:
            # Keep a durable candidate so reads and the canonical apply path
            # expose a typed blocker instead of turning current-state drift
            # into an exception or an implicit retry.
            proposal = build_delivery_identity_authority_blocked_proposal(accepted)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_delivery_identity_authority_proposals "
                "WHERE action_id = ?",
                (proposal.action_id,),
            ).fetchone()
            if row is not None:
                return ContentDeliveryIdentityAuthorityProposal.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
            connection.execute(
                "INSERT INTO content_delivery_identity_authority_proposals "
                "(action_id, proposal_digest, current_disposition_receipt_id, "
                "inventory_receipt_id, payload_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    proposal.action_id,
                    proposal.proposal_digest,
                    proposal.current_disposition_receipt_id,
                    proposal.inventory_receipt_id,
                    model_json(proposal),
                ),
            )
        return proposal

    def load_content_delivery_identity_authority_proposal(
        self, action_id: str
    ) -> ContentDeliveryIdentityAuthorityProposal | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_delivery_identity_authority_proposals "
                "WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentDeliveryIdentityAuthorityProposal.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )


__all__ = ["ContentDeliveryIdentityAuthorityStoreMixin"]
