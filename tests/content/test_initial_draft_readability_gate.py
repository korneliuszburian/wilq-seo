from __future__ import annotations

import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import cast

import pytest

from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.drafts import initial_draft_assurance_repair, initial_full_draft
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.draft_assurance import ContentDraftAssuranceReceipt
from wilq.content.drafts.draft_assurance_runtime import ContentDraftAssuranceFailure
from wilq.content.drafts.initial_draft_readability import (
    assure_readability_and_repair,
    readability_issues_for_output,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftCtaOutput,
    ContentInitialDraftFaqOutput,
    ContentInitialDraftInternalLinkOutput,
    ContentInitialDraftModelOutput,
    ContentInitialDraftRequest,
    ContentInitialDraftSectionOutput,
)
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftGenerationInput,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryDocumentAssertion,
    ContentRegulatoryRequirement,
)
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionPageAssets
from wilq.schemas import CodexRun

_CLEAN_SECTION_ONE = (
    "Przedsiębiorca sprawdza zakres obowiązków, porządkuje dokumenty i planuje "
    "kolejne działania zgodnie z profilem swojej działalności."
)
_CLEAN_SECTION_TWO = (
    "Następnie firma wyznacza odpowiedzialne osoby, terminy oraz sposób kontroli "
    "kompletności wymaganej dokumentacji."
)
_CLEAN_LEAD = "Krótki przewodnik prowadzi przez najważniejsze działania."
_DIRTY_LEAD = "Treść wymaga weryfikacji przez człowieka przed publikacją."
_DIRTY_SECTION_ONE = (
    "Ta informacja wymaga weryfikacji przez człowieka przed dalszym użyciem w "
    "gotowej treści przeznaczonej dla klienta."
)
_DIRTY_SECTION_TWO = (
    "Druga informacja wymaga weryfikacji przez człowieka przed przekazaniem tej "
    "sekcji czytelnikowi jako gotowej odpowiedzi."
)
_DIRTY_FAQ_ANSWER = (
    "Ta informacja wymaga weryfikacji przez człowieka przed przekazaniem odpowiedzi "
    "czytelnikowi zainteresowanemu usługą."
)
_CLEAN_FAQ_ANSWER = (
    "Przedsiębiorca najpierw porządkuje dokumenty, a następnie ustala zakres i terminy "
    "kolejnych działań."
)
_CTA_PARAGRAPH = (
    "Skontaktuj się z zespołem, aby omówić zakres dokumentacji i zaplanować kolejne "
    "bezpieczne działania."
)
_DUPLICATED_CTA_BODY = f"{_CTA_PARAGRAPH}\n\n{_CTA_PARAGRAPH}"
_BLOCKED_CLAIM_SECTION = (
    "Usługa zapewnia gwarantowane wyniki każdej firmie, niezależnie od zakresu "
    "obowiązków, dokumentacji oraz profilu prowadzonej działalności."
)
_REGULATED_DIRTY_SECTION = (
    f"KPO stosuje się, gdy przekazanie odpadów podlega ewidencji. {_DIRTY_SECTION_ONE}"
)
_REGULATED_CLEAN_SECTION = (
    "KPO stosuje się, gdy przekazanie odpadów podlega ewidencji. "
    "Przedsiębiorca sprawdza zakres obowiązków, porządkuje dokumenty i planuje "
    "kolejne działania zgodnie z profilem swojej działalności."
)


