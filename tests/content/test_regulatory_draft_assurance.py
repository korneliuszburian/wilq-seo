import json
from types import SimpleNamespace

import pytest

from wilq.codex.app_server import CodexAppServerTurnResult
from wilq.content.drafts import draft_assurance_runtime, initial_full_draft
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.draft_assurance import (
    ContentDraftAssuranceModelOutput,
    draft_assurance_output_schema,
    draft_assurance_turn_request,
    validate_draft_assurance_output,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
    ContentInitialDraftSectionOutput,
)
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryDocumentAssertion,
    ContentRegulatoryProfile,
    ContentRegulatoryRequirement,
    regulatory_requirement_assertion_errors,
)
from wilq.content.workflow.planning import ContentPlanningProposal
from wilq.content.workflow.revisions import ContentDraftRevisionPageAssets
from wilq.schemas import CodexRun


def _profile() -> ContentRegulatoryProfile:
    requirement = ContentRegulatoryRequirement(
        id="transport_document",
        label="warunek KPO",
        reason="KPO wymaga zakresu stosowania.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id="mentions_kpo",
                label="wzmianka o KPO",
                required_any_of=["KPO"],
            )
        ],
    )
    return ContentRegulatoryProfile(
        id="regulated_service",
        version="2026-07-31",
        service_card_ids=["service_regulated"],
        official_source_hosts=["example.gov.pl"],
        max_source_age_days=180,
        requirements=[requirement],
    )


def _planning_input(profile: ContentRegulatoryProfile) -> ContentPlanningInput:
    fact = ContentSourceFact(
        source_id="official_kpo_fact",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://example.gov.pl/kpo",
        extracted_fact="KPO stosuje się, gdy przekazanie odpadów podlega ewidencji.",
        scope="claim_policy",
        freshness_date="2026-07-31",
        confidence=1,
        review_status="approved",
        reviewer="ekspert",
        evidence_ids=["ev_kpo"],
        source_connectors=["official_regulatory_review"],
        target_card_id="regulatory_service",
        target_card_type="regulatory_source",
        target_card_title="KPO",
        official_source=True,
        regulatory_profile_id=profile.id,
        regulatory_profile_version=profile.version,
        regulatory_requirement_ids=["transport_document"],
        applicable_service_card_ids=["service_regulated"],
    )
    return ContentPlanningInput.model_construct(
        work_item_id="content_work_item_regulated",
        planning_input_digest="a" * 64,
        confirmed_service_card_id="service_regulated",
        regulatory_coverage=ContentRegulatoryCoverage(
            profile_id=profile.id,
            profile_version=profile.version,
            requirements=profile.requirements,
            requirement_coverage=[
                {
                    "requirement_id": "transport_document",
                    "source_fact_ids": [fact.source_id],
                    "evidence_ids": fact.evidence_ids,
                }
            ],
            source_fact_ids=[fact.source_id],
            evidence_ids=fact.evidence_ids,
            source_facts=[fact],
        ),
    )


def _output(body_markdown: str) -> ContentInitialDraftModelOutput:
    return ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="BDO",
            meta_title="BDO",
            meta_description="Opis BDO",
            h1="BDO",
            lead="Praktyczna informacja.",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="kpo",
                heading="KPO",
                body_markdown=body_markdown,
            )
        ],
    )


def _proposal() -> ContentPlanningProposal:
    return ContentPlanningProposal.model_construct(
        sections=[
            SimpleNamespace(
                section_id="kpo",
                regulatory_requirement_ids=["transport_document"],
            )
        ]
    )


def test_assurance_blocks_an_unqualified_kpo_statement_that_phrase_checks_allow() -> None:
    profile = _profile()
    planning_input = _planning_input(profile)
    output = _output("Każdy transport odpadów wymaga KPO.")

    assert (
        regulatory_requirement_assertion_errors(
            requirement=profile.requirements[0],
            text=output.sections[0].body_markdown,
        )
        == []
    )

    receipt = validate_draft_assurance_output(
        planning_input=planning_input,
        proposal=_proposal(),
        output=output,
        profile=profile,
        assessment=ContentDraftAssuranceModelOutput(
            checks=[
                {
                    "constraint_id": "requirement:transport_document",
                    "status": "fail",
                    "reason_code": "overbroad_claim",
                    "reason": "Zdanie przedstawia KPO jako obowiązek dla każdego transportu.",
                    "document_section_id": "kpo",
                    "evidence_ids": ["ev_kpo"],
                }
            ]
        ),
        codex_run_id="codex_content_draft_assurance_1",
    )

    assert receipt.status == "failed"
    assert receipt.failed_constraint_ids == ["requirement:transport_document"]


