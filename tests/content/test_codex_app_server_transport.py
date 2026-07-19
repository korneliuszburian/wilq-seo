from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from pytest import MonkeyPatch

from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    StdioCodexAppServerClient,
)

_FAKE_APP_SERVER = r"""#!{python}
import json
import os
import sys
from pathlib import Path

def read():
    return json.loads(sys.stdin.readline())

def write(message):
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()

initialize = read()
codex_home = Path(os.environ["CODEX_HOME"])
diagnostic = {{
    "api_key_names": [
        name for name in ("CODEX_API_KEY", "OPENAI_API_KEY") if name in os.environ
    ],
    "argv": sys.argv[1:],
    "auth_at_initialize": (codex_home / "auth.json").is_file(),
    "codex_home": str(codex_home),
    "home": os.environ["HOME"],
    "xdg_config_home": os.environ["XDG_CONFIG_HOME"],
    "mise_data_dir": os.environ.get("MISE_DATA_DIR"),
    "npm_config_cache": os.environ.get("NPM_CONFIG_CACHE"),
}}
write({{"id": initialize["id"], "result": {{}}}})
read()
thread = read()
diagnostic["auth_after_initialize"] = (codex_home / "auth.json").is_file()
diagnostic["thread_params"] = thread["params"]
write({{"id": thread["id"], "result": {{"thread": {{"id": "thread-test"}}, "model": "gpt-test"}}}})
turn = read()
diagnostic["turn_params"] = turn["params"]
if turn["params"]["input"][0]["text"] == "Attempt a tool.":
    write({{
        "method": "item/started",
        "params": {{"item": {{"type": "commandExecution"}}}},
    }})
    raise SystemExit(0)
if turn["params"]["input"][0]["text"] == "Reject this schema.":
    write({{
        "method": "error",
        "params": {{
            "error": {{"message": "invalid_json_schema: synthetic detail"}},
        }},
    }})
    raise SystemExit(0)
if turn["params"]["input"][0]["text"] == "Retry transiently.":
    write({{
        "method": "error",
        "params": {{
            "error": {{"message": "Reconnecting... 1/5"}},
            "willRetry": True,
        }},
    }})
if turn["params"]["input"][0]["text"] == "Terminal stream failure.":
    write({{
        "method": "error",
        "params": {{
            "error": {{
                "message": "stream disconnected",
                "codexErrorInfo": {{"responseStreamDisconnected": {{}}}},
            }},
            "willRetry": False,
        }},
    }})
    raise SystemExit(0)
if turn["params"]["input"][0]["text"] == "Terminal stderr failure.":
    print("responseStreamDisconnected", file=sys.stderr, flush=True)
    raise SystemExit(0)
write({{
    "id": turn["id"],
    "result": {{"turn": {{"id": "turn-test", "items": []}}}},
}})
write({{
    "method": "turn/completed",
    "params": {{
        "threadId": "thread-test",
        "turn": {{
            "id": "turn-test",
            "status": "completed",
            "items": [{{
                "type": "agentMessage",
                "phase": "final_answer",
                "text": json.dumps(diagnostic, separators=(",", ":")),
            }}],
        }},
    }},
}})
"""


def _install_fake_app_server(bin_dir: Path) -> None:
    bin_dir.mkdir()
    executable = bin_dir / "codex"
    executable.write_text(_FAKE_APP_SERVER.format(python=sys.executable), encoding="utf-8")
    executable.chmod(0o700)


