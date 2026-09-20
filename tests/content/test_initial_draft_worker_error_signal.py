"""A worker validation failure must record its failing field paths.

Live BDO: the initial-draft worker failed with ``worker_exception:ValidationError``
after the assurance pass, hiding which field broke. Record only the exception
class and the failing field locations, never candidate text.
"""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from wilq.content.drafts import initial_draft_queue
from wilq.schemas import CodexRun


class _TinyModel(BaseModel):
    count: int


def _validation_error() -> ValidationError:
    try:
        _TinyModel(count="not-an-int")  # type: ignore[arg-type]
    except ValidationError as error:
        return error
    raise AssertionError("expected a validation error")


def test_worker_validation_error_records_field_locations(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    class _Store:
        def list_codex_runs(self) -> list[CodexRun]:
            return [
                CodexRun.model_construct(
                    id="codex_content_initial_draft_signal",
                    status="started",
                )
            ]

    def _capture(store: object, run: object, *, status: str, error: str) -> None:
        recorded["status"] = status
        recorded["error"] = error

    monkeypatch.setattr(initial_draft_queue, "local_state_store", lambda: _Store())
    monkeypatch.setattr(
        initial_draft_queue, "transition_initial_draft_run_if_status", _capture
    )

    initial_draft_queue._mark_initial_draft_run_failed(
        "codex_content_initial_draft_signal", _validation_error()
    )

    assert recorded["status"] == "failed"
    error = str(recorded["error"])
    assert error.startswith("worker_exception:ValidationError:")
    assert "count" in error
