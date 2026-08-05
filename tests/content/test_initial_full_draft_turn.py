from __future__ import annotations

import json
from types import SimpleNamespace

from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_turn_request
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningInventory
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryDocumentAssertion,
    ContentRegulatoryRequirement,
)
from wilq.content.workflow.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.planning import ContentPlanningProposal


def _approved_access_fact() -> ContentSourceFact:
    return ContentSourceFact(
        source_id="official_access_fact",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://example.gov.pl/bdo",
        extracted_fact="Użytkownik główny może nadawać uprawnienia w systemie.",
        scope="claim_policy",
        freshness_date="2026-08-01",
        confidence=1,
        review_status="approved",
        reviewer="ekspert",
        evidence_ids=["ev_access"],
        source_connectors=["official_regulatory_review"],
        target_card_id="regulated_service",
        target_card_type="regulatory_source",
        target_card_title="Dostęp do systemu",
        official_source=True,
        regulatory_profile_id="regulated",
        regulatory_profile_version="2026-08",
        regulatory_requirement_ids=["access"],
        applicable_service_card_ids=["service_regulated"],
    )


def test_initial_draft_turn_exposes_server_owned_regulatory_assertions() -> None:
    fact = _approved_access_fact()
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
            source_facts=[fact],
        ),
    )
    proposal = ContentPlanningProposal.model_construct(
        proposal_id="proposal-regulated",
        planning_digest="b" * 64,
        sections=[
            SimpleNamespace(
                section_id="section_access",
                heading="Dostęp",
                inventory_disposition="rewrite",
                regulatory_requirement_ids=["access"],
            )
        ],
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
    compact_proposal = json.loads(request.untrusted_context)["approved_planning_proposal"]
    assert compact_proposal["planning_digest"] == "b" * 64
    assert "page_assets" not in compact_proposal
    assert compact_proposal["sections"][0]["section_id"] == "section_access"
    assert json.loads(request.untrusted_context)["approved_regulatory_facts_by_section"] == [
        {
            "section_id": "section_access",
            "requirement_ids": ["access"],
            "source_facts": [
                {
                    "source_fact_id": "official_access_fact",
                    "summary": "Użytkownik główny może nadawać uprawnienia w systemie.",
                    "evidence_ids": ["ev_access"],
                    "requirement_ids": ["access"],
                }
            ],
        }
    ]
    assert "Source facts służą wyłącznie do ustalenia treści" in request.instruction
    assert "nie powtarzaj tego samego twierdzenia" in request.instruction
