from __future__ import annotations

import json
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path

import pytest

from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.drafts import fact_selection
from wilq.content.drafts.initial_draft_run import transition_initial_draft_run_if_status
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
    ContentInitialDraftRequest,
    ContentInitialDraftResponse,
    ContentInitialDraftSectionOutput,
)
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningSourceFact
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionPageAssets
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.content.workflow.target.new_page import (
    ContentNewPageBrief,
    ContentNewPageBriefInput,
    ContentNewPagePlanningFoundation,
    build_new_page_brief,
    build_new_page_document_identity,
)
from wilq.content.workflow.target.new_page_document import (
    ContentNewPageCanonicalDocumentWorkspace,
    build_new_page_canonical_document_workspace,
)
from wilq.content.workflow.target.new_page_initial_draft import generate_new_page_initial_draft
from wilq.schemas.core import utc_now
from wilq.storage.local_state import LocalStateStore

_SOURCE_FACT = (
    "Źródło podaje, że dokumentację środowiskową poprzedza analiza zakresu inwestycji "
    "i jej możliwego oddziaływania na otoczenie."
)
_DOCUMENT_READY_FACT = (
    "Dokumentację środowiskową poprzedza analiza zakresu inwestycji "
    "i jej możliwego oddziaływania na otoczenie."
)
_CLEAN_BODY = (
    "Analiza porządkuje dane potrzebne do dalszych prac. "
    f"{_DOCUMENT_READY_FACT}"
)
_GENERIC_BODY = (
    "Zespół porządkuje przekazane materiały i ustala kolejność dalszych prac. "
    "Klient otrzymuje jasny opis następnych kroków oraz listę potrzebnych działań."
)
_WORKING_NOTE_BODY = (
    f"{_CLEAN_BODY}\n\n"
    "Ten fragment wymaga weryfikacji przez człowieka przed przekazaniem klientowi."
)


@dataclass(frozen=True)
class _NewPageDraftCase:
    brief: ContentNewPageBrief
    foundation: ContentNewPagePlanningFoundation
    planning_input: ContentPlanningInput
    proposal: ContentPlanningProposal
    workspace: ContentNewPageCanonicalDocumentWorkspace
    request: ContentInitialDraftRequest
    workflow_store: ContentWorkflowStore
    run_store: LocalStateStore


class _InitialDraftClient:
    def __init__(self, output: ContentInitialDraftModelOutput) -> None:
        self.output = output
        self.requests: list[CodexAppServerStructuredTurnRequest] = []

    def run_structured_turn(
        self, request: CodexAppServerStructuredTurnRequest
    ) -> CodexAppServerTurnResult:
        self.requests.append(request)
        return CodexAppServerTurnResult(
            status="completed",
            output_text=json.dumps(self.output.model_dump(mode="json")),
        )


class _ReadabilityRepairClient(_InitialDraftClient):
    def __init__(
        self,
        output: ContentInitialDraftModelOutput,
        *,
        repair_body: str = _CLEAN_BODY,
    ) -> None:
        super().__init__(output)
        self.repair_body = repair_body

    def run_structured_turn(
        self, request: CodexAppServerStructuredTurnRequest
    ) -> CodexAppServerTurnResult:
        self.requests.append(request)
        operation = json.loads(request.application_context)["operation"]
        if operation == "generate_new_page_initial_draft":
            payload = self.output.model_dump(mode="json")
        else:
            assert operation == "repair_initial_draft_readability"
            payload = {
                "sections": [
                    {
                        "section_id": "new_page_section_01",
                        "mode": "replace",
                        "body_markdown": self.repair_body,
                    }
                ],
                "publish_ready": False,
            }
        return CodexAppServerTurnResult(
            status="completed",
            output_text=json.dumps(payload),
        )


