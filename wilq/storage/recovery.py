from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypedDict

import duckdb

from wilq.storage.private_paths import prepare_private_store_path


class StorageProof(TypedDict):
    sqlite_schema_version: int
    duckdb_schema_version: int
    revision_count: int
    audit_count: int
    metric_fact_count: int


def copy_sqlite_store(source: Path, destination: Path) -> None:
    _require_distinct_new_destination(source, destination)
    prepare_private_store_path(destination, normalize_existing_parent=False)
    source_uri = f"{source.resolve().as_uri()}?mode=ro"
    try:
        with (
            sqlite3.connect(source_uri, uri=True) as source_connection,
            sqlite3.connect(destination) as destination_connection,
        ):
            source_connection.backup(destination_connection)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    destination.chmod(0o600)


def copy_duckdb_store(source: Path, destination: Path) -> None:
    _require_distinct_new_destination(source, destination)
    prepare_private_store_path(destination, normalize_existing_parent=False)
    destination_connection = duckdb.connect(str(destination))
    copied = False
    try:
        target_row = destination_connection.execute("SELECT current_database()").fetchone()
        if target_row is None:
            raise RuntimeError("DuckDB recovery destination has no active catalog")
        target_catalog = str(target_row[0])
        destination_connection.execute(
            f"ATTACH {_sql_string(source.resolve().as_posix())} AS source_store (READ_ONLY)"
        )
        destination_connection.execute(
            f"COPY FROM DATABASE source_store TO {_sql_identifier(target_catalog)}"
        )
        copied = True
    finally:
        destination_connection.close()
        if not copied:
            destination.unlink(missing_ok=True)
    destination.chmod(0o600)


def copy_storage_pair(
    *,
    sqlite_source: Path,
    duckdb_source: Path,
    sqlite_destination: Path,
    duckdb_destination: Path,
) -> StorageProof:
    _require_distinct_new_destination(sqlite_source, sqlite_destination)
    _require_distinct_new_destination(duckdb_source, duckdb_destination)
    if sqlite_destination.resolve() == duckdb_destination.resolve():
        raise ValueError("SQLite and DuckDB recovery destinations must differ")
    try:
        copy_sqlite_store(sqlite_source, sqlite_destination)
        copy_duckdb_store(duckdb_source, duckdb_destination)
        return storage_proof(sqlite_destination, duckdb_destination)
    except Exception:
        sqlite_destination.unlink(missing_ok=True)
        duckdb_destination.unlink(missing_ok=True)
        raise


def storage_proof(sqlite_path: Path, duckdb_path: Path) -> StorageProof:
    sqlite_uri = f"{sqlite_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(sqlite_uri, uri=True) as connection:
        sqlite_version_row = connection.execute("PRAGMA user_version").fetchone()
        revision_count = _sqlite_table_count(connection, "content_draft_revisions")
        audit_count = sum(
            _sqlite_table_count(connection, table)
            for table in (
                "audit_events",
                "content_workflow_audits",
                "action_mutation_audits",
            )
        )
    with duckdb.connect(str(duckdb_path), read_only=True) as connection:
        version_row = connection.execute(
            "SELECT version FROM wilq_schema_metadata WHERE store_key = 'metric_store'"
        ).fetchone()
        if version_row is None:
            raise RuntimeError("DuckDB metric store schema version is missing")
        metric_count_row = connection.execute(
            "SELECT COUNT(*) FROM connector_metric_facts"
        ).fetchone()
        if metric_count_row is None:
            raise RuntimeError("DuckDB metric fact count is unavailable")
        metric_fact_count = int(metric_count_row[0])
    return StorageProof(
        sqlite_schema_version=int(sqlite_version_row[0]),
        duckdb_schema_version=int(version_row[0]),
        revision_count=revision_count,
        audit_count=audit_count,
        metric_fact_count=metric_fact_count,
    )


def _require_distinct_new_destination(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.resolve() == destination.resolve():
        raise ValueError("Recovery destination must differ from the source store")
    if destination.exists():
        raise FileExistsError(destination)


def _sqlite_table_count(connection: sqlite3.Connection, table: str) -> int:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    if exists is None:
        return 0
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sql_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'
