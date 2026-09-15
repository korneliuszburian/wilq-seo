from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import _change_contract_model as change_contract_model
from scripts import _change_contract_observer as observer
from scripts import _change_contract_snapshot as snapshot
from scripts import check_change_contract
from scripts._change_contract_model import TestCaseRecord as _TestCaseRecord
from scripts._change_contract_model import TestReport as _TestReport

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CHECK_SCRIPT = REPOSITORY_ROOT / "scripts/check_change_contract.py"
KNOWN_CONTRACT = (
    "connector-refresh-recovery:bodyless-api-and-full-payload-cas-red->green"
)
GATE_CONTRACT = "change-contract-gate:cli-acceptance-red->green"
KNOWN_PROOF = (
    "scripts/test.sh",
    "tests/connectors/test_connector_refresh_recovery.py",
    "tests/api_contracts/test_connector_refresh_recovery_contract.py",
)
GATE_PROOF = ("scripts/test.sh", "tests/scripts/test_changes_check.py")
EMBEDDED_RUNTIME_CONTRACT = (
    "embedded-runtime-policy:terra-max-fail-closed-red->green"
)
EMBEDDED_RUNTIME_PROOF = (
    "scripts/test.sh",
    "tests/content/test_codex_app_server_transport.py",
    "tests/content/test_new_page_initial_draft.py",
    "tests/storage/test_codex_runs.py",
    "tests/content/test_initial_draft_run.py",
    "tests/content/test_initial_draft_queue_gate.py",
)
INVENTORY_CLASSIFICATION_CONTRACT = (
    "inventory-classification:exact-current-receipt-lineage-red->green"
)
CURRENT_DISPOSITION_CONTRACT = (
    "current-disposition:exact-persisted-authority-chain-red->green"
)
SOURCE_FACT_SOURCE_PACK_CONTRACT = (
    "source-fact-source-pack:exact-reviewed-row-consumption-red->green"
)
CURRENT_DISPOSITION_APPROVAL_CONTRACT = (
    "current-disposition:server-owned-approval-command-red->green"
)
CONTENT_REVIEW_CONTRACT = "content-review:exact-packet-revision-red->green"
INVENTORY_CLASSIFICATION_PROOF = (
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
)
CURRENT_DISPOSITION_PROOF = (
    "scripts/test.sh",
    "tests/content/test_current_disposition_authority.py",
    "tests/actions/test_audit_store_contracts.py::test_audit_details_for_operator_keeps_only_canonical_digest_values",
    "tests/api_contracts/test_redaction_contracts.py",
    "tests/storage/test_sqlite_schema_inventory.py::test_current_disposition_schema_hunks_are_exact",
)
CURRENT_DISPOSITION_APPROVAL_PROOF = (
    "scripts/test.sh",
    "tests/content/test_current_disposition_authority.py",
    "tests/content/test_current_disposition_approval.py",
    "tests/scripts/test_changes_check.py",
)
SOURCE_FACT_SOURCE_PACK_PROOF = (
    "scripts/test.sh",
    "tests/content/test_source_fact_authority.py",
    "tests/content/test_source_pack_binding.py",
    "tests/content/test_source_pack_binding_api.py",
    "tests/storage/test_sqlite_schema_inventory.py::test_source_fact_authority_schema_hunks_are_exact",
    "tests/api_contracts/test_redaction_contracts.py",
)
CONTENT_REVIEW_PROOF = (
    "scripts/test.sh",
    "tests/content/test_packet_bound_reviews.py",
    "tests/content/test_packet_bound_review_public_api.py",
    "tests/content/test_packet_bound_review_races.py",
    "tests/content/test_semantic_review_refresh_binding.py",
    "tests/content/test_semantic_content_review_api.py::test_existing_exact_review_wins_over_retry_preflight_and_polling",
    "tests/content/test_independent_review_runs.py::test_api_records_run_and_critical_disposition",
    "tests/content/test_revision_review_evidence.py",
    "tests/content/test_semantic_review_polling_read_path.py",
)


def _git(repo: Path, *args: str, input_text: str | None = None) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _make_repo(
    root: Path,
    *,
    changed_path: str,
    message: str,
) -> Path:
    repo = root / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "change-contract tests")

    changed_file = repo / changed_path
    changed_file.parent.mkdir(parents=True, exist_ok=True)
    changed_file.write_text("fixture\n", encoding="utf-8")

    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "--allow-empty", "-F", "-", input_text=message)
    return repo


