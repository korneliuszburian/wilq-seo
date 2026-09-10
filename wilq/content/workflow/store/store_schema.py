from __future__ import annotations

import json
import sqlite3

from wilq.storage.schema_versions import (
    SQLITE_SCHEMA_VERSION,
    ensure_sqlite_schema_version,
    reject_newer_sqlite_schema,
)

_CONTENT_WORKFLOW_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS content_human_reviews (
      id TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_workflow_audits (
      audit_id TEXT PRIMARY KEY,
      human_review_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_quality_reviews (
      review_id TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_wordpress_draft_executions (
      work_item_id TEXT PRIMARY KEY,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_wordpress_draft_execution_history (
      work_item_id TEXT NOT NULL,
      handoff_id TEXT NOT NULL,
      revision_id TEXT NOT NULL,
      revision_digest TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      PRIMARY KEY (work_item_id, handoff_id, revision_id, revision_digest)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_public_deployments (
      deployment_id TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
      revision_id TEXT NOT NULL,
      revision_digest TEXT NOT NULL,
      publication_evidence_id TEXT NOT NULL,
      confirmed_at TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      UNIQUE (work_item_id, revision_id, revision_digest, publication_evidence_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_measurement_windows (
      work_item_id TEXT PRIMARY KEY,
      window_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_measurement_window_history (
      work_item_id TEXT NOT NULL,
      window_id TEXT NOT NULL,
      window_digest TEXT NOT NULL,
      stored_at TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      PRIMARY KEY (work_item_id, window_id, window_digest)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_measurement_outcomes (
      work_item_id TEXT PRIMARY KEY,
      measurement_window_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_measurement_outcome_history (
      work_item_id TEXT NOT NULL,
      measurement_window_id TEXT NOT NULL,
      outcome_id TEXT NOT NULL,
      outcome_digest TEXT NOT NULL,
      stored_at TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      PRIMARY KEY (work_item_id, measurement_window_id, outcome_id, outcome_digest)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_learning_proposals (
      work_item_id TEXT PRIMARY KEY,
      proposal_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_learning_proposal_history (
      work_item_id TEXT NOT NULL,
      measurement_window_id TEXT NOT NULL,
      proposal_id TEXT NOT NULL,
      stored_at TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      PRIMARY KEY (work_item_id, measurement_window_id, proposal_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_planning_reviews (
      decision_id TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
      stage TEXT NOT NULL,
      decision_number INTEGER NOT NULL CHECK (decision_number >= 1),
      planning_digest TEXT NOT NULL,
      decision TEXT NOT NULL,
      created_at TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      UNIQUE (work_item_id, stage, decision_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_production_classifications (
      input_digest TEXT PRIMARY KEY,
      run_id TEXT NOT NULL UNIQUE,
      run_digest TEXT NOT NULL,
      policy_id TEXT NOT NULL,
      policy_digest TEXT NOT NULL,
      packet_sha256 TEXT NOT NULL,
      judge_sha256 TEXT NOT NULL,
      recorded_by TEXT NOT NULL,
      reviewed_by TEXT NOT NULL,
      recorded_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_delivery_identity_bindings (
      binding_id TEXT PRIMARY KEY,
      binding_digest TEXT NOT NULL UNIQUE,
      canonical_path TEXT NOT NULL,
      public_url TEXT NOT NULL,
      current_work_item_id TEXT NOT NULL,
      retained_work_item_id TEXT,
      classification_run_id TEXT NOT NULL,
      classification_run_digest TEXT NOT NULL,
      classification_source_row_digest TEXT NOT NULL,
      inventory_evidence_digest TEXT NOT NULL,
      status TEXT NOT NULL CHECK (
        status IN ('exact_current', 'reconciled_retained', 'blocked')
      ),
      recorded_by TEXT NOT NULL,
      recorded_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_delivery_identity_bindings_no_update
    BEFORE UPDATE ON content_delivery_identity_bindings
    BEGIN
      SELECT RAISE(ABORT, 'content delivery identity bindings are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_delivery_identity_bindings_no_delete
    BEFORE DELETE ON content_delivery_identity_bindings
    BEGIN
      SELECT RAISE(ABORT, 'content delivery identity bindings are append-only');
    END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_source_pack_bindings (
      binding_id TEXT PRIMARY KEY,
      binding_digest TEXT NOT NULL UNIQUE,
      source_pack_id TEXT NOT NULL,
      source_pack_sha256 TEXT NOT NULL,
      identity_binding_id TEXT NOT NULL,
      identity_binding_digest TEXT NOT NULL,
      current_work_item_id TEXT NOT NULL,
      source_facts_digest TEXT NOT NULL,
      evidence_ids_digest TEXT NOT NULL,
      fresh_context_digest TEXT NOT NULL,
      status TEXT NOT NULL CHECK (status IN ('exact_current', 'blocked')),
      recorded_by TEXT NOT NULL,
      recorded_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_pack_bindings_no_update
    BEFORE UPDATE ON content_source_pack_bindings
    BEGIN
      SELECT RAISE(ABORT, 'content source-pack bindings are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_pack_bindings_no_delete
    BEFORE DELETE ON content_source_pack_bindings
    BEGIN
      SELECT RAISE(ABORT, 'content source-pack bindings are append-only');
    END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_research_packets (
      packet_id TEXT PRIMARY KEY,
      packet_digest TEXT NOT NULL UNIQUE,
      identity_binding_id TEXT NOT NULL,
      identity_binding_digest TEXT NOT NULL,
      source_pack_binding_id TEXT NOT NULL,
      source_pack_binding_digest TEXT NOT NULL,
      current_work_item_id TEXT NOT NULL,
      canonical_path TEXT NOT NULL,
      public_url TEXT NOT NULL,
      content_kind TEXT NOT NULL,
      input_digest TEXT NOT NULL,
      status TEXT NOT NULL CHECK (status IN ('exact_current', 'blocked')),
      recorded_by TEXT NOT NULL,
      recorded_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_research_packets_no_update
    BEFORE UPDATE ON content_research_packets
    BEGIN
      SELECT RAISE(ABORT, 'content research packets are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_research_packets_no_replace
    BEFORE INSERT ON content_research_packets
    WHEN EXISTS (
      SELECT 1 FROM content_research_packets
      WHERE packet_id = NEW.packet_id OR packet_digest = NEW.packet_digest
    )
    BEGIN
      SELECT RAISE(ABORT, 'content research packets are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_research_packets_no_delete
    BEFORE DELETE ON content_research_packets
    BEGIN
      SELECT RAISE(ABORT, 'content research packets are append-only');
    END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_landing_hub_authorizations (
      authorization_id TEXT PRIMARY KEY,
      authorization_digest TEXT NOT NULL UNIQUE,
      work_item_id TEXT NOT NULL,
      classification_run_id TEXT NOT NULL,
      classification_run_digest TEXT NOT NULL,
      decision_set_digest TEXT NOT NULL,
      source_packet_row_digest TEXT NOT NULL,
      canonical_path TEXT NOT NULL,
      public_url TEXT NOT NULL,
      content_kind TEXT NOT NULL CHECK (content_kind = 'landing_or_hub'),
      input_digest TEXT NOT NULL,
      authorized_by TEXT NOT NULL,
      authorized_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_landing_hub_authorizations_no_update
    BEFORE UPDATE ON content_landing_hub_authorizations
    BEGIN
      SELECT RAISE(ABORT, 'content landing/hub authorizations are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_landing_hub_authorizations_no_delete
    BEFORE DELETE ON content_landing_hub_authorizations
    BEGIN
      SELECT RAISE(ABORT, 'content landing/hub authorizations are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_landing_hub_authorizations_no_replace
    BEFORE INSERT ON content_landing_hub_authorizations
    WHEN EXISTS (
      SELECT 1 FROM content_landing_hub_authorizations
      WHERE authorization_id = NEW.authorization_id
         OR authorization_digest = NEW.authorization_digest
    )
    BEGIN
      SELECT RAISE(ABORT, 'content landing/hub authorizations are append-only');
    END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_delivery_records (
      record_id TEXT PRIMARY KEY,
      record_digest TEXT NOT NULL UNIQUE,
      binding_id TEXT NOT NULL UNIQUE,
      binding_digest TEXT NOT NULL,
      final_disposition TEXT NOT NULL CHECK (
        final_disposition IN ('keep', 'noindex', 'redirect', 'remove')
      ),
      content_state TEXT NOT NULL CHECK (
        content_state IN ('identity_bound', 'identity_blocked')
      ),
      delivery_status TEXT NOT NULL CHECK (delivery_status IN ('not_started', 'blocked')),
      robot_ready INTEGER NOT NULL CHECK (robot_ready = 0),
      blocker_code TEXT,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_delivery_records_no_update
    BEFORE UPDATE ON content_delivery_records
    BEGIN
      SELECT RAISE(ABORT, 'content delivery records are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_delivery_records_no_delete
    BEFORE DELETE ON content_delivery_records
    BEGIN
      SELECT RAISE(ABORT, 'content delivery records are append-only');
    END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_kind_receipts (
      receipt_id TEXT PRIMARY KEY,
      receipt_digest TEXT NOT NULL UNIQUE,
      work_item_id TEXT NOT NULL,
      classification_run_id TEXT NOT NULL,
      classification_run_digest TEXT NOT NULL,
      decision_set_digest TEXT NOT NULL,
      source_packet_row_digest TEXT NOT NULL,
      canonical_path TEXT NOT NULL,
      public_url TEXT NOT NULL,
      planning_input_digest TEXT NOT NULL,
      content_kind TEXT NOT NULL CHECK (content_kind = 'editorial'),
      wordpress_content_type TEXT NOT NULL,
      inventory_evidence_digest TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      UNIQUE (
        work_item_id, classification_run_digest, decision_set_digest,
        source_packet_row_digest, canonical_path, public_url,
        planning_input_digest, content_kind
      )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_refresh_preparation_authorizations (
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
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_draft_revisions (
      revision_id TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
      revision_number INTEGER NOT NULL CHECK (revision_number >= 1),
      base_revision_id TEXT,
      content_digest TEXT NOT NULL,
      created_at TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      UNIQUE (work_item_id, revision_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_new_page_briefs (
      brief_id TEXT PRIMARY KEY,
      created_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_new_page_foundations (
      foundation_id TEXT PRIMARY KEY,
      brief_id TEXT NOT NULL UNIQUE,
      work_item_id TEXT NOT NULL UNIQUE,
      created_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_draft_revision_reviews (
      decision_id TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
      revision_id TEXT NOT NULL,
      decision_number INTEGER NOT NULL CHECK (decision_number >= 1),
      revision_digest TEXT NOT NULL,
      decision TEXT NOT NULL,
      created_at TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      UNIQUE (revision_id, decision_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_target_mapping_confirmations (
      confirmation_id TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
      revision_id TEXT NOT NULL,
      revision_digest TEXT NOT NULL,
      target_contract_digest TEXT NOT NULL,
      binding_digest TEXT NOT NULL,
      confirmation_number INTEGER NOT NULL CHECK (confirmation_number >= 1),
      confirmation_digest TEXT NOT NULL,
      created_at TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      UNIQUE (
        work_item_id, revision_id, target_contract_digest, binding_digest, confirmation_number
      )
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS social_reuse_proposals (
      proposal_id TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
      platform TEXT NOT NULL,
      source_revision_id TEXT NOT NULL,
      source_revision_digest TEXT NOT NULL,
      proposal_digest TEXT NOT NULL,
      created_at TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      UNIQUE (work_item_id, platform, source_revision_id, source_revision_digest)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS social_reuse_reviews (
      review_id TEXT PRIMARY KEY,
      proposal_id TEXT NOT NULL,
      proposal_digest TEXT NOT NULL,
      review_number INTEGER NOT NULL CHECK (review_number >= 1),
      created_at TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      UNIQUE (proposal_id, proposal_digest, review_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS social_reuse_child_proposals (
      proposal_id TEXT PRIMARY KEY,
      parent_proposal_id TEXT NOT NULL,
      work_item_id TEXT NOT NULL,
      platform TEXT NOT NULL,
      source_revision_id TEXT NOT NULL,
      source_revision_digest TEXT NOT NULL,
      proposal_digest TEXT NOT NULL,
      proposal_number INTEGER NOT NULL CHECK (proposal_number >= 2),
      created_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_events (
      id TEXT PRIMARY KEY,
      action_id TEXT,
      created_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS action_mutation_audits (
      id TEXT PRIMARY KEY,
      action_id TEXT NOT NULL,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_wordpress_revision_apply_claims (
      claim_key TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
      revision_id TEXT NOT NULL,
      approval_decision_id TEXT NOT NULL,
      action_id TEXT NOT NULL,
      status TEXT NOT NULL CHECK (status IN ('claimed', 'applied', 'failed')),
      claimed_by TEXT NOT NULL,
      claimed_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_content_wordpress_apply_claim_work_item_status
    ON content_wordpress_revision_apply_claims (work_item_id, status)
    """,
    """
    CREATE TABLE IF NOT EXISTS content_new_page_revision_apply_claims (
      claim_key TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
      revision_id TEXT NOT NULL,
      revision_digest TEXT NOT NULL,
      action_id TEXT NOT NULL,
      status TEXT NOT NULL CHECK (status IN ('claimed', 'applied', 'failed')),
      result_json TEXT,
      claimed_by TEXT NOT NULL,
      claimed_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_content_new_page_apply_claim_work_item_status
    ON content_new_page_revision_apply_claims (work_item_id, status)
    """,
)


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
    if ("index", "uq_refresh_preparation_authorization_context") not in objects:
        return False
    required_columns = {
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
    for table, expected in required_columns.items():
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
