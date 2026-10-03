"""Append-only local receipts and one-shot dispatch for revision repair."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel

from wilq.content.drafts.revision_repair_action import (
    ContentRevisionRepairBinding,
    ContentRevisionRepairReceipt,
    ContentRevisionRepairSnapshot,
    ContentRevisionRepairWorkerStart,
)
from wilq.schemas.core import utc_now

_Stage = Literal["snapshot", "receipt", "dispatch", "worker_start"]
_Model = TypeVar("_Model", bound=BaseModel)
_SELECT = (
    "SELECT payload_json FROM content_revision_repair_authority WHERE action_id = ? AND stage = ?"
)
_INSERT = (
    "INSERT INTO content_revision_repair_authority (action_id, stage, payload_json) "
    "VALUES (?, ?, ?)"
)


def ensure_content_revision_repair_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS content_revision_repair_authority "
        "(action_id TEXT NOT NULL, stage TEXT NOT NULL CHECK (stage IN "
        "('snapshot', 'receipt', 'dispatch', 'worker_start')), payload_json TEXT NOT NULL, "
        "PRIMARY KEY (action_id, stage))"
    )
    connection.execute(
        "CREATE TRIGGER IF NOT EXISTS content_revision_repair_authority_no_update "
        "BEFORE UPDATE ON content_revision_repair_authority "
        "BEGIN SELECT RAISE(ABORT, 'content revision repair authority is append-only'); END"
    )
    connection.execute(
        "CREATE TRIGGER IF NOT EXISTS content_revision_repair_authority_no_delete "
        "BEFORE DELETE ON content_revision_repair_authority "
        "BEGIN SELECT RAISE(ABORT, 'content revision repair authority is append-only'); END"
    )
    connection.execute(
        "CREATE TRIGGER IF NOT EXISTS content_revision_repair_authority_no_replace "
        "BEFORE INSERT ON content_revision_repair_authority "
        "WHEN EXISTS (SELECT 1 FROM content_revision_repair_authority "
        "WHERE action_id = NEW.action_id AND stage = NEW.stage) "
        "BEGIN SELECT RAISE(ABORT, 'content revision repair authority is append-only'); END"
    )


def _load[T: BaseModel](
    connection: sqlite3.Connection, action_id: str, stage: _Stage, model: type[T]
) -> T | None:
    row = connection.execute(_SELECT, (action_id, stage)).fetchone()
    if row is None:
        return None
    value = model.model_validate_json(row["payload_json"])
    actual = (
        value.action_id
        if isinstance(value, ContentRevisionRepairSnapshot)
        else value.snapshot.action_id
        if isinstance(value, ContentRevisionRepairReceipt)
        else value.action_id
        if isinstance(value, ContentRevisionRepairBinding)
        else value.binding.action_id
        if isinstance(value, ContentRevisionRepairWorkerStart)
        else None
    )
    if actual != action_id:
        raise ValueError("content_revision_repair_stored_identity_mismatch")
    return value


def _record(
    connection: sqlite3.Connection, action_id: str, stage: _Stage, value: BaseModel
) -> Literal["created", "idempotent", "conflict"]:
    old = connection.execute(_SELECT, (action_id, stage)).fetchone()
    if old is not None:
        return "idempotent" if old["payload_json"] == value.model_dump_json() else "conflict"
    connection.execute(_INSERT, (action_id, stage, value.model_dump_json()))
    return "created"


class ContentRevisionRepairStoreMixin:
    path: Path

    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_content_revision_repair_snapshot(
        self, snapshot: ContentRevisionRepairSnapshot
    ) -> Literal["created", "idempotent", "conflict"]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            return _record(connection, snapshot.action_id, "snapshot", snapshot)

    def load_content_revision_repair_snapshot(
        self, action_id: str
    ) -> ContentRevisionRepairSnapshot | None:
        with self._connect() as connection:
            return _load(connection, action_id, "snapshot", ContentRevisionRepairSnapshot)

    def record_content_revision_repair_receipt(
        self, receipt: ContentRevisionRepairReceipt
    ) -> Literal["created", "idempotent", "conflict"]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            snapshot = _load(
                connection,
                receipt.snapshot.action_id,
                "snapshot",
                ContentRevisionRepairSnapshot,
            )
            if snapshot != receipt.snapshot:
                raise ValueError("content_revision_repair_snapshot_changed")
            return _record(connection, receipt.snapshot.action_id, "receipt", receipt)

    def load_content_revision_repair_receipt(
        self, action_id: str
    ) -> ContentRevisionRepairReceipt | None:
        with self._connect() as connection:
            return _load(connection, action_id, "receipt", ContentRevisionRepairReceipt)

    def record_content_revision_repair_binding(
        self, receipt: ContentRevisionRepairReceipt, binding: ContentRevisionRepairBinding
    ) -> Literal["created", "idempotent", "conflict"]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = _load(
                connection,
                receipt.snapshot.action_id,
                "receipt",
                ContentRevisionRepairReceipt,
            )
            if current != receipt or binding.receipt_digest != receipt.receipt_digest:
                raise ValueError("content_revision_repair_receipt_changed")
            return _record(connection, binding.action_id, "dispatch", binding)

    def load_content_revision_repair_binding(
        self, action_id: str
    ) -> ContentRevisionRepairBinding | None:
        with self._connect() as connection:
            return _load(connection, action_id, "dispatch", ContentRevisionRepairBinding)

    def load_content_revision_repair_worker_start(
        self, action_id: str
    ) -> ContentRevisionRepairWorkerStart | None:
        with self._connect() as connection:
            return _load(connection, action_id, "worker_start", ContentRevisionRepairWorkerStart)

    def start_content_revision_repair_worker(
        self,
        receipt: ContentRevisionRepairReceipt,
        binding: ContentRevisionRepairBinding,
        current_guard: Callable[[], bool],
    ) -> bool:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            snapshot = _load(
                connection,
                binding.action_id,
                "snapshot",
                ContentRevisionRepairSnapshot,
            )
            current_receipt = _load(
                connection,
                binding.action_id,
                "receipt",
                ContentRevisionRepairReceipt,
            )
            current_binding = _load(
                connection,
                binding.action_id,
                "dispatch",
                ContentRevisionRepairBinding,
            )
            started = _load(
                connection,
                binding.action_id,
                "worker_start",
                ContentRevisionRepairWorkerStart,
            )
            if (
                snapshot != receipt.snapshot
                or current_receipt != receipt
                or current_binding != binding
                or started is not None
                or not current_guard()
            ):
                return False
            worker = ContentRevisionRepairWorkerStart(binding=binding, started_at=utc_now())
            connection.execute(
                _INSERT,
                (binding.action_id, "worker_start", worker.model_dump_json()),
            )
            return True


__all__ = ["ContentRevisionRepairStoreMixin", "ensure_content_revision_repair_schema"]
