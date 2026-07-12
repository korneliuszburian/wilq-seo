from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_STORE_FIXTURE = REPO_ROOT / "tests/actions/test_audit_store_contracts.py"
SECURITY_SCRIPT = REPO_ROOT / "scripts/security.sh"


def _detect_secret_results(path: Path) -> dict[str, object]:
    if path.is_relative_to(REPO_ROOT):
        cwd = REPO_ROOT
        scan_target = str(path.relative_to(REPO_ROOT))
    else:
        cwd = path.parent
        scan_target = path.name
    completed = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", scan_target],
        check=True,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    results = payload.get("results")
    assert isinstance(results, dict)
    return results


def test_audit_redaction_fixture_is_allowlisted_only_on_its_test_line() -> None:
    assert _detect_secret_results(AUDIT_STORE_FIXTURE) == {}


def test_detect_secrets_still_flags_the_same_unallowlisted_field_in_another_file(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "unallowlisted_fixture.py"
    field_name = "mapping_" + "secret"
    candidate.write_text(f'fixture = {{"{field_name}": "hide"}}\n')

    assert any(
        isinstance(finding, dict) and finding.get("type") == "Secret Keyword"
        for findings in _detect_secret_results(candidate).values()
        if isinstance(findings, list)
        for finding in findings
    )


def test_security_script_keeps_the_fixture_in_full_repository_scan_scope() -> None:
    script = SECURITY_SCRIPT.read_text()

    assert "detect-secrets scan ." in script
    assert "test_audit_store_contracts.py" not in script
