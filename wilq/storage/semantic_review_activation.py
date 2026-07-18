from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypedDict

from wilq.storage.recovery import copy_storage_pair, storage_proof
from wilq.storage.schema_versions import (
    ensure_sqlite_schema_version,
    reject_newer_sqlite_schema,
)


class SemanticReviewActivationReport(TypedDict):
    status: str
    backup_sqlite: str
    backup_duckdb: str
    before: dict[str, int]
    after: dict[str, int]
    table_created: bool


class MaintenanceWindowRequired(RuntimeError):
    """Raised when a state mutation is attempted without explicit approval."""


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


def activate_semantic_review_storage(
    *,
    state_path: Path,
    metric_path: Path,
    backup_state_path: Path,
    backup_metric_path: Path,
    approved_maintenance_window: bool,
) -> SemanticReviewActivationReport:
    """Backup both stores, then activate semantic-review storage transactionally.

    This is an explicit maintenance seam. The normal API never calls it, and
    callers must provide the approval flag plus fresh, distinct backup paths.
    """
    if not approved_maintenance_window:
        raise MaintenanceWindowRequired(
            "Semantic-review activation requires an approved maintenance window."
        )
    before = storage_proof(state_path, metric_path)
    copy_storage_pair(
        sqlite_source=state_path,
        duckdb_source=metric_path,
        sqlite_destination=backup_state_path,
        duckdb_destination=backup_metric_path,
    )
    backup = storage_proof(backup_state_path, backup_metric_path)
    if backup != before:
        raise RuntimeError("Storage backup proof does not match the source state.")

    table_created = False
    connection = sqlite3.connect(state_path)
    try:
        reject_newer_sqlite_schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        existed = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("content_semantic_reviews",),
        ).fetchone()
        connection.execute(_CREATE_TABLE)
        ensure_sqlite_schema_version(connection)
        connection.commit()
        table_created = existed is None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    after = storage_proof(state_path, metric_path)
    if (
        after["revision_count"] != before["revision_count"]
        or after["audit_count"] != before["audit_count"]
        or after["metric_fact_count"] != before["metric_fact_count"]
    ):
        raise RuntimeError("Semantic-review activation changed existing store counts.")
    return {
        "status": "activated" if table_created else "already_active",
        "backup_sqlite": str(backup_state_path),
        "backup_duckdb": str(backup_metric_path),
        "before": before,
        "after": after,
        "table_created": table_created,
    }


__all__ = [
    "MaintenanceWindowRequired",
    "SemanticReviewActivationReport",
    "activate_semantic_review_storage",
]