class _PatchClient:
    def __init__(self, replacements: dict[str, str] | None = None) -> None:
        self.replacements = replacements or {}
        self.requests: list[CodexAppServerStructuredTurnRequest] = []

    def run_structured_turn(
        self,
        request: CodexAppServerStructuredTurnRequest,
    ) -> CodexAppServerTurnResult:
        self.requests.append(request)
        application_context = json.loads(request.application_context)
        candidate = json.loads(request.untrusted_context)["candidate_document"]
        bodies = {
            section["section_id"]: section["body_markdown"] for section in candidate["sections"]
        }
        bodies.update(
            {
                f"faq:{index}": item["answer_markdown"]
                for index, item in enumerate(candidate["faq"], start=1)
            }
        )
        bodies.update(
            {
                f"cta:{index}": item["body_markdown"]
                for index, item in enumerate(candidate["cta_blocks"], start=1)
            }
        )
        bodies.update(
            {f"page_assets:{field}": value for field, value in candidate["page_assets"].items()}
        )
        bodies.update(
            {
                f"link:{index}": item["anchor_text"]
                for index, item in enumerate(candidate["internal_links"], start=1)
            }
        )
        return CodexAppServerTurnResult(
            status="completed",
            output_text=json.dumps(
                {
                    "sections": [
                        {
                            "section_id": section_id,
                            "mode": "replace",
                            "body_markdown": self.replacements.get(
                                section_id,
                                bodies[section_id],
                            ),
                        }
                        for section_id in application_context["affected_section_ids"]
                    ],
                    "publish_ready": False,
                },
                ensure_ascii=False,
            ),
            turn_id=f"readability-repair-{len(self.requests)}",
        )


def _planning_input() -> ContentPlanningInput:
    return ContentPlanningInput.model_construct(
        work_item_id="content_work_item_readability_gate",
        planning_input_digest="a" * 64,
        regulatory_coverage=ContentRegulatoryCoverage(),
        claim_ledger=[],
        evidence_ids=["ev_readability_gate"],
    )


def _proposal() -> ContentPlanningProposal:
    return ContentPlanningProposal.model_construct(
        work_item_id="content_work_item_readability_gate",
        proposal_id="content_planning_proposal_readability_gate",
        planning_digest="b" * 64,
        planning_input_digest="a" * 64,
        sections=[
            ContentPlanningSection(
                section_id="section_01",
                heading="Pierwszy krok",
                purpose="Wyjaśnij pierwszy krok.",
                evidence_ids=["ev_readability_gate"],
            ),
            ContentPlanningSection(
                section_id="section_02",
                heading="Drugi krok",
                purpose="Wyjaśnij drugi krok.",
                evidence_ids=["ev_readability_gate"],
            ),
        ],
        faq=[],
        cta_blocks=[],
        internal_links=[],
        evidence_ids=["ev_readability_gate"],
    )


def _generation_contract() -> StructuredDraftGenerationContract:
    return StructuredDraftGenerationContract.model_construct(
        model_input=StructuredDraftGenerationInput.model_construct(
            claims_removed_or_blocked=[],
            removed_or_blocked_claim_markers=[],
            human_review_questions=[],
        )
    )


def _prepared_inputs() -> initial_full_draft._InitialDraftInputs:
    return initial_full_draft._InitialDraftInputs(
        planning_input=_planning_input(),
        proposal=_proposal(),
        generation_contract=_generation_contract(),
    )


def _regulated_prepared_inputs() -> initial_full_draft._InitialDraftInputs:
    prepared = _prepared_inputs()
    requirement = ContentRegulatoryRequirement(
        id="transport_document",
        label="Warunek KPO",
        reason="Treść musi zachować warunek stosowania KPO.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id="mentions_kpo",
                label="Wzmianka o KPO",
                required_any_of=["KPO"],
            )
        ],
    )
    return initial_full_draft._InitialDraftInputs(
        planning_input=prepared.planning_input.model_copy(
            update={
                "confirmed_service_card_id": "service_regulated",
                "regulatory_coverage": ContentRegulatoryCoverage(
                    profile_id="regulated_profile",
                    profile_version="1",
                    requirements=[requirement],
                ),
            }
        ),
        proposal=prepared.proposal.model_copy(
            update={
                "sections": [
                    prepared.proposal.sections[0].model_copy(
                        update={"regulatory_requirement_ids": [requirement.id]}
                    ),
                    prepared.proposal.sections[1],
                ]
            }
        ),
        generation_contract=prepared.generation_contract,
    )


