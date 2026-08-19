from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_stop_hook_posts_an_empty_request_only_to_stop_telemetry(
    monkeypatch,
    capsys,
) -> None:
    captured: dict[str, object] = {}

    class Response:
        def close(self) -> None:
            captured["closed"] = True

    def capture_request(request, *, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setenv("WILQ_API_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setattr("urllib.request.urlopen", capture_request)
    namespace = runpy.run_path(str(REPO_ROOT / ".codex/hooks/stop_log.py"))

    namespace["main"]()

    request = captured["request"]
    assert request.full_url == "http://127.0.0.1:8000/api/codex/telemetry/stop-events"
    assert request.get_method() == "POST"
    assert request.data is None
    assert dict(request.header_items()) == {}
    assert captured["timeout"] == 2
    assert captured["closed"] is True
    assert capsys.readouterr() == ("", "")


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
