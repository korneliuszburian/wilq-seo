from __future__ import annotations

import subprocess
from pathlib import Path


def test_bare_backend_test_command_refuses_to_start_a_full_suite() -> None:
    result = subprocess.run(
        ["bash", "scripts/test.sh"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 64
    assert "Run focused Python tests" in result.stderr


def test_full_backend_suite_requires_explicit_exclusive_authority() -> None:
    result = subprocess.run(
        ["bash", "scripts/test.sh", "--full"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 75
    assert "WILQ_TEST_EXCLUSIVE=1" in result.stderr


def test_full_suite_is_exclusive_and_frontend_tests_have_a_separate_owner() -> None:
    test_script = Path("scripts/test.sh").read_text(encoding="utf-8")
    quality_script = Path("scripts/quality.sh").read_text(encoding="utf-8")
    verify_script = Path("scripts/verify.sh").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/quality.yml").read_text(encoding="utf-8")

    assert "WILQ_TEST_EXCLUSIVE=1" in test_script
    assert "flock -n 9" in test_script
    assert "pnpm test" not in test_script
    assert "scripts/test.sh" not in quality_script
    assert "WILQ_TEST_EXCLUSIVE=1 scripts/test.sh --full" in verify_script
    assert "WILQ_TEST_EXCLUSIVE=1 scripts/test.sh --full" in workflow