def _assurance_receipt(codex_run_id: str) -> ContentDraftAssuranceReceipt:
    return ContentDraftAssuranceReceipt(
        status="passed",
        profile_id="regulated_profile",
        profile_version="1",
        codex_run_id=codex_run_id,
    )


def _output(
    *,
    first_body: str,
    second_body: str = _CLEAN_SECTION_TWO,
    faq_answer: str | None = None,
    cta_body: str | None = None,
    lead: str = _CLEAN_LEAD,
    internal_link_anchor: str | None = None,
) -> ContentInitialDraftModelOutput:
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Czytelny przewodnik",
            meta_title="Czytelny przewodnik dla firmy",
            meta_description="Praktyczne kroki dla przedsiębiorcy.",
            h1="Jak uporządkować obowiązki",
            lead=lead,
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="section_01",
                heading="Pierwszy krok",
                body_markdown=first_body,
            ),
            ContentInitialDraftSectionOutput(
                section_id="section_02",
                heading="Drugi krok",
                body_markdown=second_body,
            ),
        ],
        faq=(
            [
                ContentInitialDraftFaqOutput(
                    question="Jak zacząć porządkowanie dokumentacji?",
                    answer_markdown=faq_answer,
                )
            ]
            if faq_answer is not None
            else []
        ),
        cta_blocks=(
            [ContentInitialDraftCtaOutput(body_markdown=cta_body)] if cta_body is not None else []
        ),
    )
    if internal_link_anchor is None:
        return output
    return output.model_copy(
        update={
            "internal_links": [
                ContentInitialDraftInternalLinkOutput.model_construct(
                    target_url="https://www.ekologus.pl/uslugi/",
                    anchor_text=internal_link_anchor,
                )
            ]
        }
    )


def _assure(
    output: ContentInitialDraftModelOutput,
    client: _PatchClient,
    trace: ContentCodexRuntimeTrace,
    output_blocker: Callable[[ContentInitialDraftModelOutput], ContentInitialDraftBlocker | None],
):
    return assure_readability_and_repair(
        planning_input=_planning_input(),
        proposal=_proposal(),
        output=output,
        trace=trace,
        client=client,
        run_store=cast(object, SimpleNamespace()),
        output_blocker=output_blocker,
    )


def _allow_output(
    _output: ContentInitialDraftModelOutput,
) -> ContentInitialDraftBlocker | None:
    return None


def _generate_blocked_response(monkeypatch, output, client):
    prepared = _prepared_inputs()
    planning_input = prepared.planning_input
    proposal = prepared.proposal
    trace = ContentCodexRuntimeTrace(status="completed", turn_id="initial-turn")
    run = CodexRun.model_construct(
        id="codex_content_initial_draft_readability_gate",
        status="started",
    )
    persistence_calls: list[dict[str, object]] = []
    finish_calls: list[dict[str, object]] = []

    monkeypatch.setattr(initial_full_draft, "_prepare_inputs", lambda *_args: prepared)
    monkeypatch.setattr(
        initial_full_draft,
        "initial_full_draft_turn_request",
        lambda **_kwargs: SimpleNamespace(instruction="initial draft"),
    )
    monkeypatch.setattr(
        initial_full_draft,
        "start_initial_draft_run",
        lambda *_args, **_kwargs: run,
    )
    monkeypatch.setattr(
        initial_full_draft,
        "_execute_runtime",
        lambda *_args, **_kwargs: (output, trace),
    )
    monkeypatch.setattr(
        initial_full_draft,
        "repair_initial_output_blocker",
        lambda **kwargs: (kwargs["output"], kwargs["trace"], None),
    )
    monkeypatch.setattr(
        initial_full_draft,
        "assure_and_repair_initial_draft",
        lambda **kwargs: (kwargs["output"], kwargs["trace"], None, None),
    )
    monkeypatch.setattr(
        initial_full_draft,
        "finish_initial_draft_run",
        lambda *_args, **kwargs: finish_calls.append(kwargs),
    )
    monkeypatch.setattr(
        initial_full_draft,
        "persist_initial_draft",
        lambda **kwargs: persistence_calls.append(kwargs),
    )
    response = initial_full_draft.generate_initial_full_draft(
        snapshot=SimpleNamespace(
            preflight=SimpleNamespace(item=SimpleNamespace(id=planning_input.work_item_id))
        ),
        request=ContentInitialDraftRequest(
            expected_proposal_id=proposal.proposal_id,
            expected_planning_digest=proposal.planning_digest,
            expected_planning_input_digest=proposal.planning_input_digest,
            requested_by="wilku",
        ),
        client=client,
        workflow_store=cast(object, SimpleNamespace()),
        run_store=cast(object, SimpleNamespace()),
        context_digest="c" * 64,
    )
    return response, persistence_calls, finish_calls