def test_structured_turn_isolates_login_and_disables_runtime_capabilities(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    source_home = tmp_path / "source-home"
    source_codex_home = source_home / ".codex"
    source_xdg = tmp_path / "source-xdg"
    source_codex_home.mkdir(parents=True)
    source_xdg.mkdir()
    (source_home / ".local" / "share" / "mise").mkdir(parents=True)
    (source_home / ".npm").mkdir()
    (source_codex_home / "auth.json").write_text("fake-login", encoding="utf-8")
    (source_codex_home / "config.toml").write_text(
        "model='gpt-test'\nmodel_provider='codex'\n"
        "[model_providers.codex]\n"
        "name='codex'\nbase_url='https://provider.example/v1'\n"
        "wire_api='responses'\nrequires_openai_auth=true\n"
        "web_search='live'",
        encoding="utf-8",
    )
    fake_bin = tmp_path / "bin"
    _install_fake_app_server(fake_bin)
    monkeypatch.setenv("HOME", str(source_home))
    monkeypatch.setenv("CODEX_HOME", str(source_codex_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(source_xdg))
    monkeypatch.setenv("CODEX_API_KEY", "must-not-cross")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-cross")
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")

    result = StdioCodexAppServerClient(timeout_seconds=5).run_structured_turn(
        CodexAppServerStructuredTurnRequest(
            instruction="Return the constrained object.",
            application_context="application",
            untrusted_context="untrusted",
            output_schema={"type": "object"},
        )
    )

    assert result.status == "completed"
    payload = json.loads(result.output_text or "")
    assert payload["api_key_names"] == []
    assert payload["auth_at_initialize"] is True
    assert payload["auth_after_initialize"] is True
    assert payload["home"] != str(source_home)
    assert payload["codex_home"] != str(source_codex_home)
    assert payload["xdg_config_home"] != str(source_xdg)
    assert payload["mise_data_dir"] == str(source_home / ".local" / "share" / "mise")
    assert payload["npm_config_cache"] == str(source_home / ".npm")
    argv = payload["argv"]
    overrides = {argv[index + 1] for index, value in enumerate(argv) if value == "--config"}
    disabled = {argv[index + 1] for index, value in enumerate(argv) if value == "--disable"}
    assert {
        'web_search="disabled"',
        "mcp_servers={}",
        "features.remote_models=false",
        'model="gpt-test"',
    } <= overrides
    assert not any(value.startswith("model_provider=") for value in overrides)
    assert not any(value.startswith("model_providers.") for value in overrides)
    assert {"apps", "browser_use", "multi_agent", "plugins", "shell_tool"} <= disabled
    thread = payload["thread_params"]
    assert thread["environments"] == []
    assert thread["runtimeWorkspaceRoots"] == []
    assert thread["selectedCapabilityRoots"] == []
    assert thread["dynamicTools"] == []
    assert thread["config"]["web_search"] == "disabled"
    assert thread["config"]["mcp_servers"] == {}
    assert payload["turn_params"]["model"] == "gpt-test"
    turn = payload["turn_params"]
    assert turn["environments"] == []
    assert turn["runtimeWorkspaceRoots"] == []
    assert turn["sandboxPolicy"] == {"type": "readOnly", "networkAccess": False}

    blocked = StdioCodexAppServerClient(timeout_seconds=5).run_structured_turn(
        CodexAppServerStructuredTurnRequest(
            instruction="Attempt a tool.",
            application_context="application",
            untrusted_context="untrusted",
            output_schema={"type": "object"},
        )
    )
    assert blocked.status == "blocked"
    assert blocked.external_call_attempted is True
    assert blocked.output_text is None
    assert [blocker.code for blocker in blocked.blockers] == ["codex_external_call_blocked"]

    invalid_schema = StdioCodexAppServerClient(timeout_seconds=5).run_structured_turn(
        CodexAppServerStructuredTurnRequest(
            instruction="Reject this schema.",
            application_context="application",
            untrusted_context="untrusted",
            output_schema={"type": "object"},
        )
    )
    assert invalid_schema.status == "failed"
    assert invalid_schema.output_text is None
    assert [blocker.code for blocker in invalid_schema.blockers] == [
        "codex_output_schema_invalid_other"
    ]

    retried = StdioCodexAppServerClient(timeout_seconds=5).run_structured_turn(
        CodexAppServerStructuredTurnRequest(
            instruction="Retry transiently.",
            application_context="application",
            untrusted_context="untrusted",
            output_schema={"type": "object"},
        )
    )
    assert retried.status == "completed"

    stream_failure = StdioCodexAppServerClient(timeout_seconds=5).run_structured_turn(
        CodexAppServerStructuredTurnRequest(
            instruction="Terminal stream failure.",
            application_context="application",
            untrusted_context="untrusted",
            output_schema={"type": "object"},
        )
    )
    assert stream_failure.status == "failed"
    assert [blocker.code for blocker in stream_failure.blockers] == [
        "codex_response_stream_disconnected"
    ]

    stderr_stream_failure = StdioCodexAppServerClient(timeout_seconds=5).run_structured_turn(
        CodexAppServerStructuredTurnRequest(
            instruction="Terminal stderr failure.",
            application_context="application",
            untrusted_context="untrusted",
            output_schema={"type": "object"},
        )
    )
    assert stderr_stream_failure.status == "failed"
    assert [blocker.code for blocker in stderr_stream_failure.blockers] == [
        "codex_response_stream_disconnected"
    ]