def _run_cli(repo: Path, ref: str = "HEAD") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), "--repo-root", str(repo), ref],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )


@pytest.mark.parametrize(
    ("changed_path", "message", "expected_returncode"),
    [
        ("README.md", "docs: update fixture", 0),
        ("apps/dashboard/dist/assets/bundle.js", "assets: update fixture", 0),
        ("packages/example/fixtures/data.ts", "fixtures: update fixture", 0),
        ("wilq/docs/example.py", "docs: update fixture", 0),
        ("apps/example.md", "docs: update fixture", 0),
        ("wilq/example.yaml", "config: update fixture", 0),
        ("packages/example/README.md", "docs: update fixture", 0),
        ("scripts/unrelated.sh", "scripts: maintenance", 0),
        ("scripts/test.sh", "scripts: gate update", 1),
        ("apps/example/package.json", "config: update fixture", 1),
        ("wilq/example/pyproject.toml", "config: update fixture", 1),
        ("apps/example.py", "feat: harness change", 1),
        (
            "apps/example.py",
            f"feat: duplicate declaration\n\nChange-contract: {KNOWN_CONTRACT}\n"
            f"Change-contract: {KNOWN_CONTRACT}\n",
            1,
        ),
        (
            "apps/example.py",
            "feat: malformed declaration\n\nChange-contract: "
            "connector-refresh-recovery:bodyless-api-and-full-payload-cas\n",
            1,
        ),
        (
            "apps/example.py",
            "feat: unknown declaration\n\nChange-contract: "
            "unknown-check:unknown-proof-red->green\n",
            1,
        ),
    ],
)
def test_changes_check_contract_cases(
    tmp_path: Path,
    changed_path: str,
    message: str,
    expected_returncode: int,
) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path=changed_path,
        message=message,
    )

    result = _run_cli(repo)

    assert result.returncode == expected_returncode, result.stdout + result.stderr


def test_changes_check_accepts_explicit_commit_ref(tmp_path: Path) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path="README.md",
        message="docs: valid fixture",
    )

    result = _run_cli(repo, "HEAD")

    assert result.returncode == 0, result.stdout + result.stderr


def test_changes_check_accepts_explicit_ref_with_injected_cli_gate_proof(
    tmp_path: Path,
) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path="scripts/check_change_contract.py",
        message=f"feat: mapped proof\n\nChange-contract: {GATE_CONTRACT}\n",
    )

    calls: list[tuple[str, ...]] = []

    def proof_runner(command: tuple[str, ...]) -> bool:
        calls.append(command)
        return True

    result = check_change_contract.check_commit(
        "HEAD",
        repository_root=repo,
        proof_runner=proof_runner,
    )

    assert result == 0
    assert calls == [GATE_PROOF]


def test_changes_check_maps_embedded_runtime_policy_to_exact_focused_proof(
    tmp_path: Path,
) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path="wilq/example.py",
        message=(
            f"feat: mapped embedded runtime proof\n\n"
            f"Change-contract: {EMBEDDED_RUNTIME_CONTRACT}\n"
        ),
    )
    calls: list[tuple[str, ...]] = []

    def proof_runner(command: tuple[str, ...]) -> bool:
        calls.append(command)
        return True

    result = check_change_contract.check_commit(
        "HEAD",
        repository_root=repo,
        proof_runner=proof_runner,
    )

    assert result == 0
    assert calls == [EMBEDDED_RUNTIME_PROOF]


def test_changes_check_maps_inventory_classification_to_exact_focused_proof(
    tmp_path: Path,
) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path="wilq/example.py",
        message=(
            f"feat: mapped inventory classification proof\n\n"
            f"Change-contract: {INVENTORY_CLASSIFICATION_CONTRACT}\n"
        ),
    )
    calls: list[tuple[str, ...]] = []

    def proof_runner(command: tuple[str, ...]) -> bool:
        calls.append(command)
        return True

    result = check_change_contract.check_commit(
        "HEAD",
        repository_root=repo,
        proof_runner=proof_runner,
    )

    assert result == 0
    assert calls == [INVENTORY_CLASSIFICATION_PROOF]