def _generate_assured_response(
    monkeypatch,
    *,
    output: ContentInitialDraftModelOutput,
    client: _PatchClient,
    assurance_results: list[ContentDraftAssuranceReceipt | ContentDraftAssuranceFailure],
):
    prepared = _regulated_prepared_inputs()
    trace = ContentCodexRuntimeTrace(status="completed", turn_id="initial-turn")
    run = CodexRun.model_construct(
        id="codex_content_initial_draft_regulatory_readability_gate",
        status="started",
    )
    pending_results = list(assurance_results)
    assurance_candidates: list[ContentInitialDraftModelOutput] = []
    persistence_calls: list[dict[str, object]] = []
    finish_calls: list[dict[str, object]] = []

    def fake_assure_regulated_draft(
        **kwargs: object,
    ) -> ContentDraftAssuranceReceipt | ContentDraftAssuranceFailure:
        assurance_candidates.append(cast(ContentInitialDraftModelOutput, kwargs["output"]))
        return pending_results.pop(0)

    def fake_persist_initial_draft(**kwargs: object) -> SimpleNamespace:
        persistence_calls.append(kwargs)
        return SimpleNamespace(status="created")

    monkeypatch.setattr(initial_full_draft, "_prepare_inputs", lambda *_args: prepared)
    monkeypatch.setattr(
        initial_full_draft,
        "initial_full_draft_turn_request",
        lambda **_kwargs: SimpleNamespace(instruction="initial draft"),
    )
    monkeypatch.setattr(
        initial_full_draft, "start_initial_draft_run", lambda *_args, **_kwargs: run
    )
    monkeypatch.setattr(
        initial_full_draft,
        "_execute_runtime",
        lambda *_args, **_kwargs: (output, trace),
    )
    monkeypatch.setattr(
        initial_full_draft,
        "assure_regulated_draft",
        fake_assure_regulated_draft,
    )
    monkeypatch.setattr(
        initial_draft_assurance_repair,
        "assure_regulated_draft",
        fake_assure_regulated_draft,
    )
    monkeypatch.setattr(
        initial_full_draft,
        "finish_initial_draft_run",
        lambda *_args, **kwargs: finish_calls.append(kwargs),
    )
    monkeypatch.setattr(initial_full_draft, "persist_initial_draft", fake_persist_initial_draft)
    response = initial_full_draft.generate_initial_full_draft(
        snapshot=SimpleNamespace(
            preflight=SimpleNamespace(item=SimpleNamespace(id=prepared.planning_input.work_item_id))
        ),
        request=ContentInitialDraftRequest(
            expected_proposal_id=prepared.proposal.proposal_id,
            expected_planning_digest=prepared.proposal.planning_digest,
            expected_planning_input_digest=prepared.proposal.planning_input_digest,
            requested_by="wilku",
        ),
        client=client,
        workflow_store=cast(object, SimpleNamespace()),
        run_store=cast(object, SimpleNamespace()),
        context_digest="c" * 64,
    )
    assert pending_results == []
    return response, assurance_candidates, persistence_calls, finish_calls


