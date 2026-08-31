from __future__ import annotations

import sqlite3

_PROPOSALS = """
CREATE TABLE {table} (
  proposal_id TEXT PRIMARY KEY,
  work_item_id TEXT NOT NULL,
  proposal_version INTEGER NOT NULL CHECK (proposal_version >= 1),
  service_card_id TEXT,
  content_kind TEXT NOT NULL CHECK (content_kind IN ('service', 'editorial')),
  subject_key TEXT NOT NULL,
  planning_input_digest TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  CHECK ((content_kind = 'service' AND service_card_id IS NOT NULL
    AND subject_key = service_card_id)
    OR (content_kind = 'editorial' AND service_card_id IS NULL AND subject_key = 'editorial')),
  UNIQUE (work_item_id, proposal_version),
  UNIQUE (work_item_id, content_kind, subject_key, planning_input_digest)
)
"""
_REPAIRS = """
CREATE TABLE {table} (
  proposal_id TEXT PRIMARY KEY,
  work_item_id TEXT NOT NULL,
  proposal_version INTEGER NOT NULL CHECK (proposal_version >= 1),
  service_card_id TEXT,
  content_kind TEXT NOT NULL CHECK (content_kind IN ('service', 'editorial')),
  subject_key TEXT NOT NULL,
  planning_input_digest TEXT NOT NULL,
  supersedes_proposal_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  CHECK ((content_kind = 'service' AND service_card_id IS NOT NULL
    AND subject_key = service_card_id)
    OR (content_kind = 'editorial' AND service_card_id IS NULL AND subject_key = 'editorial')),
  UNIQUE (work_item_id, proposal_version)
)
"""
_JOBS = """
CREATE TABLE {table} (
  work_item_id TEXT NOT NULL,
  service_card_id TEXT,
  content_kind TEXT NOT NULL CHECK (content_kind IN ('service', 'editorial')),
  subject_key TEXT NOT NULL,
  planning_input_digest TEXT NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK ((content_kind = 'service' AND service_card_id IS NOT NULL
    AND subject_key = service_card_id)
    OR (content_kind = 'editorial' AND service_card_id IS NULL AND subject_key = 'editorial')),
  PRIMARY KEY (work_item_id, content_kind, subject_key, planning_input_digest)
)
"""


def ensure_generated_proposal_schema(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")
    try:
        _ensure_table(connection, "content_planning_proposals", _PROPOSALS)
        _ensure_table(connection, "content_planning_proposal_repairs", _REPAIRS)
        _ensure_table(connection, "content_planning_generation_jobs", _JOBS)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS codex_runs (
              id TEXT PRIMARY KEY,
              started_at TEXT NOT NULL,
              payload_json TEXT NOT NULL
            )
            """
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def _ensure_table(connection: sqlite3.Connection, table: str, schema: str) -> None:
    if not _table_exists(connection, table):
        connection.execute(schema.format(table=table))  # nosec B608 -- fixed names.
        return
    columns = {
        str(row[1]): (bool(row[3]), int(row[5]))
        for row in connection.execute(f"PRAGMA table_info({table})")
    }
    expected_pk = 3 if table == "content_planning_generation_jobs" else 0
    if (
        "content_kind" in columns
        and "subject_key" in columns
        and not columns["service_card_id"][0]
        and columns["subject_key"][1] == expected_pk
    ):
        return
    _rebuild_table(connection, table, schema)


def _rebuild_table(connection: sqlite3.Connection, table: str, schema: str) -> None:
    legacy = f"{table}_service_v1"
    connection.execute(f"ALTER TABLE {table} RENAME TO {legacy}")  # nosec B608
    connection.execute(schema.format(table=table))  # nosec B608 -- fixed names.
    columns = [str(row[1]) for row in connection.execute(f"PRAGMA table_info({legacy})")]
    copied = [name for name in columns if name not in {"content_kind", "subject_key"}]
    split_at = 2 if table == "content_planning_generation_jobs" else 4
    target_columns = [*copied[:split_at], "content_kind", "subject_key", *copied[split_at:]]
    select_values = [
        "'service'"
        if name == "content_kind"
        else "service_card_id"
        if name == "subject_key"
        else name
        for name in target_columns
    ]
    connection.execute(
        f"INSERT INTO {table} ({', '.join(target_columns)}) "  # nosec B608
        f"SELECT {', '.join(select_values)} FROM {legacy}"  # nosec B608
    )
    connection.execute(f"DROP TABLE {legacy}")  # nosec B608


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        is not None
    )


__all__ = ["ensure_generated_proposal_schema"]
