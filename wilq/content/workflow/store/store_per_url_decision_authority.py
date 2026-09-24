"""Append-only persistence for semantic per-URL decision observations."""

from __future__ import annotations

import sqlite3
from typing import Literal, cast

from wilq.content.workflow.per_url_decision_authority import (
    ContentPerUrlDecisionObservation,
)
from wilq.storage.model_json import model_json


def ensure_per_url_decision_authority_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS content_per_url_decision_observations (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            observation_id TEXT NOT NULL UNIQUE,
            canonical_path TEXT NOT NULL,
            current_work_item_id TEXT NOT NULL,
            semantic_row_digest TEXT NOT NULL,
            evidence_digest TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS content_per_url_decision_observations_by_path
        ON content_per_url_decision_observations(canonical_path, sequence);

        CREATE INDEX IF NOT EXISTS content_per_url_decision_observations_by_work_item
        ON content_per_url_decision_observations(current_work_item_id, sequence);

        CREATE TRIGGER IF NOT EXISTS content_per_url_decision_observations_no_update
        BEFORE UPDATE ON content_per_url_decision_observations
        BEGIN SELECT RAISE(ABORT, 'per-URL decision observations are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_per_url_decision_observations_no_replace
        BEFORE INSERT ON content_per_url_decision_observations
        WHEN EXISTS (
            SELECT 1 FROM content_per_url_decision_observations
            WHERE observation_id = NEW.observation_id
        )
        BEGIN SELECT RAISE(ABORT, 'per-URL decision observations are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS content_per_url_decision_observations_no_delete
        BEFORE DELETE ON content_per_url_decision_observations
        BEGIN SELECT RAISE(ABORT, 'per-URL decision observations are append-only'); END;
        """
    )


class ContentPerUrlDecisionAuthorityStoreMixin:
    def _connect(self) -> sqlite3.Connection:
        raise NotImplementedError

    def record_content_per_url_decision_observation(
        self,
        observation: ContentPerUrlDecisionObservation,
    ) -> tuple[Literal["created", "idempotent", "conflict"], ContentPerUrlDecisionObservation]:
        accepted = ContentPerUrlDecisionObservation.model_validate_json(
            observation.model_dump_json(), strict=True
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload_json FROM content_per_url_decision_observations "
                "WHERE observation_id = ?",
                (accepted.observation_id,),
            ).fetchone()
            if row is not None:
                stored = ContentPerUrlDecisionObservation.model_validate_json(
                    cast(str, row["payload_json"]), strict=True
                )
                return ("idempotent" if stored == accepted else "conflict", stored)
            connection.execute(
                "INSERT INTO content_per_url_decision_observations "
                "(observation_id, canonical_path, current_work_item_id, "
                "semantic_row_digest, evidence_digest, observed_at, payload_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    accepted.observation_id,
                    accepted.policy_facts.canonical_path,
                    accepted.policy_facts.current_work_item_id,
                    accepted.semantic_row_digest,
                    accepted.evidence_digest,
                    accepted.observed_at.isoformat(),
                    model_json(accepted),
                ),
            )
        return "created", accepted

    def load_content_per_url_decision_observation(
        self,
        observation_id: str,
    ) -> ContentPerUrlDecisionObservation | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM content_per_url_decision_observations "
                "WHERE observation_id = ?",
                (observation_id,),
            ).fetchone()
        return (
            None
            if row is None
            else ContentPerUrlDecisionObservation.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
        )

    def list_content_per_url_decision_observations(
        self,
        canonical_path: str,
    ) -> list[ContentPerUrlDecisionObservation]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM content_per_url_decision_observations "
                "WHERE canonical_path = ? ORDER BY sequence ASC",
                (canonical_path,),
            ).fetchall()
        return [
            ContentPerUrlDecisionObservation.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
            for row in rows
        ]

    def list_content_per_url_decision_observations_for_scope(
        self,
        *,
        canonical_path: str,
        current_work_item_id: str,
    ) -> list[ContentPerUrlDecisionObservation]:
        """Read the newest history visible through either stable scope identity."""

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM content_per_url_decision_observations "
                "WHERE canonical_path = ? OR current_work_item_id = ? "
                "ORDER BY sequence ASC",
                (canonical_path, current_work_item_id),
            ).fetchall()
        return [
            ContentPerUrlDecisionObservation.model_validate_json(
                cast(str, row["payload_json"]), strict=True
            )
            for row in rows
        ]


__all__ = [
    "ContentPerUrlDecisionAuthorityStoreMixin",
    "ensure_per_url_decision_authority_schema",
]