def test_initial_draft_readability_gate_repairs_or_blocks_before_persistence(
    monkeypatch,
) -> None:
    dirty_output = _output(first_body=_DIRTY_SECTION_ONE)
    issues = readability_issues_for_output(dirty_output)

    assert any(
        code == "working_note" and section_id == "section_01" for code, section_id, _ in issues
    )

    trace = ContentCodexRuntimeTrace(status="completed", turn_id="initial-turn")
    repair_client = _PatchClient({"section_01": _CLEAN_SECTION_ONE})
    repaired, repaired_trace, blocker = _assure(
        dirty_output,
        repair_client,
        trace,
        _allow_output,
    )

    assert blocker is None
    assert repaired.sections[0].body_markdown == _CLEAN_SECTION_ONE
    assert readability_issues_for_output(repaired) == []
    assert repaired_trace.turn_id == "readability-repair-1"
    assert len(repair_client.requests) == 1
    repair_context = json.loads(repair_client.requests[0].untrusted_context)
    assert repair_context["candidate_document"]["sections"][0]["section_id"] == ("section_01")
    assert repair_context["issues"]
    repair_schema = repair_client.requests[0].output_schema
    assert repair_schema["properties"]["sections"]["minItems"] == 1
    assert repair_schema["properties"]["sections"]["maxItems"] == 1
    assert repair_schema["$defs"]["_RegulatorySectionPatch"]["properties"]["section_id"][
        "enum"
    ] == ["section_01"]

    clean_output = _output(first_body=_CLEAN_SECTION_ONE)
    no_call_client = _PatchClient()
    clean_blocker_calls: list[ContentInitialDraftModelOutput] = []

    def clean_output_blocker(
        candidate: ContentInitialDraftModelOutput,
    ) -> ContentInitialDraftBlocker | None:
        clean_blocker_calls.append(candidate)
        return None

    passed, passed_trace, passed_blocker = _assure(
        clean_output,
        no_call_client,
        trace,
        clean_output_blocker,
    )

    assert passed is clean_output
    assert passed_trace is trace
    assert passed_blocker is None
    assert no_call_client.requests == []
    assert clean_blocker_calls == []

    unchanged_client = _PatchClient()
    response, persistence_calls, finish_calls = _generate_blocked_response(
        monkeypatch,
        _output(
            first_body=_DIRTY_SECTION_ONE,
            second_body=_DIRTY_SECTION_TWO,
        ),
        unchanged_client,
    )

    assert len(unchanged_client.requests) == 2
    assert response.status == "blocked"
    assert response.revision is None
    assert response.blockers[0].code == "readability_gate_failed"
    assert "working_note" in response.blockers[0].source_codes
    assert persistence_calls == []
    assert len(finish_calls) == 1


def test_readability_repair_reassures_and_persists_the_fresh_receipt(monkeypatch) -> None:
    output = _output(first_body=_REGULATED_DIRTY_SECTION)
    before_receipt = _assurance_receipt("assurance-before-readability")
    after_receipt = _assurance_receipt("assurance-after-readability")
    client = _PatchClient({"section_01": _REGULATED_CLEAN_SECTION})

    response, assurance_candidates, persistence_calls, finish_calls = _generate_assured_response(
        monkeypatch,
        output=output,
        client=client,
        assurance_results=[before_receipt, after_receipt],
    )

    assert response.status == "created"
    assert len(assurance_candidates) == 2
    assert assurance_candidates[0] is output
    assert assurance_candidates[1] is not output
    assert assurance_candidates[1].sections[0].body_markdown == _REGULATED_CLEAN_SECTION
    assert len(client.requests) == 1
    assert len(persistence_calls) == 1
    assert persistence_calls[0]["output"] is assurance_candidates[1]
    assert persistence_calls[0]["regulatory_assurance"] is after_receipt
    assert persistence_calls[0]["regulatory_assurance"] is not before_receipt
    assert finish_calls == []


