from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

from scripts import check_bandit_baseline
from scripts.check_bandit_baseline import BanditBaselineError, validate_report

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
type BanditReport = tuple[Path, int, int]


@pytest.fixture(scope="module")
def current_bandit_report() -> Iterator[BanditReport]:
    with tempfile.TemporaryDirectory(prefix="wilq-bandit-baseline-test-") as temporary_name:
        report_path = Path(temporary_name) / "bandit.json"
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "bandit",
                "-q",
                "-r",
                "wilq",
                "apps/api",
                ".codex/hooks",
                "-f",
                "json",
                "-o",
                str(report_path),
            ],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode in {0, 1}, "Bandit scan failed before baseline validation"
        payload = _read_report(report_path)
        results = payload.get("results")
        assert isinstance(results, list)
        finding_count = len(results)
        assert finding_count <= 33
        assert all(
            isinstance(record, dict) and record.get("issue_severity") == "LOW"
            for record in results
        )
        assert (completed.returncode == 1) == bool(results)
        yield report_path, completed.returncode, finding_count


def _read_report(report_path: Path) -> dict[str, object]:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_report(report_path: Path, payload: dict[str, object]) -> None:
    report_path.write_text(json.dumps(payload), encoding="utf-8")


def _adjust_report_metrics(
    payload: dict[str, object],
    finding: dict[str, object],
    adjustment: int,
) -> None:
    metrics = payload.get("metrics")
    assert isinstance(metrics, dict)
    filename = finding.get("filename")
    severity = finding.get("issue_severity")
    confidence = finding.get("issue_confidence")
    assert isinstance(filename, str)
    assert isinstance(severity, str)
    assert isinstance(confidence, str)
    totals = metrics.get("_totals")
    file_metrics = metrics.get(filename)
    assert isinstance(totals, dict)
    assert isinstance(file_metrics, dict)
    for stats in (totals, file_metrics):
        for name in (f"SEVERITY.{severity}", f"CONFIDENCE.{confidence}"):
            count = stats.get(name)
            assert isinstance(count, int) and not isinstance(count, bool)
            stats[name] = count + adjustment


def _adjust_report_metric(payload: dict[str, object], metric_name: str) -> None:
    metrics = payload.get("metrics")
    assert isinstance(metrics, dict)
    totals = metrics.get("_totals")
    assert isinstance(totals, dict)
    file_metrics = next(value for path, value in metrics.items() if path != "_totals")
    assert isinstance(file_metrics, dict)
    for stats in (totals, file_metrics):
        count = stats.get(metric_name)
        assert isinstance(count, int) and not isinstance(count, bool)
        stats[metric_name] = count + 1


def _next_unreported_line(results: Sequence[object], finding: dict[str, object]) -> int:
    line_number = finding["line_number"]
    filename = finding["filename"]
    assert isinstance(line_number, int)
    occupied_lines = {
        record["line_number"]
        for record in results
        if isinstance(record, dict)
        and record.get("filename") == filename
        and isinstance(record.get("line_number"), int)
    }
    candidate_line = line_number + 1
    while candidate_line in occupied_lines:
        candidate_line += 1
    return candidate_line


def test_exact_current_low_baseline_passes(current_bandit_report: BanditReport) -> None:
    report_path, bandit_status, finding_count = current_bandit_report

    assert validate_report(report_path, bandit_status) == finding_count


def test_parseable_empty_bandit_report_with_success_status_fails(tmp_path: Path) -> None:
    report_path = tmp_path / "empty-report.json"
    report_path.write_text(json.dumps({"errors": [], "results": []}), encoding="utf-8")

    with pytest.raises(BanditBaselineError, match="fields are missing"):
        validate_report(report_path, 0)


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        ("generated_at", "", "generated_at"),
        ("metrics", {}, "metrics"),
    ],
)
def test_malformed_bandit_metadata_fails(
    current_bandit_report: BanditReport,
    tmp_path: Path,
    field: str,
    value: object,
    expected_message: str,
) -> None:
    report_path, bandit_status, _ = current_bandit_report
    payload = _read_report(report_path)
    payload[field] = value
    malformed_report = tmp_path / f"malformed-{field}.json"
    _write_report(malformed_report, payload)

    with pytest.raises(BanditBaselineError, match=expected_message):
        validate_report(malformed_report, bandit_status)


