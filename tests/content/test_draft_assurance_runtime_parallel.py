import threading
import time

from wilq.content.drafts import draft_assurance_runtime


def test_assurance_executor_keeps_parallel_slots_for_independent_checks() -> None:
    barrier = threading.Barrier(2)

    def check() -> None:
        barrier.wait(timeout=1)
        time.sleep(0.01)

    futures = [draft_assurance_runtime._ASSURANCE_EXECUTOR.submit(check) for _ in range(2)]
    for future in futures:
        future.result(timeout=2)


def test_bounded_checks_run_independent_critics_concurrently(
    monkeypatch,
) -> None:
    from wilq.content.drafts import draft_assurance_runtime
    from wilq.content.drafts.draft_assurance import (
        ContentDraftAssuranceCheckOutput,
        ContentDraftAssuranceModelOutput,
    )
    from wilq.content.regulatory.policy import ContentRegulatoryClaimConstraint
    from wilq.schemas import CodexRun

    started = threading.Barrier(2)
    overlap = threading.Event()

    def fake_request(**kwargs):
        return object()

    def slow_run(client, request):
        started.wait(timeout=2)
        overlap.set()
        time.sleep(0.05)
        return type(
            "Result",
            (),
            {
                "status": "completed",
                "output_text": ContentDraftAssuranceModelOutput(
                    checks=[
                        ContentDraftAssuranceCheckOutput(
                            constraint_id="constraint_check",
                            status="pass",
                            reason_code="not_assessable",
                            reason="OK.",
                        )
                    ],
                    publish_ready=False,
                    human_review_required=True,
                ).model_dump_json(),
                "external_call_attempted": False,
                "blockers": [],
            },
        )()

    monkeypatch.setattr(draft_assurance_runtime, "draft_assurance_turn_request", fake_request)
    monkeypatch.setattr(
        draft_assurance_runtime, "_run_assurance_turn", slow_run
    )

    constraints = [
        ContentRegulatoryClaimConstraint(
            id=f"constraint_{index}",
            label="Constraint",
            instruction="Sprawdź wymagany element.",
            requirement_ids=["requirement:" + str(index)],
        )
        for index in range(2)
    ]
    profile = type("Profile", (), {"id": "profile", "requirements": []})()
    output = type("Output", (), {"sections": [], "faq": [], "cta_blocks": []})()
    planning_input = type("Input", (), {"source_facts": []})()
    proposal = type("Proposal", (), {"sections": []})()
    critic_run = CodexRun.model_construct(id="critic_run_parallel")

    class RunStore:
        def save_codex_run(self, run):
            return run

    results = draft_assurance_runtime._collect_bounded_checks(
        planning_input=planning_input,
        proposal=proposal,
        output=output,
        profile=profile,
        constraints=constraints,
        client=object(),
        run_store=RunStore(),
        critic_run=critic_run,
    )

    assert overlap.is_set()
    assert isinstance(results, list)
    assert len(results) == 2