def test_clean_readability_path_keeps_the_initial_assurance_receipt(monkeypatch) -> None:
    output = _output(first_body=_REGULATED_CLEAN_SECTION)
    initial_receipt = _assurance_receipt("assurance-clean-output")
    client = _PatchClient()

    response, assurance_candidates, persistence_calls, finish_calls = _generate_assured_response(
        monkeypatch,
        output=output,
        client=client,
        assurance_results=[initial_receipt],
    )

    assert response.status == "created"
    assert assurance_candidates == [output]
    assert assurance_candidates[0] is output
    assert client.requests == []
    assert len(persistence_calls) == 1
    assert persistence_calls[0]["output"] is output
    assert persistence_calls[0]["regulatory_assurance"] is initial_receipt
    assert finish_calls == []


def test_failed_reassurance_after_readability_repair_blocks_without_persistence(
    monkeypatch,
) -> None:
    output = _output(first_body=_REGULATED_DIRTY_SECTION)
    initial_receipt = _assurance_receipt("assurance-before-failed-reassurance")
    failure = ContentDraftAssuranceFailure(
        code="draft_assurance_failed",
        label="Tekst nie przeszedł ponownej kontroli merytorycznej",
        reason="Naprawa czytelności zmieniła zakres warunku regulacyjnego.",
        next_step="Odrzuć wynik i uruchom nową próbę.",
        source_codes=["requirement:transport_document"],
        repair_reasons={"requirement:transport_document": "missing_scope"},
    )
    client = _PatchClient({"section_01": _REGULATED_CLEAN_SECTION})

    response, assurance_candidates, persistence_calls, finish_calls = _generate_assured_response(
        monkeypatch,
        output=output,
        client=client,
        assurance_results=[initial_receipt, failure],
    )

    assert len(assurance_candidates) == 2
    assert assurance_candidates[0] is output
    assert assurance_candidates[1].sections[0].body_markdown == _REGULATED_CLEAN_SECTION
    assert len(client.requests) == 1
    assert response.status == "blocked"
    assert response.revision is None
    assert response.blockers[0].code == failure.code
    assert response.blockers[0].label == failure.label
    assert response.blockers[0].reason == failure.reason
    assert response.blockers[0].next_step == failure.next_step
    assert response.blockers[0].source_codes == failure.source_codes
    assert persistence_calls == []
    assert finish_calls == [
        {
            "status": "blocked",
            "error": "draft_assurance_failed|requirement:transport_document",
        }
    ]


def test_readability_gate_flags_working_note_in_faq_answer() -> None:
    issues = readability_issues_for_output(
        _output(
            first_body=_CLEAN_SECTION_ONE,
            faq_answer=_DIRTY_FAQ_ANSWER,
        )
    )

    assert any(code == "working_note" and section_id == "faq:1" for code, section_id, _ in issues)


@pytest.mark.parametrize(
    "field",
    ["wordpress_title", "meta_title", "meta_description", "h1", "lead"],
)
def test_readability_gate_flags_working_note_in_page_asset(field: str) -> None:
    output = _output(first_body=_CLEAN_SECTION_ONE)
    output = output.model_copy(
        update={"page_assets": output.page_assets.model_copy(update={field: _DIRTY_LEAD})}
    )
    issues = readability_issues_for_output(output)

    assert [
        (code, section_id) for code, section_id, _ in issues if section_id == f"page_assets:{field}"
    ] == [("working_note", f"page_assets:{field}")]


