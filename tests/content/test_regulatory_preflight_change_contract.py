"""Parent-safe observer for the regulatory preflight metadata contract."""

from __future__ import annotations

from wilq.content.drafts.regulatory_repair import regulatory_draft_preflight_errors
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


def test_bound_groundable_plan_without_metadata_assertion_terms_passes() -> None:
    requirement_id = "bdo_definition"
    assertion_term = (
        "Baza danych o produktach i opakowaniach oraz o gospodarce odpadami"
    )
    requirement = ContentRegulatoryRequirement(
        id=requirement_id,
        label="Pełna nazwa BDO",
        reason="Pełna nazwa musi wynikać ze źródła urzędowego.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id="bdo_full_name",
                label="Pełna nazwa systemu",
                required_any_of=[assertion_term],
            )
        ],
    )
    fact = ContentSourceFact(
        source_id="regulatory_source_fact_bdo_definition",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://bdo.mos.gov.pl/o-systemie-bdo/",
        extracted_fact=assertion_term,
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
        regulatory_requirement_ids=[requirement_id],
        applicable_service_card_ids=["ekologus_service_bdo_reporting"],
    )
    planning_input = ContentPlanningInput.model_construct(
        regulatory_coverage=ContentRegulatoryCoverage(
            profile_id="bdo",
            profile_version="2026-08",
            requirements=[requirement],
            source_facts=[fact],
        )
    )
    proposal = ContentPlanningProposal.model_construct(
        sections=[
            ContentPlanningSection(
                section_id="section_bdo_definition",
                heading="Czym jest BDO",
                purpose="Wyjaśnij definicję i zastosowanie systemu BDO.",
                reader_question="Co oznacza skrót BDO?",
                inventory_disposition="rewrite",
                regulatory_requirement_ids=[requirement_id],
            )
        ]
    )

    assert regulatory_draft_preflight_errors(planning_input, proposal) == []
