from __future__ import annotations

import sqlite3

from wilq.storage.schema_versions import ensure_sqlite_schema_version, reject_newer_sqlite_schema

_CONTENT_WORKFLOW_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS content_human_reviews (
      id TEXT PRIMARY KEY,
      work_item_id TEXT NOT NULL,
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
    CREATE TABLE IF NOT EXISTS content_measurement_windows (
      work_item_id TEXT PRIMARY KEY,
      window_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
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
    CREATE TABLE IF NOT EXISTS content_learning_proposals (
      work_item_id TEXT PRIMARY KEY,
      proposal_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
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
)


def ensure_content_workflow_schema(connection: sqlite3.Connection) -> None:
    reject_newer_sqlite_schema(connection)
    for statement in _CONTENT_WORKFLOW_SCHEMA:
        connection.execute(statement)
    ensure_sqlite_schema_version(connection)