def test_generic_mapping_observer_paths_are_unique_and_first_seen() -> None:
    descriptor = change_contract_model.MAPPINGS[
        ("inventory-classification", "exact-current-receipt-lineage")
    ]

    assert descriptor.selectors == INVENTORY_CLASSIFICATION_PROOF[1:]
    assert descriptor.observer_paths == (
        "tests/content/test_content_production_classification_boundaries.py",
        "tests/content/test_current_blocked_classification.py",
        "tests/content/test_inventory_catalog.py",
        "tests/content/test_authoring_inventory_receipt.py",
        "tests/content/test_authoring_inventory_receipt_store.py",
        "tests/content/test_current_inventory_reconciliation.py",
        "tests/content/test_inventory_journal_reconciliation.py",
        "tests/storage/test_sqlite_schema_inventory.py",
        "tests/content/test_production_registered_inventory_receipt.py",
    )
    assert len(descriptor.observer_paths) == len(set(descriptor.observer_paths))


def test_changes_check_maps_current_disposition_to_exact_focused_proof(
    tmp_path: Path,
) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path="wilq/example.py",
        message=(
            "feat: mapped current disposition proof\n\n"
            f"Change-contract: {CURRENT_DISPOSITION_CONTRACT}\n"
        ),
    )
    calls: list[tuple[str, ...]] = []

    def proof_runner(command: tuple[str, ...]) -> bool:
        calls.append(command)
        return True

    result = check_change_contract.check_commit(
        "HEAD",
        repository_root=repo,
        proof_runner=proof_runner,
    )

    assert result == 0
    assert calls == [CURRENT_DISPOSITION_PROOF]


def test_changes_check_maps_server_owned_current_disposition_approval_to_backend_proof(
    tmp_path: Path,
) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path="wilq/content/workflow/current_disposition_approval.py",
        message=(
            "feat: map current disposition approval proof\n\n"
            f"Change-contract: {CURRENT_DISPOSITION_APPROVAL_CONTRACT}\n"
        ),
    )
    calls: list[tuple[str, ...]] = []

    def proof_runner(command: tuple[str, ...]) -> bool:
        calls.append(command)
        return True

    result = check_change_contract.check_commit(
        "HEAD",
        repository_root=repo,
        proof_runner=proof_runner,
    )

    descriptor = change_contract_model.MAPPINGS[
        ("current-disposition", "server-owned-approval-command")
    ]
    assert result == 0
    assert calls == [CURRENT_DISPOSITION_APPROVAL_PROOF]
    assert descriptor.selectors == (
        "tests/content/test_current_disposition_approval_change_contract.py",
    )
    assert descriptor.observer_paths == descriptor.selectors
    assert descriptor.expectation == "red-green"
    assert descriptor.allow_new_mapping is True


