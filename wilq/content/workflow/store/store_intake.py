"""Persistence for idempotent ask-only content intake requests."""

from __future__ import annotations

import sqlite3
from typing import Literal, cast

from wilq.content.workflow.intake import ContentIntakeQueueItem
from wilq.storage.model_json import model_json


def ensure_content_intake_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS content_intake_requests (
            queue_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL UNIQUE,
            input_digest TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE TRIGGER IF NOT EXISTS content_intake_requests_no_update
        BEFORE UPDATE ON content_intake_requests
        BEGIN SELECT RAISE(ABORT, 'content intake requests are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_intake_requests_no_delete
        BEFORE DELETE ON content_intake_requests
        BEGIN SELECT RAISE(ABORT, 'content intake requests are retained'); END;
        """
    )


class ContentIntakeStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def create_content_intake_request(
        self,
        item: ContentIntakeQueueItem,
    ) -> tuple[Literal["created", "idempotent", "conflict"], ContentIntakeQueueItem]:
        accepted = ContentIntakeQueueItem.model_validate_json(
            item.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM content_intake_requests WHERE request_id = ?",
                (str(accepted.request_id),),
            ).fetchone()
            if row is not None:
                stored = _item_from_row(row)
                if stored.input_digest != accepted.input_digest:
                    return "conflict", stored
                return "idempotent", stored
            connection.execute(
                "INSERT INTO content_intake_requests "
                "(queue_id, request_id, input_digest, created_at, payload_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    accepted.queue_id,
                    str(accepted.request_id),
                    accepted.input_digest,
                    accepted.created_at.isoformat(),
                    model_json(accepted),
                ),
            )
        return "created", accepted

    def load_content_intake_request(self, queue_id: str) -> ContentIntakeQueueItem | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM content_intake_requests WHERE queue_id = ?",
                (queue_id,),
            ).fetchone()
        return None if row is None else _item_from_row(row)


def _item_from_row(row: sqlite3.Row) -> ContentIntakeQueueItem:
    item = ContentIntakeQueueItem.model_validate_json(
        cast(str, row["payload_json"]), strict=True
    )
    if (
        item.queue_id != row["queue_id"]
        or str(item.request_id) != row["request_id"]
        or item.input_digest != row["input_digest"]
        or item.created_at.isoformat() != row["created_at"]
    ):
        raise ValueError("Content intake storage columns do not match payload.")
    return item


__all__ = ["ContentIntakeStoreMixin", "ensure_content_intake_schema"]
