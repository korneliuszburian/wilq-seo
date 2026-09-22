"""One bounded retry for a transient critic turn failure.

Live BDO: the independent assurance turn can return a classified transport
failure and block the whole draft. Retry exactly once for that failure, never
for a blocked external call, and never to change a critic verdict.
"""

from __future__ import annotations

from wilq.codex.app_server import CodexAppServerTurnBlocker, CodexAppServerTurnResult
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
    client = _FlakyClient(
        first=CodexAppServerTurnResult(
            status="failed",
            blockers=(
                CodexAppServerTurnBlocker(
                    code="codex_transport_error",
                    message="Transient transport failure.",
                ),
            ),
        )
    )

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


def test_classified_timeout_is_not_retried() -> None:
    client = _FlakyClient(
        first=CodexAppServerTurnResult(
            status="failed",
            blockers=(
                CodexAppServerTurnBlocker(
                    code="codex_timeout",
                    message="The bounded turn deadline expired.",
                ),
            ),
        )
    )

    result = _run_assurance_turn(client, object())  # type: ignore[arg-type]

    assert result.status == "failed"
    assert [blocker.code for blocker in result.blockers] == ["codex_timeout"]
    assert client.calls == 1
