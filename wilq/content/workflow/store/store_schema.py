from __future__ import annotations

import json
import sqlite3

from wilq.content.workflow.store._store_schema_ddl import _CONTENT_WORKFLOW_SCHEMA
from wilq.storage.schema_versions import (
    SQLITE_SCHEMA_VERSION,
    ensure_sqlite_schema_version,
    reject_newer_sqlite_schema,
)

_CONTENT_WORKFLOW_REQUIRED_COLUMNS = {
    "content_authoring_inventory_receipts": {
        "receipt_id",
        "receipt_digest",
        "catalog_id",
        "current_work_item_id",
        "canonical_path",
        "public_url",
        "catalog_snapshot_digest",
        "recorded_by",
        "recorded_at",
        "payload_json",
    },
    "content_human_reviews": {"updated_at"},
    "content_new_page_revision_apply_claims": {"result_json"},
    "content_refresh_preparation_authorizations": {
        "canonical_path",
        "public_url",
        "content_kind",
        "service_card_id",
    },
    "content_kind_receipts": {
        "canonical_path",
        "public_url",
        "content_kind",
        "inventory_evidence_digest",
    },
    "content_delivery_identity_bindings": {"recorded_by", "recorded_at"},
    "content_source_fact_authority_proposals": {
        "action_id",
        "proposal_digest",
        "identity_binding_id",
    },
    "content_source_fact_authority_receipts": {
        "receipt_id",
        "receipt_digest",
        "action_id",
        "action_payload_digest",
        "identity_binding_id",
        "current_work_item_id",
    },
    "content_source_pack_bindings": {
        "source_pack_id",
        "source_pack_sha256",
        "identity_binding_id",
        "identity_binding_digest",
        "current_work_item_id",
        "source_facts_digest",
        "evidence_ids_digest",
        "fresh_context_digest",
        "recorded_by",
        "recorded_at",
    },
    "content_research_packet_preparation_receipts": {
        "receipt_id",
        "receipt_digest",
        "identity_binding_id",
        "identity_binding_digest",
        "source_pack_binding_id",
        "source_pack_binding_digest",
        "current_work_item_id",
        "input_digest",
        "recorded_at",
        "payload_json",
    },
    "content_research_packets": {
        "packet_id",
        "packet_digest",
        "identity_binding_id",
        "identity_binding_digest",
        "source_pack_binding_id",
        "source_pack_binding_digest",
        "current_work_item_id",
        "canonical_path",
        "public_url",
        "content_kind",
        "input_digest",
        "status",
        "recorded_by",
        "recorded_at",
    },
    "content_landing_hub_authorizations": {
        "authorization_id",
        "authorization_digest",
        "work_item_id",
        "classification_run_id",
        "classification_run_digest",
        "decision_set_digest",
        "source_packet_row_digest",
        "canonical_path",
        "public_url",
        "content_kind",
        "input_digest",
        "authorized_by",
        "authorized_at",
    },
}


