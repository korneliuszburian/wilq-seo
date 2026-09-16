from __future__ import annotations

import json
from threading import Lock
from types import SimpleNamespace
from typing import Any

from wilq.codex.app_server import (
    CodexAppServerStructuredTurnRequest,
    CodexAppServerTurnResult,
)
from wilq.content.drafts import draft_alteration, draft_assurance, draft_assurance_runtime
from wilq.content.drafts.codex_runtime import ContentCodexRuntimeTrace
from wilq.content.drafts.draft_assurance import (
    ContentDraftAssuranceModelOutput,
    draft_assurance_fingerprint,
)
from wilq.content.drafts.draft_plan_preparation import PreparedDraftPlan, prepare_draft_plan
from wilq.content.drafts.initial_draft_pipeline import (
    InitialDraftPipelineInputs,
    InitialDraftRunMetadata,
    generate_initial_draft,
)
from wilq.content.drafts.initial_draft_readability import readability_issues_for_output
from wilq.content.drafts.initial_draft_runtime import InitialDraftFailureCopy, InitialDraftTurnGoal
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
    ContentInitialDraftSectionOutput,
)
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningSourceFact
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryDocumentAssertion,
    ContentRegulatoryProfile,
    ContentRegulatoryRequirement,
)
from wilq.content.workflow.decisions.planning import ContentPlanningProposal, ContentPlanningSection
from wilq.content.workflow.documents.revisions import ContentDraftRevisionPageAssets
from wilq.schemas import CodexRun

_REPAIR_OPERATION = "repair_initial_draft_readability"
_CRITIC_OPERATION = "assure_regulatory_content_draft"


class _RecordingModel:
    """Scripted model boundary that preserves every request it receives."""

    def __init__(
        self,
        *,
        readability_repair_body: str | None = None,
        critic_passes_immediately: bool = False,
    ) -> None:
        self.requests: list[CodexAppServerStructuredTurnRequest] = []
        self.operations: list[str] = []
        self.operations_after_pass: list[str] = []
        self._critic_turns = 0
        self._has_returned_pass = False
        self._readability_repairs = 0
        self._readability_repair_body = readability_repair_body
        self._critic_passes_immediately = critic_passes_immediately
        self._lock = Lock()

    def run_structured_turn(
        self,
        request: CodexAppServerStructuredTurnRequest,
    ) -> CodexAppServerTurnResult:
        application_context = json.loads(request.application_context)
        operation = application_context["operation"]
        with self._lock:
            if self._has_returned_pass:
                self.operations_after_pass.append(operation)
            self.requests.append(request)
            self.operations.append(operation)

        if operation == _REPAIR_OPERATION:
            with self._lock:
                self._readability_repairs += 1
                repaired_body = self._readability_repair_body or (
                    "Warunek alfa obowiązuje wyłącznie w przypisanym zakresie i wymaga "
                    "oceny konkretnego przypadku w wersji pierwszej."
                    if self._readability_repairs == 1
                    else (
                        "Warunek alfa obowiązuje wyłącznie w przypisanym zakresie i wymaga "
                        "oceny konkretnego przypadku w wersji końcowej."
                    )
                )
            return CodexAppServerTurnResult(
                status="completed",
                output_text=json.dumps(
                    {
                        "sections": [
                            {
                                "section_id": "section_alpha",
                                "mode": "replace",
                                "body_markdown": repaired_body,
                            }
                        ],
                        "publish_ready": False,
                    },
                    ensure_ascii=False,
                ),
                turn_id="readability-repair",
            )
        if operation == "repair_initial_draft_regulatory_assertions":
            return CodexAppServerTurnResult(
                status="completed",
                output_text=json.dumps(
                    {
                        "sections": [
                            {
                                "section_id": "section_alpha",
                                "mode": "replace",
                                "body_markdown": (
                                    "Warunek alfa obowiązuje wyłącznie w przypisanym zakresie. "
                                    "Ta informacja wymaga weryfikacji przez człowieka przed "
                                    "przekazaniem jej czytelnikowi jako gotowej odpowiedzi."
                                ),
                            }
                        ],
                        "publish_ready": False,
                    },
                    ensure_ascii=False,
                ),
                turn_id="regulatory-repair",
            )
        if operation == _CRITIC_OPERATION:
            constraint_id = application_context["constraint_ids_in_order"][0]
            candidate = json.loads(request.untrusted_context)["candidate_document"]
            section_id = candidate["sections"][0]["section_id"]
            with self._lock:
                self._critic_turns += 1
                critic_turn = self._critic_turns
            passed = self._critic_passes_immediately or critic_turn > 1
            check = {
                "constraint_id": constraint_id,
                "status": "pass" if passed else "fail",
                "reason_code": "supported" if passed else "missing_scope",
                "reason": (
                    "Kandydat zachowuje przypisany zakres."
                    if passed
                    else "Kandydat wymaga uzupełnienia przypisanego zakresu."
                ),
                "document_section_id": section_id,
                "evidence_ids": [],
            }
            result = CodexAppServerTurnResult(
                status="completed",
                output_text=ContentDraftAssuranceModelOutput(
                    checks=[check]
                ).model_dump_json(),
                turn_id="final-critic",
            )
            if passed:
                with self._lock:
                    self._has_returned_pass = True
            return result
        raise AssertionError(f"Unexpected model operation: {operation}")


