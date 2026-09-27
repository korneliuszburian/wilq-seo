from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).parent.parent
type SecurityProcessResult = subprocess.CompletedProcess[str]


@pytest.fixture(scope="module")
def known_bandit_report(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, int, int]:
    report_path = tmp_path_factory.mktemp("security-bandit-report") / "bandit.json"
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
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    report_path.write_text(completed.stdout, encoding="utf-8")
    payload = json.loads(completed.stdout)
    results = payload.get("results") if isinstance(payload, dict) else None

    assert completed.returncode in {0, 1}
    assert isinstance(results, list) and len(results) <= 33
    assert all(
        isinstance(result, dict) and result.get("issue_severity") == "LOW"
        for result in results
    )
    assert (completed.returncode == 1) == bool(results)
    return report_path, completed.returncode, len(results)


def _run_security_gate(
    tmp_path: Path,
    report_path: Path,
    bandit_status: int,
) -> SecurityProcessResult:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    call_log = tmp_path / "uv-calls.log"
    uv_stub = fake_bin / "uv"
    uv_stub.write_text(
        f"""#!{sys.executable}
import shutil
import subprocess
import sys
from pathlib import Path

call_log = Path({str(call_log)!r})
with call_log.open("a", encoding="utf-8") as output:
    output.write(" ".join(sys.argv[1:]) + "\\n")
arguments = sys.argv[1:]
if not arguments or arguments.pop(0) != "run":
    sys.exit(97)
if arguments[:2] == ["--extra", "dev"]:
    del arguments[:2]
if not arguments or arguments.pop(0) != "python":
    sys.exit(97)
repository_root = Path({str(REPOSITORY_ROOT)!r})
if arguments and arguments[0] == "scripts/check_bandit_baseline.py":
    completed = subprocess.run(
        [sys.executable, str(repository_root / arguments[0]), *arguments[1:]],
        check=False,
    )
    sys.exit(completed.returncode)
if arguments[:2] == ["-m", "bandit"]:
    if len(arguments) >= 2 and arguments[-2] == "-o":
        shutil.copyfile({str(report_path)!r}, arguments[-1])
    sys.exit({bandit_status})
if arguments[:3] == ["-m", "pip_audit", "--version"]:
    sys.exit(1)
if arguments[:3] == ["-m", "detect_secrets", "--version"]:
    sys.exit(1)
sys.exit(97)
""",
        encoding="utf-8",
    )
    uv_stub.chmod(0o755)
    semgrep_stub = fake_bin / "semgrep"
    semgrep_stub.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    semgrep_stub.chmod(0o755)
    environment = {
        "HOME": str(tmp_path),
        "PATH": os.pathsep.join((str(fake_bin), "/usr/bin", "/bin")),
        "TMPDIR": str(tmp_path),
    }
    return subprocess.run(
        [str(REPOSITORY_ROOT / "scripts/security.sh")],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
        env=environment,
    )


def test_security_gate_audits_dependencies_with_the_active_uv_interpreter() -> None:
    script = Path("scripts/security.sh").read_text(encoding="utf-8")

    assert "uv run --extra dev python -m pip_audit" in script
    assert "uv run --extra dev pip-audit" not in script


def test_python_quality_tools_use_the_active_uv_interpreter() -> None:
    expected_commands = {
        "scripts/lint.sh": "uv run --extra dev python -m ruff check .",
        "scripts/typecheck.sh": "uv run --extra dev python -m mypy",
        "scripts/test.sh": "uv run --extra dev python -m pytest \"$@\"",
        "scripts/security.sh": "uv run --extra dev python -m bandit",
        "scripts/verify.sh": "uv run python -m uvicorn",
        "scripts/local_stack.sh": "uv run python -m uvicorn",
        "scripts/access_pack_manifest.sh": "uv run python -",
        "scripts/access_pack_check.sh": "uv run python -",
        ".github/workflows/quality.yml": "scripts/test.sh",
    }

    for path, command in expected_commands.items():
        assert command in Path(path).read_text(encoding="utf-8")

    verify_script = Path("scripts/verify.sh").read_text(encoding="utf-8")
    assert ".venv/bin/" not in verify_script
    assert "uv run python -m wilq.cli jobs status" in verify_script
    assert (
        "uv run python -m uvicorn apps.api.wilq_api.main:app "
        '--host 127.0.0.1 --port "$skill_api_port"'
    ) in verify_script


def test_security_gate_uses_reviewed_bandit_baseline(
    known_bandit_report: tuple[Path, int, int],
    tmp_path: Path,
) -> None:
    report_path, bandit_status, finding_count = known_bandit_report
    completed = _run_security_gate(tmp_path, report_path, bandit_status)

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert f"Bandit baseline accepted: {finding_count} known LOW findings" in completed.stdout
    assert "Skipping pip-audit: command unavailable." in completed.stdout
    assert "Skipping detect-secrets: command unavailable." in completed.stdout
    uv_calls = (tmp_path / "uv-calls.log").read_text(encoding="utf-8")
    assert "python -m pip_audit --version" in uv_calls
    assert "python -m detect_secrets --version" in uv_calls


def test_security_gate_rejects_unsupported_bandit_status(
    known_bandit_report: tuple[Path, int, int],
    tmp_path: Path,
) -> None:
    report_path, _, _ = known_bandit_report
    completed = _run_security_gate(tmp_path, report_path, 2)

    assert completed.returncode != 0
    assert "Bandit exited with unsupported status 2" in completed.stderr
    uv_calls = (tmp_path / "uv-calls.log").read_text(encoding="utf-8")
    assert "python -m pip_audit --version" not in uv_calls
    assert "python -m detect_secrets --version" not in uv_calls
