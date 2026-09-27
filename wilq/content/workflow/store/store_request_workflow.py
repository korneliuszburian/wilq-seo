"""Append-only persistence for request-owned workflow events."""

from __future__ import annotations

import sqlite3
from typing import Literal, cast

from wilq.content.workflow.request_workflow import (
    ContentRequestWorkflowEvent,
    content_request_workflow_event_request_digest,
)
from wilq.storage.model_json import model_json


def ensure_content_request_workflow_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS content_request_workflow_events (
            event_id TEXT PRIMARY KEY,
            queue_id TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            request_digest TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            UNIQUE (queue_id, idempotency_key)
        );

        CREATE TRIGGER IF NOT EXISTS content_request_workflow_events_no_update
        BEFORE UPDATE ON content_request_workflow_events
        BEGIN SELECT RAISE(ABORT, 'request workflow events are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_request_workflow_events_no_delete
        BEFORE DELETE ON content_request_workflow_events
        BEGIN SELECT RAISE(ABORT, 'request workflow events are retained'); END;
        """
    )


class ContentRequestWorkflowStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def append_content_request_workflow_event(
        self,
        event: ContentRequestWorkflowEvent,
    ) -> tuple[
        Literal["created", "idempotent", "conflict"], ContentRequestWorkflowEvent
    ]:
        accepted = ContentRequestWorkflowEvent.model_validate_json(
            event.model_dump_json(), strict=True
        )
        request_digest = content_request_workflow_event_request_digest(accepted)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM content_request_workflow_events "
                "WHERE queue_id = ? AND idempotency_key = ?",
                (accepted.queue_id, accepted.idempotency_key),
            ).fetchone()
            if row is not None:
                stored = _event_from_row(row)
                if (
                    content_request_workflow_event_request_digest(stored)
                    != request_digest
                ):
                    return "conflict", stored
                return "idempotent", stored
            connection.execute(
                "INSERT INTO content_request_workflow_events "
                "(event_id, queue_id, idempotency_key, request_digest, created_at, "
                "payload_json) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    accepted.event_id,
                    accepted.queue_id,
                    accepted.idempotency_key,
                    request_digest,
                    accepted.created_at.isoformat(),
                    model_json(accepted),
                ),
            )
        return "created", accepted

    def list_content_request_workflow_events(
        self,
        queue_id: str,
    ) -> tuple[ContentRequestWorkflowEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM content_request_workflow_events WHERE queue_id = ? "
                "ORDER BY created_at ASC, event_id ASC",
                (queue_id,),
            ).fetchall()
        return tuple(_event_from_row(row) for row in rows)


def _event_from_row(row: sqlite3.Row) -> ContentRequestWorkflowEvent:
    event = ContentRequestWorkflowEvent.model_validate_json(
        cast(str, row["payload_json"]), strict=True
    )
    if (
        event.event_id != row["event_id"]
        or event.queue_id != row["queue_id"]
        or event.idempotency_key != row["idempotency_key"]
        or event.created_at.isoformat() != row["created_at"]
        or content_request_workflow_event_request_digest(event) != row["request_digest"]
    ):
        raise ValueError("Request workflow storage columns do not match payload.")
    return event


__all__ = [
    "ContentRequestWorkflowStoreMixin",
    "ensure_content_request_workflow_schema",
]
