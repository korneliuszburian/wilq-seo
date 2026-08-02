from __future__ import annotations

import json
from types import SimpleNamespace

from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_turn_request
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningInventory
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryDocumentAssertion,
    ContentRegulatoryRequirement,
)
from wilq.content.workflow.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.planning import ContentPlanningProposal


def test_initial_draft_turn_exposes_server_owned_regulatory_assertions() -> None:
    planning_input = ContentPlanningInput.model_construct(
        work_item_id="content_work_item_regulated",
        planning_input_digest="a" * 64,
        confirmed_service_card_id="service_regulated",
        inventory=ContentPlanningInventory(status="available"),
        query_portfolio=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Brak exact zapytań.",
        ),
        measurement_observation_rule="Porównaj zamknięte okresy.",
        measurement_success_claim_rule="Nie claimuj bez dowodu.",
        source_assessments=[],
        regulatory_coverage=ContentRegulatoryCoverage(
            profile_id="regulated",
            profile_version="2026-08",
            requirements=[
                ContentRegulatoryRequirement(
                    id="access",
                    label="dostęp do konta",
                    reason="Wymaga źródła urzędowego.",
                    document_assertions=[
                        ContentRegulatoryDocumentAssertion(
                            id="roles",
                            label="role lub uprawnienia",
                            required_any_of=["rola", "uprawnien"],
                        )
                    ],
                )
            ],
        ),
    )
    proposal = ContentPlanningProposal.model_construct(
        proposal_id="proposal-regulated",
        planning_digest="b" * 64,
        sections=[],
        faq=[],
        cta_blocks=[],
        internal_links=[],
    )
    generation_contract = SimpleNamespace(
        model_input=SimpleNamespace(model_dump=lambda mode: {})
    )

    request = initial_full_draft_turn_request(
        planning_input=planning_input,
        proposal=proposal,
        generation_contract=generation_contract,
    )

    assert json.loads(request.application_context)["regulatory_document_assertions"] == [
        {
            "requirement_id": "access",
            "assertion_id": "roles",
            "label": "role lub uprawnienia",
            "required_any_of": ["rola", "uprawnien"],
        }
    ]
