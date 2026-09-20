"""An unexpected assurance transport failure must keep one typed signal.

Live BDO: the critic run failed in about one second with
``draft_assurance_runtime_failed`` and empty ``source_codes`` because
``_run_assurance_turn`` swallowed the exception and returned a bare failed
result. Preserve the exception class as a safe blocker code so the next
occurrence is diagnosable without retaining any provider payload.
"""

from __future__ import annotations

from wilq.content.drafts.draft_assurance_runtime import _run_assurance_turn


class _RaisingClient:
    def run_structured_turn(self, request: object) -> object:
        raise RuntimeError("unexpected transport failure")


def test_assurance_turn_transport_exception_is_typed() -> None:
    result = _run_assurance_turn(_RaisingClient(), object())  # type: ignore[arg-type]

    assert result.status == "failed"
    assert [blocker.code for blocker in result.blockers] == [
        "assurance_turn_runtimeerror"
    ]
    assert result.external_call_attempted is False
