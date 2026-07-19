from __future__ import annotations

import os
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from wilq.codex.model_policy import MODEL_POLICY_NOTES


@dataclass(frozen=True, slots=True)
class CodexLocalRuntimeReadiness:
    status: Literal["ready", "missing_cli", "missing_login"]
    cli_available: bool
    login_available: bool
    blocker_code: str | None
    blocker_label: str | None


def codex_auth_path() -> Path | None:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "auth.json"
    home = os.environ.get("HOME")
    return Path(home).expanduser() / ".codex" / "auth.json" if home else None


def codex_local_runtime_readiness() -> CodexLocalRuntimeReadiness:
    cli_available = shutil.which("codex") is not None
    auth_path = codex_auth_path()
    login_available = auth_path is not None and auth_path.is_file()
    if not cli_available:
        return CodexLocalRuntimeReadiness(
            status="missing_cli",
            cli_available=False,
            login_available=login_available,
            blocker_code="codex_cli_missing",
            blocker_label="Lokalny executable Codex nie jest dostępny.",
        )
    if not login_available:
        return CodexLocalRuntimeReadiness(
            status="missing_login",
            cli_available=True,
            login_available=False,
            blocker_code="codex_login_missing",
            blocker_label="Lokalny Codex nie ma dostępnej sesji ChatGPT.",
        )
    return CodexLocalRuntimeReadiness(
        status="ready",
        cli_available=True,
        login_available=True,
        blocker_code=None,
        blocker_label=None,
    )


def codex_runtime_status() -> dict[str, Any]:
    readiness = codex_local_runtime_readiness()
    skills_dir = Path(".agents/skills")
    hooks_file = Path(".codex/hooks.json")
    last_run = _last_codex_run_summary()
    return {
        "readiness_status": readiness.status,
        "codex_available": readiness.cli_available,
        "login_available": readiness.login_available,
        "blocker_code": readiness.blocker_code,
        "blocker_label": readiness.blocker_label,
        "codex_version_if_known": None,
        "skills_directory_status": "present" if skills_dir.exists() else "missing",
        "hooks_status": "present" if hooks_file.exists() else "missing",
        "last_codex_run": last_run,
        "last_codex_error": last_run["error"] if last_run else None,
        "model_policy_notes": MODEL_POLICY_NOTES,
    }


def _last_codex_run_summary() -> dict[str, Any] | None:
    """Expose the latest typed run outcome without raw provider payloads."""

    try:
        from wilq.storage.local_state import local_state_store

        run = next(
            (
                candidate
                for candidate in local_state_store().list_codex_runs()
                if candidate.skill is not None or candidate.source != "codex_hook"
            ),
            None,
        )
    except (OSError, RuntimeError, ValueError, sqlite3.Error):
        return None
    if run is None:
        return None
    return {
        "id": run.id,
        "status": run.status,
        "skill": run.skill,
        "hook": run.hook,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error": run.error,
    }
