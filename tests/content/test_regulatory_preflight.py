from types import SimpleNamespace

import pytest

from wilq.content.drafts import initial_full_draft
from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftRequest
from wilq.content.drafts.regulatory_repair import (
    regulatory_draft_preflight_errors,
)
from wilq.content.knowledge.source_facts import ContentSourceFact
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

_REQUIREMENT_ID = "bdo_definition"
_ASSERTION_ID = "bdo_full_name"
_ASSERTION_TERM = (
    "Baza danych o produktach i opakowaniach oraz o gospodarce odpadami"
)


def _requirement() -> ContentRegulatoryRequirement:
    return ContentRegulatoryRequirement(
        id=_REQUIREMENT_ID,
        label="Pełna nazwa BDO",
        reason="Pełna nazwa musi wynikać ze źródła urzędowego.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id=_ASSERTION_ID,
                label="Pełna nazwa systemu",
                required_any_of=[_ASSERTION_TERM],
            )
        ],
    )


def _section(*, purpose: str, bound: bool = True) -> ContentPlanningSection:
    return ContentPlanningSection(
        section_id="section_bdo_definition",
        heading="Czym jest BDO",
        purpose=purpose,
        reader_question="Co oznacza skrót BDO?",
        inventory_disposition="rewrite",
        regulatory_requirement_ids=[_REQUIREMENT_ID] if bound else [],
    )


def _approved_official_fact(*, extracted_fact: str) -> ContentSourceFact:
    return ContentSourceFact(
        source_id="regulatory_source_fact_bdo_definition",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://bdo.mos.gov.pl/o-systemie-bdo/",
        extracted_fact=extracted_fact,
        scope="claim_policy",
        freshness_date="2026-08-01",
        confidence=1,
        review_status="approved",
        reviewer="ekspert",
        evidence_ids=["ev_bdo_definition"],
        source_connectors=["official_regulatory_review"],
        target_card_id="regulatory_bdo",
        target_card_type="regulatory_source",
        target_card_title="Oficjalny opis systemu BDO",
        official_source=True,
        regulatory_profile_id="bdo",
        regulatory_profile_version="2026-08",
        regulatory_requirement_ids=[_REQUIREMENT_ID],
        applicable_service_card_ids=["ekologus_service_bdo_reporting"],
    )


def _preflight_input(
    requirements: list[ContentRegulatoryRequirement],
    sections: list[ContentPlanningSection],
    facts: list[ContentSourceFact],
) -> tuple[ContentPlanningInput, ContentPlanningProposal]:
    planning_input = ContentPlanningInput.model_construct(
        regulatory_coverage=(
            ContentRegulatoryCoverage()
            if not requirements
            else ContentRegulatoryCoverage(
                profile_id="bdo",
                profile_version="2026-08",
                requirements=requirements,
                source_facts=facts,
            )
        )
    )
    proposal = ContentPlanningProposal.model_construct(sections=sections)
    return planning_input, proposal


def test_preflight_passes_when_plan_is_complete_and_groundable() -> None:
    planning_input, proposal = _preflight_input(
        [_requirement()],
        [_section(purpose=f"Wyjaśnij pełną nazwę: {_ASSERTION_TERM}.")],
        [_approved_official_fact(extracted_fact=_ASSERTION_TERM)],
    )

    assert regulatory_draft_preflight_errors(planning_input, proposal) == []


def test_preflight_blocks_unbound_requirement() -> None:
    requirement = ContentRegulatoryRequirement(
        id=_REQUIREMENT_ID,
        label="Definicja BDO",
        reason="Wymaga osobnej sekcji.",
    )
    planning_input, proposal = _preflight_input(
        [requirement],
        [_section(purpose="Wyjaśnij definicję BDO.", bound=False)],
        [],
    )

    assert regulatory_draft_preflight_errors(planning_input, proposal) == [
        f"regulatory_preflight:missing_section_binding:{_REQUIREMENT_ID}"
    ]


