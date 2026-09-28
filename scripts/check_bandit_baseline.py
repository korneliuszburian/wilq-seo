#!/usr/bin/env python3
"""Fail closed on Bandit findings outside the reviewed code-context baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import cast

BASELINE_PATH = Path(__file__).with_name("bandit_baseline.json")
BASELINE_ENTRY_COUNT = 33
BANDIT_REVIEWED_METRIC_CAPS = {"nosec": 0, "skipped_tests": 26}
FINGERPRINT_PATTERN = re.compile(r"[0-9a-f]{64}")
TEST_ID_PATTERN = re.compile(r"B[0-9]{3}")
SEVERITIES = frozenset({"LOW", "MEDIUM", "HIGH"})
CONFIDENCES = frozenset({"LOW", "MEDIUM", "HIGH"})
BANDIT_METRIC_FIELDS = frozenset(
    {
        "CONFIDENCE.HIGH",
        "CONFIDENCE.LOW",
        "CONFIDENCE.MEDIUM",
        "CONFIDENCE.UNDEFINED",
        "SEVERITY.HIGH",
        "SEVERITY.LOW",
        "SEVERITY.MEDIUM",
        "SEVERITY.UNDEFINED",
        "loc",
        "nosec",
        "skipped_tests",
    }
)
type Fingerprint = tuple[str, int, str, str, str, str]
type MetricCounts = dict[str, int]


class BanditBaselineError(ValueError):
    pass


def _metric_counts(value: object, label: str) -> MetricCounts:
    metrics = _object(value, label)
    if set(metrics) != BANDIT_METRIC_FIELDS:
        raise BanditBaselineError(f"{label} fields are malformed")
    counts: MetricCounts = {}
    for name, count in metrics.items():
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise BanditBaselineError(f"{label} counts are malformed")
        counts[name] = count
    return counts


def _report_metrics(payload: dict[str, object]) -> MetricCounts:
    metrics = _object(payload["metrics"], "Bandit JSON report metrics")
    if "_totals" not in metrics or len(metrics) == 1:
        raise BanditBaselineError("Bandit JSON report metrics are incomplete")
    totals = _metric_counts(metrics["_totals"], "Bandit metrics totals")
    file_totals: MetricCounts = {name: 0 for name in BANDIT_METRIC_FIELDS}
    for path, value in metrics.items():
        if path == "_totals":
            continue
        _canonical_repo_path(path)
        counts = _metric_counts(value, f"Bandit metrics for {path}")
        for name, count in counts.items():
            file_totals[name] += count
    if file_totals != totals:
        raise BanditBaselineError("Bandit JSON report metrics totals are inconsistent")
    return totals


def _read_json(path: Path, label: str) -> object:
    try:
        return cast(object, json.loads(path.read_text(encoding="utf-8")))
    except OSError as error:
        raise BanditBaselineError(f"{label} is missing or unreadable") from error
    except (UnicodeError, json.JSONDecodeError) as error:
        raise BanditBaselineError(f"{label} is malformed") from error


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise BanditBaselineError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _canonical_repo_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise BanditBaselineError("finding path is not a canonical repo-relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or not path.parts
        or any(part in {".", ".."} for part in path.parts)
    ):
        raise BanditBaselineError("finding path is not a canonical repo-relative path")
    if not (
        path.parts[0] == "wilq"
        or path.parts[:2] == ("apps", "api")
        or path.parts[:2] == (".codex", "hooks")
    ):
        raise BanditBaselineError("finding path is outside the Bandit scan targets")
    return value


def _text_field(record: dict[str, object], name: str) -> str:
    value = record.get(name)
    if not isinstance(value, str) or not value:
        raise BanditBaselineError(f"finding field {name} is missing or malformed")
    return value


def _integer_field(record: dict[str, object], name: str) -> int:
    value = record.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise BanditBaselineError(f"finding field {name} is missing or malformed")
    return value


def _baseline_fingerprint(record: object) -> tuple[Fingerprint, int]:
    entry = _object(record, "baseline finding")
    expected_fields = {
        "path",
        "line",
        "test_id",
        "severity",
        "confidence",
        "code_sha256",
        "count",
    }
    if set(entry) != expected_fields:
        raise BanditBaselineError("baseline finding fields are malformed")
    path = _canonical_repo_path(entry["path"])
    line = _integer_field(entry, "line")
    test_id = _text_field(entry, "test_id")
    severity = _text_field(entry, "severity")
    confidence = _text_field(entry, "confidence")
    code_sha256 = _text_field(entry, "code_sha256")
    count = _integer_field(entry, "count")
    if TEST_ID_PATTERN.fullmatch(test_id) is None:
        raise BanditBaselineError("baseline finding test_id is malformed")
    if severity != "LOW" or severity not in SEVERITIES:
        raise BanditBaselineError("baseline contains a disallowed severity")
    if confidence not in CONFIDENCES:
        raise BanditBaselineError("baseline finding confidence is malformed")
    if FINGERPRINT_PATTERN.fullmatch(code_sha256) is None:
        raise BanditBaselineError("baseline finding code_sha256 is malformed")
    return (path, line, test_id, severity, confidence, code_sha256), count


def _load_baseline() -> dict[Fingerprint, int]:
    payload = _object(_read_json(BASELINE_PATH, "Bandit baseline"), "Bandit baseline")
    if set(payload) != {"version", "findings"}:
        raise BanditBaselineError("Bandit baseline fields are malformed")
    if type(payload["version"]) is not int or payload["version"] != 1:
        raise BanditBaselineError("Bandit baseline version is unsupported")
    findings = payload["findings"]
    if not isinstance(findings, list) or len(findings) != BASELINE_ENTRY_COUNT:
        raise BanditBaselineError("Bandit baseline must contain exactly 33 entries")
    expected: dict[Fingerprint, int] = {}
    for record in findings:
        fingerprint, count = _baseline_fingerprint(record)
        if fingerprint in expected:
            raise BanditBaselineError("Bandit baseline contains a duplicate fingerprint")
        expected[fingerprint] = count
    if sum(expected.values()) != BASELINE_ENTRY_COUNT:
        raise BanditBaselineError("Bandit baseline must allow exactly 33 findings")
    return expected


def _result_fingerprint(record: object) -> Fingerprint:
    finding = _object(record, "Bandit finding")
    path = _canonical_repo_path(finding.get("filename"))
    line = _integer_field(finding, "line_number")
    test_id = _text_field(finding, "test_id")
    severity = _text_field(finding, "issue_severity")
    confidence = _text_field(finding, "issue_confidence")
    code = finding.get("code")
    if not isinstance(code, str) or not code:
        raise BanditBaselineError("Bandit finding code context is missing or malformed")
    if TEST_ID_PATTERN.fullmatch(test_id) is None:
        raise BanditBaselineError("Bandit finding test_id is malformed")
    if severity not in SEVERITIES:
        raise BanditBaselineError("Bandit finding severity is malformed")
    if severity != "LOW":
        raise BanditBaselineError(f"disallowed Bandit severity {severity}")
    if confidence not in CONFIDENCES:
        raise BanditBaselineError("Bandit finding confidence is malformed")
    try:
        code_sha256 = hashlib.sha256(code.encode("utf-8")).hexdigest()
    except UnicodeEncodeError as error:
        raise BanditBaselineError("Bandit finding code context is malformed") from error
    return path, line, test_id, severity, confidence, code_sha256


def validate_report(report_path: Path, bandit_status: int) -> int:
    if isinstance(bandit_status, bool) or bandit_status not in {0, 1}:
        raise BanditBaselineError(f"Bandit exited with unsupported status {bandit_status}")
    expected = _load_baseline()
    payload = _object(_read_json(report_path, "Bandit JSON report"), "Bandit JSON report")
    required_fields = {"errors", "generated_at", "metrics", "results"}
    if not required_fields.issubset(payload):
        raise BanditBaselineError("Bandit JSON report fields are missing")
    generated_at = payload["generated_at"]
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise BanditBaselineError("Bandit JSON report generated_at is missing or malformed")
    errors = payload["errors"]
    results = payload["results"]
    if not isinstance(errors, list) or not isinstance(results, list):
        raise BanditBaselineError("Bandit JSON report fields are malformed")
    if errors:
        raise BanditBaselineError("Bandit JSON report contains errors")
    if bandit_status == 1 and not results:
        raise BanditBaselineError("Bandit exited 1 without JSON findings")
    if bandit_status == 0 and results:
        raise BanditBaselineError("Bandit exited 0 with JSON findings")
    report_metrics = _report_metrics(payload)
    for metric_name, reviewed_cap in BANDIT_REVIEWED_METRIC_CAPS.items():
        if report_metrics[metric_name] > reviewed_cap:
            raise BanditBaselineError(
                f"Bandit JSON report {metric_name} count exceeds reviewed cap {reviewed_cap}"
            )
    actual: Counter[Fingerprint] = Counter()
    severities: Counter[str] = Counter()
    confidences: Counter[str] = Counter()
    for record in results:
        fingerprint = _result_fingerprint(record)
        actual[fingerprint] += 1
        severities[fingerprint[3]] += 1
        confidences[fingerprint[4]] += 1
    for severity in ("LOW", "MEDIUM", "HIGH", "UNDEFINED"):
        if report_metrics[f"SEVERITY.{severity}"] != severities[severity]:
            raise BanditBaselineError("Bandit JSON report severity metrics are inconsistent")
    for confidence in ("LOW", "MEDIUM", "HIGH", "UNDEFINED"):
        if report_metrics[f"CONFIDENCE.{confidence}"] != confidences[confidence]:
            raise BanditBaselineError("Bandit JSON report confidence metrics are inconsistent")
    for fingerprint, count in actual.items():
        if fingerprint not in expected:
            path, line, test_id, _, _, _ = fingerprint
            raise BanditBaselineError(f"new or changed Bandit finding: {path}:{line} ({test_id})")
        if count > expected[fingerprint]:
            path, line, test_id, _, _, _ = fingerprint
            raise BanditBaselineError(f"excess Bandit finding count: {path}:{line} ({test_id})")
    return sum(actual.values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("bandit_status", type=int)
    arguments = parser.parse_args(argv)
    try:
        finding_count = validate_report(arguments.report, arguments.bandit_status)
    except BanditBaselineError as error:
        print(f"Bandit baseline rejected: {error}", file=sys.stderr)
        return 1
    print(f"Bandit baseline accepted: {finding_count} known LOW findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
