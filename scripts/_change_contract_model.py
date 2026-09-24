"""Private data model and trusted mapping for the change-contract gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ProofCommand = tuple[str, ...]
Expectation = Literal["red-green", "unchanged-green"]


@dataclass(frozen=True)
class MappingDescriptor:
    """Non-executable authority for one named change-contract check."""

    proof: ProofCommand
    selectors: tuple[str, ...]
    observer_paths: tuple[str, ...]
    expectation: Expectation
    mapping_path: str = "scripts/_change_contract_model.py"
    reporter_path: str = "scripts/trusted_test_report.py"
    allow_new_mapping: bool = False


@dataclass(frozen=True)
class TestCaseRecord:
    nodeid: str
    when: str
    outcome: str
    assertion: bool


@dataclass(frozen=True)
class TestReport:
    pytest_status: int
    tests_collected: int
    collection_errors: int
    internal_errors: int
    setup_failures: int
    teardown_failures: int
    call_assertion_failures: int
    call_non_assertion_failures: int
    overflow: bool
    cases: tuple[TestCaseRecord, ...]


@dataclass(frozen=True)
class CounterfactualResult:
    ok: bool
    infrastructure: bool
    reason: str


_PROOFS: dict[tuple[str, str], ProofCommand] = {
    ("change-contract-gate", "cli-acceptance"): (
        "scripts/test.sh",
        "tests/scripts/test_changes_check.py",
    ),
    ("change-contract-gate", "observed-before-state"): (
        "scripts/test.sh",
        "tests/scripts/test_changes_check.py::test_changes_check_observes_before_state_through_candidate_snapshot",
    ),
    ("complexity-audit", "shrinking-frozen-facade"): (
        "scripts/test.sh",
        "tests/test_audit_complexity.py::test_frozen_growth_gate_accepts_a_shrinking_facade",
    ),
    ("complexity-audit", "unchanged-hotspot-budget"): (
        "scripts/test.sh",
        "tests/test_audit_complexity.py::"
        "test_changed_budget_ignores_existing_hotspots_that_do_not_grow",
    ),
    ("material-review-ui", "explicit-exact-attestation"): (
        "scripts/test.sh",
        "tests/dashboard/test_material_review_ui_runtime.py::"
        "test_material_review_ui_requires_explicit_attestation_and_safe_source",
    ),
    ("legacy-source-pack", "direct-post-action-required"): (
        "scripts/test.sh",
        "tests/content/test_source_pack_binding_api.py::"
        "test_legacy_source_pack_post_requires_an_action_without_persisting",
    ),
    ("planning-packet", "action-required-before-write"): (
        "scripts/test.sh",
        "tests/content/test_planning_packet_action_boundary.py::"
        "test_public_planning_post_blocks_before_implicit_research_packet_write",
    ),
    ("research-packet-v2", "exact-readonly-preview"): (
        "scripts/test.sh",
        "tests/content/test_research_packet_v2_preview_change_contract.py::"
        "test_public_v2_packet_preview_preserves_exact_source_blocker",
    ),
    ("research-packet-v2-action", "exact-reviewed-local-receipt"): (
        "scripts/test.sh",
        "tests/content/test_research_packet_v2_action.py::"
        "test_public_packet_v2_action_reviews_exact_snapshot_and_records_local_receipt",
    ),
    ("approved-v2-planner-projection", "exact-selected-facts"): (
        "scripts/test.sh",
        "tests/content/test_approved_packet_v2_change_contract.py::"
        "test_planner_projects_only_exact_approved_v2_packet_facts",
    ),
    ("v2-planning-worker", "guard-before-model-and-save"): (
        "scripts/test.sh",
        "tests/content/test_v2_planner_worker_change_contract.py::"
        "test_direct_v2_planner_requires_guard_before_model",
    ),
    ("v2-planning-route", "exact-readonly-binding"): (
        "scripts/test.sh",
        "tests/content/test_route_packet_v2_binding.py::"
        "test_route_binds_approved_v2_without_entering_legacy_packet_writer",
    ),
    ("planning-generation-intent", "exact-local-action-preview"): (
        "scripts/test.sh",
        "tests/content/test_planning_generation_intent_change_contract.py::"
        "test_public_generation_intent_exposes_typed_blocked_preview_contract",
    ),
    ("planning-deferred-dispatch", "explicit-post-audit-authority"): (
        "scripts/test.sh",
        "tests/content/test_planning_deferred_dispatch_change_contract.py::"
        "test_planning_action_authorizes_only_exact_post_audit_dispatch",
    ),
    ("research-packet-v2-ui", "explicit-review-local-apply"): (
        "scripts/test.sh",
        "tests/dashboard/test_research_packet_v2_ui_runtime.py::"
        "test_packet_review_and_local_apply_require_exact_action_acknowledgement",
    ),
    ("action-lifecycle-ui", "canonical-step-order"): (
        "scripts/test.sh",
        "tests/dashboard/test_action_lifecycle_ui_order_runtime.py::"
        "test_action_ui_orders_validate_preview_review_and_completion",
    ),
    ("connector-refresh-recovery", "bodyless-api-and-full-payload-cas"): (
        "scripts/test.sh",
        "tests/connectors/test_connector_refresh_recovery.py",
        "tests/api_contracts/test_connector_refresh_recovery_contract.py",
    ),
    ("embedded-runtime-policy", "terra-max-fail-closed"): (
        "scripts/test.sh",
        "tests/content/test_codex_app_server_transport.py",
        "tests/content/test_new_page_initial_draft.py",
        "tests/storage/test_codex_runs.py",
        "tests/content/test_initial_draft_run.py",
        "tests/content/test_initial_draft_queue_gate.py",
    ),
    ("inventory-classification", "exact-current-receipt-lineage"): (
        "scripts/test.sh",
        "tests/content/test_content_production_classification_boundaries.py::test_parser_accepts_signed_blocked_historical_protection_without_reuse",
        "tests/content/test_content_production_classification_boundaries.py::test_persisted_head_payload_without_optional_history_remains_readable_without_tampering",
        "tests/content/test_current_blocked_classification.py::test_current_builder_returns_sorted_57_row_all_blocked_run_with_history_protection",
        "tests/content/test_inventory_catalog.py::test_inventory_catalog_uses_the_latest_wordpress_refresh_batch",
        "tests/content/test_inventory_catalog.py::test_latest_wordpress_refresh_uses_completion_time_not_storage_order",
        "tests/content/test_inventory_catalog.py::test_latest_metric_refresh_uses_completion_time_not_storage_order",
        "tests/content/test_authoring_inventory_receipt.py::test_receipt_binds_full_current_catalog_material_not_just_url_or_work_item",
        "tests/content/test_authoring_inventory_receipt.py::test_url_only_or_unscoped_evidence_cannot_register_current_inventory_receipt",
        "tests/content/test_authoring_inventory_receipt_store.py::test_store_is_append_only_idempotent_and_keeps_distinct_current_snapshots",
        "tests/content/test_authoring_inventory_receipt_store.py::test_store_conflicts_on_same_snapshot_with_different_receipt_payload",
        "tests/content/test_current_inventory_reconciliation.py::test_reconcile_persists_only_material_keep_receipts_and_a_blocked_run",
        "tests/content/test_inventory_journal_reconciliation.py::test_reconciliation_counts_only_exact_normalized_paths_and_never_mints_bindings",
        "tests/content/test_inventory_journal_reconciliation.py::test_reconciliation_does_not_claim_complete_for_partial_canonical_journal",
        "tests/content/test_inventory_journal_reconciliation.py::test_reconciliation_rejects_same_count_substituted_path",
        "tests/storage/test_sqlite_schema_inventory.py::test_authoring_inventory_receipt_schema_hunk_is_exact",
        "tests/content/test_production_registered_inventory_receipt.py::test_registered_inventory_receipt_rejects_a_forged_digest",
    ),
    ("wordpress-refresh-coverage", "targeted-keeps-baseline"): (
        "scripts/test.sh",
        "tests/content/test_targeted_wordpress_refresh_keeps_baseline_change_contract.py",
    ),
    ("wordpress-sitemap-safety", "off-origin-loc-fails-closed"): (
        "scripts/test.sh",
        "tests/api_contracts/test_wordpress_sitemap_safety.py::"
        "test_off_origin_sitemap_locations_are_not_fetched_or_persisted",
    ),
    ("wordpress-sitemap-safety", "configured-alias-preserves-coverage"): (
        "scripts/test.sh",
        "tests/api_contracts/test_wordpress_sitemap_safety.py::"
        "test_top_level_sitemap_redirect_alias_requires_exact_configured_candidate",
    ),
    ("current-disposition", "exact-persisted-authority-chain"): (
        "scripts/test.sh",
        "tests/content/test_current_disposition_authority.py",
        "tests/actions/test_audit_store_contracts.py::test_audit_details_for_operator_keeps_only_canonical_digest_values",
        "tests/api_contracts/test_redaction_contracts.py",
        "tests/storage/test_sqlite_schema_inventory.py::test_current_disposition_schema_hunks_are_exact",
    ),
    ("current-disposition", "server-owned-approval-command"): (
        "scripts/test.sh",
        "tests/content/test_current_disposition_authority.py",
        "tests/content/test_current_disposition_approval.py",
        "tests/scripts/test_changes_check.py",
    ),
    ("current-disposition", "non-keep-candidate-blocked"): (
        "scripts/test.sh",
        "tests/content/test_current_disposition_authority.py::"
        "test_public_non_keep_dispositions_are_blocked_before_persistence",
    ),
    ("current-disposition", "operator-decision-card"): (
        "pnpm",
        "--filter",
        "@wilq/dashboard",
        "exec",
        "vitest",
        "run",
        "src/routes/ActionDetailRoute.test.tsx",
    ),
    ("delivery-identity", "exact-registered-receipt-authority"): (
        "scripts/test.sh",
        "tests/content/test_delivery_identity_authority.py",
        "tests/content/test_delivery_identity_binding.py",
        "tests/content/test_delivery_identity_api.py",
        "tests/storage/test_sqlite_schema_inventory.py::test_delivery_identity_authority_schema_hunks_are_exact",
        "tests/api_contracts/test_redaction_contracts.py",
    ),
    ("source-fact-source-pack", "exact-reviewed-row-consumption"): (
        "scripts/test.sh",
        "tests/content/test_source_fact_authority.py",
        "tests/content/test_source_pack_binding.py",
        "tests/content/test_source_pack_binding_api.py",
        "tests/storage/test_sqlite_schema_inventory.py::test_source_fact_authority_schema_hunks_are_exact",
        "tests/api_contracts/test_redaction_contracts.py",
    ),
    ("current-preparation", "exact-downstream-receipts"): (
        "scripts/test.sh",
        "tests/content/test_current_preparation_readiness.py",
        "tests/content/test_refresh_preparation_authority.py::test_runtime_requires_exact_authorization_and_proposal_binding",
        "tests/content/test_content_selected_workspace_production_decision.py::test_selected_workspace_rejects_mismatched_production_identity",
        "tests/content/test_refresh_preparation_atomic_current_reads.py::test_real_plan_and_revision_writers_accept_ready_blocked_row_with_readback",
        "tests/content/test_refresh_preparation_atomic_current_reads.py::test_real_writers_reject_distinct_attempts_after_newer_blocked_pack",
        "tests/content/test_initial_draft_production_authority.py::test_authorized_current_preparation_bypasses_canonical_guard_without_duplicate_resolve",
        "tests/content/test_initial_draft_status_read_path.py::test_status_reads_authorized_refresh_for_exact_current_preparation_blocker",
        "tests/content/test_initial_draft_status_read_path.py::test_status_preserves_exact_current_preparation_guard_when_refresh_read_is_none",
        "tests/content/test_initial_draft_status_read_path.py::test_status_does_not_read_refresh_for_other_blocked_or_write_rows",
        "tests/content/test_initial_draft_status_read_path.py::test_status_does_not_read_refresh_for_conflict_or_reuse",
    ),
    ("current-inventory-reconciliation", "coverage-policy-blocks-before-write"): (
        "scripts/test.sh",
        "tests/content/test_current_inventory_reconciliation.py::"
        "test_reconciliation_blocks_unknown_and_complete_coverage_before_store_access",
    ),
    ("current-verification", "exact-draft-receipt-readback"): (
        "scripts/test.sh",
        "tests/content/test_current_verification_record.py",
        "tests/content/test_wordpress_draft_apply_receipt.py",
    ),
    ("ads-operator-labels", "api-owned-priority-and-risk"): (
        "pnpm",
        "--filter",
        "@wilq/dashboard",
        "exec",
        "vitest",
        "run",
        "src/routes/AdsDoctorSections/formatters.test.ts",
    ),
    ("recommendation-log", "canonical-workspace-guard"): (
        "scripts/test.sh",
        "tests/test_recommendation_log_workspace.py",
        "tests/api_contracts/test_daily_check_api.py",
    ),
    ("action-preview-cards", "api-owned-payload-narration"): (
        "pnpm",
        "--filter",
        "@wilq/dashboard",
        "exec",
        "vitest",
        "run",
        "src/routes/ActionPanels.test.tsx",
    ),
    ("revision-save-policy", "domain-owned-exact-validation"): (
        "scripts/test.sh",
        "tests/content/test_revision_save_validation_domain.py",
    ),
    ("ads-external-audit", "domain-owned-exact-binding"): (
        "scripts/test.sh",
        "tests/actions/test_ads_external_execution_ack.py",
        "tests/actions/test_ads_external_execution_domain.py",
    ),
    ("social-review-policy", "domain-owned-append-only-numbering"): (
        "scripts/test.sh",
        "tests/content/test_social_reuse_proposal_api.py",
        "tests/content/test_social_reuse_review_domain.py",
    ),
    ("public-deployment-gate", "domain-owned-exact-approval"): (
        "scripts/test.sh",
        "tests/content/test_public_deployment_confirmation.py",
        "tests/content/test_public_deployment_review_gate_domain.py",
    ),
    ("redaction-digest-allowlist", "authoring-profile-digest-preserved"): (
        "scripts/test.sh",
        "tests/test_redaction_authoring_profile_digest.py",
        "tests/api_contracts/test_redaction_contracts.py",
        "tests/content/test_new_page_action_lifecycle.py",
    ),
    ("keep-eligibility-pin", "source-facts-sha-refresh"): (
        "scripts/test.sh",
        "tests/content/test_content_keep_eligibility.py",
    ),
    ("packet-id-normalization", "operational-to-inventory"): (
        "scripts/test.sh",
        "tests/content/test_packet_plan_draft_binding.py",
        "tests/content/test_packet_plan_draft_contracts.py",
        "tests/content/test_packet_plan_draft_http.py",
    ),
    ("planning-codex-deadline", "covers-full-turn"): (
        "scripts/test.sh",
        "tests/content/test_planning_runtime_contract.py",
    ),
    ("regulatory-fact-proposal-deadline", "covers-full-turn"): (
        "scripts/test.sh",
        "tests/content/test_regulatory_fact_proposal_deadline_change_contract.py",
    ),
    ("section-repair-deadline", "covers-full-turn"): (
        "scripts/test.sh",
        "tests/content/test_section_repair_deadline_change_contract.py",
    ),
    ("child-revision-packet-binding", "inherits-base-packet"): (
        "scripts/test.sh",
        "tests/content/test_child_revision_packet_binding_change_contract.py",
    ),
    ("regulatory-grounding-fallback", "requirement-wide-approved-facts"): (
        "scripts/test.sh",
        "tests/content/test_regulatory_grounding_fallback.py",
    ),
    ("regulatory-source-selection", "bounded-exact-fail-closed"): (
        "scripts/test.sh",
        "tests/content/test_regulatory_source_selection_change_contract.py",
    ),
    ("regulatory-preflight", "bound-groundable-plan-without-metadata-terms"): (
        "scripts/test.sh",
        "tests/content/test_regulatory_preflight_change_contract.py",
    ),
    ("readability-regulatory-restore", "pure-grounding-after-model-repair"): (
        "scripts/test.sh",
        "tests/content/test_readability_regulatory_restore.py",
    ),
    ("assurance-turn-signal", "typed-transport-exception"): (
        "scripts/test.sh",
        "tests/content/test_draft_assurance_runtime_signal.py",
    ),
    ("initial-draft-deadline", "covers-full-finalization"): (
        "scripts/test.sh",
        "tests/content/test_initial_draft_runtime_contract.py",
    ),
    ("semantic-review-runtime", "terra-max-deadline"): (
        "scripts/test.sh",
        "tests/content/test_semantic_review_runtime_contract.py",
    ),
    ("planning-directives", "claim-free-source-facts"): (
        "scripts/test.sh",
        "tests/content/test_planning_directive_change_contract.py",
    ),
    ("draft-plan-preparation", "drops-unsupported-body-targets"): (
        "scripts/test.sh",
        "tests/content/test_draft_plan_preparation_change_contract.py",
    ),
    ("initial-draft-worker-error", "typed-field-locations"): (
        "scripts/test.sh",
        "tests/content/test_initial_draft_worker_error_signal.py",
    ),
    ("document-fact-working-note", "protected-term-strips-note"): (
        "scripts/test.sh",
        "tests/content/test_document_fact_working_note.py",
    ),
    ("assurance-turn-retry", "transient-failure-once"): (
        "scripts/test.sh",
        "tests/content/test_assurance_turn_retry.py",
    ),
    ("assurance-batching", "single-critic-turn-all-constraints"): (
        "scripts/test.sh",
        "tests/content/test_assurance_batching_change_contract.py",
    ),
    ("initial-draft-context", "single-existing-body"): (
        "scripts/test.sh",
        "tests/content/test_initial_draft_single_body_change_contract.py",
    ),
    ("assurance-fingerprint", "malformed-dropped-not-fatal"): (
        "scripts/test.sh",
        "tests/content/test_exact_assurance_fingerprint.py",
    ),
    ("assurance-fingerprint", "valid-digest-persists"): (
        "scripts/test.sh",
        "tests/content/test_content_workflow_revisions.py::"
        "test_append_draft_revision_preserves_regulatory_assurance_fingerprint_after_redaction",
    ),
    ("content-research-packet", "server-owned-exact-plan-draft"): (
        "scripts/test.sh",
        "tests/content/test_packet_plan_draft_binding.py",
        "tests/content/test_research_packet.py",
        "tests/content/test_packet_plan_draft_contracts.py",
        "tests/content/test_packet_plan_draft_http.py",
        "tests/content/test_selected_source_pack_projection.py",
        "tests/content/test_regulatory_planning_lineage.py",
        "tests/content/test_initial_draft_editorial_packet_guard.py",
        "tests/content/test_editorial_planning_pipeline.py",
        "tests/content/test_regulated_draft_finalization.py",
    ),
    ("research-packet-legal-requirements", "accepts-domain-requirement-ids"): (
        "scripts/test.sh",
        "tests/content/test_research_packet_legal_requirements_change_contract.py",
    ),
    ("content-review", "exact-packet-revision"): (
        "scripts/test.sh",
        "tests/content/test_packet_bound_reviews.py",
        "tests/content/test_packet_bound_review_public_api.py",
        "tests/content/test_packet_bound_review_races.py",
        "tests/content/test_semantic_review_refresh_change_contract.py",
        "tests/content/test_semantic_review_refresh_binding.py",
        "tests/content/test_semantic_content_review_api.py::test_existing_exact_review_wins_over_retry_preflight_and_polling",
        "tests/content/test_independent_review_runs.py::test_api_records_run_and_critical_disposition",
        "tests/content/test_revision_review_evidence.py",
        "tests/content/test_semantic_review_polling_read_path.py",
    ),
    ("material-review", "unchanged-material-stays-current"): (
        "scripts/test.sh",
        "tests/content/test_material_review.py::"
        "test_public_material_review_routes_are_immutable_idempotent_and_drift_aware",
    ),
    ("current-material-review-action-v2", "exact-reviewed-material"): (
        "scripts/test.sh",
        "tests/content/test_material_review_action_v2.py::"
        "test_public_action_lifecycle_approves_only_exact_reviewed_current_material",
    ),
    ("current-page-evidence", "stable-per-url-material-meaning"): (
        "scripts/test.sh",
        "tests/content/test_current_page_evidence.py::"
        "test_public_current_page_evidence_tracks_exact_material_meaning_per_url",
    ),
    ("current-page-disposition-v2", "exact-lifecycle-revalidates-material-meaning"): (
        "scripts/test.sh",
        "tests/content/test_current_page_disposition_v2_action.py",
    ),
    ("current-page-identity-v2", "receipt-backed-exact-current"): (
        "scripts/test.sh",
        "tests/content/test_current_page_identity_v2.py",
    ),
    ("current-source-fact-candidates-v2", "exact-keep-scoped-selection"): (
        "scripts/test.sh",
        "tests/content/test_source_fact_candidate_v2.py::"
        "test_public_v2_source_fact_candidates_require_exact_current_keep",
    ),
    ("current-source-fact-authority-v2", "exact-keep-reviewed-facts"): (
        "scripts/test.sh",
        "tests/content/test_source_fact_authority_v2.py::"
        "test_public_v2_authority_requires_exact_keep_reviewed_facts_and_no_vendor_write",
    ),
    ("current-source-pack-v2", "exact-authority-packet"): (
        "scripts/test.sh",
        "tests/content/test_source_pack_v2.py",
    ),
}


def _test_selectors(proof: ProofCommand) -> tuple[str, ...]:
    return tuple(entry for entry in proof[1:] if entry.startswith("tests/"))


_MAPPINGS: dict[tuple[str, str], MappingDescriptor] = {
    key: MappingDescriptor(
        proof=proof,
        # Use a small parent-safe harness for counterfactuals: changed test and
        # resolver files are overlaid into the parent so the old implementation
        # fails in its call phase while the candidate passes.
        selectors=(
            (
                "tests/content/test_packet_plan_draft_change_contract.py::"
                "test_research_packet_identifier_contract_keeps_regulatory_prefix_and_secret_guard",
                "tests/content/test_packet_plan_draft_change_contract.py::"
                "test_research_packet_cta_fallback_contract_is_exact_and_evidence_bound",
                "tests/content/test_packet_plan_draft_change_contract.py::"
                "test_research_packet_freshness_projection_contract_is_complete",
                "tests/content/test_packet_plan_draft_change_contract.py::"
                "test_selected_source_pack_projection_is_exact_and_editorial_only",
                "tests/content/test_packet_plan_draft_change_contract.py::"
                "test_bdo_profile_owns_the_editorial_canonical_path",
                "tests/content/test_packet_plan_draft_change_contract.py::"
                "test_packet_context_partitions_use_the_projected_planning_input",
                "tests/content/test_packet_plan_draft_change_contract.py::"
                "test_editorial_initial_draft_requires_a_current_research_packet",
                "tests/content/test_packet_plan_draft_change_contract.py::"
                "test_packet_bound_refresh_status_reads_exact_projected_job",
                "tests/content/test_regulated_draft_finalization.py::"
                "test_regulated_finalization_repairs_exact_scope_before_its_only_passing_critic",
            )
            if key == ("content-research-packet", "server-owned-exact-plan-draft")
            else (
                "tests/content/test_semantic_review_refresh_change_contract.py::"
                "test_semantic_refresh_source_contract",
                "tests/content/test_packet_bound_reviews.py::"
                "test_public_packet_bound_revision_reaches_semantic_and_independent_reviews",
                "tests/content/test_packet_bound_review_public_api.py::"
                "test_content_model_routes_pass_review_snapshot_loader_to_research_packet_read",
                "tests/content/test_selected_source_pack_projection.py::"
                "test_packet_bound_review_rebuilds_exact_projected_source_pack_digest",
            )
            if key == ("content-review", "exact-packet-revision")
            else ("tests/dashboard/test_current_disposition_card_change_contract.py",)
            if key == ("current-disposition", "operator-decision-card")
            else ("tests/content/test_current_disposition_approval_change_contract.py",)
            if key == ("current-disposition", "server-owned-approval-command")
            else ("tests/content/test_current_disposition_authority.py",)
            if key == ("current-disposition", "non-keep-candidate-blocked")
            else ("tests/content/test_current_preparation_readiness_change_contract.py",)
            if key == ("current-preparation", "exact-downstream-receipts")
            else ("tests/content/test_source_fact_authority_attempt_change_contract.py",)
            if key == ("source-fact-source-pack", "exact-reviewed-row-consumption")
            else _test_selectors(proof)
        ),
        observer_paths=(
            (
                "tests/scripts/test_changes_check.py",
                "scripts/_change_contract_model.py",
                "scripts/_change_contract_observer.py",
                "scripts/_change_contract_snapshot.py",
                "scripts/trusted_test_report.py",
            )
            if key == ("change-contract-gate", "observed-before-state")
            else (
                "tests/__init__.py",
                "tests/content/test_packet_plan_draft_change_contract.py",
                "tests/content/test_regulated_draft_finalization.py",
            )
            if key == ("content-research-packet", "server-owned-exact-plan-draft")
            else (
                "tests/__init__.py",
                "tests/content/test_semantic_review_refresh_change_contract.py",
                "tests/content/test_packet_bound_review_public_api.py",
                "tests/content/test_selected_source_pack_projection.py",
            )
            if key == ("content-review", "exact-packet-revision")
            else ("tests/dashboard/test_current_disposition_card_change_contract.py",)
            if key == ("current-disposition", "operator-decision-card")
            else ("tests/content/test_current_disposition_approval_change_contract.py",)
            if key == ("current-disposition", "server-owned-approval-command")
            else ("tests/content/test_current_disposition_authority.py",)
            if key == ("current-disposition", "non-keep-candidate-blocked")
            else ("tests/content/test_current_preparation_readiness_change_contract.py",)
            if key == ("current-preparation", "exact-downstream-receipts")
            else ("tests/content/test_source_fact_authority_attempt_change_contract.py",)
            if key == ("source-fact-source-pack", "exact-reviewed-row-consumption")
            else ("tests/content/test_current_page_evidence.py",)
            if key == ("current-page-evidence", "stable-per-url-material-meaning")
            else ("tests/content/test_current_page_disposition_v2_action.py",)
            if key
            == ("current-page-disposition-v2", "exact-lifecycle-revalidates-material-meaning")
            else ("tests/content/test_current_page_identity_v2.py",)
            if key == ("current-page-identity-v2", "receipt-backed-exact-current")
            else ("tests/content/test_source_fact_candidate_v2.py",)
            if key == ("current-source-fact-candidates-v2", "exact-keep-scoped-selection")
            else ("tests/content/test_source_fact_authority_v2.py",)
            if key == ("current-source-fact-authority-v2", "exact-keep-reviewed-facts")
            else ("tests/content/test_source_pack_v2.py",)
            if key == ("current-source-pack-v2", "exact-authority-packet")
            else ("tests/test_audit_complexity.py",)
            if key == ("complexity-audit", "shrinking-frozen-facade")
            else tuple(dict.fromkeys(entry.split("::", 1)[0] for entry in _test_selectors(proof)))
        ),
        expectation="red-green",
        allow_new_mapping=key
        in {
            ("change-contract-gate", "observed-before-state"),
            ("complexity-audit", "shrinking-frozen-facade"),
            ("complexity-audit", "unchanged-hotspot-budget"),
            ("material-review-ui", "explicit-exact-attestation"),
            ("legacy-source-pack", "direct-post-action-required"),
            ("planning-packet", "action-required-before-write"),
            ("research-packet-v2", "exact-readonly-preview"),
            ("research-packet-v2-action", "exact-reviewed-local-receipt"),
            ("approved-v2-planner-projection", "exact-selected-facts"),
            ("v2-planning-worker", "guard-before-model-and-save"),
            ("v2-planning-route", "exact-readonly-binding"),
            ("planning-generation-intent", "exact-local-action-preview"),
            ("planning-deferred-dispatch", "explicit-post-audit-authority"),
            ("research-packet-v2-ui", "explicit-review-local-apply"),
            ("action-lifecycle-ui", "canonical-step-order"),
            ("content-research-packet", "server-owned-exact-plan-draft"),
            ("wordpress-refresh-coverage", "targeted-keeps-baseline"),
            ("wordpress-sitemap-safety", "off-origin-loc-fails-closed"),
            ("wordpress-sitemap-safety", "configured-alias-preserves-coverage"),
            ("research-packet-legal-requirements", "accepts-domain-requirement-ids"),
            ("content-review", "exact-packet-revision"),
            ("material-review", "unchanged-material-stays-current"),
            ("current-material-review-action-v2", "exact-reviewed-material"),
            ("current-page-evidence", "stable-per-url-material-meaning"),
            ("current-page-disposition-v2", "exact-lifecycle-revalidates-material-meaning"),
            ("current-page-identity-v2", "receipt-backed-exact-current"),
            ("current-source-fact-candidates-v2", "exact-keep-scoped-selection"),
            ("current-source-fact-authority-v2", "exact-keep-reviewed-facts"),
            ("current-source-pack-v2", "exact-authority-packet"),
            ("current-disposition", "operator-decision-card"),
            ("current-disposition", "server-owned-approval-command"),
            ("current-disposition", "non-keep-candidate-blocked"),
            ("current-preparation", "exact-downstream-receipts"),
            ("current-inventory-reconciliation", "coverage-policy-blocks-before-write"),
            ("current-verification", "exact-draft-receipt-readback"),
            ("ads-operator-labels", "api-owned-priority-and-risk"),
            ("recommendation-log", "canonical-workspace-guard"),
            ("action-preview-cards", "api-owned-payload-narration"),
            ("revision-save-policy", "domain-owned-exact-validation"),
            ("ads-external-audit", "domain-owned-exact-binding"),
            ("social-review-policy", "domain-owned-append-only-numbering"),
            ("public-deployment-gate", "domain-owned-exact-approval"),
            ("redaction-digest-allowlist", "authoring-profile-digest-preserved"),
            ("keep-eligibility-pin", "source-facts-sha-refresh"),
            ("packet-id-normalization", "operational-to-inventory"),
            ("planning-codex-deadline", "covers-full-turn"),
            ("regulatory-fact-proposal-deadline", "covers-full-turn"),
            ("section-repair-deadline", "covers-full-turn"),
            ("child-revision-packet-binding", "inherits-base-packet"),
            ("regulatory-grounding-fallback", "requirement-wide-approved-facts"),
            ("regulatory-source-selection", "bounded-exact-fail-closed"),
            ("regulatory-preflight", "bound-groundable-plan-without-metadata-terms"),
            ("readability-regulatory-restore", "pure-grounding-after-model-repair"),
            ("assurance-turn-signal", "typed-transport-exception"),
            ("initial-draft-deadline", "covers-full-finalization"),
            ("semantic-review-runtime", "terra-max-deadline"),
            ("planning-directives", "claim-free-source-facts"),
            ("draft-plan-preparation", "drops-unsupported-body-targets"),
            ("initial-draft-worker-error", "typed-field-locations"),
            ("document-fact-working-note", "protected-term-strips-note"),
            ("assurance-turn-retry", "transient-failure-once"),
            ("assurance-batching", "single-critic-turn-all-constraints"),
            ("initial-draft-context", "single-existing-body"),
            ("assurance-fingerprint", "malformed-dropped-not-fatal"),
            ("assurance-fingerprint", "valid-digest-persists"),
        },
    )
    for key, proof in _PROOFS.items()
}

# Explicit aliases keep the trusted map discoverable to reviewers and old
# focused tests source-compatible.
PROOFS = _PROOFS
MAPPINGS = _MAPPINGS
_PROOF_MAPPINGS = _MAPPINGS