def ensure_content_workflow_schema(connection: sqlite3.Connection) -> None:
    reject_newer_sqlite_schema(connection)
    if _content_workflow_schema_is_current(connection):
        return
    for statement in _CONTENT_WORKFLOW_SCHEMA:
        connection.execute(statement)
    _ensure_content_human_review_updated_at(connection)
    _ensure_content_new_page_apply_result_json(connection)
    _ensure_refresh_preparation_authorization_columns(connection)
    _ensure_content_delivery_identity_columns(connection)
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_refresh_preparation_authorization_context
        ON content_refresh_preparation_authorizations (
          work_item_id, classification_run_digest, decision_set_digest,
          source_packet_row_digest, planning_input_digest, content_kind,
          COALESCE(service_card_id, '')
        )
        """
    )
    ensure_sqlite_schema_version(connection, require_all_milestones=True)


def _content_workflow_schema_is_current(connection: sqlite3.Connection) -> bool:
    if int(connection.execute("PRAGMA user_version").fetchone()[0]) != SQLITE_SCHEMA_VERSION:
        return False
    if not _schema_objects_are_current(connection):
        return False
    return _schema_columns_are_current(connection)


def _schema_objects_are_current(connection: sqlite3.Connection) -> bool:
    objects = {
        (str(row[0]), str(row[1]))
        for row in connection.execute(
            "SELECT type, name FROM sqlite_master WHERE type IN ('table', 'index', 'trigger')"
        )
    }
    for statement in _CONTENT_WORKFLOW_SCHEMA:
        normalized = " ".join(statement.split())
        object_type = (
            "table"
            if normalized.startswith("CREATE TABLE")
            else "trigger"
            if normalized.startswith("CREATE TRIGGER")
            else "index"
        )
        marker = f"CREATE {object_type.upper()} IF NOT EXISTS "
        name = normalized.removeprefix(marker).split(" ", 1)[0]
        if (object_type, name) not in objects:
            return False
    return ("index", "uq_refresh_preparation_authorization_context") in objects


def _schema_columns_are_current(connection: sqlite3.Connection) -> bool:
    for table, expected in _CONTENT_WORKFLOW_REQUIRED_COLUMNS.items():
        rows = list(connection.execute(f"PRAGMA table_info({table})"))
        columns = {str(row[1]) for row in rows}
        if not expected.issubset(columns):
            return False
        if table == "content_refresh_preparation_authorizations":
            service_row = next(row for row in rows if str(row[1]) == "service_card_id")
            if bool(service_row[3]):
                return False
    return True


def _ensure_content_delivery_identity_columns(connection: sqlite3.Connection) -> None:
    table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        ("content_delivery_identity_bindings",),
    ).fetchone()
    if table is None:
        return
    columns = {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(content_delivery_identity_bindings)")
    }
    if "recorded_by" in columns:
        return
    connection.execute("SAVEPOINT migrate_content_delivery_identity_actor")
    try:
        connection.execute("DROP TRIGGER IF EXISTS content_delivery_identity_bindings_no_update")
        connection.execute(
            "ALTER TABLE content_delivery_identity_bindings "
            "ADD COLUMN recorded_by TEXT NOT NULL DEFAULT ''"
        )
        rows = connection.execute(
            "SELECT binding_id, payload_json FROM content_delivery_identity_bindings"
        ).fetchall()
        for row in rows:
            payload = json.loads(str(row["payload_json"]))
            recorded_by = payload.get("recorded_by")
            if not isinstance(recorded_by, str) or not recorded_by:
                raise ValueError("Stored content delivery identity has no valid audit actor.")
            connection.execute(
                "UPDATE content_delivery_identity_bindings "
                "SET recorded_by = ? WHERE binding_id = ?",
                (recorded_by, str(row["binding_id"])),
            )
        connection.execute(
            """
            CREATE TRIGGER content_delivery_identity_bindings_no_update
            BEFORE UPDATE ON content_delivery_identity_bindings
            BEGIN
              SELECT RAISE(ABORT, 'content delivery identity bindings are append-only');
            END
            """
        )
    except (json.JSONDecodeError, ValueError, sqlite3.Error):
        connection.execute("ROLLBACK TO migrate_content_delivery_identity_actor")
        connection.execute("RELEASE migrate_content_delivery_identity_actor")
        raise
    connection.execute("RELEASE migrate_content_delivery_identity_actor")
    connection.commit()


def _ensure_content_human_review_updated_at(connection: sqlite3.Connection) -> None:
    columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(content_human_reviews)")
    }
    migrated = False
    if "updated_at" not in columns:
        connection.execute(
            "ALTER TABLE content_human_reviews ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''"
        )
        migrated = True
    missing_timestamp = connection.execute(
        "SELECT 1 FROM content_human_reviews WHERE updated_at = '' LIMIT 1"
    ).fetchone()
    if missing_timestamp is not None:
        connection.execute(
            """
            UPDATE content_human_reviews
            SET updated_at = printf('%020d', rowid)
            WHERE updated_at = ''
            """
        )
        migrated = True
    if migrated:
        connection.commit()


def _ensure_content_new_page_apply_result_json(connection: sqlite3.Connection) -> None:
    columns = {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(content_new_page_revision_apply_claims)")
    }
    if "result_json" not in columns:
        connection.execute(
            "ALTER TABLE content_new_page_revision_apply_claims ADD COLUMN result_json TEXT"
        )
        connection.commit()


def _ensure_refresh_preparation_authorization_columns(connection: sqlite3.Connection) -> None:
    table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        ("content_refresh_preparation_authorizations",),
    ).fetchone()
    if table is None:
        return
    column_rows = list(
        connection.execute("PRAGMA table_info(content_refresh_preparation_authorizations)")
    )
    columns = {str(row[1]) for row in column_rows}
    for name in ("canonical_path", "public_url"):
        if name in columns:
            continue
        connection.execute(
            "ALTER TABLE content_refresh_preparation_authorizations "
            f"ADD COLUMN {name} TEXT NOT NULL DEFAULT ''"  # nosec B608 -- fixed names.
        )
    service_not_null = next(
        (bool(row[3]) for row in column_rows if str(row[1]) == "service_card_id"),
        False,
    )
    if "content_kind" not in columns or service_not_null:
        _migrate_refresh_preparation_authorizations_v2(connection)
        return
    connection.commit()


def _migrate_refresh_preparation_authorizations_v2(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        BEGIN IMMEDIATE;
        ALTER TABLE content_refresh_preparation_authorizations
          RENAME TO content_refresh_preparation_authorizations_v1;
        CREATE TABLE content_refresh_preparation_authorizations (
          authorization_id TEXT PRIMARY KEY,
          authorization_digest TEXT NOT NULL UNIQUE,
          work_item_id TEXT NOT NULL,
          classification_run_id TEXT NOT NULL,
          classification_run_digest TEXT NOT NULL,
          decision_set_digest TEXT NOT NULL,
          source_packet_row_digest TEXT NOT NULL,
          canonical_path TEXT NOT NULL,
          public_url TEXT NOT NULL,
          planning_input_digest TEXT NOT NULL,
          content_kind TEXT NOT NULL DEFAULT 'service'
            CHECK (content_kind IN ('service', 'editorial')),
          service_card_id TEXT,
          authorized_by TEXT NOT NULL,
          authorized_at TEXT NOT NULL,
          payload_json TEXT NOT NULL
        );
        INSERT INTO content_refresh_preparation_authorizations (
          authorization_id, authorization_digest, work_item_id,
          classification_run_id, classification_run_digest, decision_set_digest,
          source_packet_row_digest, canonical_path, public_url,
          planning_input_digest, content_kind, service_card_id,
          authorized_by, authorized_at, payload_json
        )
        SELECT authorization_id, authorization_digest, work_item_id,
          classification_run_id, classification_run_digest, decision_set_digest,
          source_packet_row_digest, canonical_path, public_url,
          planning_input_digest, 'service', service_card_id,
          authorized_by, authorized_at, payload_json
        FROM content_refresh_preparation_authorizations_v1;
        DROP TABLE content_refresh_preparation_authorizations_v1;
        CREATE UNIQUE INDEX uq_refresh_preparation_authorization_context
        ON content_refresh_preparation_authorizations (
          work_item_id, classification_run_digest, decision_set_digest,
          source_packet_row_digest, planning_input_digest, content_kind,
          COALESCE(service_card_id, '')
        );
        COMMIT;
        """
    )