def test_assurance_uses_server_owned_evidence_instead_of_critic_selection() -> None:
    profile = _profile()
    planning_input = _planning_input(profile)

    receipt = validate_draft_assurance_output(
        planning_input=planning_input,
        proposal=_proposal(),
        output=_output("KPO stosuje się, gdy przekazanie podlega ewidencji."),
        profile=profile,
        assessment=ContentDraftAssuranceModelOutput(
            checks=[
                {
                    "constraint_id": "requirement:transport_document",
                    "status": "pass",
                    "reason_code": "supported",
                    "reason": "Warunek został podany.",
                    "document_section_id": "kpo",
                    "evidence_ids": ["ev_other"],
                }
            ]
        ),
        codex_run_id="codex_content_draft_assurance_1",
    )
    assert receipt.status == "passed"


def test_assurance_does_not_require_model_selected_evidence() -> None:
    profile = _profile()
    planning_input = _planning_input(profile)

    receipt = validate_draft_assurance_output(
        planning_input=planning_input,
        proposal=_proposal(),
        output=_output("KPO stosuje się, gdy przekazanie podlega ewidencji."),
        profile=profile,
        assessment=ContentDraftAssuranceModelOutput(
            checks=[
                {
                    "constraint_id": "requirement:transport_document",
                    "status": "pass",
                    "reason_code": "supported",
                    "reason": "Warunek został podany.",
                    "document_section_id": "kpo",
                    "evidence_ids": [],
                }
            ]
        ),
        codex_run_id="codex_content_draft_assurance_1",
    )
    assert receipt.status == "passed"


def test_assurance_rejects_a_pass_without_a_document_section() -> None:
    profile = _profile()
    with pytest.raises(ValueError, match="must cite a candidate document section"):
        validate_draft_assurance_output(
            planning_input=_planning_input(profile),
            proposal=_proposal(),
            output=_output("KPO stosuje się, gdy przekazanie podlega ewidencji."),
            profile=profile,
            assessment=ContentDraftAssuranceModelOutput(
                checks=[
                    {
                        "constraint_id": "requirement:transport_document",
                        "status": "pass",
                        "reason_code": "supported",
                        "reason": "Warunek został podany.",
                        "document_section_id": None,
                        "evidence_ids": ["ev_kpo"],
                    }
                ]
            ),
            codex_run_id="codex_content_draft_assurance_1",
        )


def test_assurance_rejects_a_check_bound_to_an_unrelated_document_section() -> None:
    profile = _profile()
    output = _output("KPO stosuje się, gdy przekazanie podlega ewidencji.")
    output = output.model_copy(
        update={
            "sections": [
                *output.sections,
                ContentInitialDraftSectionOutput(
                    section_id="other",
                    heading="Inna sekcja",
                    body_markdown="Treść niezwiązana z KPO.",
                ),
            ]
        }
    )
    proposal = ContentPlanningProposal.model_construct(
        sections=[
            SimpleNamespace(
                section_id="kpo",
                regulatory_requirement_ids=["transport_document"],
            ),
            SimpleNamespace(section_id="other", regulatory_requirement_ids=[]),
        ]
    )

    with pytest.raises(ValueError, match="assigned to the constraint requirement"):
        validate_draft_assurance_output(
            planning_input=_planning_input(profile),
            proposal=proposal,
            output=output,
            profile=profile,
            assessment=ContentDraftAssuranceModelOutput(
                checks=[
                    {
                        "constraint_id": "requirement:transport_document",
                        "status": "pass",
                        "reason_code": "supported",
                        "reason": "Warunek został podany.",
                        "document_section_id": "other",
                        "evidence_ids": ["ev_kpo"],
                    }
                ]
            ),
            codex_run_id="codex_content_draft_assurance_1",
        )


