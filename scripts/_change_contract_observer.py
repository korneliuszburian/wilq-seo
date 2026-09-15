"""Private observed-before execution and pytest outcome classification."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._change_contract_model import (
    CounterfactualResult,
    MappingDescriptor,
    TestCaseRecord,
    TestReport,
)
from scripts._change_contract_snapshot import (
    INJECTION_ENVIRONMENT_KEYS,
    SnapshotError,
    archive_tree,
    git_environment,
    observer_signature,
    overlay_observers,
    safe_relative_path,
    selector_path,
    snapshot_path,
)

_REPORT_HELPER = Path(__file__).resolve().parent / "trusted_test_report.py"
_MAX_REPORT_BYTES = 2_000_000
_MAX_REPORT_CASES = 4096
_TEST_TIMEOUT_SECONDS = 60
def clean_test_environment(temporary_root: Path) -> dict[str, str]:
    environment = {
        "PATH": os.defpath,
        "LC_ALL": "C",
        "LANG": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "PYTHONNOUSERSITE": "1",
        "PYTHONHASHSEED": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "TMPDIR": str(temporary_root),
        "TEMP": str(temporary_root),
        "TMP": str(temporary_root),
    }
    clean = {
        key: value
        for key, value in environment.items()
        if key not in INJECTION_ENVIRONMENT_KEYS
    }
    clean["GIT_CONFIG_GLOBAL"] = os.devnull
    clean["GIT_NO_REPLACE_OBJECTS"] = "1"
    return clean


def _report_integer(payload: dict[str, object], name: str) -> int:
    value = payload.get(name)
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > _MAX_REPORT_CASES
    ):
        raise SnapshotError(f"pytest report field {name} is invalid")
    return value


def parse_report(path: Path) -> TestReport:
    try:
        if path.stat().st_size > _MAX_REPORT_BYTES:
            raise SnapshotError("pytest report is too large")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SnapshotError("pytest report is unreadable") from error
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise SnapshotError("pytest report has an unknown version")
    overflow = payload.get("overflow")
    raw_cases = payload.get("cases")
    if not isinstance(overflow, bool) or not isinstance(raw_cases, list):
        raise SnapshotError("pytest report shape is invalid")
    if len(raw_cases) > _MAX_REPORT_CASES:
        raise SnapshotError("pytest report cases are invalid")
    cases: list[TestCaseRecord] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise SnapshotError("pytest report case is invalid")
        nodeid, when, outcome, assertion = (
            raw_case.get("nodeid"),
            raw_case.get("when"),
            raw_case.get("outcome"),
            raw_case.get("assertion"),
        )
        if (
            not isinstance(nodeid, str)
            or not isinstance(when, str)
            or not isinstance(outcome, str)
            or not isinstance(assertion, bool)
        ):
            raise SnapshotError("pytest report case field is invalid")
        cases.append(TestCaseRecord(nodeid, when, outcome, assertion))
    return TestReport(
        pytest_status=_report_integer(payload, "pytest_status"),
        tests_collected=_report_integer(payload, "tests_collected"),
        collection_errors=_report_integer(payload, "collection_errors"),
        internal_errors=_report_integer(payload, "internal_errors"),
        setup_failures=_report_integer(payload, "setup_failures"),
        teardown_failures=_report_integer(payload, "teardown_failures"),
        call_assertion_failures=_report_integer(payload, "call_assertion_failures"),
        call_non_assertion_failures=_report_integer(payload, "call_non_assertion_failures"),
        overflow=overflow,
        cases=tuple(cases),
    )


def run_report(
    snapshot: Path,
    selectors: Sequence[str],
    temporary_root: Path,
    helper: Path = _REPORT_HELPER,
) -> TestReport:
    if not helper.is_file():
        raise SnapshotError("trusted pytest report helper is absent")
    report_path = temporary_root / (
        f"report-{hashlib.sha256(str(snapshot).encode()).hexdigest()}.json"
    )
    command = [
        sys.executable,
        "-I",
        "-S",
        str(helper),
        "--root",
        str(snapshot),
        "--report-file",
        str(report_path),
        *selectors,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=snapshot,
            check=False,
            env=clean_test_environment(temporary_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=_TEST_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SnapshotError("pytest execution did not complete") from error
    try:
        return parse_report(report_path)
    except SnapshotError as error:
        if result.returncode == 0:
            raise
        raise SnapshotError(
            f"pytest report missing after exit {result.returncode}"
        ) from error


def report_error(report: TestReport) -> str | None:
    if report.overflow:
        return "report-overflow"
    if report.collection_errors:
        return "collection-error"
    if report.internal_errors:
        return "internal-error"
    if report.setup_failures:
        return "setup-error"
    if report.teardown_failures:
        return "teardown-error"
    call_cases = [case for case in report.cases if case.when == "call"]
    assertion_failures = sum(
        1 for case in call_cases if case.outcome == "failed" and case.assertion
    )
    non_assertion_failures = sum(
        1 for case in call_cases if case.outcome == "failed" and not case.assertion
    )
    if (
        assertion_failures != report.call_assertion_failures
        or non_assertion_failures != report.call_non_assertion_failures
        or (report.pytest_status == 0 and assertion_failures + non_assertion_failures > 0)
        or (report.pytest_status == 1 and assertion_failures + non_assertion_failures == 0)
    ):
        return "report-inconsistent"
    if report.call_non_assertion_failures:
        return "call-error"
    if not call_cases:
        return "no-call-tests"
    if any(case.outcome != "passed" and not case.assertion for case in call_cases):
        return "call-not-passed"
    if report.pytest_status not in {0, 1}:
        return "pytest-error"
    if report.tests_collected < 1:
        return "no-tests-collected"
    return None


def meaningful_red(report: TestReport) -> bool:
    assertion_failures = sum(
        1
        for case in report.cases
        if case.when == "call" and case.outcome == "failed" and case.assertion
    )
    return (
        report_error(report) is None
        and report.pytest_status == 1
        and assertion_failures > 0
        and assertion_failures == report.call_assertion_failures
    )


def green(report: TestReport) -> bool:
    return report_error(report) is None and report.pytest_status == 0


def call_outcomes(report: TestReport) -> dict[str, str]:
    return {
        case.nodeid: case.outcome
        for case in report.cases
        if case.when == "call"
    }


def mapping_presence(
    repository_root: Path,
    commit: str,
    descriptor: MappingDescriptor,
    key: tuple[str, str],
) -> bool:
    result = subprocess.run(
        ["git", "show", f"{commit}:{descriptor.mapping_path}"],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
        input=None,
        env=git_environment(),
    )
    if result.returncode != 0:
        return False
    marker = re.compile(
        rf"[\"']{re.escape(key[0])}[\"']\s*,\s*[\"']{re.escape(key[1])}[\"']"
    )
    return marker.search(result.stdout) is not None


def _validate_descriptor(
    descriptor: MappingDescriptor,
    parent_snapshot: Path,
    candidate_snapshot: Path,
) -> None:
    if not descriptor.selectors or not descriptor.observer_paths:
        raise SnapshotError("mapping descriptor must name selectors and observers")
    if len(set(descriptor.observer_paths)) != len(descriptor.observer_paths):
        raise SnapshotError("mapping descriptor repeats an observer path")
    safe_relative_path(descriptor.mapping_path)
    safe_relative_path(descriptor.reporter_path)
    reporter = snapshot_path(candidate_snapshot, descriptor.reporter_path)
    if not reporter.is_file() or reporter.is_symlink():
        raise SnapshotError("trusted pytest report helper is not a regular candidate file")
    for selector in descriptor.selectors:
        relative = selector_path(selector)
        candidate_path = snapshot_path(candidate_snapshot, relative)
        if not candidate_path.is_file() or candidate_path.is_symlink():
            raise SnapshotError(f"selector path is not a regular candidate file: {relative}")
        parent_path = parent_snapshot / relative
        if parent_path.exists() and (parent_path.is_symlink() or not parent_path.is_file()):
            raise SnapshotError(f"selector path is not a regular parent file: {relative}")
    for relative in descriptor.observer_paths:
        observer_signature(candidate_snapshot, relative)


def _observer_signatures(
    parent_snapshot: Path,
    candidate_snapshot: Path,
    descriptor: MappingDescriptor,
) -> tuple[dict[str, str], dict[str, str]]:
    parent: dict[str, str] = {}
    for path in descriptor.observer_paths:
        destination = parent_snapshot / path
        if destination.exists() or destination.is_symlink():
            parent[path] = observer_signature(parent_snapshot, path)
    candidate = {
        path: observer_signature(candidate_snapshot, path)
        for path in descriptor.observer_paths
    }
    return parent, candidate


def _evaluate_reports(
    parent_report: TestReport,
    candidate_report: TestReport,
    descriptor: MappingDescriptor,
) -> CounterfactualResult:
    if not green(candidate_report):
        reason = report_error(candidate_report) or "after-not-green"
        return CounterfactualResult(False, reason != "after-not-green", reason)
    if descriptor.expectation == "red-green":
        if not meaningful_red(parent_report):
            reason = report_error(parent_report) or "before-state-not-red"
            return CounterfactualResult(False, reason != "before-state-not-red", reason)
        base_cases, head_cases = call_outcomes(parent_report), call_outcomes(candidate_report)
        missing = sorted(
            nodeid
            for nodeid, outcome in base_cases.items()
            if outcome == "failed" and head_cases.get(nodeid) != "passed"
        )
        if missing:
            return CounterfactualResult(False, False, "observer-shrinkage:" + ",".join(missing[:8]))
    elif not green(parent_report):
        reason = report_error(parent_report) or "before-not-green"
        return CounterfactualResult(False, reason != "before-not-green", reason)
    elif set(call_outcomes(parent_report)) != set(call_outcomes(candidate_report)):
        return CounterfactualResult(False, False, "selectors-changed")
    return CounterfactualResult(True, False, "green")


def counterfactual(
    repository_root: Path,
    candidate_commit: str,
    before_commit: str,
    descriptor: MappingDescriptor,
    mapping_key: tuple[str, str],
    helper: Path = _REPORT_HELPER,
) -> CounterfactualResult:
    del helper
    try:
        with tempfile.TemporaryDirectory(prefix="changes-check-") as temporary_name:
            temporary_root = Path(temporary_name)
            parent_snapshot, candidate_snapshot = (
                temporary_root / "parent",
                temporary_root / "candidate",
            )
            archive_tree(repository_root, before_commit, parent_snapshot)
            archive_tree(repository_root, candidate_commit, candidate_snapshot)
            _validate_descriptor(descriptor, parent_snapshot, candidate_snapshot)
            parent_presence = mapping_presence(
                repository_root, before_commit, descriptor, mapping_key
            )
            candidate_presence = mapping_presence(
                repository_root, candidate_commit, descriptor, mapping_key
            )
            if parent_presence is True and candidate_presence is not True:
                return CounterfactualResult(False, False, "mapping-missing-candidate")
            if candidate_presence is False and not descriptor.allow_new_mapping:
                return CounterfactualResult(False, False, "mapping-missing-candidate")
            if (
                parent_presence is False
                and candidate_presence is True
                and not descriptor.allow_new_mapping
            ):
                return CounterfactualResult(False, False, "mapping-absent-before")
            signatures_parent, signatures_candidate = _observer_signatures(
                parent_snapshot, candidate_snapshot, descriptor
            )
            reporter = snapshot_path(candidate_snapshot, descriptor.reporter_path)
            if descriptor.expectation == "unchanged-green":
                if signatures_parent != signatures_candidate:
                    return CounterfactualResult(False, False, "observer-changed")
            else:
                overlay_observers(
                    parent_snapshot,
                    candidate_snapshot,
                    descriptor.observer_paths,
                )
            parent_report = run_report(
                parent_snapshot, descriptor.selectors, temporary_root, reporter
            )
            candidate_report = run_report(
                candidate_snapshot, descriptor.selectors, temporary_root, reporter
            )
            return _evaluate_reports(parent_report, candidate_report, descriptor)
    except (OSError, RuntimeError, SnapshotError, TypeError, ValueError) as error:
        return CounterfactualResult(False, True, str(error))