def _brief_and_foundation(
    *,
    service_card_id: str = "service_environment",
) -> tuple[ContentNewPageBrief, ContentNewPagePlanningFoundation]:
    brief = build_new_page_brief(
        ContentNewPageBriefInput(
            title="Dokumentacja środowiskowa inwestycji",
            purpose="Pomóc inwestorowi przygotować dokumentację środowiskową.",
            service="Dokumentacja środowiskowa",
            audience="Inwestor przygotowujący przedsięwzięcie",
            search_intent="dokumentacja środowiskowa inwestycji",
            proposed_ia_location="Usługi → Dokumentacja środowiskowa",
        )
    )
    foundation = ContentNewPagePlanningFoundation(
        foundation_id="content_new_page_foundation_quality_gate",
        work_item_id="content_work_item_new_page_quality_gate",
        brief_id=brief.brief_id,
        brief_digest=brief.brief_digest,
        overlap_digest="a" * 64,
        service_card_id=service_card_id,
        service_card_digest="b" * 64,
        service_label="Dokumentacja środowiskowa",
        confirmed_by="Wilku",
        created_at=utc_now(),
    )
    return brief, foundation


def _planning_input(
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation,
) -> tuple[ContentPlanningInput, ContentSourceFact]:
    source_fact = ContentSourceFact.model_construct(
        source_id="source_fact_new_page_environment",
        review_status="approved",
        official_source=False,
        target_card_id=foundation.service_card_id,
        target_card_type="service",
        target_card_title=foundation.service_label,
        service_fit_terms=["dokumentacja środowiskowa"],
        buyer_problem_terms=["inwestycja"],
        extracted_fact=_SOURCE_FACT,
        evidence_ids=["ev_new_page_source_fact"],
    )
    return (
        ContentPlanningInput.model_construct(
            planning_input_digest="d" * 64,
            work_item_id=foundation.work_item_id,
            goal="new_page",
            proposed_ia_location=brief.proposed_ia_location,
            new_page_foundation=foundation,
            confirmed_service_card_id=foundation.service_card_id,
            service_label=foundation.service_label,
            source_facts=[
                ContentPlanningSourceFact(
                    fact_id="planning_source_fact_new_page_environment",
                    summary=_SOURCE_FACT,
                    source_connector="approved_source_review",
                    evidence_ids=source_fact.evidence_ids,
                    source_fact_ids=[source_fact.source_id],
                    knowledge_card_ids=[foundation.service_card_id],
                )
            ],
            regulatory_coverage=ContentRegulatoryCoverage(),
            claim_ledger=[],
            evidence_ids=source_fact.evidence_ids,
        ),
        source_fact,
    )


def _proposal(
    brief: ContentNewPageBrief,
    foundation: ContentNewPagePlanningFoundation,
    planning_input_digest: str,
) -> ContentPlanningProposal:
    return ContentPlanningProposal(
        work_item_id=foundation.work_item_id,
        planning_digest="c" * 64,
        proposal_id="content_planning_proposal_new_page_quality_gate",
        proposal_version=1,
        codex_run_id="codex_new_page_plan_quality_gate",
        generation_status="codex_generated",
        planning_input_digest=planning_input_digest,
        goal="new_page",
        proposed_ia_location=brief.proposed_ia_location,
        new_page_document_identity=build_new_page_document_identity(
            foundation=foundation,
            proposed_ia_location=brief.proposed_ia_location,
        ),
        service_card_id=foundation.service_card_id,
        service_label=foundation.service_label,
        service_selection_confirmed=True,
        target_reader=brief.audience,
        buyer_problem=brief.purpose,
        buyer_trigger="Przed rozpoczęciem inwestycji.",
        search_intent=brief.search_intent,
        cta_direction="Poproś o konsultację.",
        sections=[
            ContentPlanningSection(
                section_id="new_page_section_01",
                heading="Jak przygotować dokumentację",
                purpose="Wyjaśnia pierwszy krok.",
                reader_question="Jak zacząć przygotowanie dokumentacji?",
                inventory_disposition="create",
                query_terms=["dokumentacja środowiskowa"],
                evidence_ids=["ev_new_page_source_fact"],
                knowledge_card_ids=[foundation.service_card_id],
            )
        ],
        search_demand=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Zapisz plan do review.",
        ),
        evidence_ids=["ev_new_page_source_fact"],
        source_connectors=["approved_source_review"],
        knowledge_card_ids=[foundation.service_card_id],
    )


