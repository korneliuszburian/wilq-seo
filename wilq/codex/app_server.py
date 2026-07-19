from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import tempfile
import tomllib
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, cast

from wilq.codex.runtime_status import codex_auth_path

CodexAppServerTurnStatus = Literal["completed", "blocked", "failed"]

_SAFE_ITEM_TYPES = frozenset(
    {
        "agentMessage",
        "contextCompaction",
        "enteredReviewMode",
        "exitedReviewMode",
        "plan",
        "reasoning",
        "userMessage",
    }
)
_EXTERNAL_METHOD_PREFIXES = (
    "command/",
    "hook/",
    "item/collabAgentToolCall/",
    "item/commandExecution/",
    "item/dynamicToolCall/",
    "item/fileChange/",
    "item/imageGeneration/",
    "item/imageView/",
    "item/mcpToolCall/",
    "item/sleep/",
    "item/subAgentActivity/",
    "item/webSearch/",
    "process/",
)
_EXTERNAL_METHODS = frozenset({"turn/diff/updated"})
_READ_LIMIT_BYTES = 8 * 1024 * 1024
_DEFAULT_TIMEOUT_SECONDS = 120.0
_PROCESS_EXIT_GRACE_SECONDS = 2.0
_CODEX_PROCESS_ENV_NAMES = frozenset(
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
_CODEX_CONFIG_OVERRIDES = (
    'approval_policy="never"',
    'sandbox_mode="read-only"',
    "features.remote_models=false",
    'web_search="disabled"',
    "mcp_servers={}",
    "apps={_default={enabled=false,destructive_enabled=false,open_world_enabled=false}}",
    'shell_environment_policy={inherit="none"}',
)
_THREAD_CONFIG = {
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


@dataclass(frozen=True, slots=True)
class CodexAppServerStructuredTurnRequest:
    instruction: str
    application_context: str
    untrusted_context: str
    output_schema: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class CodexAppServerTurnBlocker:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class CodexAppServerTurnResult:
    status: CodexAppServerTurnStatus
    output_text: str | None = None
    thread_id: str | None = None
    turn_id: str | None = None
    event_methods: tuple[str, ...] = ()
    item_types: tuple[str, ...] = ()
    external_call_attempted: bool = False
    blockers: tuple[CodexAppServerTurnBlocker, ...] = ()


class CodexAppServerClientProtocol(Protocol):
    def run_structured_turn(
        self, request: CodexAppServerStructuredTurnRequest
    ) -> CodexAppServerTurnResult: ...


class _SafeTransportFailure(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.safe_message = message


class _ExternalCallBlocked(_SafeTransportFailure):
    pass


@dataclass(slots=True)
class _TurnObserver:
    thread_id: str | None = None
    model: str | None = None
    turn_id: str | None = None
    event_methods: list[str] = field(default_factory=list)
    item_types: list[str] = field(default_factory=list)
    final_output_text: str | None = None
    unphased_output_text: str | None = None
    stderr_stream_disconnected: bool = False

    def add_event_method(self, method: str) -> None:
        if method not in self.event_methods:
            self.event_methods.append(method)

    def observe_item(self, value: object, *, completed: bool) -> None:
        item = _as_object(value)
        if item is None:
            raise _SafeTransportFailure(
                "codex_protocol_error",
                "Codex zwrócił nieprawidłowy element odpowiedzi.",
            )
        item_type = item.get("type")
        if not isinstance(item_type, str):
            raise _SafeTransportFailure(
                "codex_protocol_error",
                "Codex zwrócił element bez rozpoznawalnego typu.",
            )
        if item_type not in self.item_types:
            self.item_types.append(item_type)
        if item_type not in _SAFE_ITEM_TYPES:
            raise _ExternalCallBlocked(
                "codex_external_call_blocked",
                "Codex próbował uruchomić narzędzie; wynik został odrzucony.",
            )
        if not completed or item_type != "agentMessage":
            return
        text = item.get("text")
        if not isinstance(text, str):
            raise _SafeTransportFailure(
                "codex_protocol_error",
                "Końcowa odpowiedź Codexa nie zawiera tekstu.",
            )
        phase = item.get("phase")
        if phase == "final_answer":
            self.final_output_text = text
        elif phase is None:
            self.unphased_output_text = text

    def result(
        self,
        status: CodexAppServerTurnStatus,
        *,
        blocker: CodexAppServerTurnBlocker | None = None,
        external_call_attempted: bool = False,
    ) -> CodexAppServerTurnResult:
        output_text = (
            self.final_output_text
            if self.final_output_text is not None
            else self.unphased_output_text
        )
        if status != "completed":
            output_text = None
        return CodexAppServerTurnResult(
            status=status,
            output_text=output_text,
            thread_id=self.thread_id,
            turn_id=self.turn_id,
            event_methods=tuple(self.event_methods),
            item_types=tuple(self.item_types),
            external_call_attempted=external_call_attempted,
            blockers=(blocker,) if blocker is not None else (),
        )


@dataclass(frozen=True, slots=True)
class _IsolatedCodexRuntime:
    auth_path: Path
    cwd: str
    environment: Mapping[str, str]


class StdioCodexAppServerClient:
    def __init__(self, *, timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS) -> None:
        self._timeout_seconds = timeout_seconds

    @property
    def timeout_seconds(self) -> float:
        """Configured deadline used by the synchronous structured-turn seam."""

        return self._timeout_seconds

    def run_structured_turn(
        self, request: CodexAppServerStructuredTurnRequest
    ) -> CodexAppServerTurnResult:
        observer = _TurnObserver()
        invalid_blocker = _validate_request(request, timeout_seconds=self._timeout_seconds)
        if invalid_blocker is not None:
            return observer.result("failed", blocker=invalid_blocker)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            return observer.result(
                "failed",
                blocker=CodexAppServerTurnBlocker(
                    code="codex_sync_context_required",
                    message="Ten adapter Codexa wymaga synchronicznego kontekstu wykonania.",
                ),
            )
        try:
            return asyncio.run(
                asyncio.wait_for(
                    self._run_turn(request, observer),
                    timeout=self._timeout_seconds,
                )
            )
        except TimeoutError:
            if observer.stderr_stream_disconnected:
                return observer.result(
                    "failed",
                    blocker=CodexAppServerTurnBlocker(
                        code="codex_response_stream_disconnected",
                        message=(
                            "Provider Codexa przerwał strumień odpowiedzi przed "
                            "zakończeniem tury."
                        ),
                    ),
                )
            return observer.result(
                "failed",
                blocker=CodexAppServerTurnBlocker(
                    code="codex_timeout",
                    message="Codex nie zakończył generowania w dozwolonym czasie.",
                ),
            )
        except _ExternalCallBlocked as exc:
            return observer.result(
                "blocked",
                blocker=CodexAppServerTurnBlocker(code=exc.code, message=exc.safe_message),
                external_call_attempted=True,
            )
        except _SafeTransportFailure as exc:
            if observer.stderr_stream_disconnected:
                return observer.result(
                    "failed",
                    blocker=CodexAppServerTurnBlocker(
                        code="codex_response_stream_disconnected",
                        message=(
                            "Provider Codexa przerwał strumień odpowiedzi przed "
                            "zakończeniem tury."
                        ),
                    ),
                )
            return observer.result(
                "failed",
                blocker=CodexAppServerTurnBlocker(code=exc.code, message=exc.safe_message),
            )
        except FileNotFoundError:
            return observer.result(
                "failed",
                blocker=CodexAppServerTurnBlocker(
                    code="codex_not_available",
                    message="Lokalny runtime Codexa nie jest dostępny.",
                ),
            )
        except (OSError, TypeError, ValueError):
            return observer.result(
                "failed",
                blocker=CodexAppServerTurnBlocker(
                    code="codex_transport_error",
                    message="Nie udało się bezpiecznie uruchomić lokalnego Codexa.",
                ),
            )

    async def _run_turn(
        self,
        request: CodexAppServerStructuredTurnRequest,
        observer: _TurnObserver,
    ) -> CodexAppServerTurnResult:
        with tempfile.TemporaryDirectory(prefix="wilq-codex-app-server-") as root:
            runtime = _prepare_isolated_runtime(Path(root))
            process = await asyncio.create_subprocess_exec(
                *_codex_process_command(),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=runtime.cwd,
                env=dict(runtime.environment),
                limit=_READ_LIMIT_BYTES,
                start_new_session=True,
            )
            stderr_task: asyncio.Task[None] | None = None
            try:
                stdin, stdout = process.stdin, process.stdout
                stderr = process.stderr
                if stdin is None or stdout is None or stderr is None:
                    raise _SafeTransportFailure(
                        "codex_transport_error",
                        "Nie udało się otworzyć bezpiecznego kanału do Codexa.",
                    )
                stderr_task = asyncio.create_task(_observe_stderr(stderr, observer=observer))
                await _initialize_app_server(stdin, stdout, runtime, observer)
                await _start_thread(stdin, stdout, runtime.cwd, observer)
                await _start_turn(stdin, stdout, runtime.cwd, request, observer)
                return await _complete_turn(stdout, observer)
            finally:
                await _terminate_process(process)
                if stderr_task is not None:
                    try:
                        await asyncio.wait_for(stderr_task, timeout=0.25)
                    except TimeoutError:
                        stderr_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await stderr_task


def _prepare_isolated_runtime(root: Path) -> _IsolatedCodexRuntime:
    source_auth = codex_auth_path()
    if source_auth is None or not source_auth.is_file():
        raise _SafeTransportFailure(
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
        raise _SafeTransportFailure(
            "codex_auth_isolation_failed",
            "Nie udało się odizolować lokalnej sesji Codexa.",
        ) from exc
    environment = _codex_process_environment(root, home, codex_home, temp)
    return _IsolatedCodexRuntime(
        auth_path=auth_path,
        cwd=str(cwd),
        environment=environment,
    )


async def _initialize_app_server(
    stdin: asyncio.StreamWriter,
    stdout: asyncio.StreamReader,
    runtime: _IsolatedCodexRuntime,
    observer: _TurnObserver,
) -> None:
    await _send_request(
        stdin,
        request_id=1,
        method="initialize",
        params={
            "clientInfo": {
                "name": "wilq-content-workflow",
                "title": "WILQ Content Workflow",
                "version": "0.1.0",
            },
            "capabilities": {
                "experimentalApi": True,
                "mcpServerOpenaiFormElicitation": False,
                "requestAttestation": False,
            },
        },
    )
    await _wait_for_response(stdout, request_id=1, observer=observer)
    # Newer app-server versions refresh model metadata after ``initialize``
    # and still need the isolated login for thread/turn startup. The copy is
    # scoped to this TemporaryDirectory and is removed with the whole runtime
    # in ``_run_turn``'s finally block; never persist it or expose its path.
    await _send_notification(stdin, method="initialized")


async def _start_thread(
    stdin: asyncio.StreamWriter,
    stdout: asyncio.StreamReader,
    cwd: str,
    observer: _TurnObserver,
) -> None:
    await _send_request(
        stdin,
        request_id=2,
        method="thread/start",
        params={
            "allowProviderModelFallback": False,
            "approvalPolicy": "never",
            "baseInstructions": (
                "Return only the requested structured content without using tools or "
                "external resources."
            ),
            "config": _THREAD_CONFIG,
            "cwd": cwd,
            "developerInstructions": (
                "Use only the supplied instruction and additional context. Do not call "
                "tools, commands, hooks, MCP servers, web search, sub-agents, files, or "
                "network services. Return only the structured answer requested by the "
                "output schema."
            ),
            "dynamicTools": [],
            "environments": [],
            "ephemeral": True,
            "experimentalRawEvents": False,
            "runtimeWorkspaceRoots": [],
            "sandbox": "read-only",
            "selectedCapabilityRoots": [],
        },
    )
    result = await _wait_for_response(stdout, request_id=2, observer=observer)
    observer.thread_id = _nested_string(result, "thread", "id")
    if observer.thread_id is None:
        raise _SafeTransportFailure(
            "codex_protocol_error",
            "Codex nie zwrócił identyfikatora wątku.",
        )
    observer.model = _string_value(result, "model")


async def _start_turn(
    stdin: asyncio.StreamWriter,
    stdout: asyncio.StreamReader,
    cwd: str,
    request: CodexAppServerStructuredTurnRequest,
    observer: _TurnObserver,
) -> None:
    turn_params: dict[str, object] = {
        "additionalContext": {
            "wilq_application": {
                "kind": "application",
                "value": request.application_context,
            },
            "wilq_untrusted_source": {
                "kind": "untrusted",
                "value": request.untrusted_context,
            },
        },
        "approvalPolicy": "never",
        "cwd": cwd,
        "environments": [],
        "input": [{"type": "text", "text": request.instruction}],
        "outputSchema": dict(request.output_schema),
        "runtimeWorkspaceRoots": [],
        "sandboxPolicy": {"type": "readOnly", "networkAccess": False},
        "threadId": observer.thread_id,
    }
    if observer.model:
        turn_params["model"] = observer.model
    await _send_request(
        stdin,
        request_id=3,
        method="turn/start",
        params=turn_params,
    )
    result = await _wait_for_response(stdout, request_id=3, observer=observer)
    turn = _nested_object(result, "turn")
    if turn is None:
        raise _SafeTransportFailure(
            "codex_protocol_error",
            "Codex nie zwrócił danych tury.",
        )
    observer.turn_id = _string_value(turn, "id")
    if observer.turn_id is None:
        raise _SafeTransportFailure(
            "codex_protocol_error",
            "Codex nie zwrócił identyfikatora tury.",
        )
    _observe_turn_items(turn, observer=observer, completed=False)


async def _complete_turn(
    stdout: asyncio.StreamReader, observer: _TurnObserver
) -> CodexAppServerTurnResult:
    if await _wait_for_turn_completion(stdout, observer=observer) != "completed":
        if observer.stderr_stream_disconnected:
            return observer.result(
                "failed",
                blocker=CodexAppServerTurnBlocker(
                    code="codex_response_stream_disconnected",
                    message="Provider Codexa przerwał strumień odpowiedzi przed zakończeniem tury.",
                ),
            )
        return observer.result(
            "failed",
            blocker=CodexAppServerTurnBlocker(
                code="codex_turn_failed",
                message="Codex nie zakończył poprawnie generowania.",
            ),
        )
    if observer.final_output_text is None and observer.unphased_output_text is None:
        return observer.result(
            "failed",
            blocker=CodexAppServerTurnBlocker(
                code="codex_output_missing",
                message="Codex nie zwrócił końcowej odpowiedzi.",
            ),
        )
    return observer.result("completed")


async def _observe_stderr(
    stderr: asyncio.StreamReader, *, observer: _TurnObserver
) -> None:
    """Classify one safe provider signal without retaining stderr payloads."""

    while True:
        chunk = await stderr.read(4096)
        if not chunk:
            return
        lowered = chunk.decode("utf-8", errors="ignore").lower()
        if "responsestreamdisconnected" in lowered or "stream disconnected" in lowered:
            observer.stderr_stream_disconnected = True


def _validate_request(
    request: CodexAppServerStructuredTurnRequest, *, timeout_seconds: float
) -> CodexAppServerTurnBlocker | None:
    if not request.instruction.strip():
        return CodexAppServerTurnBlocker(
            code="codex_request_invalid",
            message="Instrukcja dla Codexa nie może być pusta.",
        )
    if not request.output_schema:
        return CodexAppServerTurnBlocker(
            code="codex_request_invalid",
            message="Generowanie Codexa wymaga schematu odpowiedzi.",
        )
    if timeout_seconds <= 0:
        return CodexAppServerTurnBlocker(
            code="codex_request_invalid",
            message="Limit czasu Codexa musi być dodatni.",
        )
    return None


def _codex_process_environment(
    root: Path, home: Path, codex_home: Path, temp: Path
) -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if key in _CODEX_PROCESS_ENV_NAMES
    }
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
    source_auth = codex_auth_path()
    if source_auth is not None:
        source_home = source_auth.parent.parent
        mise_data = source_auth.parent.parent / ".local" / "share" / "mise"
        if mise_data.is_dir():
            # The local `codex` launcher resolves its installed Node runtime
            # through mise. Keep that runtime lookup available without
            # inheriting the operator's HOME, config, cache, or credentials.
            environment["MISE_DATA_DIR"] = str(mise_data)
        npm_cache = source_home / ".npm"
        if npm_cache.is_dir():
            # The launcher resolves @openai/codex through npx. Reuse only the
            # package cache so an isolated HOME does not trigger a network
            # install before app-server JSON-RPC can answer.
            environment["NPM_CONFIG_CACHE"] = str(npm_cache)
    return environment


def _codex_process_command() -> tuple[str, ...]:
    command = ["codex", "app-server", "--stdio"]
    overrides = list(_CODEX_CONFIG_OVERRIDES)
    configured_model = _configured_model()
    if configured_model is not None:
        overrides.append(f"model={json.dumps(configured_model, ensure_ascii=False)}")
    # App-server owns provider selection and its model catalog.  Passing a
    # custom ``model_providers`` block here looks harmless, but it routes the
    # Responses stream through providers that are valid for ``codex exec`` and
    # can still be incompatible with app-server (the observed failure is a
    # reconnect loop ending in ``responseStreamDisconnected``).  Keep the
    # app-server on the authenticated provider selected by Codex itself; carry
    # only the model scalar above.
    for override in overrides:
        command.extend(("--config", override))
    for feature in _DISABLED_TOOL_FEATURES:
        command.extend(("--disable", feature))
    return tuple(command)


def _configured_model() -> str | None:
    """Read only the selected model from the operator's Codex config.

    The isolated runtime intentionally does not copy user config wholesale:
    MCP, plugin and credential settings must not cross the boundary. Newer
    app-server versions nevertheless need the selected model explicitly when
    remote model refresh is disabled, so carry this one non-secret scalar.
    """

    auth_path = codex_auth_path()
    if auth_path is None:
        return None
    config_path = auth_path.parent / "config.toml"
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return None
    model = config.get("model")
    if not isinstance(model, str):
        return None
    model = model.strip()
    return model if 0 < len(model) <= 200 else None


async def _send_request(
    stdin: asyncio.StreamWriter,
    *,
    request_id: int,
    method: str,
    params: Mapping[str, object],
) -> None:
    await _write_message(
        stdin,
        {"id": request_id, "method": method, "params": dict(params)},
    )


async def _send_notification(stdin: asyncio.StreamWriter, *, method: str) -> None:
    await _write_message(stdin, {"method": method})


async def _write_message(stdin: asyncio.StreamWriter, message: Mapping[str, object]) -> None:
    try:
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":"))
        stdin.write(payload.encode("utf-8") + b"\n")
        await stdin.drain()
    except (BrokenPipeError, ConnectionResetError) as exc:
        raise _SafeTransportFailure(
            "codex_transport_error",
            "Połączenie z lokalnym Codexem zostało przerwane.",
        ) from exc


async def _wait_for_response(
    stdout: asyncio.StreamReader,
    *,
    request_id: int,
    observer: _TurnObserver,
) -> dict[str, object]:
    while True:
        message = await _read_message(stdout)
        method = message.get("method")
        if isinstance(method, str):
            _observe_inbound_method(message, method=method, observer=observer)
            continue
        if message.get("id") != request_id:
            raise _SafeTransportFailure(
                "codex_protocol_error",
                "Codex zwrócił odpowiedź dla nieznanego żądania.",
            )
        if "error" in message:
            raise _SafeTransportFailure(
                "codex_protocol_error",
                "Codex odrzucił bezpieczne żądanie generowania.",
            )
        result = _as_object(message.get("result"))
        if result is None:
            raise _SafeTransportFailure(
                "codex_protocol_error",
                "Codex zwrócił nieprawidłową odpowiedź protokołu.",
            )
        return result


async def _wait_for_turn_completion(
    stdout: asyncio.StreamReader, *, observer: _TurnObserver
) -> str:
    while True:
        message = await _read_message(stdout)
        method = message.get("method")
        if not isinstance(method, str):
            raise _SafeTransportFailure(
                "codex_protocol_error",
                "Codex zwrócił nieoczekiwaną odpowiedź protokołu.",
            )
        params = _observe_inbound_method(message, method=method, observer=observer)
        if method != "turn/completed":
            continue
        thread_id = _string_value(params, "threadId")
        turn = _nested_object(params, "turn")
        if (
            thread_id != observer.thread_id
            or turn is None
            or _string_value(turn, "id") != observer.turn_id
        ):
            raise _SafeTransportFailure(
                "codex_protocol_error",
                "Codex zakończył inną turę niż oczekiwana.",
            )
        _observe_turn_items(turn, observer=observer, completed=True)
        status = _string_value(turn, "status")
        if status is None:
            raise _SafeTransportFailure(
                "codex_protocol_error",
                "Codex nie zwrócił statusu zakończonej tury.",
            )
        return status


def _observe_inbound_method(
    message: Mapping[str, object],
    *,
    method: str,
    observer: _TurnObserver,
) -> dict[str, object]:
    observer.add_event_method(method)
    if "id" in message:
        raise _ExternalCallBlocked(
            "codex_server_request_blocked",
            "Codex zażądał wykonania operacji po stronie WILQ; wynik został odrzucony.",
        )
    if method in _EXTERNAL_METHODS or method.startswith(_EXTERNAL_METHOD_PREFIXES):
        raise _ExternalCallBlocked(
            "codex_external_call_blocked",
            "Codex próbował wykonać operację zewnętrzną; wynik został odrzucony.",
        )
    if method == "error":
        params = _as_object(message.get("params"))
        if params is not None and params.get("willRetry") is True:
            # Reconnect notices are transient app-server events. Let its
            # retry loop reach turn/completed before classifying the turn.
            return params
        raise _codex_error_blocker(message.get("params"))
    params_value = message.get("params", {})
    params = _as_object(params_value)
    if params is None:
        raise _SafeTransportFailure(
            "codex_protocol_error",
            "Codex zwrócił nieprawidłowe dane zdarzenia.",
        )
    if method in {"item/started", "item/completed"}:
        observer.observe_item(
            params.get("item"),
            completed=method == "item/completed",
        )
    return params


def _codex_error_blocker(params_value: object) -> _SafeTransportFailure:
    """Expose a small safe error class, never Codex's error payload."""

    params = _as_object(params_value)
    error = None if params is None else _as_object(params.get("error"))
    message = None if error is None else error.get("message")
    if isinstance(message, str) and "invalid_json_schema" in message:
        category = _schema_error_category(message)
        return _SafeTransportFailure(
            f"codex_output_schema_invalid_{category}",
            "Schemat odpowiedzi WILQ został odrzucony przez lokalny runtime Codexa.",
        )
    codex_error_info = None if error is None else _as_object(error.get("codexErrorInfo"))
    if (
        codex_error_info is not None
        and "responseStreamDisconnected" in codex_error_info
    ) or (isinstance(message, str) and "disconnected" in message.lower()):
        return _SafeTransportFailure(
            "codex_response_stream_disconnected",
            "Provider Codexa przerwał strumień odpowiedzi przed zakończeniem tury.",
        )
    return _SafeTransportFailure(
        "codex_turn_failed",
        "Codex zgłosił błąd podczas generowania.",
    )


def _schema_error_category(message: str) -> str:
    detail = message
    try:
        payload = _as_object(json.loads(message))
    except json.JSONDecodeError:
        payload = None
    if payload is not None:
        error = _as_object(payload.get("error"))
        nested_message = None if error is None else error.get("message")
        if isinstance(nested_message, str):
            detail = nested_message
    if "additionalProperties" in detail:
        return "additional_properties"
    if "required" in detail:
        return "required"
    if "type" in detail:
        return "type"
    if "anyOf" in detail or "allOf" in detail:
        return "composition"
    return "other"


async def _read_message(stdout: asyncio.StreamReader) -> dict[str, object]:
    try:
        line = await stdout.readline()
    except (ValueError, asyncio.LimitOverrunError) as exc:
        raise _SafeTransportFailure(
            "codex_protocol_error",
            "Odpowiedź Codexa przekroczyła bezpieczny limit.",
        ) from exc
    if not line:
        raise _SafeTransportFailure(
            "codex_transport_error",
            "Lokalny runtime Codexa zakończył pracę przed zwróceniem odpowiedzi.",
        )
    try:
        decoded: object = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _SafeTransportFailure(
            "codex_protocol_error",
            "Codex zwrócił nieprawidłową wiadomość protokołu.",
        ) from exc
    message = _as_object(decoded)
    if message is None:
        raise _SafeTransportFailure(
            "codex_protocol_error",
            "Codex zwrócił nieprawidłową wiadomość protokołu.",
        )
    return message


def _observe_turn_items(
    turn: Mapping[str, object], *, observer: _TurnObserver, completed: bool
) -> None:
    items = turn.get("items", [])
    if not isinstance(items, list):
        raise _SafeTransportFailure(
            "codex_protocol_error",
            "Codex zwrócił nieprawidłową listę elementów tury.",
        )
    for item in items:
        observer.observe_item(item, completed=completed)


async def _terminate_process(process: asyncio.subprocess.Process) -> None:
    if os.name == "posix":
        if process.returncode is None:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                await asyncio.wait_for(process.wait(), timeout=_PROCESS_EXIT_GRACE_SECONDS)
            except TimeoutError:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                await process.wait()
        # The app-server may have exited before a child that it spawned. The
        # final group kill prevents that child from surviving a blocked turn.
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        return
    if process.returncode is not None:
        return
    try:
        process.terminate()
    except ProcessLookupError:
        await process.wait()
        return
    try:
        await asyncio.wait_for(process.wait(), timeout=_PROCESS_EXIT_GRACE_SECONDS)
    except TimeoutError:
        with suppress(ProcessLookupError):
            process.kill()
        await process.wait()


def _as_object(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    if not all(isinstance(key, str) for key in value):
        return None
    return cast(dict[str, object], value)


def _nested_object(value: Mapping[str, object], key: str) -> dict[str, object] | None:
    return _as_object(value.get(key))


def _nested_string(value: Mapping[str, object], key: str, nested_key: str) -> str | None:
    nested = _nested_object(value, key)
    return _string_value(nested, nested_key) if nested is not None else None


def _string_value(value: Mapping[str, object], key: str) -> str | None:
    candidate = value.get(key)
    return candidate if isinstance(candidate, str) else None


__all__ = [
    "CodexAppServerClientProtocol",
    "CodexAppServerStructuredTurnRequest",
    "CodexAppServerTurnBlocker",
    "CodexAppServerTurnResult",
    "StdioCodexAppServerClient",
]
