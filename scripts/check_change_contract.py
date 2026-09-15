#!/usr/bin/env python3
"""Check a declared change contract at an immutable Git fixed point."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path, PurePosixPath

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._change_contract_model import (
    MAPPINGS as _MAPPINGS,
)
from scripts._change_contract_model import (
    PROOFS as _PROOFS,
)
from scripts._change_contract_model import (
    CounterfactualResult,
    Expectation,
    MappingDescriptor,
    ProofCommand,
)
from scripts._change_contract_observer import counterfactual
from scripts._change_contract_snapshot import (
    INJECTION_ENVIRONMENT_KEYS,
    git_environment,
)

_PROOF_MAPPINGS = _MAPPINGS

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_REPORT_HELPER = REPOSITORY_ROOT / "scripts" / "trusted_test_report.py"
_TOKEN = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_CONTRACT = re.compile(
    rf"^(?P<check>{_TOKEN}):(?P<prediction>{_TOKEN})-"
    rf"(?P<before>red|green)->(?P<after>red|green)$"
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
        "scripts/trusted_test_report.py",
        "scripts/typecheck.sh",
        "scripts/verify.sh",
    }
)
ProofRunner = Callable[[ProofCommand], bool]


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
        env=git_environment(),
    )


def _valid_ref(ref: str) -> bool:
    return (
        bool(ref)
        and not ref.startswith("-")
        and "\\" not in ref
        and not any(character in ref for character in "\x00\r\n")
        and ".." not in PurePosixPath(ref).parts
    )


def _resolve_commit(repository_root: Path, ref: str) -> str | None:
    if not _valid_ref(ref):
        print(f"changes:check: invalid commit ref {ref!r}", file=sys.stderr)
        return None
    result = _git(
        repository_root,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{ref}^{{commit}}",
    )
    resolved = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", resolved):
        print(f"changes:check: cannot resolve commit ref {ref!r}", file=sys.stderr)
        return None
    return resolved


def _commit_parents(repository_root: Path, commit: str) -> list[str] | None:
    result = _git(repository_root, "rev-list", "--parents", "-n", "1", commit)
    fields = result.stdout.strip().split()
    if result.returncode != 0 or not fields or fields[0] != commit:
        return None
    return fields[1:]


def _changed_paths(repository_root: Path, commit: str) -> list[str] | None:
    result = _git(
        repository_root,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        "-m",
        "--root",
        "-z",
        commit,
    )
    if result.returncode != 0:
        print(f"changes:check: cannot inspect commit {commit}", file=sys.stderr)
        return None
    return list(dict.fromkeys(path for path in result.stdout.split("\0") if path))


def _is_harness_surface(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if _NON_RUNTIME_PATH_PARTS.intersection(PurePosixPath(normalized).parts):
        return False
    if normalized.startswith((".github/workflows/", ".githooks/", "tests/scripts/")):
        return True
    if PurePosixPath(normalized).name in _MANIFEST_NAMES:
        return True
    if normalized in _EXECUTABLE_GATE_SCRIPTS or normalized.startswith(
        "scripts/_change_contract_"
    ):
        return True
    return normalized.startswith(_RUNTIME_PREFIXES) and PurePosixPath(
        normalized
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
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in INJECTION_ENVIRONMENT_KEYS
    }
    environment["UV_OFFLINE"] = "1"
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    executable = Path(command[0])
    if not executable.is_absolute():
        candidate = (REPOSITORY_ROOT / executable).resolve()
        if candidate.is_file():
            executable = candidate
    try:
        result = subprocess.run(
            [str(executable), *command[1:]],
            cwd=REPOSITORY_ROOT,
            check=False,
            env=environment,
        )
    except OSError:
        return False
    return result.returncode == 0


def _fixed_point(
    repository_root: Path,
    ref: str,
    before_ref: str | None,
) -> tuple[str, str | None] | None:
    candidate = _resolve_commit(repository_root, ref)
    if candidate is None:
        return None
    parents = _commit_parents(repository_root, candidate)
    if parents is None:
        print(f"changes:check: cannot inspect parents of {candidate}", file=sys.stderr)
        return None
    if before_ref is None:
        if len(parents) > 1:
            print(
                "changes:check: merge commits require --before and a sole parent",
                file=sys.stderr,
            )
            return None
        return candidate, None
    before = _resolve_commit(repository_root, before_ref)
    if before is None:
        return None
    if candidate == before:
        print("changes:check: candidate and --before are identical", file=sys.stderr)
        return None
    if len(parents) == 0:
        print("changes:check: candidate root commit has no sole parent", file=sys.stderr)
        return None
    if len(parents) != 1:
        print("changes:check: candidate merge commits are unsupported", file=sys.stderr)
        return None
    if parents[0] != before:
        print("changes:check: --before is not the candidate's sole parent", file=sys.stderr)
        return None
    return candidate, before


def _contract_expectation(match: re.Match[str]) -> Expectation | None:
    transition = match.group("before"), match.group("after")
    if transition == ("red", "green"):
        return "red-green"
    if transition == ("green", "green"):
        return "unchanged-green"
    return None


def _legacy_result(
    candidate: str,
    key: tuple[str, str],
    proof: ProofCommand,
    proof_runner: ProofRunner | None,
) -> int:
    runner = _run_proof if proof_runner is None else proof_runner
    if not runner(proof):
        print(
            f"changes:check: GREEN proof failed for harness-surface commit {candidate}; "
            f"declared RED was not executed; revert {candidate}",
            file=sys.stderr,
        )
        return 1
    print(
        f"changes:check: {candidate[:8]} GREEN proof passed for "
        f"{key[0]}:{key[1]}; declared RED was not executed"
    )
    return 0


def _observed_result(
    repository_root: Path,
    candidate: str,
    before: str,
    key: tuple[str, str],
    descriptor: MappingDescriptor,
) -> int:
    result: CounterfactualResult = counterfactual(
        repository_root,
        candidate,
        before,
        descriptor,
        key,
        _REPORT_HELPER,
    )
    if result.ok:
        outcome = (
            "GREEN unchanged-green (observer unchanged)"
            if descriptor.expectation == "unchanged-green"
            else "GREEN after observed RED"
        )
        print(
            f"changes:check: {candidate[:8]} {outcome} for "
            f"{key[0]}:{key[1]} (before {before[:8]})"
        )
        return 0
    if result.infrastructure:
        print(
            f"changes:check: {key[0]}:{key[1]} could not be verified: {result.reason}",
            file=sys.stderr,
        )
        return 2
    print(
        f"changes:check: {key[0]}:{key[1]} contract failed: {result.reason}; "
        f"revert {candidate} or repair the candidate",
        file=sys.stderr,
    )
    return 1


def check_commit(
    ref: str = "HEAD",
    repository_root: Path = REPOSITORY_ROOT,
    *,
    before: str | None = None,
    proof_runner: ProofRunner | None = None,
) -> int:
    try:
        repository_root = repository_root.resolve(strict=True)
    except OSError:
        print("changes:check: repository root is not readable", file=sys.stderr)
        return 2
    try:
        fixed = _fixed_point(repository_root, ref, before)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"changes:check: fixed-point inspection failed: {error}", file=sys.stderr)
        return 2
    if fixed is None:
        return 2
    candidate, before_commit = fixed
    paths = _changed_paths(repository_root, candidate)
    if paths is None:
        return 2
    if not any(_is_harness_surface(path) for path in paths):
        print(f"changes:check: {candidate[:8]} is not a harness-surface commit")
        return 0
    values = _change_contract_values(repository_root, candidate)
    if values is None:
        return 2
    if len(values) != 1:
        print(
            f"changes:check: harness-surface commit {candidate} requires exactly one "
            "Change-contract trailer",
            file=sys.stderr,
        )
        return 1
    match = _CONTRACT.fullmatch(values[0])
    if match is None:
        print(
            f"changes:check: malformed Change-contract trailer on commit {candidate}",
            file=sys.stderr,
        )
        return 1
    key = match.group("check"), match.group("prediction")
    proof = _PROOFS.get(key)
    descriptor = _MAPPINGS.get(key)
    expectation = _contract_expectation(match)
    if proof is None or descriptor is None:
        print(
            f"changes:check: unknown proof mapping for {key[0]}:{key[1]} on commit "
            f"{candidate}; revert {candidate} or add a repo-owned mapping",
            file=sys.stderr,
        )
        return 1
    if expectation is None or descriptor.expectation != expectation:
        print(
            f"changes:check: contract expectation for {key[0]}:{key[1]} does not match "
            "the trusted mapping",
            file=sys.stderr,
        )
        return 1
    if before_commit is None:
        return _legacy_result(candidate, key, proof, proof_runner)
    return _observed_result(repository_root, candidate, before_commit, key, descriptor)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=argv[0])
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPOSITORY_ROOT,
        help="Git object repository to inspect; execution uses trusted snapshots",
    )
    parser.add_argument(
        "--before",
        dest="before_ref",
        help="the candidate's sole parent commit (required for observed RED->GREEN)",
    )
    parser.add_argument("commit_ref", nargs="?", default="HEAD")
    arguments = parser.parse_args(argv[1:])
    return check_commit(
        arguments.commit_ref,
        arguments.repo_root,
        before=arguments.before_ref,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