def _draft_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    service_card_id: str = "service_environment",
) -> _NewPageDraftCase:
    brief, foundation = _brief_and_foundation(service_card_id=service_card_id)
    planning_input, source_fact = _planning_input(brief, foundation)
    monkeypatch.setattr(fact_selection, "ekologus_source_facts", lambda: (source_fact,))
    proposal = _proposal(brief, foundation, planning_input.planning_input_digest)
    workspace = build_new_page_canonical_document_workspace(
        brief=brief,
        foundation=foundation,
        proposal=proposal,
    )
    assert workspace is not None
    return _NewPageDraftCase(
        brief=brief,
        foundation=foundation,
        planning_input=planning_input,
        proposal=proposal,
        workspace=workspace,
        request=ContentInitialDraftRequest(
            expected_proposal_id=proposal.proposal_id or "",
            expected_planning_digest=proposal.planning_digest,
            expected_planning_input_digest=planning_input.planning_input_digest,
            requested_by="Wilku",
        ),
        workflow_store=ContentWorkflowStore(tmp_path / "new-page-quality.sqlite3"),
        run_store=LocalStateStore(tmp_path / "new-page-quality.sqlite3"),
    )


def _output(body_markdown: str) -> ContentInitialDraftModelOutput:
    return ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Dokumentacja środowiskowa inwestycji",
            meta_title="Dokumentacja środowiskowa | Ekologus",
            meta_description="Przygotuj dokumentację środowiskową inwestycji.",
            h1="Dokumentacja środowiskowa inwestycji",
            lead="Sprawdź pierwszy krok przed rozpoczęciem inwestycji.",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="new_page_section_01",
                heading="Jak przygotować dokumentację",
                body_markdown=body_markdown,
            )
        ],
    )


def _generate(
    case: _NewPageDraftCase,
    client: _InitialDraftClient,
) -> ContentInitialDraftResponse:
    return generate_new_page_initial_draft(
        brief=case.brief,
        foundation=case.foundation,
        planning_input=case.planning_input,
        proposal=case.proposal,
        workspace=case.workspace,
        request=case.request,
        client=client,
        workflow_store=case.workflow_store,
        run_store=case.run_store,
        endpoint_path="/api/content/new-page-briefs/test/initial-draft",
    )


