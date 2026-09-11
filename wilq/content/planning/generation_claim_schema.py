from __future__ import annotations

import sqlite3

_SCHEMA = """
CREATE TABLE {table} (
  claim_key TEXT PRIMARY KEY,
  work_item_id TEXT NOT NULL,
  service_card_id TEXT,
  content_kind TEXT NOT NULL CHECK (content_kind IN ('service', 'editorial')),
  subject_key TEXT NOT NULL,
  planning_input_digest TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('claimed', 'finished', 'failed')),
  claim_owner TEXT NOT NULL,
  claim_version INTEGER NOT NULL DEFAULT 1 CHECK (claim_version >= 1),
  refresh_preparation_authorization_id TEXT,
  refresh_preparation_authorization_digest TEXT,
  claimed_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK ((content_kind = 'service' AND service_card_id IS NOT NULL
    AND subject_key = service_card_id)
    OR (content_kind = 'editorial' AND service_card_id IS NULL AND subject_key = 'editorial')),
  UNIQUE (work_item_id, content_kind, subject_key, planning_input_digest)
)
"""


def ensure_generation_claim_schema(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")
    try:
        if not _table_exists(connection):
            connection.execute(_SCHEMA.format(table="content_planning_generation_claims"))
        elif _needs_rebuild(connection):
            _rebuild(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _needs_rebuild(connection: sqlite3.Connection) -> bool:
    columns = {
        str(row[1]): bool(row[3])
        for row in connection.execute("PRAGMA table_info(content_planning_generation_claims)")
    }
    return (
        "content_kind" not in columns
        or "subject_key" not in columns
        or columns["service_card_id"]
        or "refresh_preparation_authorization_id" not in columns
        or "refresh_preparation_authorization_digest" not in columns
    )


def _rebuild(connection: sqlite3.Connection) -> None:
    table = "content_planning_generation_claims"
    legacy = f"{table}_service_v1"
    connection.execute(f"ALTER TABLE {table} RENAME TO {legacy}")
    connection.execute(_SCHEMA.format(table=table))
    old_columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({legacy})")}
    optional = (
        "refresh_preparation_authorization_id",
        "refresh_preparation_authorization_digest",
    )
    target = [
        "claim_key",
        "work_item_id",
        "service_card_id",
        "content_kind",
        "subject_key",
        "planning_input_digest",
        "status",
        "claim_owner",
        "claim_version",
        *optional,
        "claimed_at",
        "updated_at",
    ]
    selected = [
        "'service'"
        if name == "content_kind"
        else "service_card_id"
        if name == "subject_key"
        else name
        if name in old_columns
        else "NULL"
        for name in target
    ]
    connection.execute(
        f"INSERT INTO {table} ({', '.join(target)}) "  # nosec B608
        f"SELECT {', '.join(selected)} FROM {legacy}"  # nosec B608
    )
    connection.execute(f"DROP TABLE {legacy}")


def _table_exists(connection: sqlite3.Connection) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'content_planning_generation_claims'"
        ).fetchone()
        is not None
    )


__all__ = ["ensure_generation_claim_schema"]