class _RunStore:
    def __init__(self) -> None:
        self.saved: list[CodexRun] = []

    def save_codex_run(self, run: CodexRun) -> CodexRun:
        self.saved.append(run)
        return run


def _profile() -> ContentRegulatoryProfile:
    requirement = ContentRegulatoryRequirement(
        id="requirement_alpha",
        label="warunek alfa",
        reason="Zakres alfa musi pozostać dokładny.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id="alpha_scope",
                label="zakres alfa",
                required_any_of=["Warunek alfa"],
            )
        ],
    )
    return ContentRegulatoryProfile(
        id="synthetic_regulated_service",
        version="synthetic-v1",
        service_card_ids=["service_synthetic"],
        official_source_hosts=["example.invalid"],
        max_source_age_days=30,
        requirements=[requirement],
    )


def _official_fact(
    *,
    source_id: str,
    text: str,
) -> ContentSourceFact:
    return ContentSourceFact(
        source_id=source_id,
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path=f"https://example.invalid/{source_id}",
        extracted_fact=text,
        scope="claim_policy",
        freshness_date="2026-01-01",
        confidence=1,
        review_status="approved",
        reviewer="reviewer",
        evidence_ids=[f"evidence_{source_id}"],
        source_connectors=["synthetic_source"],
        target_card_id="synthetic_regulated_service",
        target_card_type="regulatory_source",
        target_card_title=source_id,
        official_source=True,
        regulatory_profile_id="synthetic_regulated_service",
        regulatory_profile_version="synthetic-v1",
        regulatory_requirement_ids=["requirement_alpha"],
        applicable_service_card_ids=["service_synthetic"],
    )