def test_new_page_turn_receives_approved_source_facts_by_section(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _draft_case(tmp_path, monkeypatch)
    client = _InitialDraftClient(_output(_CLEAN_BODY))

    result = _generate(case, client)

    assert result.status == "created"
    context = json.loads(client.requests[0].untrusted_context)
    assert context["approved_source_facts_by_section"] == [
        {
            "section_id": "new_page_section_01",
            "source_facts": [
                {
                    "source_fact_id": "source_fact_new_page_environment",
                    "summary": _SOURCE_FACT,
                    "evidence_ids": ["ev_new_page_source_fact"],
                    "service_label": "Dokumentacja środowiskowa",
                }
            ],
        }
    ]


def test_new_page_run_record_uses_project_model_policy_for_prompt_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text(
        'model = "gpt-5.6-sol"\nmodel_reasoning_effort = "ultra"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    case = _draft_case(tmp_path, monkeypatch)
    client = _InitialDraftClient(_output(_CLEAN_BODY))

    result = _generate(case, client)

    assert result.status == "created"
    assert result.run_id is not None
    run = next(run for run in case.run_store.list_codex_runs() if run.id == result.run_id)
    assert run.model == "gpt-5.6-terra"
    assert run.model_reasoning_effort == "max"
    assert run.prompt_digest == sha256(client.requests[0].instruction.encode()).hexdigest()
    assert run.prompt_template_id is not None


def test_new_page_finish_is_status_guarded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _draft_case(tmp_path, monkeypatch)

    class ConcurrentTerminalClient:
        def run_structured_turn(
            self, request: CodexAppServerStructuredTurnRequest
        ) -> CodexAppServerTurnResult:
            del request
            started = next(
                run
                for run in case.run_store.list_codex_runs()
                if run.id.startswith("codex_content_new_page_draft_")
            )
            assert transition_initial_draft_run_if_status(
                case.run_store,
                started,
                status="failed",
                error="initial_draft_timeout",
            ) is not None
            return CodexAppServerTurnResult(status="blocked")

    result = _generate(case, ConcurrentTerminalClient())

    assert result.status == "blocked"
    persisted = next(
        run
        for run in case.run_store.list_codex_runs()
        if run.id.startswith("codex_content_new_page_draft_")
    )
    assert persisted.status == "failed"
    assert persisted.error == "initial_draft_timeout"


def test_new_page_turn_request_failure_is_audited_as_failed_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _draft_case(tmp_path, monkeypatch)

    def fail_source_fact_read() -> tuple[ContentSourceFact, ...]:
        raise OSError("source fact store unavailable")

    monkeypatch.setattr(fact_selection, "ekologus_source_facts", fail_source_fact_read)

    result = _generate(case, _InitialDraftClient(_output(_CLEAN_BODY)))

    assert result.status == "failed"
    assert result.run_id is not None
    assert result.runtime.status == "failed"
    assert result.blockers[0].code == "runtime_failed"
    run = next(
        run
        for run in case.run_store.list_codex_runs()
        if run.id == result.run_id
    )
    assert run.status == "failed"
    assert run.error == "runtime_failed"


def test_new_page_runtime_failure_preserves_historical_terminal_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _draft_case(tmp_path, monkeypatch)

    class FailedTurnClient(_InitialDraftClient):
        def run_structured_turn(
            self, request: CodexAppServerStructuredTurnRequest
        ) -> CodexAppServerTurnResult:
            self.requests.append(request)
            return CodexAppServerTurnResult(
                status="failed",
                thread_id="thread-new-page",
                turn_id="turn-new-page",
                event_methods=("turn/started", "turn/failed"),
                item_types=("reasoning",),
            )

    result = _generate(case, FailedTurnClient(_output(_CLEAN_BODY)))

    assert result.status == "failed"
    assert result.runtime.model_dump(mode="json") == {
        "status": "failed",
        "run_id": None,
        "thread_id": "thread-new-page",
        "turn_id": "turn-new-page",
        "event_methods": ["turn/started", "turn/failed"],
        "item_types": ["reasoning"],
        "external_call_attempted": False,
    }
    assert result.blockers[0].model_dump(mode="json") == {
        "code": "runtime_failed",
        "label": "Nie utworzono dokumentu nowej strony",
        "reason": "Codex nie zwrócił poprawnego dokumentu; nic nie zapisano.",
        "next_step": "Codex nie zwrócił poprawnego dokumentu; nic nie zapisano.",
        "source_codes": [],
        "retry_after_seconds": None,
    }
    run = next(item for item in case.run_store.list_codex_runs() if item.id == result.run_id)
    assert run.status == "failed"
    assert run.error == "runtime_failed"


def test_new_page_goal_mismatch_preserves_historical_blocker_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _draft_case(tmp_path, monkeypatch)
    client = _InitialDraftClient(_output(_CLEAN_BODY))
    case = replace(
        case,
        planning_input=case.planning_input.model_copy(update={"goal": "refresh_existing"}),
    )

    result = _generate(case, client)

    assert result.status == "blocked"
    assert result.blockers[0].model_dump(mode="json") == {
        "code": "proposal_mismatch",
        "label": "Nie utworzono dokumentu nowej strony",
        "reason": "Odśwież dokładny plan przed generowaniem.",
        "next_step": "Odśwież dokładny plan przed generowaniem.",
        "source_codes": [],
        "retry_after_seconds": None,
    }
    assert client.requests == []


def test_new_page_generic_section_is_grounded_before_revision_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _draft_case(tmp_path, monkeypatch)

    result = _generate(case, _InitialDraftClient(_output(_GENERIC_BODY)))

    assert result.status == "created"
    assert result.revision is not None
    assert _DOCUMENT_READY_FACT in result.revision.sections[0].body_markdown


def test_new_page_working_note_is_repaired_before_revision_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _draft_case(tmp_path, monkeypatch)
    client = _ReadabilityRepairClient(_output(_WORKING_NOTE_BODY))

    result = _generate(case, client)

    assert result.status == "created"
    assert result.revision is not None
    assert result.revision.sections[0].body_markdown == _CLEAN_BODY
    assert [
        json.loads(request.application_context)["operation"] for request in client.requests
    ] == ["generate_new_page_initial_draft", "repair_initial_draft_readability"]


def test_new_page_clean_grounded_draft_persists_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _draft_case(tmp_path, monkeypatch)
    client = _InitialDraftClient(_output(_CLEAN_BODY))

    result = _generate(case, client)

    assert result.status == "created"
    assert result.revision is not None
    assert result.revision.sections[0].body_markdown == _CLEAN_BODY
    assert len(client.requests) == 1


def test_new_page_readability_failure_keeps_terminal_blocker_and_skips_persistence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _draft_case(tmp_path, monkeypatch)
    client = _ReadabilityRepairClient(
        _output(_WORKING_NOTE_BODY),
        repair_body=_WORKING_NOTE_BODY,
    )

    result = _generate(case, client)

    assert result.status == "blocked"
    assert result.revision is None
    assert result.blockers[0].code == "readability_gate_failed"
    assert "working_note" in result.blockers[0].source_codes
    revision_state = case.workflow_store.load_draft_revision_state(case.foundation.work_item_id)
    assert revision_state.revision_count == 0


def test_new_page_high_risk_promise_is_blocked_without_persisting_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _draft_case(tmp_path, monkeypatch)
    revision_count_before = case.workflow_store.load_draft_revision_state(
        case.foundation.work_item_id
    ).revision_count

    result = _generate(
        case,
        _InitialDraftClient(
            _output(f"{_CLEAN_BODY} Usługa gwarantuje pełną zgodność z prawem.")
        ),
    )

    assert result.status == "blocked"
    assert result.revision is None
    assert result.blockers[0].code == "generated_claim_blocked"
    assert result.blockers[0].source_codes == ["undeclared_high_risk_claim_language"]
    revision_count_after = case.workflow_store.load_draft_revision_state(
        case.foundation.work_item_id
    ).revision_count
    assert revision_count_after == revision_count_before


def test_new_page_empty_regulatory_coverage_skips_assurance_and_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _draft_case(
        tmp_path,
        monkeypatch,
        service_card_id="ekologus_service_environmental_compliance_audit",
    )

    result = _generate(case, _InitialDraftClient(_output(_CLEAN_BODY)))

    assert result.status == "created"
    assert result.revision is not None
    metadata = result.revision.proposal_metadata
    assert metadata is not None
    assert not any("regulatory" in code for code in metadata.quality_finding_codes)
    assert metadata.regulatory_assurance_run_id is None
    assert metadata.regulatory_assurance_criteria_version is None
    matching_assurance_runs = [
        run
        for run in case.run_store.list_codex_runs()
        if run.hook == "content_regulatory_draft_assurance"
        and run.proposal_id == case.proposal.proposal_id
        and run.planning_input_digest == case.planning_input.planning_input_digest
    ]
    assert matching_assurance_runs == []
