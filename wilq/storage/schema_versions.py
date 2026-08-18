from __future__ import annotations

import sqlite3

import duckdb

SQLITE_SCHEMA_VERSION = 5
DUCKDB_SCHEMA_VERSION = 2
_CONTENT_SECTION_FOCUS_SCHEMA_VERSION = 4
_STOP_TELEMETRY_SCHEMA_VERSION = 5
_SQLITE_SCHEMA_MILESTONES = (
    (_CONTENT_SECTION_FOCUS_SCHEMA_VERSION, "content_section_focus"),
    (_STOP_TELEMETRY_SCHEMA_VERSION, "codex_stop_events"),
)


def reject_newer_sqlite_schema(connection: sqlite3.Connection) -> None:
    row = connection.execute("PRAGMA user_version").fetchone()
    current_version = int(row[0]) if row is not None else 0
    if current_version > SQLITE_SCHEMA_VERSION:
        raise RuntimeError(
            f"SQLite schema version {current_version} is newer than supported "
            f"version {SQLITE_SCHEMA_VERSION}"
        )


def ensure_sqlite_schema_version(connection: sqlite3.Connection) -> None:
    row = connection.execute("PRAGMA user_version").fetchone()
    current_version = int(row[0]) if row is not None else 0
    target_version = SQLITE_SCHEMA_VERSION
    for schema_version, required_table in _SQLITE_SCHEMA_MILESTONES:
        if current_version >= schema_version or schema_version > SQLITE_SCHEMA_VERSION:
            continue
        table_exists = connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (required_table,),
        ).fetchone()
        if table_exists is None:
            target_version = min(target_version, schema_version - 1)
    if current_version < target_version:
        connection.execute(f"PRAGMA user_version = {target_version}")


def reject_newer_duckdb_schema(connection: duckdb.DuckDBPyConnection) -> None:
    metadata_exists = connection.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'wilq_schema_metadata'
        """
    ).fetchone()
    if metadata_exists is None:
        return
    row = connection.execute(
        "SELECT version FROM wilq_schema_metadata WHERE store_key = 'metric_store'"
    ).fetchone()
    current_version = int(row[0]) if row is not None else 0
    if current_version > DUCKDB_SCHEMA_VERSION:
        raise RuntimeError(
            f"DuckDB schema version {current_version} is newer than supported "
            f"version {DUCKDB_SCHEMA_VERSION}"
        )


def ensure_duckdb_schema_version(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS wilq_schema_metadata (
          store_key VARCHAR PRIMARY KEY,
          version INTEGER NOT NULL
        )
        """
    )
    row = connection.execute(
        "SELECT version FROM wilq_schema_metadata WHERE store_key = 'metric_store'"
    ).fetchone()
    current_version = int(row[0]) if row is not None else 0
    if row is None:
        connection.execute(
            "INSERT INTO wilq_schema_metadata (store_key, version) VALUES ('metric_store', ?)",
            [DUCKDB_SCHEMA_VERSION],
        )
    elif current_version < DUCKDB_SCHEMA_VERSION:
        connection.execute(
            "UPDATE wilq_schema_metadata SET version = ? WHERE store_key = 'metric_store'",
            [DUCKDB_SCHEMA_VERSION],
        )
