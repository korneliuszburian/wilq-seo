from __future__ import annotations

import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import cast

from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.drafts import initial_full_draft
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.initial_draft_readability import (
    assure_readability_and_repair,
    readability_issues_for_output,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftBlocker,
    ContentInitialDraftModelOutput,
    ContentInitialDraftRequest,
    ContentInitialDraftSectionOutput,
)
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftGenerationInput,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
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
_DIRTY_SECTION_ONE = (
    "Ta informacja wymaga weryfikacji przez człowieka przed dalszym użyciem w "
    "gotowej treści przeznaczonej dla klienta."
)
_DIRTY_SECTION_TWO = (
    "Druga informacja wymaga weryfikacji przez człowieka przed przekazaniem tej "
    "sekcji czytelnikowi jako gotowej odpowiedzi."
)
_BLOCKED_CLAIM_SECTION = (
    "Usługa zapewnia gwarantowane wyniki każdej firmie, niezależnie od zakresu "
    "obowiązków, dokumentacji oraz profilu prowadzonej działalności."
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


def _output(
    *,
    first_body: str,
    second_body: str = _CLEAN_SECTION_TWO,
) -> ContentInitialDraftModelOutput:
    return ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Czytelny przewodnik",
            meta_title="Czytelny przewodnik dla firmy",
            meta_description="Praktyczne kroki dla przedsiębiorcy.",
            h1="Jak uporządkować obowiązki",
            lead="Krótki przewodnik prowadzi przez najważniejsze działania.",
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
