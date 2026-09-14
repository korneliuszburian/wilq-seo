from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import check_change_contract

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
