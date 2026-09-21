import threading
import time

from wilq.codex.app_server import (
    CodexAppServerClientProtocol,
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.drafts import draft_assurance_runtime
from wilq.content.drafts.draft_assurance import ContentDraftAssuranceModelOutput
from wilq.content.drafts.draft_plan_preparation import PreparedDraftPlan, prepare_draft_plan
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
    ContentInitialDraftSectionOutput,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningSourceFact
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryProfile,
    ContentRegulatoryRequirement,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal, ContentPlanningSection
from wilq.content.workflow.documents.revisions import ContentDraftRevisionPageAssets
from wilq.schemas import CodexRun


def test_assurance_executor_keeps_parallel_slots_for_independent_checks() -> None:
    barrier = threading.Barrier(2)

    def check() -> None:
        barrier.wait(timeout=1)
        time.sleep(0.01)

    futures = [draft_assurance_runtime._ASSURANCE_EXECUTOR.submit(check) for _ in range(2)]
    for future in futures:
        future.result(timeout=2)


def _batched_assurance_case() -> tuple[
    ContentRegulatoryProfile,
    ContentPlanningInput,
    ContentPlanningProposal,
    PreparedDraftPlan,
    ContentInitialDraftModelOutput,
]:
    requirements = [
        ContentRegulatoryRequirement(
            id=f"batch_requirement_{index}",
            label=f"Wymóg batch {index}",
            reason="Wymóg testu batchowania.",
        )
        for index in range(6)
    ]
    profile = ContentRegulatoryProfile(
        id="batched_assurance_service",
        version="2026-09-21",
        service_card_ids=["service_batched_assurance"],
        official_source_hosts=["example.gov.pl"],
        max_source_age_days=30,
        requirements=requirements,
    )
    evidence_ids = [f"ev_batch_{index}" for index in range(6)]
    source_facts = [
        ContentPlanningSourceFact(
            fact_id=f"planning_batch_fact_{index}",
            summary=f"Potwierdzony fakt batch {index}.",
            source_connector="official_regulatory_review",
            evidence_ids=[evidence_ids[index]],
            source_fact_ids=[f"source_batch_fact_{index}"],
            regulatory_requirement_ids=[requirements[index].id],
        )
        for index in range(6)
    ]
    planning_input = ContentPlanningInput.model_construct(
        work_item_id="content_work_item_batched_assurance",
        planning_input_digest="c" * 64,
        confirmed_service_card_id="service_batched_assurance",
        source_facts=source_facts,
        regulatory_coverage=ContentRegulatoryCoverage(
            applicability_status="required",
            profile_id=profile.id,
            profile_version=profile.version,
            requirements=requirements,
            requirement_coverage=[
                {
                    "requirement_id": requirement.id,
                    "source_fact_ids": [source_facts[index].source_fact_ids[0]],
                    "evidence_ids": [evidence_ids[index]],
                }
                for index, requirement in enumerate(requirements)
            ],
            source_fact_ids=[fact.source_fact_ids[0] for fact in source_facts],
            evidence_ids=evidence_ids,
        ),
    )
    requirement_ids = [requirement.id for requirement in requirements]
    section = ContentPlanningSection(
        section_id="batch_assurance_section",
        heading="Sekcja batch assurance",
        purpose="Zawiera wszystkie wymagania testu.",
        evidence_ids=evidence_ids,
        regulatory_requirement_ids=requirement_ids,
    )
    proposal = ContentPlanningProposal.model_construct(
        work_item_id=planning_input.work_item_id,
        planning_input_digest=planning_input.planning_input_digest,
        planning_digest="d" * 64,
        sections=[section],
    )
    prepared_plan = prepare_draft_plan(proposal, planning_input)
    assert isinstance(prepared_plan, PreparedDraftPlan)
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Batch assurance",
            meta_title="Batch assurance",
            meta_description="Test batchowania assurance.",
            h1="Batch assurance",
            lead="Test batchowania assurance.",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id=section.section_id,
                heading=section.heading,
                body_markdown="Treść oparta na sześciu faktach.",
            )
        ],
    )
    return profile, planning_input, proposal, prepared_plan, output


class _RecordingAssuranceClient:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.requests: list[CodexAppServerStructuredTurnRequest] = []

    def run_structured_turn(
        self, request: CodexAppServerStructuredTurnRequest
    ) -> CodexAppServerTurnResult:
        self.requests.append(request)
        return CodexAppServerTurnResult(status="completed", output_text=self.output_text)


class _RecordingRunStore:
    def __init__(self) -> None:
        self.saved: list[CodexRun] = []

    def save_codex_run(self, run: CodexRun) -> CodexRun:
        self.saved.append(run)
        return run


def test_batched_assurance_uses_one_call_and_rejects_bad_batches(monkeypatch) -> None:
    profile, planning_input, proposal, prepared_plan, output = _batched_assurance_case()
    monkeypatch.setattr(
        draft_assurance_runtime,
        "regulatory_draft_assurance_profile",
        lambda _planning_input: profile,
    )
    constraint_ids = [f"requirement:{requirement.id}" for requirement in profile.requirements]
    for returned_constraint_ids in (list(reversed(constraint_ids)), constraint_ids[:-1]):
        response = ContentDraftAssuranceModelOutput(
            checks=[
                {
                    "constraint_id": constraint_id,
                    "status": "fail",
                    "reason_code": "not_assessable",
                    "reason": "Wynik testowy.",
                    "document_section_id": None,
                    "evidence_ids": [],
                }
                for constraint_id in returned_constraint_ids
            ]
        ).model_dump_json()
        client: CodexAppServerClientProtocol = _RecordingAssuranceClient(response)
        result = draft_assurance_runtime.run_regulatory_draft_assurance(
            planning_input=planning_input,
            proposal=proposal,
            output=output,
            client=client,
            run_store=_RecordingRunStore(),
            prepared_plan=prepared_plan,
        )

        assert getattr(result, "code", None) == "draft_assurance_invalid_output"
        recording_client = client
        assert isinstance(recording_client, _RecordingAssuranceClient)
        assert len(recording_client.requests) == 1
        schema = recording_client.requests[0].output_schema
        assert schema["properties"]["checks"]["minItems"] == 6
        assert schema["properties"]["checks"]["maxItems"] == 6
        assert schema["$defs"]["ContentDraftAssuranceCheckOutput"]["properties"][
            "constraint_id"
        ]["enum"] == constraint_ids


def test_bounded_checks_accept_one_batched_critic_result(monkeypatch) -> None:
    from wilq.content.drafts import draft_assurance_runtime
    from wilq.content.drafts.draft_assurance import (
        ContentDraftAssuranceCheckOutput,
        ContentDraftAssuranceModelOutput,
    )
    from wilq.content.regulatory.policy import ContentRegulatoryClaimConstraint
    from wilq.schemas import CodexRun

    def fake_request(**kwargs):
        return object()

    def batched_run(client, request):
        return type(
            "Result",
            (),
            {
                "status": "completed",
                "output_text": ContentDraftAssuranceModelOutput(
                    checks=[
                        ContentDraftAssuranceCheckOutput(
                            constraint_id=f"constraint_{index}",
                            status="pass",
                            reason_code="supported",
                            reason="OK.",
                        )
                        for index in range(2)
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
        draft_assurance_runtime, "_run_assurance_turn", batched_run
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

    assert isinstance(results, list)
    assert [check.constraint_id for check in results] == [
        "constraint_0",
        "constraint_1",
    ]
