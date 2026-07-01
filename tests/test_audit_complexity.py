from __future__ import annotations

from pathlib import Path

from scripts.audit_complexity import (
    CHANGED_CLASS_LINE_LIMIT,
    CHANGED_FILE_LOC_LIMIT,
    CHANGED_FUNCTION_BRANCH_LIMIT,
    CHANGED_FUNCTION_LINE_LIMIT,
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
        "- Changed Python files are within budgets: "
        f"file <= {CHANGED_FILE_LOC_LIMIT} LOC, "
        f"function <= {CHANGED_FUNCTION_LINE_LIMIT} lines, "
        f"function <= {CHANGED_FUNCTION_BRANCH_LIMIT} branches, "
        f"class <= {CHANGED_CLASS_LINE_LIMIT} lines."
    ]
