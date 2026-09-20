from __future__ import annotations

import json

from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.generated_proposal_turn import content_planning_turn_request
from wilq.content.planning.input_sources import ContentPlanningInventory
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryDocumentAssertion,
    ContentRegulatoryRequirement,
)
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence


def test_planning_turn_keeps_document_assertions_out_of_claim_free_directives() -> None:
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
                    id="reporting",
                    label="termin sprawozdania",
                    reason="Wymaga źródła urzędowego.",
                    document_assertions=[
                        ContentRegulatoryDocumentAssertion(
                            id="deadline",
                            label="termin 15 marca",
                            required_any_of=["15 marca"],
                        )
                    ],
                )
            ],
        ),
    )

    request = content_planning_turn_request(planning_input, operator_hint="")

    assert "regulatory_document_assertions" not in json.loads(request.application_context)
