from __future__ import annotations

import ast
import inspect
import subprocess
from pathlib import Path

import pytest

from scripts import audit_complexity
from scripts.audit_complexity import (
    CHANGED_CLASS_LINE_LIMIT,
    CHANGED_FILE_LOC_LIMIT,
    CHANGED_FUNCTION_BRANCH_LIMIT,
    CHANGED_FUNCTION_LINE_LIMIT,
    FROZEN_GROWTH_FILES,
    CodeBlockMetric,
    FileMetric,
    changed_budget_violations,
    render_budget_rows,
)


def test_changed_budget_violations_detect_changed_file_growth() -> None:
    changed = {Path("wilq/content/example.py")}

    violations = changed_budget_violations(
        files=[
            FileMetric(
                path=Path("wilq/content/example.py"),
                loc=CHANGED_FILE_LOC_LIMIT + 1,
            )
        ],
        functions=[
            CodeBlockMetric(
                path=Path("wilq/content/example.py"),
                name="large_function",
                line=10,
                lines=CHANGED_FUNCTION_LINE_LIMIT + 1,
                branch_count=CHANGED_FUNCTION_BRANCH_LIMIT + 1,
            )
        ],
        classes=[
            CodeBlockMetric(
                path=Path("wilq/content/example.py"),
                name="LargeClass",
                line=30,
                lines=CHANGED_CLASS_LINE_LIMIT + 1,
                branch_count=0,
            )
        ],
        changed=changed,
    )

    assert {(item.kind, item.metric) for item in violations} == {
        ("file", "LOC"),
        ("function", "lines"),
        ("function", "branches"),
        ("class", "lines"),
    }


def test_changed_budget_ignores_existing_hotspots_that_do_not_grow() -> None:
    assert "baseline_files" in inspect.signature(changed_budget_violations).parameters
    path = Path("tests/content/historical_contract.py")
    current_file = FileMetric(path=path, loc=CHANGED_FILE_LOC_LIMIT + 20)
    current_function = CodeBlockMetric(
        path=path,
        name="old_fixture",
        line=10,
        lines=CHANGED_FUNCTION_LINE_LIMIT + 1,
        branch_count=0,
    )
    assert changed_budget_violations(
        files=[current_file],
        functions=[current_function],
        classes=[],
        changed={path},
        baseline_files=[FileMetric(path=path, loc=current_file.loc + 1)],
        baseline_functions=[current_function],
    ) == []
    assert any(
        row.kind == "file"
        for row in changed_budget_violations(
            files=[FileMetric(path=path, loc=current_file.loc + 2)],
            functions=[],
            classes=[],
            changed={path},
            baseline_files=[current_file],
        )
    )


def test_baseline_metrics_fail_closed_for_unreadable_existing_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = Path("tests/content/existing.py")

    def broken_show(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[1] == "show":
            return subprocess.CompletedProcess(args, 0, stdout="def broken(", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout=path.as_posix(), stderr="")

    monkeypatch.setattr(audit_complexity.subprocess, "run", broken_show)
    with pytest.raises(RuntimeError, match="baseline"):
        audit_complexity.baseline_metrics(tmp_path, {path})


def test_baseline_metrics_fail_closed_when_existing_head_read_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = Path("tests/content/existing.py")

    def failed_show(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[1] == "show":
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="read failed")
        return subprocess.CompletedProcess(args, 0, stdout=path.as_posix(), stderr="")

    monkeypatch.setattr(audit_complexity.subprocess, "run", failed_show)
    with pytest.raises(RuntimeError, match="baseline"):
        audit_complexity.baseline_metrics(tmp_path, {path})


def test_nested_function_identity_includes_its_parent() -> None:
    source = "def first():\n def helper():\n  pass\ndef second():\n def helper():\n  pass\n"
    visitor = audit_complexity.ComplexityVisitor(Path("sample.py"))
    visitor.visit(ast.parse(source))
    assert {item.name for item in visitor.functions} == {
        "first",
        "first.helper",
        "second",
        "second.helper",
    }


def test_duplicate_function_identity_cannot_hide_growth() -> None:
    path = Path("tests/content/duplicate.py")
    current = [
        CodeBlockMetric(path, "helper", 10, 120, 0),
        CodeBlockMetric(path, "helper", 140, 121, 0),
    ]
    baseline = [CodeBlockMetric(path, "helper", 10, 200, 0)]
    violations = changed_budget_violations(
        files=[],
        functions=current,
        classes=[],
        changed={path},
        baseline_functions=baseline,
    )
    assert len([item for item in violations if item.metric == "lines"]) == 2


def test_frozen_growth_gate_tracks_schema_compatibility_facade() -> None:
    assert Path("wilq/schemas/__init__.py") in FROZEN_GROWTH_FILES
    assert Path("wilq/schemas.py") not in FROZEN_GROWTH_FILES


def test_frozen_growth_gate_accepts_a_shrinking_facade() -> None:
    path = Path("wilq/actions/service.py")
    assert hasattr(audit_complexity, "frozen_growth_files")
    assert audit_complexity.frozen_growth_files({path}, {path: 799}, {path: 886}) == []
    assert audit_complexity.frozen_growth_files({path}, {path: 887}, {path: 886}) == [path]
    assert audit_complexity.frozen_growth_files({path}, {path: 799}, {}) == [path]


def test_changed_budget_violations_ignore_unchanged_hotspots() -> None:
    violations = changed_budget_violations(
        files=[
            FileMetric(
                path=Path("tests/test_api_contracts.py"),
                loc=CHANGED_FILE_LOC_LIMIT + 10_000,
            )
        ],
        functions=[
            CodeBlockMetric(
                path=Path("tests/test_api_contracts.py"),
                name="legacy_test",
                line=1,
                lines=CHANGED_FUNCTION_LINE_LIMIT + 1_000,
                branch_count=CHANGED_FUNCTION_BRANCH_LIMIT + 100,
            )
        ],
        classes=[],
        changed={Path("wilq/content/new_slice.py")},
    )

    assert violations == []


def test_render_budget_rows_reports_clean_limits() -> None:
    rows = render_budget_rows([], limit=5)

    assert rows == [
        "- No new or growing Python hotspots exceed budgets: "
        f"file <= {CHANGED_FILE_LOC_LIMIT} LOC, "
        f"function <= {CHANGED_FUNCTION_LINE_LIMIT} lines, "
        f"function <= {CHANGED_FUNCTION_BRANCH_LIMIT} branches, "
        f"class <= {CHANGED_CLASS_LINE_LIMIT} lines."
    ]
