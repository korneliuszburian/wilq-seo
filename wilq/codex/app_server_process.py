"""Trusted launch boundary for the isolated WILQ Codex app-server process."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from wilq.codex.model_policy import configured_codex_runtime_selection
from wilq.codex.runtime_status import codex_auth_path

_PROCESS_ENV_NAMES = frozenset(
    {
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "LOGNAME",
        "NODE_EXTRA_CA_CERTS",
        "PATH",
        "SHELL",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "USER",
    }
)
_DISABLED_TOOL_FEATURES = (
    "apps",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "code_mode_host",
    "computer_use",
    "goals",
    "hooks",
    "image_generation",
    "in_app_browser",
    "multi_agent",
    "plugins",
    "remote_plugin",
    "shell_snapshot",
    "shell_tool",
    "skill_mcp_dependency_install",
    "tool_call_mcp_elicitation",
    "tool_suggest",
    "unified_exec",
    "workspace_dependencies",
)
_CONFIG_OVERRIDES = (
    'approval_policy="never"',
    'sandbox_mode="read-only"',
    "features.remote_models=false",
    'web_search="disabled"',
    "mcp_servers={}",
    "apps={_default={enabled=false,destructive_enabled=false,open_world_enabled=false}}",
    'shell_environment_policy={inherit="none"}',
)
THREAD_CONFIG: Mapping[str, object] = {
    "apps": {
        "_default": {
            "destructive_enabled": False,
            "enabled": False,
            "open_world_enabled": False,
        }
    },
    "features": {feature: False for feature in _DISABLED_TOOL_FEATURES},
    "mcp_servers": {},
    "shell_environment_policy": {"inherit": "none"},
    "web_search": "disabled",
}


class CodexAppServerProcessFailure(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.safe_message = message


@dataclass(frozen=True, slots=True)
class CodexAppServerLaunch:
    command: tuple[str, ...]
    cwd: str
    environment: Mapping[str, str]
    model: str
    model_reasoning_effort: str


@dataclass(frozen=True, slots=True)
class _IsolatedCodexRuntime:
    cwd: str
    environment: Mapping[str, str]


def prepare_codex_app_server_launch(root: Path) -> CodexAppServerLaunch:
    """Build one isolated launch from the project-pinned model policy."""

    selection = configured_codex_runtime_selection()
    if selection is None:
        raise CodexAppServerProcessFailure(
            "codex_model_policy_invalid",
            "Konfiguracja modelu WILQ musi wskazywać gpt-5.6-terra z wysiłkiem max.",
        )
    runtime = _prepare_isolated_runtime(root)
    return CodexAppServerLaunch(
        command=_codex_process_command(
            model=selection.model,
            model_reasoning_effort=selection.model_reasoning_effort,
        ),
        cwd=runtime.cwd,
        environment=runtime.environment,
        model=selection.model,
        model_reasoning_effort=selection.model_reasoning_effort,
    )


def _prepare_isolated_runtime(root: Path) -> _IsolatedCodexRuntime:
    source_auth = codex_auth_path()
    if source_auth is None or not source_auth.is_file():
        raise CodexAppServerProcessFailure(
            "codex_not_authenticated",
            "Lokalny Codex nie ma dostępnej sesji ChatGPT.",
        )
    home = root / "home"
    codex_home = root / "codex-home"
    cwd = root / "workspace"
    temp = root / "tmp"
    for path in (home, codex_home, cwd, temp):
        path.mkdir(mode=0o700)
    auth_path = codex_home / "auth.json"
    try:
        shutil.copyfile(source_auth, auth_path)
        auth_path.chmod(0o600)
    except OSError as exc:
        raise CodexAppServerProcessFailure(
            "codex_auth_isolation_failed",
            "Nie udało się odizolować lokalnej sesji Codexa.",
        ) from exc
    return _IsolatedCodexRuntime(
        cwd=str(cwd),
        environment=_codex_process_environment(
            root=root,
            home=home,
            codex_home=codex_home,
            temp=temp,
            source_auth=source_auth,
        ),
    )


def _codex_process_environment(
    *,
    root: Path,
    home: Path,
    codex_home: Path,
    temp: Path,
    source_auth: Path,
) -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if key in _PROCESS_ENV_NAMES}
    environment.update(
        {
            "CODEX_HOME": str(codex_home),
            "HOME": str(home),
            "TEMP": str(temp),
            "TMP": str(temp),
            "TMPDIR": str(temp),
            "XDG_CACHE_HOME": str(root / "xdg-cache"),
            "XDG_CONFIG_HOME": str(root / "xdg-config"),
            "XDG_DATA_HOME": str(root / "xdg-data"),
            "XDG_STATE_HOME": str(root / "xdg-state"),
        }
    )
    source_home = source_auth.parent.parent
    mise_data = source_home / ".local" / "share" / "mise"
    if mise_data.is_dir():
        # The local `codex` launcher resolves its installed Node runtime
        # through mise. Keep that lookup without inheriting configuration,
        # cache, credentials, or the operator's HOME.
        environment["MISE_DATA_DIR"] = str(mise_data)
    npm_cache = source_home / ".npm"
    if npm_cache.is_dir():
        # Reuse only the package cache so isolated startup does not make a
        # network install before the app-server can answer JSON-RPC.
        environment["NPM_CONFIG_CACHE"] = str(npm_cache)
    return environment


def _codex_process_command(*, model: str, model_reasoning_effort: str) -> tuple[str, ...]:
    command = ["codex", "app-server", "--stdio"]
    overrides = [
        *_CONFIG_OVERRIDES,
        f"model={json.dumps(model, ensure_ascii=False)}",
        f"model_reasoning_effort={json.dumps(model_reasoning_effort, ensure_ascii=False)}",
    ]
    # App-server owns provider selection and its catalog. Passing an operator
    # ``model_providers`` block can route this protocol through an incompatible
    # provider, so the isolated process carries only trusted scalar selection.
    for override in overrides:
        command.extend(("--config", override))
    for feature in _DISABLED_TOOL_FEATURES:
        command.extend(("--disable", feature))
    return tuple(command)


__all__ = [
    "CodexAppServerLaunch",
    "CodexAppServerProcessFailure",
    "THREAD_CONFIG",
    "prepare_codex_app_server_launch",
]
