from types import SimpleNamespace

from wilq.content.planning.generated_proposal import _persisted_runtime_trace
from wilq.schemas import CodexRun


def test_persisted_generated_plan_reports_completed_codex_after_reload(monkeypatch):
    run = CodexRun(
        id="codex_content_planning_demo",
        status="completed",
        skill="wilq-content-operator",
    )
    monkeypatch.setattr(
        "wilq.content.planning.generated_proposal.local_state_store",
        lambda: SimpleNamespace(list_codex_runs=lambda: [run]),
    )

    trace = _persisted_runtime_trace(
        SimpleNamespace(codex_run_id="codex_content_planning_demo")
    )

    assert trace.status == "completed"
    assert trace.run_id == "codex_content_planning_demo"
    assert trace.external_call_attempted is True
