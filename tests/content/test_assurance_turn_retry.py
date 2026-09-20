"""One bounded retry for a transient critic turn failure.

Live BDO: the independent assurance turn returned ``codex_turn_failed`` and the
whole draft blocked. Retry exactly once for a transient turn failure, never for
a blocked external call, and never to change a critic verdict.
"""

from __future__ import annotations

from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.drafts.draft_assurance_runtime import _run_assurance_turn


class _FlakyClient:
    def __init__(self, *, first: CodexAppServerTurnResult) -> None:
        self.first = first
        self.calls = 0

    def run_structured_turn(self, request: object) -> CodexAppServerTurnResult:
        self.calls += 1
        if self.calls == 1:
            return self.first
        return CodexAppServerTurnResult(status="completed", output_text="{}")


def test_transient_turn_failure_is_retried_once() -> None:
    client = _FlakyClient(first=CodexAppServerTurnResult(status="failed"))

    result = _run_assurance_turn(client, object())  # type: ignore[arg-type]

    assert result.status == "completed"
    assert client.calls == 2


def test_blocked_external_call_is_not_retried() -> None:
    client = _FlakyClient(
        first=CodexAppServerTurnResult(status="blocked", external_call_attempted=True)
    )

    result = _run_assurance_turn(client, object())  # type: ignore[arg-type]

    assert result.status == "blocked"
    assert result.external_call_attempted is True
    assert client.calls == 1