def test_preflight_blocks_ungroundable_assertion() -> None:
    planning_input, proposal = _preflight_input(
        [_requirement()],
        [_section(purpose=f"Wyjaśnij pełną nazwę: {_ASSERTION_TERM}.")],
        [
            _approved_official_fact(
                extracted_fact="System BDO wspiera elektroniczną obsługę obowiązków."
            )
        ],
    )

    assert regulatory_draft_preflight_errors(planning_input, proposal) == [
        (
            "regulatory_preflight:ungroundable_assertion:"
            f"{_REQUIREMENT_ID}:{_ASSERTION_ID}"
        )
    ]


def test_preflight_blocks_legacy_plan_without_assertion_terms() -> None:
    planning_input, proposal = _preflight_input(
        [_requirement()],
        [_section(purpose="Wyjaśnij definicję i zastosowanie systemu BDO.")],
        [_approved_official_fact(extracted_fact=_ASSERTION_TERM)],
    )

    assert regulatory_draft_preflight_errors(planning_input, proposal) == [
        (
            "regulatory_preflight:missing_plan_assertion:"
            f"{_REQUIREMENT_ID}:{_ASSERTION_ID}"
        )
    ]


def test_preflight_is_silent_without_regulatory_requirements() -> None:
    planning_input, proposal = _preflight_input(
        [],
        [_section(purpose="Wyjaśnij definicję BDO.", bound=False)],
        [],
    )

    assert regulatory_draft_preflight_errors(planning_input, proposal) == []


def test_generate_initial_full_draft_blocks_before_any_client_call_on_preflight_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planning_input, proposal = _preflight_input(
        [_requirement()],
        [_section(purpose=f"Wyjaśnij pełną nazwę: {_ASSERTION_TERM}.")],
        [
            _approved_official_fact(
                extracted_fact="System BDO wspiera elektroniczną obsługę obowiązków."
            )
        ],
    )
    planning_input = planning_input.model_copy(
        update={
            "work_item_id": "content_work_item_regulatory_preflight",
            "planning_input_digest": "a" * 64,
            "confirmed_service_card_id": "ekologus_service_bdo_reporting",
        }
    )
    proposal = proposal.model_copy(
        update={
            "work_item_id": planning_input.work_item_id,
            "proposal_id": "content_planning_proposal_regulatory_preflight",
            "planning_digest": "b" * 64,
            "planning_input_digest": planning_input.planning_input_digest,
            "generation_status": "codex_generated",
            "service_card_id": planning_input.confirmed_service_card_id,
        }
    )
    snapshot = SimpleNamespace(
        planning_workspace=SimpleNamespace(
            section_map_current=True,
            proposal=proposal,
        ),
        revision_workspace=SimpleNamespace(
            latest_revision=None,
            context_current=True,
        ),
        structured_generation=SimpleNamespace(
            structured_generation_result=SimpleNamespace(
                contract=object(),
                blockers=[],
            )
        ),
        preflight=SimpleNamespace(item=SimpleNamespace(id=planning_input.work_item_id)),
    )

    class UnexpectedClient:
        called = False

        def run_structured_turn(self, _request: object) -> None:
            self.called = True
            raise AssertionError("model must not be called")

    client = UnexpectedClient()

    monkeypatch.setattr(
        initial_full_draft,
        "_current_planning_input",
        lambda *_args: SimpleNamespace(planning_input=planning_input, blockers=[]),
    )

    def must_not_start(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("draft run must not be started")

    monkeypatch.setattr(initial_full_draft, "start_initial_draft_run", must_not_start)

    response = initial_full_draft.generate_initial_full_draft(
        snapshot=snapshot,
        request=ContentInitialDraftRequest(
            expected_proposal_id=proposal.proposal_id,
            expected_planning_digest=proposal.planning_digest,
            expected_planning_input_digest=proposal.planning_input_digest,
            requested_by="wilku",
        ),
        client=client,
        workflow_store=SimpleNamespace(),
        run_store=SimpleNamespace(),
        context_digest="c" * 64,
    )

    assert response.status == "blocked"
    assert response.runtime.status == "not_started"
    assert response.blockers[0].code == "regulatory_preflight_failed"
    assert response.blockers[0].label == "Plan regulacyjny nie spełnia warunków szkicu"
    assert response.blockers[0].source_codes == [
        (
            "regulatory_preflight:ungroundable_assertion:"
            f"{_REQUIREMENT_ID}:{_ASSERTION_ID}"
        )
    ]
    assert client.called is False