def test_server_owned_current_disposition_approval_observer_is_red_then_green(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "counterfactual"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "current disposition approval observer")

    observed_sources = (
        "wilq/content/workflow/current_disposition_approval.py",
        "apps/api/wilq_api/routers/content_current_disposition_authority.py",
        "apps/api/wilq_api/routers/actions.py",
        "wilq/actions/action_chain.py",
        "scripts/_change_contract_observer.py",
    )
    for relative in observed_sources:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("old implementation\n", encoding="utf-8")
    reporter = repo / "scripts/trusted_test_report.py"
    reporter.parent.mkdir(parents=True, exist_ok=True)
    reporter.write_bytes((REPOSITORY_ROOT / "scripts/trusted_test_report.py").read_bytes())
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "base")
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    for relative in observed_sources:
        (repo / relative).write_text(
            (REPOSITORY_ROOT / relative).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    observer_path = repo / "tests/content/test_current_disposition_approval_change_contract.py"
    observer_path.parent.mkdir(parents=True, exist_ok=True)
    observer_path.write_text(
        (
            REPOSITORY_ROOT
            / "tests/content/test_current_disposition_approval_change_contract.py"
        ).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    mapping = repo / "scripts/_change_contract_model.py"
    mapping.write_text(
        "MAPPING = ('current-disposition', 'server-owned-approval-command')\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "candidate")
    candidate = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    descriptor = change_contract_model.MAPPINGS[
        ("current-disposition", "server-owned-approval-command")
    ]
    result = observer.counterfactual(
        repo,
        candidate,
        parent,
        descriptor,
        ("current-disposition", "server-owned-approval-command"),
    )

    assert result.ok is True, result.reason
    assert result.infrastructure is False
    assert result.reason == "green"


def test_allow_new_mapping_still_requires_candidate_mapping_presence(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "missing-candidate-mapping"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "missing candidate mapping")

    source = repo / "value.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    reporter = repo / "scripts/trusted_test_report.py"
    reporter.parent.mkdir(parents=True, exist_ok=True)
    reporter.write_bytes((REPOSITORY_ROOT / "scripts/trusted_test_report.py").read_bytes())
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "base")
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    source.write_text("VALUE = 2\n", encoding="utf-8")
    observer_file = repo / "tests/test_mapping.py"
    observer_file.parent.mkdir(parents=True, exist_ok=True)
    observer_file.write_text(
        "from pathlib import Path\n\n"
        "def test_candidate_source_is_new():\n"
        "    assert 'VALUE = 2' in (Path(__file__).parents[1] / 'value.py').read_text()\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "candidate without mapping")
    candidate = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    descriptor = change_contract_model.MappingDescriptor(
        proof=(),
        selectors=("tests/test_mapping.py",),
        observer_paths=("tests/test_mapping.py",),
        expectation="red-green",
        mapping_path="scripts/_change_contract_model.py",
        allow_new_mapping=True,
    )
    result = observer.counterfactual(
        repo,
        candidate,
        parent,
        descriptor,
        ("current-disposition", "server-owned-approval-command"),
    )

    assert result.ok is False
    assert result.infrastructure is False
    assert result.reason == "mapping-missing-candidate"


def test_changes_check_maps_source_fact_source_pack_to_exact_focused_proof(
    tmp_path: Path,
) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path="wilq/example.py",
        message=(
            "feat: mapped source fact source pack proof\n\n"
            f"Change-contract: {SOURCE_FACT_SOURCE_PACK_CONTRACT}\n"
        ),
    )
    calls: list[tuple[str, ...]] = []

    def proof_runner(command: tuple[str, ...]) -> bool:
        calls.append(command)
        return True

    result = check_change_contract.check_commit(
        "HEAD",
        repository_root=repo,
        proof_runner=proof_runner,
    )

    assert result == 0
    assert calls == [SOURCE_FACT_SOURCE_PACK_PROOF]


def test_changes_check_maps_content_review_to_exact_packet_revision_proof(
    tmp_path: Path,
) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path="wilq/content/quality/review_packet_binding.py",
        message=(
            "feat: mapped content review proof\n\n"
            f"Change-contract: {CONTENT_REVIEW_CONTRACT}\n"
        ),
    )
    calls: list[tuple[str, ...]] = []

    def proof_runner(command: tuple[str, ...]) -> bool:
        calls.append(command)
        return True

    result = check_change_contract.check_commit(
        "HEAD",
        repository_root=repo,
        proof_runner=proof_runner,
    )

    assert result == 0
    assert calls == [CONTENT_REVIEW_PROOF]


@pytest.mark.parametrize("proof_ok, expected_returncode", [(True, 0), (False, 1)])
def test_changes_check_runs_known_proof_through_injected_runner(
    tmp_path: Path,
    proof_ok: bool,
    expected_returncode: int,
) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path="packages/example/index.ts",
        message=f"feat: mapped proof\n\nChange-contract: {KNOWN_CONTRACT}\n",
    )
    calls: list[tuple[str, ...]] = []

    def proof_runner(command: tuple[str, ...]) -> bool:
        calls.append(command)
        return proof_ok

    result = check_change_contract.check_commit(
        "HEAD",
        repository_root=repo,
        proof_runner=proof_runner,
    )

    assert result == expected_returncode
    assert calls == [KNOWN_PROOF]


@pytest.mark.parametrize(
    "message",
    [
        "feat: missing declaration",
        "feat: malformed declaration\n\nChange-contract: not-a-contract\n",
        "feat: unknown declaration\n\nChange-contract: unknown-check:unknown-proof-red->green\n",
        (
            f"feat: duplicate declaration\n\nChange-contract: {KNOWN_CONTRACT}\n"
            f"Change-contract: {KNOWN_CONTRACT}\n"
        ),
    ],
)
def test_changes_check_never_runs_proof_for_invalid_declarations(
    tmp_path: Path,
    message: str,
) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path="apps/example.py",
        message=message,
    )
    calls: list[tuple[str, ...]] = []

    def proof_runner(command: tuple[str, ...]) -> bool:
        calls.append(command)
        return True

    result = check_change_contract.check_commit(
        "HEAD",
        repository_root=repo,
        proof_runner=proof_runner,
    )

    assert result == 1
    assert calls == []