def _compiled_case() -> tuple[
    ContentRegulatoryProfile,
    ContentPlanningInput,
    ContentPlanningProposal,
    PreparedDraftPlan,
    ContentInitialDraftModelOutput,
]:
    profile = _profile()
    assigned_fact = _official_fact(
        source_id="official_alpha",
        text="Warunek alfa dotyczy tylko przypisanego przypadku.",
    )
    broader_fact = _official_fact(
        source_id="official_broader_inventory",
        text="Szerszy fakt inventory nie należy do sekcji alfa.",
    )
    planning_input = ContentPlanningInput.model_construct(
        work_item_id="work_item_synthetic",
        planning_input_digest="a" * 64,
        confirmed_service_card_id="service_synthetic",
        evidence_ids=["evidence_alpha", "evidence_beta", "evidence_broader"],
        regulatory_coverage=ContentRegulatoryCoverage(
            applicability_status="required",
            profile_id=profile.id,
            profile_version=profile.version,
            requirements=profile.requirements,
            source_fact_ids=[assigned_fact.source_id, broader_fact.source_id],
            evidence_ids=["evidence_official_alpha", "evidence_official_broader_inventory"],
            source_facts=[assigned_fact, broader_fact],
        ),
        source_facts=[
            ContentPlanningSourceFact(
                fact_id="assignment_alpha",
                summary="Warunek alfa dotyczy tylko przypisanego przypadku.",
                source_connector="synthetic_source",
                evidence_ids=["evidence_alpha"],
                source_fact_ids=[assigned_fact.source_id],
                regulatory_requirement_ids=["requirement_alpha"],
            ),
            ContentPlanningSourceFact(
                fact_id="assignment_beta",
                summary="Fakt beta należy wyłącznie do sekcji beta.",
                source_connector="synthetic_source",
                evidence_ids=["evidence_beta"],
                source_fact_ids=["official_beta"],
            ),
            ContentPlanningSourceFact(
                fact_id="broader_inventory_fact",
                summary="Szerszy fakt inventory nie należy do sekcji alfa.",
                source_connector="synthetic_source",
                evidence_ids=["evidence_broader"],
                source_fact_ids=[broader_fact.source_id],
                regulatory_requirement_ids=["requirement_alpha"],
            ),
        ],
    )
    proposal = ContentPlanningProposal.model_construct(
        work_item_id=planning_input.work_item_id,
        proposal_id="proposal_synthetic",
        planning_digest="b" * 64,
        planning_input_digest=planning_input.planning_input_digest,
        sections=[
            ContentPlanningSection(
                section_id="section_alpha",
                heading="Zakres alfa",
                purpose="Wyjaśnij tylko warunek alfa.",
                evidence_ids=["evidence_alpha"],
                regulatory_requirement_ids=["requirement_alpha"],
            ),
            ContentPlanningSection(
                section_id="section_beta",
                heading="Zakres beta",
                purpose="Wyjaśnij tylko fakt beta.",
                evidence_ids=["evidence_beta"],
            ),
        ],
    )
    prepared_plan = prepare_draft_plan(proposal, planning_input)
    assert isinstance(prepared_plan, PreparedDraftPlan)
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Syntetyczny przewodnik",
            meta_title="Syntetyczny przewodnik zakresów",
            meta_description="Krótki opis dwóch niezależnych zakresów.",
            h1="Zakresy syntetyczne",
            lead="Dokument rozróżnia przypisane informacje.",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="section_alpha",
                heading="Zakres alfa",
                body_markdown=(
                    "Warunek alfa. Ta informacja wymaga weryfikacji przez człowieka "
                    "przed przekazaniem jej czytelnikowi jako gotowej odpowiedzi."
                ),
            ),
            ContentInitialDraftSectionOutput(
                section_id="section_beta",
                heading="Zakres beta",
                body_markdown=(
                    "Fakt beta pozostaje wyłącznie w swojej sekcji i nie rozszerza "
                    "warunku alfa."
                ),
            ),
        ],
    )
    return profile, planning_input, proposal, prepared_plan, output


def _install_regulatory_profile(monkeypatch, profile: ContentRegulatoryProfile) -> None:
    monkeypatch.setattr(
        draft_alteration,
        "regulatory_draft_assurance_profile",
        lambda _planning_input: profile,
    )
    monkeypatch.setattr(
        draft_assurance_runtime,
        "regulatory_draft_assurance_profile",
        lambda _planning_input: profile,
    )


