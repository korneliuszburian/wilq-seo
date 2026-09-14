#!/usr/bin/env python3
"""Check the declared proof contract for one commit without replaying RED."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path, PurePosixPath

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_TOKEN = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_CONTRACT = re.compile(
    rf"^(?P<check>{_TOKEN}):(?P<prediction>{_TOKEN})-red->green$"
)
_RUNTIME_PREFIXES = ("apps/", "packages/", "wilq/")
_RUNTIME_SOURCE_EXTENSIONS = frozenset(
    {".cjs", ".cts", ".js", ".jsx", ".mjs", ".mts", ".py", ".ts", ".tsx"}
)
_MANIFEST_NAMES = frozenset({"package.json", "pyproject.toml"})
_NON_RUNTIME_PATH_PARTS = frozenset({"assets", "docs", "fixtures"})
_EXECUTABLE_GATE_SCRIPTS = frozenset(
    {
        "scripts/access_pack_check.sh",
        "scripts/check_change_contract.py",
        "scripts/check_commit_message.py",
        "scripts/codex_skill_eval.sh",
        "scripts/eval_action_validation.sh",
        "scripts/eval_marketing_brief.sh",
        "scripts/health_check.sh",
        "scripts/lint.sh",
        "scripts/pre_demo_gate.sh",
        "scripts/quality.sh",
        "scripts/security.sh",
        "scripts/test.sh",
        "scripts/typecheck.sh",
        "scripts/verify.sh",
    }
)
ProofCommand = tuple[str, ...]
ProofRunner = Callable[[ProofCommand], bool]
_PROOFS: dict[tuple[str, str], ProofCommand] = {
    (
        "change-contract-gate",
        "cli-acceptance",
    ): (
        "scripts/test.sh",
        "tests/scripts/test_changes_check.py",
    ),
    (
        "connector-refresh-recovery",
        "bodyless-api-and-full-payload-cas",
    ): (
        "scripts/test.sh",
        "tests/connectors/test_connector_refresh_recovery.py",
        "tests/api_contracts/test_connector_refresh_recovery_contract.py",
    ),
    (
        "embedded-runtime-policy",
        "terra-max-fail-closed",
    ): (
        "scripts/test.sh",
        "tests/content/test_codex_app_server_transport.py",
        "tests/content/test_new_page_initial_draft.py",
        "tests/storage/test_codex_runs.py",
        "tests/content/test_initial_draft_run.py",
        "tests/content/test_initial_draft_queue_gate.py",
    ),
    (
        "inventory-classification",
        "exact-current-receipt-lineage",
    ): (
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
    (
        "current-disposition",
        "exact-persisted-authority-chain",
    ): (
        "scripts/test.sh",
        "tests/content/test_current_disposition_authority.py",
        "tests/actions/test_audit_store_contracts.py::test_audit_details_for_operator_keeps_only_canonical_digest_values",
        "tests/api_contracts/test_redaction_contracts.py",
        "tests/storage/test_sqlite_schema_inventory.py::test_current_disposition_schema_hunks_are_exact",
    ),
    (
        "delivery-identity",
        "exact-registered-receipt-authority",
    ): (
        "scripts/test.sh",
        "tests/content/test_delivery_identity_authority.py",
        "tests/content/test_delivery_identity_binding.py",
        "tests/content/test_delivery_identity_api.py",
        "tests/storage/test_sqlite_schema_inventory.py::test_delivery_identity_authority_schema_hunks_are_exact",
        "tests/api_contracts/test_redaction_contracts.py",
    ),
}


def _git(
    repository_root: Path,
    *args: str,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
    )


def _resolve_commit(repository_root: Path, ref: str) -> str | None:
    result = _git(
        repository_root,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{ref}^{{commit}}",
    )
    if result.returncode != 0:
        print(f"changes:check: cannot resolve commit ref {ref!r}", file=sys.stderr)
        return None
    return result.stdout.strip()


def _changed_paths(repository_root: Path, commit: str) -> list[str] | None:
    result = _git(
        repository_root,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        "--root",
        "-z",
        commit,
    )
    if result.returncode != 0:
        print(f"changes:check: cannot inspect commit {commit}", file=sys.stderr)
        return None
    return [path for path in result.stdout.split("\0") if path]


def _is_harness_surface(path: str) -> bool:
    normalized_path = path.replace("\\", "/")
    path_parts = PurePosixPath(normalized_path).parts
    if _NON_RUNTIME_PATH_PARTS.intersection(path_parts):
        return False
    if normalized_path.startswith((".github/workflows/", ".githooks/")):
        return True
    if PurePosixPath(normalized_path).name in _MANIFEST_NAMES:
        return True
    if normalized_path in _EXECUTABLE_GATE_SCRIPTS:
        return True
    return normalized_path.startswith(_RUNTIME_PREFIXES) and PurePosixPath(
        normalized_path
    ).suffix in _RUNTIME_SOURCE_EXTENSIONS


def _change_contract_values(repository_root: Path, commit: str) -> list[str] | None:
    message = _git(repository_root, "show", "-s", "--format=%B", commit)
    if message.returncode != 0:
        print(f"changes:check: cannot read commit message for {commit}", file=sys.stderr)
        return None
    parsed = _git(
        repository_root,
        "interpret-trailers",
        "--parse",
        "--unfold",
        input_text=message.stdout,
    )
    if parsed.returncode != 0:
        print(f"changes:check: cannot parse trailers for {commit}", file=sys.stderr)
        return None
    return [
        value.lstrip(" ")
        for line in parsed.stdout.splitlines()
        for key, separator, value in [line.partition(":")]
        if separator and key == "Change-contract"
    ]


def _run_proof(command: ProofCommand) -> bool:
    environment = os.environ.copy()
    environment["UV_OFFLINE"] = "1"
    executable = Path(command[0])
    if not executable.is_absolute():
        repository_executable = (REPOSITORY_ROOT / executable).resolve()
        if repository_executable.is_file():
            executable = repository_executable
    resolved_command = [str(executable), *command[1:]]
    try:
        result = subprocess.run(
            resolved_command,
            cwd=REPOSITORY_ROOT,
            check=False,
            env=environment,
        )
    except OSError:
        return False
    return result.returncode == 0


def check_commit(
    ref: str = "HEAD",
    repository_root: Path = REPOSITORY_ROOT,
    *,
    proof_runner: ProofRunner | None = None,
) -> int:
    commit = _resolve_commit(repository_root, ref)
    if commit is None:
        return 2
    paths = _changed_paths(repository_root, commit)
    if paths is None:
        return 2
    if not any(_is_harness_surface(path) for path in paths):
        print(f"changes:check: {commit[:8]} is not a harness-surface commit")
        return 0

    values = _change_contract_values(repository_root, commit)
    if values is None:
        return 2
    if len(values) != 1:
        print(
            f"changes:check: harness-surface commit {commit} requires exactly one "
            "Change-contract trailer",
            file=sys.stderr,
        )
        return 1

    match = _CONTRACT.fullmatch(values[0])
    if match is None:
        print(
            f"changes:check: malformed Change-contract trailer on commit {commit}",
            file=sys.stderr,
        )
        return 1
    contract = match.group("check"), match.group("prediction")
    check, prediction = contract
    proof = _PROOFS.get(contract)
    if proof is None:
        print(
            f"changes:check: unknown proof mapping for {check}:{prediction} on commit {commit}; "
            f"revert {commit} or add a repo-owned mapping",
            file=sys.stderr,
        )
        return 1
    runner = _run_proof if proof_runner is None else proof_runner
    if not runner(proof):
        print(
            f"changes:check: GREEN proof failed for harness-surface commit {commit}; "
            f"declared RED was not executed; revert {commit}",
            file=sys.stderr,
        )
        return 1
    print(
        f"changes:check: {commit[:8]} GREEN proof passed for {check}:{prediction}; "
        "declared RED was not executed"
    )
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=argv[0])
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPOSITORY_ROOT,
        help="metadata repository root to inspect; proofs use the canonical repository root",
    )
    parser.add_argument("commit_ref", nargs="?", default="HEAD")
    arguments = parser.parse_args(argv[1:])
    return check_commit(arguments.commit_ref, arguments.repo_root)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
