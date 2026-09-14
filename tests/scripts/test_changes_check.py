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