def _finalization_inputs(
    planning_input: ContentPlanningInput,
    proposal: ContentPlanningProposal,
    prepared_plan: PreparedDraftPlan,
    initial_output: ContentInitialDraftModelOutput,
    persisted: list[dict[str, Any]],
) -> InitialDraftPipelineInputs:
    return InitialDraftPipelineInputs(
        planning_input=planning_input,
        proposal=proposal,
        preflight_response=None,
        turn_request=lambda: CodexAppServerStructuredTurnRequest(
            instruction="synthetic writer",
            application_context="{}",
            untrusted_context="{}",
            output_schema={},
        ),
        turn_goal=InitialDraftTurnGoal(
            runtime_failure=InitialDraftFailureCopy(
                label="Nie udało się utworzyć szkicu",
                reason="Test runtime failure.",
                next_step="Nie uruchamiaj zapisu.",
            ),
            invalid_structured_output=InitialDraftFailureCopy(
                label="Niepoprawny szkic",
                reason="Test schema failure.",
                next_step="Nie uruchamiaj zapisu.",
            ),
            include_runtime_source_codes=False,
        ),
        run=InitialDraftRunMetadata(
            work_item_id=planning_input.work_item_id,
            evidence_ids=planning_input.evidence_ids,
            source_material_ids=[],
            proposal_id="proposal_synthetic",
            planning_digest=proposal.planning_digest,
            planning_input_digest=planning_input.planning_input_digest,
            context_digest=None,
            endpoint_path=None,
        ),
        output_blocker=lambda _candidate: None,
        response=lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("Finalization unexpectedly returned a blocker.")
        ),
        persist=lambda **kwargs: persisted.append(kwargs) or SimpleNamespace(status="created"),
        prepared_plan=prepared_plan,
        start_run=lambda *_args, **_kwargs: CodexRun.model_construct(
            id="initial-run", status="started"
        ),
        terminal_hook=lambda *_args, **_kwargs: None,
        execute_turn=lambda **_kwargs: (
            initial_output,
            ContentCodexRuntimeTrace(status="completed", turn_id="writer"),
        ),
    )


def _request_contexts(
    model: _RecordingModel,
    operation: str,
) -> list[dict[str, Any]]:
    return [
        json.loads(request.untrusted_context)
        for request in model.requests
        if json.loads(request.application_context)["operation"] == operation
    ]


def _assert_finalization_operations(response: Any, model: _RecordingModel) -> None:
    assert response.status == "created"
    assert model.operations == [
        _REPAIR_OPERATION,
        _CRITIC_OPERATION,
        "repair_initial_draft_regulatory_assertions",
        _REPAIR_OPERATION,
        _CRITIC_OPERATION,
    ]
    assert model.operations_after_pass == []


def _assert_repair_contexts_are_exact(model: _RecordingModel) -> None:
    repair_contexts = _request_contexts(model, _REPAIR_OPERATION)
    expected_requirements = [
        {
            "id": "requirement_alpha",
            "label": "warunek alfa",
            "document_assertions": [
                {
                    "id": "alpha_scope",
                    "label": "zakres alfa",
                    "required_any_of": ["Warunek alfa"],
                }
            ],
        }
    ]

    assert len(repair_contexts) == 2
    assert all(
        [
            assignment["immutable_section"]["section_id"]
            for assignment in context["prepared_plan_assignments"]
        ]
        == ["section_alpha"]
        for context in repair_contexts
    )
    assert all(
        context["prepared_plan_assignments"][0]["assigned_source_facts"][0][
            "source_fact_ids"
        ]
        == ["official_alpha"]
        for context in repair_contexts
    )
    assert all(
        context["prepared_plan_assignments"][0]["regulatory_requirements"]
        == expected_requirements
        for context in repair_contexts
    )
    assert all(
        "section_beta" not in json.dumps(context, ensure_ascii=False)
        for context in repair_contexts
    )
    assert all(
        "official_broader_inventory" not in json.dumps(context, ensure_ascii=False)
        for context in repair_contexts
    )


def _assert_critic_contexts_are_exact(model: _RecordingModel) -> None:
    critic_contexts = _request_contexts(model, _CRITIC_OPERATION)

    assert all(
        [fact["source_fact_ids"] for fact in context["official_source_facts"]]
        == [["official_alpha"]]
        for context in critic_contexts
    )
    assert all(
        [fact["assigned_document_section_id"] for fact in context["official_source_facts"]]
        == ["section_alpha"]
        for context in critic_contexts
    )
    assert all(
        "official_broader_inventory" not in json.dumps(context, ensure_ascii=False)
        for context in critic_contexts
    )


