from __future__ import annotations

import json
from types import SimpleNamespace
from typing import cast

import pytest

from wilq.content.drafts import (
    codex_section_proposal_turn,
    initial_full_draft_turn,
    regulatory_draft_repair,
)
from wilq.content.drafts.structured_generation import StructuredDraftGenerationContract
from wilq.content.knowledge.source_facts import ContentSourceFact, SourceFactReviewStatus
from wilq.content.planning import generated_proposal_turn
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningInventory
from wilq.content.regulatory import turn_context as regulatory_turn_context
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryDocumentAssertion,
    ContentRegulatoryRequirement,
)
from wilq.content.regulatory.turn_context import (
    approved_regulatory_source_facts,
    regulatory_document_assertion_context,
    regulatory_facts_for_requirements,
)
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import ContentPlanningProposal


def test_planning_and_draft_turns_share_the_assertion_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requirement = ContentRegulatoryRequirement(
        id="access",
        label="Dostęp",
        reason="Wymaga źródła urzędowego.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id="roles",
                label="Role i uprawnienia",
                required_any_of=["rola", "uprawnien"],
            )
        ],
    )
    planning_input = _planning_input(ContentRegulatoryCoverage(requirements=[requirement]))
    proposal = ContentPlanningProposal.model_construct(
        proposal_id="proposal-regulated",
        planning_digest="b" * 64,
        service_card_id="service-regulated",
        sections=[],
        faq=[],
        cta_blocks=[],
        internal_links=[],
    )
    generation_contract = cast(
        StructuredDraftGenerationContract,
        SimpleNamespace(model_input=SimpleNamespace(model_dump=lambda *, mode: {})),
    )
    expected = regulatory_document_assertion_context(planning_input)
    projected_inputs: list[ContentPlanningInput] = []

    def shared_projection(value: ContentPlanningInput) -> list[dict[str, object]]:
        projected_inputs.append(value)
        return regulatory_document_assertion_context(value)

    monkeypatch.setattr(
        regulatory_turn_context,
        "regulatory_document_assertion_context",
        shared_projection,
    )

    planning_turn = generated_proposal_turn.content_planning_turn_request(
        planning_input,
        operator_hint="",
    )
    draft_turn = initial_full_draft_turn.initial_full_draft_turn_request(
        planning_input=planning_input,
        proposal=proposal,
        generation_contract=generation_contract,
    )

    planning_assertions = json.loads(planning_turn.application_context)[
        "regulatory_document_assertions"
    ]
    draft_assertions = json.loads(draft_turn.application_context)[
        "regulatory_document_assertions"
    ]
    assert planning_assertions == expected
    assert draft_assertions == expected
    assert projected_inputs == [planning_input, planning_input]


def test_approved_regulatory_facts_filter_is_shared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    approved = _fact("approved", ["access"])
    review_required = _fact("review-required", ["access"], review_status="review_required")
    unofficial = _fact("unofficial", [], official_source=False)
    other = _fact("other", ["reporting"])
    planning_input = _planning_input(
        ContentRegulatoryCoverage.model_construct(
            source_facts=[approved, review_required, unofficial, other],
        )
    )

    assert regulatory_facts_for_requirements(planning_input, {"access"}) == [
        approved,
        review_required,
    ]
    assert approved_regulatory_source_facts(planning_input) == [approved, other]
    assert approved_regulatory_source_facts(planning_input, set()) == []
    assert approved_regulatory_source_facts(planning_input, {"access"}) == [approved]

    selected_requirement_ids: list[set[str] | None] = []

    def shared_filter(
        value: ContentPlanningInput,
        requirement_ids: set[str] | None = None,
    ) -> list[ContentSourceFact]:
        selected_requirement_ids.append(requirement_ids)
        return approved_regulatory_source_facts(value, requirement_ids)

    monkeypatch.setattr(
        regulatory_turn_context,
        "approved_regulatory_source_facts",
        shared_filter,
    )
    assert regulatory_draft_repair._approved_facts_for_requirement(
        planning_input,
        requirement_id="access",
        assertion_terms=None,
    ) == ["Fakt approved."]
    assert (
        regulatory_draft_repair._approved_facts_for_requirement(
            planning_input,
            requirement_id="access",
            assertion_terms=["nieobecny termin"],
        )
        == []
    )
    selected_facts = codex_section_proposal_turn._selected_regulatory_facts(
        planning_input,
        _snapshot(
            [SimpleNamespace(heading="Dostęp", regulatory_requirement_ids=["access"])]
        ),
        ["Dostęp"],
    )
    assert [fact["source_fact_id"] for fact in selected_facts] == ["approved"]
    assert selected_requirement_ids == [{"access"}, {"access"}, {"access"}]


