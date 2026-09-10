from __future__ import annotations

import sqlite3

import duckdb

SQLITE_SCHEMA_VERSION = 10
DUCKDB_SCHEMA_VERSION = 2
_CONTENT_SECTION_FOCUS_SCHEMA_VERSION = 4
_STOP_TELEMETRY_SCHEMA_VERSION = 5
_STOP_TELEMETRY_INDEX_SCHEMA_VERSION = 6
_LEGACY_STOP_RECONCILIATION_SCHEMA_VERSION = 7
_REFRESH_PREPARATION_AUTHORIZATION_SCHEMA_VERSION = 8
_CONTENT_DELIVERY_SCHEMA_VERSION = 9
_CONTENT_RESEARCH_PACKET_SCHEMA_VERSION = 10
_SQLITE_SCHEMA_MILESTONES = (
    (_CONTENT_SECTION_FOCUS_SCHEMA_VERSION, "table", "content_section_focus"),
    (_STOP_TELEMETRY_SCHEMA_VERSION, "table", "codex_stop_events"),
    (
        _STOP_TELEMETRY_INDEX_SCHEMA_VERSION,
        "index",
        "idx_codex_stop_events_received_at_id",
    ),
    (
        _LEGACY_STOP_RECONCILIATION_SCHEMA_VERSION,
        "table",
        "codex_stop_reconciliation_batches",
    ),
    (
        _LEGACY_STOP_RECONCILIATION_SCHEMA_VERSION,
        "table",
        "codex_stop_events_legacy",
    ),
    (
        _REFRESH_PREPARATION_AUTHORIZATION_SCHEMA_VERSION,
        "table",
        "content_refresh_preparation_authorizations",
    ),
    (_CONTENT_DELIVERY_SCHEMA_VERSION, "table", "content_delivery_identity_bindings"),
    (_CONTENT_DELIVERY_SCHEMA_VERSION, "table", "content_source_pack_bindings"),
    (_CONTENT_DELIVERY_SCHEMA_VERSION, "table", "content_delivery_records"),
    (_CONTENT_RESEARCH_PACKET_SCHEMA_VERSION, "table", "content_research_packets"),
)


def reject_newer_sqlite_schema(connection: sqlite3.Connection) -> None:
    row = connection.execute("PRAGMA user_version").fetchone()
    current_version = int(row[0]) if row is not None else 0
    if current_version > SQLITE_SCHEMA_VERSION:
        raise RuntimeError(
            f"SQLite schema version {current_version} is newer than supported "
            f"version {SQLITE_SCHEMA_VERSION}"
        )


def ensure_sqlite_schema_version(
    connection: sqlite3.Connection,
    *,
    require_all_milestones: bool = False,
) -> None:
    row = connection.execute("PRAGMA user_version").fetchone()
    current_version = int(row[0]) if row is not None else 0
    target_version = SQLITE_SCHEMA_VERSION
    if require_all_milestones:
        for schema_version, object_type, object_name in _SQLITE_SCHEMA_MILESTONES:
            if current_version >= schema_version or schema_version > SQLITE_SCHEMA_VERSION:
                continue
            object_exists = connection.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = ? AND name = ?
                """,
                (object_type, object_name),
            ).fetchone()
            if object_exists is None:
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
