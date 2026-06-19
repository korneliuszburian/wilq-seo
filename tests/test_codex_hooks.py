from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_stop_hook_outputs_valid_json_when_wilq_api_is_unreachable() -> None:
    env = {
        **os.environ,
        "WILQ_API_BASE_URL": "http://127.0.0.1:9",
    }

    result = subprocess.run(
        [sys.executable, ".codex/hooks/stop_log.py"],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["continue"] is True
    assert "API is unreachable" in payload["systemMessage"]
    assert result.stderr == ""


def test_hooks_config_uses_uv_python_instead_of_global_python3() -> None:
    hooks_config = json.loads((REPO_ROOT / ".codex/hooks.json").read_text())
    commands = [
        hook["command"]
        for matcher_group in hooks_config["hooks"].values()
        for group in matcher_group
        for hook in group["hooks"]
    ]

    assert commands
    assert all("uv run python" in command for command in commands)
    assert all("python3" not in command for command in commands)