def _assert_persisted_finalization(
    persisted: list[dict[str, Any]],
    initial_output: ContentInitialDraftModelOutput,
    prepared_plan: PreparedDraftPlan,
    profile: ContentRegulatoryProfile,
    model: _RecordingModel,
) -> None:
    assert len(persisted) == 1
    persisted_output = persisted[0]["output"]
    assurance = persisted[0]["regulatory_assurance"]
    assert isinstance(persisted_output, ContentInitialDraftModelOutput)
    assert persisted_output.sections[0].body_markdown == (
        "Warunek alfa obowiązuje wyłącznie w przypisanym zakresie i wymaga oceny "
        "konkretnego przypadku w wersji końcowej."
    )
    assert persisted_output.sections[1] == initial_output.sections[1]
    critic_input_digest_from_requests = getattr(
        draft_assurance,
        "draft_assurance_critic_input_digest_from_requests",
        None,
    )
    assert callable(critic_input_digest_from_requests)
    assert assurance.critic_input_digest == critic_input_digest_from_requests([model.requests[-1]])
    assert assurance.assurance_fingerprint == draft_assurance_fingerprint(
        output=persisted_output,
        prepared_plan=prepared_plan,
        profile_id=profile.id,
        profile_version=profile.version,
        critic_input_digest=assurance.critic_input_digest,
    )


def test_regulated_finalization_repairs_exact_scope_before_its_only_passing_critic(
    monkeypatch,
) -> None:
    profile, planning_input, proposal, prepared_plan, initial_output = _compiled_case()
    model = _RecordingModel()
    run_store = _RunStore()
    persisted: list[dict[str, Any]] = []
    _install_regulatory_profile(monkeypatch, profile)

    response = generate_initial_draft(
        inputs=_finalization_inputs(
            planning_input,
            proposal,
            prepared_plan,
            initial_output,
            persisted,
        ),
        client=model,
        run_store=run_store,
    )

    _assert_finalization_operations(response, model)
    _assert_repair_contexts_are_exact(model)
    _assert_critic_contexts_are_exact(model)
    _assert_persisted_finalization(
        persisted,
        initial_output,
        prepared_plan,
        profile,
        model,
    )


def test_regulated_finalization_persists_after_only_residual_long_sentence(
    monkeypatch,
) -> None:
    profile, planning_input, proposal, prepared_plan, initial_output = _compiled_case()
    residual_long_sentence = " ".join(
        ["Warunek", "alfa", *[f"wyraz{index}" for index in range(3, 26)]]
    ) + "."
    initial_output = initial_output.model_copy(
        update={
            "sections": [
                initial_output.sections[0].model_copy(
                    update={"body_markdown": residual_long_sentence}
                ),
                initial_output.sections[1],
            ]
        }
    )
    assert [
        (code, section_id) for code, section_id, _ in readability_issues_for_output(initial_output)
    ] == [("long_sentence", "section_alpha")]
    model = _RecordingModel(
        readability_repair_body=residual_long_sentence,
        critic_passes_immediately=True,
    )
    run_store = _RunStore()
    persisted: list[dict[str, Any]] = []
    _install_regulatory_profile(monkeypatch, profile)

    response = generate_initial_draft(
        inputs=_finalization_inputs(
            planning_input,
            proposal,
            prepared_plan,
            initial_output,
            persisted,
        ),
        client=model,
        run_store=run_store,
    )

    assert response.status == "created"
    assert model.operations == [_REPAIR_OPERATION, _CRITIC_OPERATION]
    repair_contexts = _request_contexts(model, _REPAIR_OPERATION)
    assert [
        (issue["code"], issue["affected_section_id"])
        for issue in repair_contexts[0]["issues"]
    ] == [("long_sentence", "section_alpha")]
    assert len(_request_contexts(model, _CRITIC_OPERATION)) == 1
    assert len(persisted) == 1
    assert persisted[0]["output"].sections[0].body_markdown == residual_long_sentence
    assert persisted[0]["regulatory_assurance"].status == "passed"
