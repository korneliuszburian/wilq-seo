from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import cast

from wilq.content.quality.semantic_review_contracts import ContentSemanticReview
from wilq.content.workflow.codex_revision_commit import (
    codex_completion_state,
    persist_codex_completion,
)
from wilq.schemas import CodexRun
from wilq.security.redaction import redact_mapping
from wilq.storage.local_state import DEFAULT_STATE_DB, state_db_path
from wilq.storage.private_paths import prepare_private_store_path
from wilq.storage.schema_versions import (
    ensure_sqlite_schema_version,
    reject_newer_sqlite_schema,
)


class SemanticReviewStorageActivationRequired(RuntimeError):
    pass


class SemanticReviewConflict(RuntimeError):
    pass


def content_semantic_review_store() -> ContentSemanticReviewStore:
    return ContentSemanticReviewStore(state_db_path())


class ContentSemanticReviewStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write_ready(self) -> bool:
        if self.path != DEFAULT_STATE_DB:
            return True
        connection = self._read_connection()
        if connection is None:
            return False
        with connection:
            return _table_exists(connection, "content_semantic_reviews")

    def latest(self, work_item_id: str) -> ContentSemanticReview | None:
        connection = self._read_connection()
        if connection is None:
            return None
        with connection:
            if not _table_exists(connection, "content_semantic_reviews"):
                return None
            row = connection.execute(
                """
                SELECT payload_json
                FROM content_semantic_reviews
                WHERE work_item_id = ?
                ORDER BY created_at DESC, review_id DESC
                LIMIT 1
                """,
                (work_item_id,),
            ).fetchone()
        return _review_from_row(row)

    def for_revision(
        self,
        work_item_id: str,
        revision_id: str,
        revision_digest: str,
    ) -> ContentSemanticReview | None:
        connection = self._read_connection()
        if connection is None:
            return None
        with connection:
            if not _table_exists(connection, "content_semantic_reviews"):
                return None
            row = _exact_review_row(
                connection,
                work_item_id,
                revision_id,
                revision_digest,
            )
        return _review_from_row(row)

    def for_revision_id(
        self,
        work_item_id: str,
        revision_id: str,
    ) -> ContentSemanticReview | None:
        connection = self._read_connection()
        if connection is None:
            return None
        with connection:
            if not _table_exists(connection, "content_semantic_reviews"):
                return None
            row = connection.execute(
                """
                SELECT payload_json
                FROM content_semantic_reviews
                WHERE work_item_id = ?
                  AND revision_id = ?
                  AND criteria_version = 'wilq_semantic_content_review_v1'
                LIMIT 1
                """,
                (work_item_id, revision_id),
            ).fetchone()
        return _review_from_row(row)

    def save_generated(
        self,
        review: ContentSemanticReview,
        completed_run: CodexRun,
    ) -> ContentSemanticReview:
        safe_review, safe_run = _validated_models(review, completed_run)
        with self._write_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if (
                _exact_review_row(
                    connection,
                    safe_review.work_item_id,
                    safe_review.revision_id,
                    safe_review.revision_digest,
                )
                is not None
            ):
                raise SemanticReviewConflict("Semantic review appeared concurrently.")
            if codex_completion_state(connection, safe_run) != "started":
                raise SemanticReviewConflict("Semantic review run is already completed.")
            connection.execute(
                """
                INSERT INTO content_semantic_reviews (
                  review_id, work_item_id, revision_id, revision_digest,
                  criteria_version, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    safe_review.review_id,
                    safe_review.work_item_id,
                    safe_review.revision_id,
                    safe_review.revision_digest,
                    safe_review.criteria_version,
                    safe_review.created_at.isoformat(),
                    safe_review.model_dump_json(),
                ),
            )
            persist_codex_completion(connection, safe_run)
        return safe_review

    def _write_connection(self) -> sqlite3.Connection:
        prepare_private_store_path(
            self.path,
            normalize_existing_parent=self.path == DEFAULT_STATE_DB,
        )
        connection = sqlite3.connect(self.path)
        self.path.chmod(0o600)
        connection.row_factory = sqlite3.Row
        reject_newer_sqlite_schema(connection)
        if self.path == DEFAULT_STATE_DB and not _table_exists(
            connection, "content_semantic_reviews"
        ):
            connection.close()
            raise SemanticReviewStorageActivationRequired(
                "Semantic-review storage requires an approved maintenance window."
            )
        connection.execute(_CREATE_TABLE)
        ensure_sqlite_schema_version(connection)
        return connection

    def _read_connection(self) -> sqlite3.Connection | None:
        if not self.path.exists():
            return None
        connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        reject_newer_sqlite_schema(connection)
        return connection


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS content_semantic_reviews (
  review_id TEXT PRIMARY KEY,
  work_item_id TEXT NOT NULL,
  revision_id TEXT NOT NULL,
  revision_digest TEXT NOT NULL,
  criteria_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  UNIQUE (work_item_id, revision_id, revision_digest, criteria_version)
)
"""


def _exact_review_row(
    connection: sqlite3.Connection,
    work_item_id: str,
    revision_id: str,
    revision_digest: str,
) -> sqlite3.Row | None:
    return cast(
        sqlite3.Row | None,
        connection.execute(
            """
            SELECT payload_json
            FROM content_semantic_reviews
            WHERE work_item_id = ?
              AND revision_id = ?
              AND revision_digest = ?
              AND criteria_version = 'wilq_semantic_content_review_v1'
            LIMIT 1
            """,
            (work_item_id, revision_id, revision_digest),
        ).fetchone(),
    )


def _review_from_row(row: sqlite3.Row | None) -> ContentSemanticReview | None:
    if row is None:
        return None
    return ContentSemanticReview.model_validate(json.loads(cast(str, row["payload_json"])))


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (name,),
        ).fetchone()
        is not None
    )


def _validated_models(
    review: ContentSemanticReview,
    completed_run: CodexRun,
) -> tuple[ContentSemanticReview, CodexRun]:
    safe_review = ContentSemanticReview.model_validate(
        redact_mapping(review.model_dump(mode="json"))
    )
    safe_run = CodexRun.model_validate(redact_mapping(completed_run.model_dump(mode="json")))
    if safe_review.codex_run_id != safe_run.id:
        raise ValueError("Semantic review must reference its exact Codex run.")
    if safe_run.status != "completed" or safe_run.completed_at is None or safe_run.error:
        raise ValueError("Semantic review requires one successful terminal Codex run.")
    return safe_review, safe_run


__all__ = [
    "ContentSemanticReviewStore",
    "SemanticReviewConflict",
    "SemanticReviewStorageActivationRequired",
    "content_semantic_review_store",
]
