"""Append-only persistence for per-URL delivery identity proposals and bindings."""

from __future__ import annotations

import sqlite3
from typing import Literal, cast

from wilq.content.workflow.per_url_delivery_identity_authority import (
    PerUrlDeliveryIdentityBinding,
    PerUrlDeliveryIdentityProposal,
)
from wilq.storage.model_json import model_json


def ensure_per_url_delivery_identity_authority_schema(
    connection: sqlite3.Connection,
) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS content_per_url_delivery_identity_proposals (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id TEXT NOT NULL UNIQUE,
            canonical_path TEXT NOT NULL,
            current_work_item_id TEXT NOT NULL,
            semantic_row_digest TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS content_per_url_delivery_identity_proposals_by_path
        ON content_per_url_delivery_identity_proposals(canonical_path, sequence);

        CREATE INDEX IF NOT EXISTS content_per_url_delivery_identity_proposals_by_work_item
        ON content_per_url_delivery_identity_proposals(current_work_item_id, sequence);

        CREATE TRIGGER IF NOT EXISTS content_per_url_delivery_identity_proposals_no_update
        BEFORE UPDATE ON content_per_url_delivery_identity_proposals
        BEGIN SELECT RAISE(ABORT, 'per-URL delivery identity proposals are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_per_url_delivery_identity_proposals_no_replace
        BEFORE INSERT ON content_per_url_delivery_identity_proposals
        WHEN EXISTS (
            SELECT 1 FROM content_per_url_delivery_identity_proposals
            WHERE action_id = NEW.action_id
        )
        BEGIN SELECT RAISE(ABORT, 'per-URL delivery identity proposals are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_per_url_delivery_identity_proposals_no_delete
        BEFORE DELETE ON content_per_url_delivery_identity_proposals
        BEGIN SELECT RAISE(ABORT, 'per-URL delivery identity proposals are append-only'); END;

        CREATE TABLE IF NOT EXISTS content_per_url_delivery_identity_bindings (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            binding_id TEXT NOT NULL UNIQUE,
            action_id TEXT NOT NULL UNIQUE,
            canonical_path TEXT NOT NULL,
            current_work_item_id TEXT NOT NULL,
            semantic_row_digest TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS content_per_url_delivery_identity_bindings_by_path
        ON content_per_url_delivery_identity_bindings(canonical_path, sequence);

        CREATE INDEX IF NOT EXISTS content_per_url_delivery_identity_bindings_by_work_item
        ON content_per_url_delivery_identity_bindings(current_work_item_id, sequence);

        CREATE TRIGGER IF NOT EXISTS content_per_url_delivery_identity_bindings_no_update
        BEFORE UPDATE ON content_per_url_delivery_identity_bindings
        BEGIN SELECT RAISE(ABORT, 'per-URL delivery identity bindings are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_per_url_delivery_identity_bindings_no_replace
        BEFORE INSERT ON content_per_url_delivery_identity_bindings
        WHEN EXISTS (
            SELECT 1 FROM content_per_url_delivery_identity_bindings
            WHERE binding_id = NEW.binding_id OR action_id = NEW.action_id
        )
        BEGIN SELECT RAISE(ABORT, 'per-URL delivery identity bindings are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_per_url_delivery_identity_bindings_no_delete
        BEFORE DELETE ON content_per_url_delivery_identity_bindings
        BEGIN SELECT RAISE(ABORT, 'per-URL delivery identity bindings are append-only'); END;
        """
    )


class PerUrlDeliveryIdentityAuthorityStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_per_url_delivery_identity_proposal(
        self,
        proposal: PerUrlDeliveryIdentityProposal,
    ) -> PerUrlDeliveryIdentityProposal:
        accepted = PerUrlDeliveryIdentityProposal.model_validate_json(
            proposal.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_per_url_delivery_identity_proposals "
                "WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if row is not None:
                stored = PerUrlDeliveryIdentityProposal.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
                if (
                    stored.proposal_digest != accepted.proposal_digest
                    or stored.snapshot != accepted.snapshot
                ):
                    raise ValueError("Per-URL delivery identity proposal is immutable.")
                return stored
            connection.execute(
                "INSERT INTO content_per_url_delivery_identity_proposals "
                "(action_id, canonical_path, current_work_item_id, semantic_row_digest, "
                "payload_json) VALUES (?, ?, ?, ?, ?)",
                (
                    accepted.action_id,
                    accepted.snapshot.canonical_path,
                    accepted.snapshot.current_work_item_id,
                    accepted.snapshot.semantic_row_digest,
                    model_json(accepted),
                ),
            )
        return accepted

    def load_per_url_delivery_identity_proposal(
        self,
        action_id: str,
    ) -> PerUrlDeliveryIdentityProposal | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_per_url_delivery_identity_proposals "
                "WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return (
            None
            if row is None
            else PerUrlDeliveryIdentityProposal.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def record_per_url_delivery_identity_binding(
        self,
        binding: PerUrlDeliveryIdentityBinding,
    ) -> tuple[Literal["created", "idempotent", "conflict"], PerUrlDeliveryIdentityBinding]:
        accepted = PerUrlDeliveryIdentityBinding.model_validate_json(
            binding.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            proposal_row = connection.execute(
                "SELECT payload_json FROM content_per_url_delivery_identity_proposals "
                "WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if proposal_row is None:
                raise ValueError("Per-URL identity binding requires a stored proposal.")
            proposal = PerUrlDeliveryIdentityProposal.model_validate_json(
                cast(str, proposal_row["payload_json"]), strict=True
            )
            if proposal.snapshot != accepted.snapshot:
                raise ValueError("Per-URL identity binding snapshot differs from its proposal.")
            row = connection.execute(
                "SELECT payload_json FROM content_per_url_delivery_identity_bindings "
                "WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if row is not None:
                stored = PerUrlDeliveryIdentityBinding.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
                return (
                    "idempotent"
                    if stored.action_payload_digest == accepted.action_payload_digest
                    else "conflict",
                    stored,
                )
            connection.execute(
                "INSERT INTO content_per_url_delivery_identity_bindings "
                "(binding_id, action_id, canonical_path, current_work_item_id, "
                "semantic_row_digest, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    accepted.binding_id,
                    accepted.action_id,
                    accepted.snapshot.canonical_path,
                    accepted.snapshot.current_work_item_id,
                    accepted.snapshot.semantic_row_digest,
                    model_json(accepted),
                ),
            )
        return "created", accepted

    def load_per_url_delivery_identity_binding(
        self,
        binding_id: str,
    ) -> PerUrlDeliveryIdentityBinding | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_per_url_delivery_identity_bindings "
                "WHERE binding_id = ?",
                (binding_id,),
            ).fetchone()
        return (
            None
            if row is None
            else PerUrlDeliveryIdentityBinding.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def load_per_url_delivery_identity_binding_by_action(
        self,
        action_id: str,
    ) -> PerUrlDeliveryIdentityBinding | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_per_url_delivery_identity_bindings "
                "WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        return (
            None
            if row is None
            else PerUrlDeliveryIdentityBinding.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def list_per_url_delivery_identity_bindings(
        self,
        *,
        current_work_item_id: str | None = None,
    ) -> list[PerUrlDeliveryIdentityBinding]:
        query = "SELECT payload_json FROM content_per_url_delivery_identity_bindings"
        parameters: tuple[object, ...] = ()
        if current_work_item_id is not None:
            query += " WHERE current_work_item_id = ?"
            parameters = (current_work_item_id,)
        query += " ORDER BY sequence ASC"
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [
            PerUrlDeliveryIdentityBinding.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
            for row in rows
        ]


__all__ = [
    "PerUrlDeliveryIdentityAuthorityStoreMixin",
    "ensure_per_url_delivery_identity_authority_schema",
]