def test_assurance_rejects_a_pass_with_a_reason_code_for_a_failure() -> None:
    profile = _profile()
    with pytest.raises(ValueError, match="requires the supported reason code"):
        validate_draft_assurance_output(
            planning_input=_planning_input(profile),
            proposal=_proposal(),
            output=_output("KPO stosuje się, gdy przekazanie podlega ewidencji."),
            profile=profile,
            assessment=ContentDraftAssuranceModelOutput(
                checks=[
                    {
                        "constraint_id": "requirement:transport_document",
                        "status": "pass",
                        "reason_code": "missing_scope",
                        "reason": "Warunek został podany.",
                        "document_section_id": "kpo",
                        "evidence_ids": [],
                    }
                ]
            ),
            codex_run_id="codex_content_draft_assurance_1",
        )


def test_assurance_schema_and_profile_reject_unknown_constraint_requirements() -> None:
    profile = _profile()
    schema = draft_assurance_output_schema(
        profile,
        _planning_input(profile).regulatory_coverage,
        _output("KPO stosuje się, gdy przekazanie podlega ewidencji."),
    )

    assert schema["$defs"]["ContentDraftAssuranceCheckOutput"]["properties"]["constraint_id"][
        "enum"
    ] == ["requirement:transport_document"]
    assert schema["properties"]["checks"]["minItems"] == 1
    assert schema["properties"]["checks"]["maxItems"] == 1
    assert schema["$defs"]["ContentDraftAssuranceCheckOutput"]["properties"]["reason_code"][
        "enum"
    ] == [
        "supported",
        "missing_scope",
        "missing_exception",
        "unsupported_specific",
        "overbroad_claim",
        "insufficient_source_alignment",
        "not_assessable",
    ]
    assert schema["$defs"]["ContentDraftAssuranceCheckOutput"]["properties"]["document_section_id"][
        "anyOf"
    ] == [{"enum": ["kpo"]}, {"type": "null"}]

    with pytest.raises(ValueError, match="unknown requirements"):
        ContentRegulatoryProfile(
            id="invalid",
            version="1",
            service_card_ids=["service"],
            official_source_hosts=["example.gov.pl"],
            max_source_age_days=30,
            requirements=profile.requirements,
            claim_constraints=[
                {
                    "id": "unknown",
                    "label": "unknown",
                    "instruction": "unknown",
                    "requirement_ids": ["missing"],
                }
            ],
        )


def test_assurance_schema_binds_each_check_to_its_requirement_section() -> None:
    profile = _profile()
    planning_input = _planning_input(profile)
    proposal = _proposal()
    output = _output("KPO stosuje się, gdy przekazanie podlega ewidencji.")

    schema = draft_assurance_output_schema(
        profile,
        planning_input.regulatory_coverage,
        output,
        proposal,
    )

    checks = schema["properties"]["checks"]
    check_variant = checks["items"]["anyOf"][0]
    assert check_variant["properties"]["constraint_id"] == {
        "enum": ["requirement:transport_document"]
    }
    assert check_variant["properties"]["document_section_id"] == {
        "anyOf": [{"enum": ["kpo"]}, {"type": "null"}]
    }


def test_assurance_request_exposes_profile_assertions_to_the_critic() -> None:
    profile = _profile()
    request = draft_assurance_turn_request(
        planning_input=_planning_input(profile),
        proposal=_proposal(),
        output=_output("KPO stosuje się, gdy przekazanie podlega ewidencji."),
        profile=profile,
    )

    context = json.loads(request.application_context)
    assert "nie uznawaj samej obecności frazy" in request.instruction
    assert context["required_document_assertions"] == [
        {
            "requirement_id": "transport_document",
            "label": "warunek KPO",
            "assertions": [
                {
                    "id": "mentions_kpo",
                    "label": "wzmianka o KPO",
                    "required_any_of": ["KPO"],
                }
            ],
        }
    ]


def test_assurance_invalid_output_codes_do_not_retain_model_text() -> None:
    assert (
        draft_assurance_runtime._invalid_output_code(
            ValueError("Draft assurance must cite a candidate document section.")
        )
        == "assurance_section_mismatch"
    )


def test_assurance_accepts_a_section_id_for_a_passing_check() -> None:
    profile = _profile()
    receipt = validate_draft_assurance_output(
        planning_input=_planning_input(profile),
        proposal=_proposal(),
        output=_output("KPO\n stosuje się, gdy przekazanie odpadów podlega ewidencji."),
        profile=profile,
        assessment=ContentDraftAssuranceModelOutput.model_validate(
            {
                "checks": [
                    {
                        "constraint_id": "requirement:transport_document",
                        "status": "pass",
                        "reason_code": "supported",
                        "reason": "Warunek został podany.",
                        "document_section_id": "kpo",
                        "evidence_ids": ["ev_kpo"],
                    }
                ],
                "publish_ready": False,
                "human_review_required": True,
            }
        ),
        codex_run_id="codex_content_draft_assurance_1",
    )

    assert receipt.status == "passed"
    assert (
        draft_assurance_runtime._invalid_output_code(ValueError("untrusted model text"))
        == "assurance_schema_invalid"
    )


