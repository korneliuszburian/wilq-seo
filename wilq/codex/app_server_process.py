"""Trusted launch boundary for the isolated WILQ Codex app-server process."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from wilq.codex.model_policy import embedded_codex_runtime_selection
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


def prepare_codex_app_server_launch(
    root: Path, *, deadline_monotonic: float | None = None,
) -> CodexAppServerLaunch:
    """Build one isolated launch from WILQ's embedded model policy."""

    selection = embedded_codex_runtime_selection()
    if selection is None:
        raise CodexAppServerProcessFailure(
            "codex_model_policy_invalid",
            "Wbudowana polityka app-servera WILQ musi wskazywać gpt-6-luna z wysiłkiem max.",
        )
    runtime = _prepare_isolated_runtime(root)
    return CodexAppServerLaunch(
        command=_codex_process_command(
            model=selection.model,
            model_reasoning_effort=selection.model_reasoning_effort,
            deadline_monotonic=deadline_monotonic,
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


def _resolve_codex_executable(*, deadline_monotonic: float | None = None) -> str:
    """Resolve the real Codex binary instead of an npm/mise launcher wrapper.

    A launcher script can stall or reinstall when it runs under the isolated
    HOME, so ask mise for the installed binary with only lookup-specific
    environment values, never the parent's credentials or runtime overrides.
    """

    resolved = shutil.which("codex")
    if resolved is None:
        return "codex"
    try:
        with Path(resolved).open("rb") as executable:
            text = executable.read(4096).decode("utf-8", errors="ignore")
    except OSError:
        return resolved
    first_line = text.splitlines()[0] if text else ""
    if not first_line.startswith("#!") or "bash" not in first_line:
        return resolved
    if "mise" not in text and "npm" not in text:
        return resolved
    try:
        completed = subprocess.run(
            ["mise", "which", "codex"],
            capture_output=True,
            text=True,
            timeout=_lookup_timeout(deadline_monotonic),
            check=False,
            env={
                key: value
                for key, value in os.environ.items()
                if key in {"PATH", "HOME", "MISE_DATA_DIR", "LANG", "LC_ALL", "LC_CTYPE"}
            },
        )
    except (OSError, subprocess.SubprocessError):
        _lookup_timeout(deadline_monotonic)
        return resolved
    _lookup_timeout(deadline_monotonic)
    candidate = completed.stdout.strip()
    if (
        completed.returncode == 0
        and candidate
        and Path(candidate).is_file()
        and os.access(candidate, os.X_OK)
    ):
        return candidate
    return resolved


def _lookup_timeout(deadline_monotonic: float | None) -> float:
    if deadline_monotonic is None:
        return 10
    remaining = deadline_monotonic - time.monotonic()
    if remaining <= 0:
        raise TimeoutError
    return min(10, remaining)


def _codex_process_command(
    *, model: str, model_reasoning_effort: str, deadline_monotonic: float | None = None,
) -> tuple[str, ...]:
    command = [
        _resolve_codex_executable(deadline_monotonic=deadline_monotonic), "app-server", "--stdio",
    ]
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