def test_readability_gate_flags_meta_comment_in_internal_link_anchor() -> None:
    dirty_output = _output(first_body=_CLEAN_SECTION_ONE, internal_link_anchor="[do uzupełnienia]")
    issues = readability_issues_for_output(dirty_output)

    assert [(code, section_id) for code, section_id, _ in issues if section_id == "link:1"] == [
        ("working_note", "link:1")
    ]
    valid_link = ContentInitialDraftInternalLinkOutput(
        target_url="https://www.ekologus.pl/uslugi/",
        anchor_text="Źródło wskazuje dokument",
    )
    repairable_output = _output(first_body=_CLEAN_SECTION_ONE).model_copy(
        update={"internal_links": [valid_link]}
    )
    client = _PatchClient({"link:1": "wymagania BDO"})

    repaired, _repaired_trace, blocker = _assure(
        repairable_output,
        client,
        ContentCodexRuntimeTrace(status="completed", turn_id="initial-turn"),
        _allow_output,
    )

    assert blocker is None
    assert repaired.internal_links[0].anchor_text == "wymagania BDO"
    assert repaired.internal_links[0].target_url == valid_link.target_url
    assert readability_issues_for_output(repaired) == []
    application_context = json.loads(client.requests[0].application_context)
    assert application_context["affected_section_ids"] == ["link:1"]


def test_readability_gate_flags_duplicated_paragraph_in_cta_body() -> None:
    issues = readability_issues_for_output(
        _output(
            first_body=_CLEAN_SECTION_ONE,
            cta_body=_DUPLICATED_CTA_BODY,
        )
    )

    assert any(
        code == "duplicate_paragraph" and section_id == "cta:1" for code, section_id, _ in issues
    )


def test_readability_gate_does_not_flag_thin_faq_or_cta() -> None:
    issues = readability_issues_for_output(
        _output(
            first_body=_CLEAN_SECTION_ONE,
            faq_answer="Krótka odpowiedź.",
            cta_body="Zapytaj o wycenę.",
        )
    )

    assert not any(
        code == "thin_section" and section_id in {"faq:1", "cta:1"}
        for code, section_id, _ in issues
    )


def test_readability_gate_repairs_faq_answer() -> None:
    dirty_output = _output(
        first_body=_CLEAN_SECTION_ONE,
        faq_answer=_DIRTY_FAQ_ANSWER,
    )
    client = _PatchClient({"faq:1": _CLEAN_FAQ_ANSWER})

    repaired, repaired_trace, blocker = _assure(
        dirty_output,
        client,
        ContentCodexRuntimeTrace(status="completed", turn_id="initial-turn"),
        _allow_output,
    )

    assert blocker is None
    assert repaired.faq[0].answer_markdown == _CLEAN_FAQ_ANSWER
    assert repaired.faq[0].question == dirty_output.faq[0].question
    assert repaired.sections == dirty_output.sections
    assert readability_issues_for_output(repaired) == []
    assert repaired_trace.turn_id == "readability-repair-1"
    assert len(client.requests) == 1
    application_context = json.loads(client.requests[0].application_context)
    assert application_context["affected_section_ids"] == ["faq:1"]
    repair_schema = client.requests[0].output_schema
    assert repair_schema["$defs"]["_RegulatorySectionPatch"]["properties"]["section_id"][
        "enum"
    ] == ["faq:1"]


def test_readability_gate_repairs_page_asset_lead() -> None:
    dirty_output = _output(
        first_body=_CLEAN_SECTION_ONE,
        lead=_DIRTY_LEAD,
    )
    client = _PatchClient({"page_assets:lead": _CLEAN_LEAD})

    repaired, repaired_trace, blocker = _assure(
        dirty_output,
        client,
        ContentCodexRuntimeTrace(status="completed", turn_id="initial-turn"),
        _allow_output,
    )

    assert blocker is None
    assert repaired.page_assets.lead == _CLEAN_LEAD
    assert readability_issues_for_output(repaired) == []
    assert repaired_trace.turn_id == "readability-repair-1"
    assert len(client.requests) == 1
    application_context = json.loads(client.requests[0].application_context)
    assert application_context["affected_section_ids"] == ["page_assets:lead"]
    repair_schema = client.requests[0].output_schema
    assert repair_schema["$defs"]["_RegulatorySectionPatch"]["properties"]["section_id"][
        "enum"
    ] == ["page_assets:lead"]