def test_assurance_keeps_a_critic_missing_scope_failure() -> None:
    profile = _profile()
    receipt = validate_draft_assurance_output(
        planning_input=_planning_input(profile),
        proposal=_proposal(),
        output=_output("KPO stosuje się, gdy przekazanie podlega ewidencji."),
        profile=profile,
        assessment=ContentDraftAssuranceModelOutput(
            checks=[
                {
                    "constraint_id": "requirement:transport_document",
                    "status": "fail",
                    "reason_code": "missing_scope",
                    "reason": "Zakres wymaga doprecyzowania.",
                    "document_section_id": "kpo",
                    "evidence_ids": [],
                }
            ]
        ),
        codex_run_id="codex_content_draft_assurance_1",
    )

    assert receipt.status == "failed"
    assert receipt.failed_constraint_ids == ["requirement:transport_document"]


def test_profile_rejects_a_custom_constraint_in_the_reserved_requirement_namespace() -> None:
    profile = _profile()

    with pytest.raises(ValueError, match="reserved requirement"):
        ContentRegulatoryProfile(
            id="invalid_reserved_namespace",
            version="1",
            service_card_ids=["service"],
            official_source_hosts=["example.gov.pl"],
            max_source_age_days=30,
            requirements=profile.requirements,
            claim_constraints=[
                {
                    "id": "requirement:transport_document",
                    "label": "collision",
                    "instruction": "collision",
                    "requirement_ids": ["transport_document"],
                }
            ],
        )


def test_failed_assurance_blocks_the_writer_before_document_persistence(monkeypatch) -> None:
    profile = _profile()
    planning_input = _planning_input(profile)
    output = _output("Każdy transport odpadów wymaga KPO.")

    class RunStore:
        def __init__(self) -> None:
            self.saved: list[CodexRun] = []

        def save_codex_run(self, run: CodexRun) -> CodexRun:
            self.saved.append(run)
            return run

    class Client:
        def run_structured_turn(self, _request: object) -> CodexAppServerTurnResult:
            return CodexAppServerTurnResult(
                status="completed",
                output_text=ContentDraftAssuranceModelOutput(
                    checks=[
                        {
                            "constraint_id": "requirement:transport_document",
                            "status": "fail",
                            "reason_code": "overbroad_claim",
                            "reason": "KPO jest przedstawione jako bezwarunkowe.",
                            "document_section_id": "kpo",
                            "evidence_ids": ["ev_kpo"],
                        }
                    ]
                ).model_dump_json(),
            )

    monkeypatch.setattr(
        draft_assurance_runtime,
        "regulatory_draft_assurance_profile",
        lambda _planning_input: profile,
    )
    store = RunStore()
    writer_run = CodexRun(
        id="codex_writer",
        skill="wilq-content-operator",
        hook="content_initial_full_draft",
        source="wilq_api",
        status="started",
    )
    result = initial_full_draft._assure_regulated_draft(
        inputs=initial_full_draft._InitialDraftInputs(
            planning_input=planning_input,
            proposal=type(
                "Proposal",
                (),
                {"proposal_id": "proposal-1", "sections": _proposal().sections},
            )(),
            generation_contract=object(),
        ),
        output=output,
        client=Client(),
        writer_run=writer_run,
        writer_trace=ContentCodexRuntimeTrace(status="completed"),
        run_store=store,
        snapshot=SimpleNamespace(
            preflight=SimpleNamespace(item=SimpleNamespace(id="content_work_item_regulated"))
        ),
    )

    assert result.code == "draft_assurance_failed"
    assert result.source_codes == ["requirement:transport_document"]
    assert result.repair_reasons == {"requirement:transport_document": "overbroad_claim"}
    assert [run.status for run in store.saved] == ["started", "completed"]
    assert store.saved[-1].error == (
        "draft_assurance_failed|requirement:transport_document:overbroad_claim"
    )
