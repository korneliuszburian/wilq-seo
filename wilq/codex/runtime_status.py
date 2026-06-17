from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from wilq.codex.model_policy import MODEL_POLICY_NOTES


def codex_runtime_status() -> dict[str, Any]:
    skills_dir = Path(".agents/skills")
    hooks_file = Path(".codex/hooks.json")
    return {
        "codex_available": shutil.which("codex") is not None,
        "codex_version_if_known": None,
        "skills_directory_status": "present" if skills_dir.exists() else "missing",
        "hooks_status": "present" if hooks_file.exists() else "missing",
        "last_codex_run": None,
        "last_codex_error": None,
        "model_policy_notes": MODEL_POLICY_NOTES,
    }