def test_section_bound_facts_variant_preserved() -> None:
    access_requirement = ContentRegulatoryRequirement(
        id="access",
        label="Dostęp",
        reason="Wymaga źródła urzędowego.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id="roles",
                label="Role",
                required_any_of=["rola"],
            )
        ],
    )
    reporting_requirement = ContentRegulatoryRequirement(
        id="reporting",
        label="Raportowanie",
        reason="Wymaga źródła urzędowego.",
    )
    planning_input = _planning_input(
        ContentRegulatoryCoverage.model_construct(
            requirements=[access_requirement, reporting_requirement],
            source_facts=[
                _fact("access", ["access"]),
                _fact("shared", ["reporting", "access"]),
                _fact("reporting", ["reporting"]),
            ],
        )
    )
    sections = [
        SimpleNamespace(
            section_id="section-access",
            heading="Dostęp",
            regulatory_requirement_ids=["access"],
        ),
        SimpleNamespace(
            section_id="section-reporting",
            heading="Raportowanie",
            regulatory_requirement_ids=["reporting"],
        ),
    ]
    snapshot = _snapshot(sections)

    assert codex_section_proposal_turn._selected_regulatory_facts(
        planning_input,
        snapshot,
        ["Dostęp"],
    ) == [
        {
            "source_fact_id": "access",
            "summary": "Fakt access.",
            "evidence_ids": ["ev-access"],
            "requirement_ids": ["access"],
        },
        {
            "source_fact_id": "shared",
            "summary": "Fakt shared.",
            "evidence_ids": ["ev-shared"],
            "requirement_ids": ["reporting", "access"],
        },
    ]
    assert codex_section_proposal_turn._selected_regulatory_requirements(
        planning_input,
        snapshot,
        ["Dostęp"],
    ) == [
        {
            "section_id": "section-access",
            "heading": "Dostęp",
            "requirements": [
                {
                    "requirement_id": "access",
                    "label": "Dostęp",
                    "document_assertions": [
                        {"id": "roles", "label": "Role", "required_any_of": ["rola"]}
                    ],
                }
            ],
        }
    ]


def _planning_input(coverage: ContentRegulatoryCoverage) -> ContentPlanningInput:
    return ContentPlanningInput.model_construct(
        work_item_id="content-work-item-regulated",
        planning_input_digest="a" * 64,
        confirmed_service_card_id="service-regulated",
        inventory=ContentPlanningInventory(status="available"),
        query_portfolio=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Brak exact zapytań.",
        ),
        source_assessments=[],
        measurement_observation_rule="Porównaj zamknięte okresy.",
        measurement_success_claim_rule="Nie claimuj bez dowodu.",
        regulatory_coverage=coverage,
    )


def _snapshot(sections: list[SimpleNamespace]) -> ContentWorkItemWorkflowSnapshotResponse:
    return cast(
        ContentWorkItemWorkflowSnapshotResponse,
        SimpleNamespace(
            planning_workspace=SimpleNamespace(
                proposal=SimpleNamespace(sections=sections)
            )
        ),
    )


def _fact(
    source_id: str,
    requirement_ids: list[str],
    *,
    review_status: SourceFactReviewStatus = "approved",
    official_source: bool = True,
) -> ContentSourceFact:
    return ContentSourceFact.model_construct(
        source_id=source_id,
        extracted_fact=f"Fakt {source_id}.",
        evidence_ids=[f"ev-{source_id}"],
        review_status=review_status,
        official_source=official_source,
        regulatory_requirement_ids=requirement_ids,
    )