def test_bandit_exit_zero_with_findings_fails(
    current_bandit_report: BanditReport,
) -> None:
    report_path, _, _ = current_bandit_report

    with pytest.raises(BanditBaselineError, match="exited 0 with JSON findings"):
        validate_report(report_path, 0)


def test_baseline_total_allowed_count_rejects_tampered_count(
    current_bandit_report: BanditReport,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline = json.loads(check_bandit_baseline.BASELINE_PATH.read_text(encoding="utf-8"))
    assert isinstance(baseline, dict)
    findings = baseline.get("findings")
    assert isinstance(findings, list)
    assert isinstance(findings[0], dict)
    findings[0]["count"] = 2
    tampered_baseline = tmp_path / "tampered-baseline.json"
    tampered_baseline.write_text(json.dumps(baseline), encoding="utf-8")
    monkeypatch.setattr(check_bandit_baseline, "BASELINE_PATH", tampered_baseline)
    report_path, bandit_status, _ = current_bandit_report

    with pytest.raises(BanditBaselineError, match="must allow exactly 33 findings"):
        validate_report(report_path, bandit_status)


def test_fewer_known_low_findings_pass(
    current_bandit_report: BanditReport,
    tmp_path: Path,
) -> None:
    report_path, bandit_status, finding_count = current_bandit_report
    payload = _read_report(report_path)
    results = payload["results"]
    assert isinstance(results, list)
    removed_finding = results.pop()
    assert isinstance(removed_finding, dict)
    _adjust_report_metrics(payload, removed_finding, -1)
    reduced_report = tmp_path / "reduced-findings.json"
    _write_report(reduced_report, payload)

    assert validate_report(reduced_report, bandit_status) == finding_count - 1


@pytest.mark.parametrize(
    ("metric_name", "reviewed_cap"),
    [("nosec", 0), ("skipped_tests", 26)],
)
def test_suppression_metric_increase_exceeds_reviewed_cap(
    current_bandit_report: BanditReport,
    tmp_path: Path,
    metric_name: str,
    reviewed_cap: int,
) -> None:
    report_path, bandit_status, _ = current_bandit_report
    payload = _read_report(report_path)
    original_results = copy.deepcopy(payload.get("results"))
    metrics = payload.get("metrics")
    assert isinstance(metrics, dict)
    totals = metrics.get("_totals")
    assert isinstance(totals, dict)
    assert totals.get(metric_name) == reviewed_cap

    _adjust_report_metric(payload, metric_name)
    assert payload.get("results") == original_results
    adjusted_totals = metrics.get("_totals")
    assert isinstance(adjusted_totals, dict)
    assert adjusted_totals.get(metric_name) == reviewed_cap + 1

    report_with_suppression = tmp_path / f"increased-{metric_name}.json"
    _write_report(report_with_suppression, payload)

    with pytest.raises(BanditBaselineError, match="reviewed cap"):
        validate_report(report_with_suppression, bandit_status)


def test_new_b101_at_another_line_in_an_existing_file_fails(
    current_bandit_report: BanditReport,
    tmp_path: Path,
) -> None:
    report_path, bandit_status, _ = current_bandit_report
    payload = _read_report(report_path)
    results = payload["results"]
    assert isinstance(results, list)
    existing_b101 = next(
        record
        for record in results
        if isinstance(record, dict) and record.get("test_id") == "B101"
    )
    assert isinstance(existing_b101, dict)
    new_finding = copy.deepcopy(existing_b101)
    new_line = _next_unreported_line(results, existing_b101)
    new_finding["line_number"] = new_line
    new_finding["line_range"] = [new_line]
    results.append(new_finding)
    _adjust_report_metrics(payload, new_finding, 1)
    new_report = tmp_path / "new-b101.json"
    _write_report(new_report, payload)

    with pytest.raises(BanditBaselineError, match="new or changed Bandit finding"):
        validate_report(new_report, bandit_status)


def test_new_medium_finding_fails(
    current_bandit_report: BanditReport,
    tmp_path: Path,
) -> None:
    report_path, bandit_status, _ = current_bandit_report
    payload = _read_report(report_path)
    results = payload["results"]
    assert isinstance(results, list)
    existing_b101 = next(
        record
        for record in results
        if isinstance(record, dict) and record.get("test_id") == "B101"
    )
    assert isinstance(existing_b101, dict)
    medium_finding = copy.deepcopy(existing_b101)
    new_line = _next_unreported_line(results, existing_b101)
    medium_finding["line_number"] = new_line
    medium_finding["line_range"] = [new_line]
    medium_finding["issue_severity"] = "MEDIUM"
    results.append(medium_finding)
    _adjust_report_metrics(payload, medium_finding, 1)
    medium_report = tmp_path / "new-medium.json"
    _write_report(medium_report, payload)

    with pytest.raises(BanditBaselineError, match="disallowed Bandit severity MEDIUM"):
        validate_report(medium_report, bandit_status)


def test_changed_bandit_context_fails(
    current_bandit_report: BanditReport,
    tmp_path: Path,
) -> None:
    report_path, bandit_status, _ = current_bandit_report
    payload = _read_report(report_path)
    results = payload["results"]
    assert isinstance(results, list)
    assert isinstance(results[0], dict)
    code_context = results[0].get("code")
    assert isinstance(code_context, str)
    results[0]["code"] = f"{code_context}\nchanged"
    changed_report = tmp_path / "changed-context.json"
    _write_report(changed_report, payload)

    with pytest.raises(BanditBaselineError, match="new or changed Bandit finding"):
        validate_report(changed_report, bandit_status)


def test_excess_baseline_count_fails(
    current_bandit_report: BanditReport,
    tmp_path: Path,
) -> None:
    report_path, bandit_status, _ = current_bandit_report
    payload = _read_report(report_path)
    results = payload["results"]
    assert isinstance(results, list)
    assert isinstance(results[0], dict)
    results.append(copy.deepcopy(results[0]))
    duplicate_finding = results[-1]
    assert isinstance(duplicate_finding, dict)
    _adjust_report_metrics(payload, duplicate_finding, 1)
    excess_report = tmp_path / "excess-count.json"
    _write_report(excess_report, payload)

    with pytest.raises(BanditBaselineError, match="excess Bandit finding count"):
        validate_report(excess_report, bandit_status)


def test_bandit_errors_fail(
    current_bandit_report: BanditReport,
    tmp_path: Path,
) -> None:
    report_path, bandit_status, _ = current_bandit_report
    payload = _read_report(report_path)
    payload["errors"] = ["synthetic scan error"]
    error_report = tmp_path / "bandit-errors.json"
    _write_report(error_report, payload)

    with pytest.raises(BanditBaselineError, match="report contains errors"):
        validate_report(error_report, bandit_status)


def test_bandit_exit_one_without_findings_fails(
    current_bandit_report: BanditReport,
    tmp_path: Path,
) -> None:
    report_path, _, _ = current_bandit_report
    payload = _read_report(report_path)
    payload["results"] = []
    empty_report = tmp_path / "empty-results.json"
    _write_report(empty_report, payload)

    with pytest.raises(BanditBaselineError, match="exited 1 without JSON findings"):
        validate_report(empty_report, 1)


def test_missing_bandit_report_fails(tmp_path: Path) -> None:
    with pytest.raises(BanditBaselineError, match="missing or unreadable"):
        validate_report(tmp_path / "missing.json", 1)


@pytest.mark.parametrize(
    ("report_contents", "expected_message"),
    [("{", "is malformed"), ("{}", "fields are missing")],
)
def test_malformed_bandit_report_fails(
    tmp_path: Path,
    report_contents: str,
    expected_message: str,
) -> None:
    malformed_report = tmp_path / "malformed.json"
    malformed_report.write_text(report_contents, encoding="utf-8")

    with pytest.raises(BanditBaselineError, match=expected_message):
        validate_report(malformed_report, 1)
