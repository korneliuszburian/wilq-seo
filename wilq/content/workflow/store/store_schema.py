from __future__ import annotations

import sqlite3

from wilq.storage.schema_versions import ensure_sqlite_schema_version, reject_newer_sqlite_schema

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
    for statement in _CONTENT_WORKFLOW_SCHEMA:
        connection.execute(statement)
    _ensure_content_human_review_updated_at(connection)
    _ensure_content_new_page_apply_result_json(connection)
    _ensure_refresh_preparation_authorization_columns(connection)
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
    ensure_sqlite_schema_version(connection)


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
    columns = {
        str(row[1])
        for row in column_rows
    }
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
