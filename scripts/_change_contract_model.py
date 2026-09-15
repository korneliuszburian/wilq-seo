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
    ("current-disposition", "exact-persisted-authority-chain"): (
        "scripts/test.sh",
        "tests/content/test_current_disposition_authority.py",
        "tests/actions/test_audit_store_contracts.py::test_audit_details_for_operator_keeps_only_canonical_digest_values",
        "tests/api_contracts/test_redaction_contracts.py",
        "tests/storage/test_sqlite_schema_inventory.py::test_current_disposition_schema_hunks_are_exact",
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
    ("content-research-packet", "server-owned-exact-plan-draft"): (
        "scripts/test.sh",
        "tests/content/test_packet_plan_draft_binding.py",
        "tests/content/test_packet_plan_draft_http.py",
    ),
}


def _test_selectors(proof: ProofCommand) -> tuple[str, ...]:
    return tuple(entry for entry in proof[1:] if entry.startswith("tests/"))


_MAPPINGS: dict[tuple[str, str], MappingDescriptor] = {
    key: MappingDescriptor(
        proof=proof,
        # Use a small parent-safe harness for the counterfactual: both fixed
        # points can collect it, while the old POST surface fails in its call
        # phase and the candidate's read-only surface passes.
        selectors=(
            ("tests/__init__.py", "tests/content/test_packet_plan_draft_change_contract.py")
            if key == ("content-research-packet", "server-owned-exact-plan-draft")
            else _test_selectors(proof)
        ),
        observer_paths=(
            ("tests/scripts/test_changes_check.py", "scripts/_change_contract_model.py",
             "scripts/_change_contract_observer.py", "scripts/_change_contract_snapshot.py",
             "scripts/trusted_test_report.py")
            if key == ("change-contract-gate", "observed-before-state")
            else ("tests/__init__.py", "tests/content/test_packet_plan_draft_change_contract.py")
            if key == ("content-research-packet", "server-owned-exact-plan-draft")
            else tuple(entry.split("::", 1)[0] for entry in _test_selectors(proof))
        ),
        expectation="red-green",
        allow_new_mapping=key in {
            ("change-contract-gate", "observed-before-state"),
            ("content-research-packet", "server-owned-exact-plan-draft"),
        },
    )
    for key, proof in _PROOFS.items()
}

# Explicit aliases keep the trusted map discoverable to reviewers and old
# focused tests source-compatible.
PROOFS = _PROOFS
MAPPINGS = _MAPPINGS
_PROOF_MAPPINGS = _MAPPINGS
