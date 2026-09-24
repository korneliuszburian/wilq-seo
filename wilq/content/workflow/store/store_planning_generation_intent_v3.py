"""Append-only storage for exact local v3 planning-generation intents."""

from __future__ import annotations

import re
import sqlite3
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from wilq.storage.model_json import model_json
from wilq.storage.schema_versions import reject_newer_sqlite_schema

if TYPE_CHECKING:
    from wilq.content.planning.generation_intent_v3 import (
        PlanningGenerationIntentV3Proposal,
        PlanningGenerationIntentV3Receipt,
    )

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS content_planning_generation_intent_v3_proposals (
      action_id TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
      intent_digest TEXT NOT NULL UNIQUE,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_planning_generation_intent_v3_proposals_no_update
    BEFORE UPDATE ON content_planning_generation_intent_v3_proposals
    BEGIN SELECT RAISE(ABORT, 'planning generation intent v3 proposals are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_planning_generation_intent_v3_proposals_no_replace
    BEFORE INSERT ON content_planning_generation_intent_v3_proposals
    WHEN EXISTS (SELECT 1 FROM content_planning_generation_intent_v3_proposals
                 WHERE action_id = NEW.action_id OR intent_digest = NEW.intent_digest)
    BEGIN SELECT RAISE(ABORT, 'planning generation intent v3 proposals are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_planning_generation_intent_v3_proposals_no_delete
    BEFORE DELETE ON content_planning_generation_intent_v3_proposals
    BEGIN SELECT RAISE(ABORT, 'planning generation intent v3 proposals are append-only'); END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_planning_generation_intent_v3_receipts (
      receipt_id TEXT PRIMARY KEY,
      action_id TEXT NOT NULL UNIQUE,
      receipt_digest TEXT NOT NULL UNIQUE,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_planning_generation_intent_v3_receipts_no_update
    BEFORE UPDATE ON content_planning_generation_intent_v3_receipts
    BEGIN SELECT RAISE(ABORT, 'planning generation intent v3 receipts are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_planning_generation_intent_v3_receipts_no_replace
    BEFORE INSERT ON content_planning_generation_intent_v3_receipts
    WHEN EXISTS (SELECT 1 FROM content_planning_generation_intent_v3_receipts
                 WHERE receipt_id = NEW.receipt_id OR action_id = NEW.action_id
                    OR receipt_digest = NEW.receipt_digest)
    BEGIN SELECT RAISE(ABORT, 'planning generation intent v3 receipts are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_planning_generation_intent_v3_receipts_no_delete
    BEFORE DELETE ON content_planning_generation_intent_v3_receipts
    BEGIN SELECT RAISE(ABORT, 'planning generation intent v3 receipts are append-only'); END
    """,
)
_DDL_HEADER = re.compile(r"CREATE (TABLE|TRIGGER) IF NOT EXISTS ([a-z0-9_]+)", re.IGNORECASE)


def ensure_planning_generation_intent_v3_schema(connection: sqlite3.Connection) -> None:
    reject_newer_sqlite_schema(connection)
    for statement in _SCHEMA:
        match = _DDL_HEADER.match(statement.lstrip())
        if match is None:
            raise RuntimeError("Planning generation intent v3 schema statement is invalid.")
        object_type, name = match.groups()
        connection.execute(statement)
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = ? AND name = ?",
            (object_type.lower(), name),
        ).fetchone()
        if row is None or _normalized(str(row[0])) != _normalized(statement):
            raise RuntimeError("Planning generation intent v3 schema is incomplete.")


def _normalized(sql: str) -> str:
    without_guard = re.sub(r"\bIF NOT EXISTS\b", "", sql, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", without_guard).strip().casefold()


class PlanningGenerationIntentV3StoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_planning_generation_intent_v3_proposal(
        self, proposal: PlanningGenerationIntentV3Proposal
    ) -> str:
        from wilq.content.planning.generation_intent_v3 import PlanningGenerationIntentV3Proposal

        accepted = PlanningGenerationIntentV3Proposal.model_validate(proposal, strict=True)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_planning_generation_intent_v3_proposals "
                "WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if row is not None:
                return "idempotent" if _proposal(row["payload_json"]) == accepted else "conflict"
            connection.execute(
                "INSERT INTO content_planning_generation_intent_v3_proposals "
                "(action_id, work_item_id, intent_digest, payload_json) VALUES (?, ?, ?, ?)",
                (
                    accepted.action_id,
                    accepted.snapshot.work_item_id,
                    accepted.snapshot.intent_digest,
                    model_json(accepted),
                ),
            )
        return "created"

    def load_planning_generation_intent_v3_proposal(
        self, action_id: str
    ) -> PlanningGenerationIntentV3Proposal | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT action_id, work_item_id, intent_digest, payload_json "
                "FROM content_planning_generation_intent_v3_proposals WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        if row is None:
            return None
        proposal = _proposal(row["payload_json"])
        if (row["action_id"], row["work_item_id"], row["intent_digest"]) != (
            proposal.action_id,
            proposal.snapshot.work_item_id,
            proposal.snapshot.intent_digest,
        ):
            raise ValueError("Stored planning generation intent v3 proposal index does not match.")
        return proposal

    def record_planning_generation_intent_v3_receipt(
        self, receipt: PlanningGenerationIntentV3Receipt
    ) -> str:
        from wilq.content.planning.generation_intent_v3 import PlanningGenerationIntentV3Receipt

        accepted = PlanningGenerationIntentV3Receipt.model_validate(receipt, strict=True)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            proposal = connection.execute(
                "SELECT payload_json FROM content_planning_generation_intent_v3_proposals "
                "WHERE action_id = ?",
                (accepted.action_id,),
            ).fetchone()
            if proposal is None or (
                _proposal(proposal["payload_json"]).snapshot != accepted.snapshot
            ):
                raise ValueError(
                    "Planning generation v3 receipt requires its exact stored proposal."
                )
            existing = connection.execute(
                "SELECT payload_json FROM content_planning_generation_intent_v3_receipts "
                "WHERE action_id = ? OR receipt_id = ? OR receipt_digest = ?",
                (accepted.action_id, accepted.receipt_id, accepted.receipt_digest),
            ).fetchone()
            if existing is not None:
                return (
                    "idempotent"
                    if _receipt(existing["payload_json"]) == accepted
                    else "conflict"
                )
            connection.execute(
                "INSERT INTO content_planning_generation_intent_v3_receipts "
                "(receipt_id, action_id, receipt_digest, payload_json) VALUES (?, ?, ?, ?)",
                (
                    accepted.receipt_id,
                    accepted.action_id,
                    accepted.receipt_digest,
                    model_json(accepted),
                ),
            )
        return "created"

    def load_planning_generation_intent_v3_receipt(
        self, action_id: str
    ) -> PlanningGenerationIntentV3Receipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT receipt_id, action_id, receipt_digest, payload_json "
                "FROM content_planning_generation_intent_v3_receipts WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        if row is None:
            return None
        receipt = _receipt(row["payload_json"])
        if (row["receipt_id"], row["action_id"], row["receipt_digest"]) != (
            receipt.receipt_id,
            receipt.action_id,
            receipt.receipt_digest,
        ):
            raise ValueError("Stored planning generation v3 receipt index does not match.")
        return receipt


def _proposal(value: Any) -> PlanningGenerationIntentV3Proposal:
    from wilq.content.planning.generation_intent_v3 import PlanningGenerationIntentV3Proposal

    try:
        return PlanningGenerationIntentV3Proposal.model_validate_json(value, strict=True)
    except (TypeError, ValueError, ValidationError) as error:
        raise ValueError("Stored planning generation v3 proposal is invalid.") from error


def _receipt(value: Any) -> PlanningGenerationIntentV3Receipt:
    from wilq.content.planning.generation_intent_v3 import PlanningGenerationIntentV3Receipt

    try:
        return PlanningGenerationIntentV3Receipt.model_validate_json(value, strict=True)
    except (TypeError, ValueError, ValidationError) as error:
        raise ValueError("Stored planning generation v3 receipt is invalid.") from error


__all__ = ["PlanningGenerationIntentV3StoreMixin", "ensure_planning_generation_intent_v3_schema"]
