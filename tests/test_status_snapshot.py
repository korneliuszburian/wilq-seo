from __future__ import annotations

import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STATUS_SNAPSHOT = REPOSITORY_ROOT / "scripts" / "status_snapshot.sh"


def test_status_snapshot_script_contract() -> None:
    assert STATUS_SNAPSHOT.exists()
    assert STATUS_SNAPSHOT.stat().st_mode & 0o111 != 0
    script = STATUS_SNAPSHOT.read_text(encoding="utf-8")
    for marker in (
        "set -euo pipefail",
        "WILQ_HEALTH_BASE_URL",
        "/api/health",
        "/api/system/status",
        "/api/jobs/status",
        "/api/connectors",
        "production-readiness-audit.md",
        "issues.jsonl",
        "ahead of origin/main",
    ):
        assert marker in script, f"Brak wymaganego elementu snapshotu: {marker}"


def test_status_snapshot_runs_and_reports_git_and_beads() -> None:
    completed = subprocess.run(
        ["bash", str(STATUS_SNAPSHOT)],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, completed.stderr
    output = completed.stdout
    assert "WILQ status snapshot" in output
    assert "commit" in output
    assert "Beady" in output
    assert "open=" in output
    assert "API" in output
