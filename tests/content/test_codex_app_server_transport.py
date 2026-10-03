from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from wilq.codex import model_policy
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
if turn["params"]["input"][0]["text"] in ("Usage limit exceeded.", "Structured usage limit."):
    write({{
        "method": "error",
        "params": {{
            "error": {{
                "message": (
                    "Limit reached"
                    if turn["params"]["input"][0]["text"] == "Structured usage limit."
                    else "Quota exceeded. Check your plan and billing details."
                ),
                "codexErrorInfo": {{"usageLimitExceeded": {{}}}},
            }},
            "willRetry": turn["params"]["input"][0]["text"] == "Usage limit exceeded.",
        }},
    }})
    raise SystemExit(0)
if turn["params"]["input"][0]["text"] == "Stderr quota.":
    print("quota exceeded", file=sys.stderr, flush=True)
    raise SystemExit(0)
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


def _isolated_client(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> tuple[StdioCodexAppServerClient, Path, Path, Path]:
    source_home = tmp_path / "source-home"
    source_codex_home = source_home / ".codex"
    source_xdg = tmp_path / "source-xdg"
    source_codex_home.mkdir(parents=True)
    source_xdg.mkdir()
    (source_home / ".local" / "share" / "mise").mkdir(parents=True)
    (source_home / ".npm").mkdir()
    (source_codex_home / "auth.json").write_text("fake-login", encoding="utf-8")
    (source_codex_home / "config.toml").write_text(
        "model='gpt-5.6-sol'\nmodel_reasoning_effort='ultra'\nmodel_provider='codex'\n"
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
    return StdioCodexAppServerClient(timeout_seconds=5), source_home, source_codex_home, source_xdg


def _request(instruction: str) -> CodexAppServerStructuredTurnRequest:
    return CodexAppServerStructuredTurnRequest(
        instruction=instruction,
        application_context="application",
        untrusted_context="untrusted",
        output_schema={"type": "object"},
    )


def test_structured_turn_isolates_login_and_disables_runtime_capabilities(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    client, source_home, source_codex_home, source_xdg = _isolated_client(tmp_path, monkeypatch)

    result = client.run_structured_turn(_request("Return the constrained object."))

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
        'model="gpt-6-luna"',
        'model_reasoning_effort="max"',
    } <= overrides
    assert 'model="gpt-5.6-terra"' not in overrides
    assert 'model="gpt-5.6-sol"' not in overrides
    assert 'model_reasoning_effort="ultra"' not in overrides
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
    assert payload["turn_params"]["model"] == "gpt-6-luna"
    assert payload["turn_params"]["effort"] == "max"
    turn = payload["turn_params"]
    assert turn["environments"] == []
    assert turn["runtimeWorkspaceRoots"] == []
    assert turn["sandboxPolicy"] == {"type": "readOnly", "networkAccess": False}


def test_structured_turn_classifies_protocol_failures(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    client, *_ = _isolated_client(tmp_path, monkeypatch)

    blocked = client.run_structured_turn(_request("Attempt a tool."))
    assert blocked.status == "blocked"
    assert blocked.external_call_attempted is True
    assert blocked.output_text is None
    assert [blocker.code for blocker in blocked.blockers] == ["codex_external_call_blocked"]

    invalid_schema = client.run_structured_turn(_request("Reject this schema."))
    assert invalid_schema.status == "failed"
    assert invalid_schema.output_text is None
    assert [blocker.code for blocker in invalid_schema.blockers] == [
        "codex_output_schema_invalid_other"
    ]

    retried = client.run_structured_turn(_request("Retry transiently."))
    assert retried.status == "completed"

    usage_limited = client.run_structured_turn(_request("Usage limit exceeded."))
    assert usage_limited.status == "failed"
    assert usage_limited.output_text is None
    assert [blocker.code for blocker in usage_limited.blockers] == [
        "codex_usage_limit_exceeded"
    ]

    structured_limit = client.run_structured_turn(_request("Structured usage limit."))
    assert structured_limit.status == "failed"
    assert structured_limit.output_text is None
    assert [blocker.code for blocker in structured_limit.blockers] == [
        "codex_usage_limit_exceeded"
    ]

    stderr_limit = client.run_structured_turn(_request("Stderr quota."))
    assert stderr_limit.status == "failed"
    assert stderr_limit.output_text is None
    assert [blocker.code for blocker in stderr_limit.blockers] == ["codex_usage_limit_exceeded"]

    stream_failure = client.run_structured_turn(_request("Terminal stream failure."))
    assert stream_failure.status == "failed"
    assert [blocker.code for blocker in stream_failure.blockers] == [
        "codex_response_stream_disconnected"
    ]

    stderr_stream_failure = client.run_structured_turn(_request("Terminal stderr failure."))
    assert stderr_stream_failure.status == "failed"
    assert [blocker.code for blocker in stderr_stream_failure.blockers] == [
        "codex_response_stream_disconnected"
    ]


def test_codex_executable_bypasses_launcher_wrapper(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    from wilq.codex.app_server_process import _resolve_codex_executable

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    real = bin_dir / "real-codex"
    real.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    real.chmod(0o700)
    wrapper = bin_dir / "codex"
    wrapper.write_text(
        '#!/bin/bash\nexec mise x codex -- codex "$@"\n', encoding="utf-8"
    )
    wrapper.chmod(0o700)
    observation = tmp_path / "lookup.json"
    mise = bin_dir / "mise"
    mise.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "assert sys.argv[1:] == ['which', 'codex']\n"
        "allowed = {'PATH', 'HOME', 'MISE_DATA_DIR', 'LANG', 'LC_ALL', 'LC_CTYPE'}\n"
        f"Path({str(observation)!r}).write_text(json.dumps({{\n"
        "'unexpected_names': sorted(set(os.environ) - allowed),\n"
        "'home': os.environ.get('HOME'), 'data': os.environ.get('MISE_DATA_DIR')\n"
        "}))\n"
        f"print({str(real)!r})\n",
        encoding="utf-8",
    )
    mise.chmod(0o700)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    home = str(tmp_path / "operator-home")
    data = str(tmp_path / "mise-data")
    monkeypatch.setenv("HOME", home)
    monkeypatch.setenv("MISE_DATA_DIR", data)
    for name in (
        "WILQ_RESOLVER_CANARY", "CODEX_API_KEY", "OPENAI_API_KEY", "CODEX_HOME",
        "XDG_CONFIG_HOME", "MISE_CONFIG_DIR", "PYTHONPATH",
    ):
        monkeypatch.setenv(name, "synthetic-fixture-only")

    assert _resolve_codex_executable() == str(real)
    observed = json.loads(observation.read_text())
    assert observed == {"unexpected_names": [], "home": home, "data": data}


@pytest.mark.parametrize(
    "failure", ["timeout", "os_error", "nonzero", "empty", "non_executable", "directory"]
)
def test_codex_lookup_failure_retains_original_launcher(
    tmp_path: Path, monkeypatch: MonkeyPatch, failure: str,
) -> None:
    import subprocess

    from wilq.codex import app_server_process as process

    wrapper = tmp_path / "codex"
    wrapper.write_text("#!/bin/bash\n# mise launcher\n")
    candidate = tmp_path / "candidate"
    if failure == "directory":
        candidate.mkdir()
    else:
        candidate.write_text("#!/bin/sh\nexit 0\n")
    monkeypatch.setattr(process.shutil, "which", lambda name: str(wrapper))

    def lookup(args, **kwargs):
        assert args == ["mise", "which", "codex"]
        assert kwargs["timeout"] == 10
        assert kwargs["check"] is False
        assert set(kwargs["env"]) <= {
            "PATH", "HOME", "MISE_DATA_DIR", "LANG", "LC_ALL", "LC_CTYPE"
        }
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 10)
        if failure == "os_error":
            raise OSError("controlled lookup failure")
        output = "" if failure == "empty" else str(candidate)
        return subprocess.CompletedProcess(args, 1 if failure == "nonzero" else 0, output)

    monkeypatch.setattr(process.subprocess, "run", lookup)
    assert process._resolve_codex_executable() == str(wrapper)


@pytest.mark.parametrize(
    ("first", "second", "flag"),
    [
        (b"quota ex", b"ceeded", "stderr_usage_limit_exceeded"),
        (b"usage_limit_", b"exceeded", "stderr_usage_limit_exceeded"),
        (b"responsestreamdis", b"connected", "stderr_stream_disconnected"),
        (b"stream dis", b"connected", "stderr_stream_disconnected"),
    ],
)
def test_stderr_signals_survive_split_reads(first, second, flag) -> None:
    import asyncio

    from wilq.codex.app_server import _observe_stderr, _stderr_blocker, _TurnObserver

    async def observe():
        reader = asyncio.StreamReader()
        observer = _TurnObserver()
        task = asyncio.create_task(_observe_stderr(reader, observer=observer))
        reader.feed_data(b"x" * 8192 + first)
        await asyncio.sleep(0)
        reader.feed_data(second)
        reader.feed_eof()
        await task
        assert getattr(observer, flag)
        blocker = _stderr_blocker(observer)
        assert blocker is not None
        assert blocker.code == (
            "codex_usage_limit_exceeded" if flag == "stderr_usage_limit_exceeded"
            else "codex_response_stream_disconnected"
        )

    asyncio.run(observe())


@pytest.mark.parametrize("timeout_seconds", [0.05, 0.15])
def test_stalled_lookup_obeys_turn_deadline_and_never_launches(
    tmp_path: Path, monkeypatch: MonkeyPatch, timeout_seconds: float,
) -> None:
    import time

    from wilq.codex import app_server

    _isolated_client(tmp_path, monkeypatch)
    wrapper = tmp_path / "bin" / "codex"
    real = tmp_path / "bin" / "actual-codex"
    wrapper.rename(real)
    wrapper.write_text("#!/bin/bash\n# mise wrapper\n")
    wrapper.chmod(0o700)
    mise = tmp_path / "bin" / "mise"
    mise.write_text(
        f"#!{sys.executable}\nimport time\ntime.sleep(0.5)\nprint({str(real)!r})\n"
    )
    mise.chmod(0o700)

    async def forbidden_launch(*args, **kwargs):
        raise AssertionError("Expired lookup must not launch app-server")

    monkeypatch.setattr(app_server.asyncio, "create_subprocess_exec", forbidden_launch)
    started = time.monotonic()
    result = StdioCodexAppServerClient(timeout_seconds=timeout_seconds).run_structured_turn(
        _request("Deadline fixture.")
    )
    assert time.monotonic() - started < timeout_seconds + 0.2
    assert result.status == "failed"
    assert result.output_text is None
    assert [blocker.code for blocker in result.blockers] == ["codex_timeout"]


def test_codex_native_executable_inspection_has_bounded_io(
    tmp_path: Path, monkeypatch: MonkeyPatch,
) -> None:
    from wilq.codex import app_server_process as process

    binary = tmp_path / "native-codex"
    binary.write_bytes(b"\x7fELF" + b"x" * 8192)
    original_open = Path.open
    reads = []

    class LimitedReader:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def read(self, size=-1):
            assert 0 < size <= 4096
            reads.append(size)
            return self.stream.read(size)

    def observed_open(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        return LimitedReader(stream) if path == binary else stream

    monkeypatch.setattr(Path, "open", observed_open)
    monkeypatch.setattr(process.shutil, "which", lambda name: str(binary))
    assert process._resolve_codex_executable() == str(binary)
    assert len(reads) == 1


@pytest.mark.parametrize(
    "project_config",
    [
        "",
        'model = "gpt-5.6-sol"\nmodel_reasoning_effort = "max"\n',
        'model = "gpt-5.6-terra"\nmodel_reasoning_effort = "max"\n',
        'model = "gpt-5.6-terra"\nmodel_reasoning_effort = "high"\n',
    ],
)
def test_invalid_owner_project_model_policy_does_not_change_embedded_selection(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    project_config: str,
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(project_config, encoding="utf-8")
    monkeypatch.setattr(model_policy, "_PROJECT_CODEX_CONFIG_PATH", config_path)

    assert model_policy.configured_codex_runtime_selection() is None
    embedded = model_policy.embedded_codex_runtime_selection()
    assert embedded is not None
    assert embedded.model == "gpt-6-luna"
    assert embedded.model_reasoning_effort == "max"


@pytest.mark.parametrize(
    ("constant", "value"),
    [
        ("_CONTENT_RUNTIME_MODEL", "gpt-5.6-sol"),
        ("_CONTENT_RUNTIME_MODEL", "gpt-5.6-terra"),
        ("_CONTENT_RUNTIME_REASONING_EFFORT", "high"),
    ],
)
def test_embedded_policy_fails_closed_when_pinned_constant_is_unsupported(
    monkeypatch: MonkeyPatch,
    constant: str,
    value: str,
) -> None:
    monkeypatch.setattr(model_policy, constant, value)

    assert model_policy.embedded_codex_runtime_selection() is None