def test_readability_gate_blocks_dirty_output_before_spending_a_repair_turn() -> None:
    dirty_output = _output(first_body=f"{_DIRTY_SECTION_ONE} {_BLOCKED_CLAIM_SECTION}")
    trace = ContentCodexRuntimeTrace(status="completed", turn_id="initial-turn")
    prepared = _prepared_inputs()
    blocker = initial_full_draft._output_blocker(prepared, dirty_output)
    blocker_calls: list[ContentInitialDraftModelOutput] = []

    def output_blocker(
        candidate: ContentInitialDraftModelOutput,
    ) -> ContentInitialDraftBlocker | None:
        blocker_calls.append(candidate)
        return initial_full_draft._output_blocker(prepared, candidate)

    client = _PatchClient({"section_01": _CLEAN_SECTION_ONE})
    blocked, blocked_trace, returned_blocker = _assure(
        dirty_output,
        client,
        trace,
        output_blocker,
    )

    assert blocked is dirty_output
    assert blocked_trace is trace
    assert blocker is not None
    assert blocker.code == "generated_claim_blocked"
    assert returned_blocker == blocker
    assert blocker_calls == [dirty_output]
    assert client.requests == []


def test_readability_gate_blocks_repaired_claim_before_persistence(
    monkeypatch,
) -> None:
    dirty_output = _output(
        first_body=_DIRTY_SECTION_ONE,
        second_body=_DIRTY_SECTION_TWO,
    )
    assert {section_id for _, section_id, _ in readability_issues_for_output(dirty_output)} == {
        "section_01",
        "section_02",
    }
    prepared = _prepared_inputs()

    def output_blocker(
        candidate: ContentInitialDraftModelOutput,
    ) -> ContentInitialDraftBlocker | None:
        return initial_full_draft._output_blocker(prepared, candidate)

    direct_client = _PatchClient(
        {
            "section_01": _BLOCKED_CLAIM_SECTION,
            "section_02": _DIRTY_SECTION_TWO,
        }
    )
    repaired, _repaired_trace, returned_blocker = _assure(
        dirty_output,
        direct_client,
        ContentCodexRuntimeTrace(status="completed", turn_id="initial-turn"),
        output_blocker,
    )

    assert repaired.sections[0].body_markdown == _BLOCKED_CLAIM_SECTION
    assert returned_blocker is not None
    assert returned_blocker.code == "generated_claim_blocked"
    assert returned_blocker.source_codes == ["undeclared_high_risk_claim_language"]
    assert len(direct_client.requests) == 1

    persistence_client = _PatchClient(
        {
            "section_01": _BLOCKED_CLAIM_SECTION,
            "section_02": _DIRTY_SECTION_TWO,
        }
    )
    response, persistence_calls, finish_calls = _generate_blocked_response(
        monkeypatch,
        dirty_output,
        persistence_client,
    )

    assert response.status == "blocked"
    assert response.revision is None
    assert response.blockers[0].code == "generated_claim_blocked"
    assert response.blockers[0].source_codes == ["undeclared_high_risk_claim_language"]
    assert persistence_calls == []
    assert len(persistence_client.requests) == 1
    assert len(finish_calls) == 1


@pytest.mark.parametrize("section_id", ["faq:1", "page_assets:x"])
def test_initial_draft_section_id_cannot_collide_with_gate_target(section_id: str) -> None:
    with pytest.raises(ValueError, match="must not collide with gate target"):
        ContentInitialDraftModelOutput(
            page_assets=ContentDraftRevisionPageAssets(
                wordpress_title="Czytelny przewodnik",
                meta_title="Czytelny przewodnik dla firmy",
                meta_description="Praktyczne kroki dla przedsiębiorcy.",
                h1="Jak uporządkować obowiązki",
                lead="Krótki przewodnik prowadzi przez najważniejsze działania.",
            ),
            sections=[
                ContentInitialDraftSectionOutput(
                    section_id=section_id,
                    heading="Pierwszy krok",
                    body_markdown=_CLEAN_SECTION_ONE,
                ),
            ],
        )
