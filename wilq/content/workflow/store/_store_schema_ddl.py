"""Owned SQLite DDL for the content workflow schema."""

from __future__ import annotations

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
    CREATE TABLE IF NOT EXISTS content_current_disposition_proposals (
      action_id TEXT PRIMARY KEY,
      proposal_digest TEXT NOT NULL UNIQUE,
      current_work_item_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_current_disposition_proposals_no_update
    BEFORE UPDATE ON content_current_disposition_proposals
    BEGIN SELECT RAISE(ABORT, 'current disposition proposals are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_current_disposition_proposals_no_replace
    BEFORE INSERT ON content_current_disposition_proposals
    WHEN EXISTS (
      SELECT 1 FROM content_current_disposition_proposals
      WHERE action_id = NEW.action_id OR proposal_digest = NEW.proposal_digest
    )
    BEGIN SELECT RAISE(ABORT, 'current disposition proposals are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_current_disposition_proposals_no_delete
    BEFORE DELETE ON content_current_disposition_proposals
    BEGIN SELECT RAISE(ABORT, 'current disposition proposals are append-only'); END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_current_disposition_receipts (
      receipt_id TEXT PRIMARY KEY,
      receipt_digest TEXT NOT NULL UNIQUE,
      action_id TEXT NOT NULL UNIQUE,
      current_work_item_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_current_disposition_receipts_no_update
    BEFORE UPDATE ON content_current_disposition_receipts
    BEGIN SELECT RAISE(ABORT, 'current disposition receipts are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_current_disposition_receipts_no_replace
    BEFORE INSERT ON content_current_disposition_receipts
    WHEN EXISTS (
      SELECT 1 FROM content_current_disposition_receipts
      WHERE receipt_id = NEW.receipt_id
         OR receipt_digest = NEW.receipt_digest
         OR action_id = NEW.action_id
    )
    BEGIN SELECT RAISE(ABORT, 'current disposition receipts are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_current_disposition_receipts_no_delete
    BEFORE DELETE ON content_current_disposition_receipts
    BEGIN SELECT RAISE(ABORT, 'current disposition receipts are append-only'); END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_delivery_identity_authority_proposals (
      action_id TEXT PRIMARY KEY,
      proposal_digest TEXT NOT NULL UNIQUE,
      current_disposition_receipt_id TEXT NOT NULL,
      inventory_receipt_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_delivery_identity_authority_proposals_no_update
    BEFORE UPDATE ON content_delivery_identity_authority_proposals
    BEGIN SELECT RAISE(ABORT, 'delivery identity authority proposals are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_delivery_identity_authority_proposals_no_replace
    BEFORE INSERT ON content_delivery_identity_authority_proposals
    WHEN EXISTS (
      SELECT 1 FROM content_delivery_identity_authority_proposals
      WHERE action_id = NEW.action_id
         OR proposal_digest = NEW.proposal_digest
    )
    BEGIN SELECT RAISE(ABORT, 'delivery identity authority proposals are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_delivery_identity_authority_proposals_no_delete
    BEFORE DELETE ON content_delivery_identity_authority_proposals
    BEGIN SELECT RAISE(ABORT, 'delivery identity authority proposals are append-only'); END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_authoring_inventory_receipts (
      receipt_id TEXT PRIMARY KEY,
      receipt_digest TEXT NOT NULL UNIQUE,
      catalog_id TEXT NOT NULL,
      current_work_item_id TEXT NOT NULL,
      canonical_path TEXT NOT NULL,
      public_url TEXT NOT NULL,
      catalog_snapshot_digest TEXT NOT NULL,
      recorded_by TEXT NOT NULL,
      recorded_at TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      UNIQUE (catalog_id, catalog_snapshot_digest)
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_authoring_inventory_receipts_no_update
    BEFORE UPDATE ON content_authoring_inventory_receipts
    BEGIN
      SELECT RAISE(ABORT, 'content authoring inventory receipts are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_authoring_inventory_receipts_no_delete
    BEFORE DELETE ON content_authoring_inventory_receipts
    BEGIN
      SELECT RAISE(ABORT, 'content authoring inventory receipts are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_authoring_inventory_receipts_no_replace
    BEFORE INSERT ON content_authoring_inventory_receipts
    WHEN EXISTS (
      SELECT 1 FROM content_authoring_inventory_receipts
      WHERE receipt_id = NEW.receipt_id
         OR receipt_digest = NEW.receipt_digest
         OR (
           catalog_id = NEW.catalog_id
           AND catalog_snapshot_digest = NEW.catalog_snapshot_digest
         )
    )
    BEGIN
      SELECT RAISE(ABORT, 'content authoring inventory receipt snapshot is immutable');
    END
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
    CREATE TRIGGER IF NOT EXISTS content_delivery_identity_bindings_no_replace
    BEFORE INSERT ON content_delivery_identity_bindings
    WHEN EXISTS (
      SELECT 1 FROM content_delivery_identity_bindings
      WHERE binding_id = NEW.binding_id
         OR binding_digest = NEW.binding_digest
    )
    BEGIN
      SELECT RAISE(ABORT, 'content delivery identity bindings are append-only');
    END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_source_fact_authority_proposals (
      action_id TEXT PRIMARY KEY,
      proposal_digest TEXT NOT NULL UNIQUE,
      identity_binding_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_fact_authority_proposals_no_update
    BEFORE UPDATE ON content_source_fact_authority_proposals
    BEGIN
      SELECT RAISE(ABORT, 'content source fact authority proposals are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_fact_authority_proposals_no_replace
    BEFORE INSERT ON content_source_fact_authority_proposals
    WHEN EXISTS (
      SELECT 1 FROM content_source_fact_authority_proposals
      WHERE action_id = NEW.action_id OR proposal_digest = NEW.proposal_digest
    )
    BEGIN
      SELECT RAISE(ABORT, 'content source fact authority proposals are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_fact_authority_proposals_no_delete
    BEFORE DELETE ON content_source_fact_authority_proposals
    BEGIN
      SELECT RAISE(ABORT, 'content source fact authority proposals are append-only');
    END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_source_fact_authority_receipts (
      receipt_id TEXT PRIMARY KEY,
      receipt_digest TEXT NOT NULL UNIQUE,
      action_id TEXT NOT NULL UNIQUE,
      action_payload_digest TEXT NOT NULL,
      identity_binding_id TEXT NOT NULL,
      current_work_item_id TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_content_source_fact_authority_receipt_binding
    ON content_source_fact_authority_receipts (identity_binding_id)
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_fact_authority_receipts_no_update
    BEFORE UPDATE ON content_source_fact_authority_receipts
    BEGIN SELECT RAISE(ABORT, 'content source fact authority receipts are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_fact_authority_receipts_no_replace
    BEFORE INSERT ON content_source_fact_authority_receipts
    WHEN EXISTS (
      SELECT 1 FROM content_source_fact_authority_receipts
      WHERE receipt_id = NEW.receipt_id
         OR receipt_digest = NEW.receipt_digest
         OR action_id = NEW.action_id
    )
    BEGIN SELECT RAISE(ABORT, 'content source fact authority receipts are append-only'); END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_source_fact_authority_receipts_no_delete
    BEFORE DELETE ON content_source_fact_authority_receipts
    BEGIN SELECT RAISE(ABORT, 'content source fact authority receipts are append-only'); END
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
    CREATE TRIGGER IF NOT EXISTS content_source_pack_bindings_no_replace
    BEFORE INSERT ON content_source_pack_bindings
    WHEN EXISTS (
      SELECT 1 FROM content_source_pack_bindings
      WHERE binding_id = NEW.binding_id OR binding_digest = NEW.binding_digest
    )
    BEGIN
      SELECT RAISE(ABORT, 'content source-pack bindings are append-only');
    END
    """,
    """
    CREATE TABLE IF NOT EXISTS content_research_packet_preparation_receipts (
      receipt_id TEXT PRIMARY KEY,
      receipt_digest TEXT NOT NULL UNIQUE,
      identity_binding_id TEXT NOT NULL,
      identity_binding_digest TEXT NOT NULL,
      source_pack_binding_id TEXT NOT NULL,
      source_pack_binding_digest TEXT NOT NULL,
      current_work_item_id TEXT NOT NULL,
      input_digest TEXT NOT NULL,
      recorded_at TEXT NOT NULL,
      payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_research_packet_preparation_receipts_no_update
    BEFORE UPDATE ON content_research_packet_preparation_receipts
    BEGIN
      SELECT RAISE(ABORT, 'content research packet preparation receipts are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_research_packet_preparation_receipts_no_replace
    BEFORE INSERT ON content_research_packet_preparation_receipts
    WHEN EXISTS (
      SELECT 1 FROM content_research_packet_preparation_receipts
      WHERE receipt_id = NEW.receipt_id OR receipt_digest = NEW.receipt_digest
    )
    BEGIN
      SELECT RAISE(ABORT, 'content research packet preparation receipts are append-only');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS content_research_packet_preparation_receipts_no_delete
    BEFORE DELETE ON content_research_packet_preparation_receipts
    BEGIN
      SELECT RAISE(ABORT, 'content research packet preparation receipts are append-only');
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
    CREATE TRIGGER IF NOT EXISTS content_delivery_records_no_replace
    BEFORE INSERT ON content_delivery_records
    WHEN EXISTS (
      SELECT 1 FROM content_delivery_records
      WHERE record_id = NEW.record_id
         OR record_digest = NEW.record_digest
         OR binding_id = NEW.binding_id
    )
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