def test_changes_check_resolves_proof_executable_from_canonical_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert check_change_contract._run_proof(GATE_PROOF)
    assert calls == [
        (
            [str(REPOSITORY_ROOT / "scripts/test.sh"), "tests/scripts/test_changes_check.py"],
            REPOSITORY_ROOT,
        )
    ]


def test_changes_check_rejects_an_invalid_commit_ref(tmp_path: Path) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path="README.md",
        message="docs: valid fixture",
    )

    result = _run_cli(repo, "does-not-exist")

    assert result.returncode == 2
def test_changes_check_observes_before_state_through_candidate_snapshot(
    tmp_path: Path,
) -> None:
    """The candidate CLI must fix the old parser's real call-phase assertion RED."""

    fixture = tmp_path / "fixture"
    fixture.mkdir()
    _git(fixture, "init", "--quiet")
    _git(fixture, "config", "user.email", "tests@example.invalid")
    _git(fixture, "config", "user.name", "change-contract before-state")
    checker = fixture / "tools" / "check.py"
    checker.parent.mkdir()
    checker.write_text(
        "import argparse\n"
        "argparse.ArgumentParser().parse_args()\n",
        encoding="utf-8",
    )
    _git(fixture, "add", ".")
    _git(fixture, "commit", "--quiet", "-m", "base")
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=fixture,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    candidate_source = Path("scripts/check_change_contract.py").read_text(
        encoding="utf-8"
    )
    candidate_source = candidate_source.replace(
        "from scripts._change_contract_", "from _change_contract_"
    )
    checker.write_text(candidate_source, encoding="utf-8")
    for module_name in (
        "_change_contract_model.py",
        "_change_contract_observer.py",
        "_change_contract_snapshot.py",
    ):
        module_source = (Path("scripts") / module_name).read_text(encoding="utf-8")
        module_source = module_source.replace(
            "from scripts._change_contract_", "from _change_contract_"
        )
        (checker.parent / module_name).write_text(
            module_source,
            encoding="utf-8",
        )
    _git(fixture, "add", ".")
    _git(
        fixture,
        "commit",
        "--quiet",
        "-m",
        "fixture: upgrade checker outside harness surface",
    )

    result = subprocess.run(
        [sys.executable, "tools/check.py", "HEAD", "--before", parent],
        cwd=fixture,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_before_state_missing_parent_production_is_error_not_red(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "missing-production"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "change-contract missing production")
    test_file = repo / "tests" / "test_missing.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "from missing_parent import VALUE\n\n"
        "# (\"missing-production\", \"module\")\n"
        "def test_value_is_fixed():\n"
        "    assert VALUE == 2\n",
        encoding="utf-8",
    )
    helper = repo / "scripts" / "trusted_test_report.py"
    helper.parent.mkdir()
    helper.write_bytes(Path("scripts/trusted_test_report.py").read_bytes())
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "base")
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (repo / "missing_parent.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "fix")
    candidate = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    descriptor = check_change_contract.MappingDescriptor(
        proof=(),
        selectors=("tests/test_missing.py",),
        observer_paths=("tests/test_missing.py",),
        expectation="red-green",
        mapping_path="tests/test_missing.py",
    )
    result = check_change_contract.counterfactual(
        repo,
        candidate,
        parent,
        descriptor,
        ("missing-production", "module"),
    )

    assert result.infrastructure is True
    assert result.reason == "collection-error"


def test_git_object_environment_disables_replace_refs() -> None:
    assert snapshot.git_environment()["GIT_NO_REPLACE_OBJECTS"] == "1"


def test_absent_mapping_is_an_explicit_false(tmp_path: Path) -> None:
    repo = _make_repo(
        tmp_path,
        changed_path="README.md",
        message="docs: mapping fixture",
    )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    descriptor = check_change_contract.MappingDescriptor(
        proof=(),
        selectors=("README.md",),
        observer_paths=("README.md",),
        expectation="red-green",
    )

    assert observer.mapping_presence(repo, commit, descriptor, ("missing", "mapping")) is False


def test_report_red_requires_a_concrete_failed_assertion_record() -> None:
    report = _TestReport(
        pytest_status=1,
        tests_collected=1,
        collection_errors=0,
        internal_errors=0,
        setup_failures=0,
        teardown_failures=0,
        call_assertion_failures=1,
        call_non_assertion_failures=0,
        overflow=False,
        cases=(_TestCaseRecord("tests/t.py::test_value", "call", "passed", False),),
    )

    assert observer.meaningful_red(report) is False


def test_contained_claude_symlink_signature_binds_target_content(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("first\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").symlink_to("AGENTS.md")
    before = snapshot.observer_signature(tmp_path, "CLAUDE.md")
    (tmp_path / "AGENTS.md").write_text("second\n", encoding="utf-8")

    assert snapshot.observer_signature(tmp_path, "CLAUDE.md") != before


def test_counterfactual_uses_candidate_bound_reporter_for_both_snapshots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "candidate-reporter"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "change-contract candidate reporter")
    test_file = repo / "tests" / "test_value.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "# (\"candidate-reporter\", \"test\")\n"
        "def test_value():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    helper = repo / "scripts" / "trusted_test_report.py"
    helper.parent.mkdir()
    helper.write_bytes(Path("scripts/trusted_test_report.py").read_bytes())
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "base")
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (repo / "value.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "candidate")
    candidate = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    descriptor = check_change_contract.MappingDescriptor(
        proof=(),
        selectors=("tests/test_value.py",),
        observer_paths=("tests/test_value.py",),
        expectation="red-green",
        mapping_path="tests/test_value.py",
    )
    red = _TestReport(
        1,
        1,
        0,
        0,
        0,
        0,
        1,
        0,
        False,
        (_TestCaseRecord("tests/test_value.py::test_value", "call", "failed", True),),
    )
    green = _TestReport(
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        False,
        (_TestCaseRecord("tests/test_value.py::test_value", "call", "passed", False),),
    )
    reporter_calls: list[Path] = []

    def fake_run_report(
        _snapshot: Path,
        _selectors: tuple[str, ...],
        _temporary_root: Path,
        reporter: Path,
    ) -> _TestReport:
        reporter_calls.append(reporter)
        return red if len(reporter_calls) == 1 else green

    monkeypatch.setattr(observer, "run_report", fake_run_report)
    result = observer.counterfactual(
        repo,
        candidate,
        parent,
        descriptor,
        ("candidate-reporter", "test"),
        helper=tmp_path / "dirty-live-helper.py",
    )

    assert result.ok is True
    assert len(reporter_calls) == 2
    assert reporter_calls[0] == reporter_calls[1]
    assert reporter_calls[0].name == "trusted_test_report.py"
    assert "candidate" in reporter_calls[0].parts


def test_counterfactual_missing_snapshot_module_is_collection_error_not_live_green(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "import-isolation"
    repo.mkdir()
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "change-contract import isolation")
    test_file = repo / "tests" / "test_import.py"
    test_file.parent.mkdir()
    test_file.write_text(
        "# (\"import-isolation\", \"test\")\n"
        "import scripts.check_change_contract as checker\n\n"
        "def test_import_does_not_escape_snapshot():\n"
        "    assert hasattr(checker, \"_MAPPINGS\")\n",
        encoding="utf-8",
    )
    helper = repo / "scripts" / "trusted_test_report.py"
    helper.parent.mkdir()
    helper.write_bytes(Path("scripts/trusted_test_report.py").read_bytes())
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "base")
    parent = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (repo / "value.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "candidate")
    candidate = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    descriptor = check_change_contract.MappingDescriptor(
        proof=(),
        selectors=("tests/test_import.py",),
        observer_paths=("tests/test_import.py",),
        expectation="red-green",
        mapping_path="tests/test_import.py",
    )

    result = observer.counterfactual(
        repo,
        candidate,
        parent,
        descriptor,
        ("import-isolation", "test"),
    )

    assert result.ok is False
    assert result.infrastructure is True
    assert result.reason in {"collection-error", "internal-error", "pytest-error"}
