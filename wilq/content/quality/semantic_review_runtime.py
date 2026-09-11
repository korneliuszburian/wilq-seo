from typing import Literal

from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.workflow.runtime.codex_run_lifecycle import finish_codex_run
from wilq.schemas import CodexRun
from wilq.storage.local_state import LocalStateStore


def finish_semantic_run(
    store: LocalStateStore,
    run: CodexRun,
    *,
    status: Literal["blocked", "failed"],
    error: str,
) -> CodexRun:
    return finish_codex_run(store, run, status=status, error=error)


def semantic_runtime_trace(result: CodexAppServerTurnResult) -> ContentCodexRuntimeTrace:
    return ContentCodexRuntimeTrace(
        status=result.status,
        thread_id=result.thread_id,
        turn_id=result.turn_id,
        event_methods=list(result.event_methods),
        item_types=list(result.item_types),
        external_call_attempted=result.external_call_attempted,
    )


__all__ = ["finish_semantic_run", "semantic_runtime_trace"]
