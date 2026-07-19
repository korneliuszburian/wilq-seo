from types import SimpleNamespace

from wilq.content.planning.generated_proposal import _persisted_runtime_trace, _start_run
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


def test_planning_run_persists_exact_input_digest():
    class RunStore:
        def save_codex_run(self, run):
            return run

    run = _start_run(
        SimpleNamespace(
            work_item_id="content_work_item_demo",
            planning_input_digest="a" * 64,
            evidence_ids=["ev_demo"],
        ),
        RunStore(),
    )

    assert run.planning_input_digest == "a" * 64
    assert run.evidence_ids == ["ev_demo"]
