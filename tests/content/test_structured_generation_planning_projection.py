from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftGenerationInput,
    contract_for_planning_proposal,
)
from wilq.content.workflow.planning import (
    ContentPlanningPageAssets,
    ContentPlanningProposal,
    ContentPlanningSection,
)


def test_full_draft_contract_projects_reviewed_sections_and_excludes_removed_rows() -> None:
    contract = StructuredDraftGenerationContract.model_construct(
        model_input=StructuredDraftGenerationInput.model_construct(
            work_item_id="work-item",
            title="baseline",
            cta_direction="baseline CTA",
            sections=[],
        )
    )
    proposal = ContentPlanningProposal.model_construct(
        page_assets=ContentPlanningPageAssets(title="Tytuł z planu"),
        cta_direction="CTA z planu",
        sections=[
            ContentPlanningSection(
                section_id="section_keep",
                heading="Sekcja dla odbiorcy",
                purpose="Odpowiada na pytanie",
                reader_question="Jak to działa?",
                inventory_disposition="rewrite",
                query_terms=["dokładne zapytanie"],
                evidence_ids=["ev_gsc"],
                claim_ids=["claim_allowed"],
                source_material_ids=["material_1"],
                knowledge_card_ids=["card_1"],
            ),
            ContentPlanningSection(
                section_id="section_remove",
                heading="Nie pisz tej sekcji",
                purpose="Wymaga osobnego review",
                inventory_disposition="remove_review_required",
            ),
        ],
    )

    projected = contract_for_planning_proposal(contract, proposal)
    input_model = projected.model_input

    assert input_model.title == "Tytuł z planu"
    assert input_model.cta_direction == "CTA z planu"
    assert [section.section_id for section in input_model.sections] == ["section_keep"]
    assert input_model.sections[0].query_terms == ["dokładne zapytanie"]
    assert input_model.sections[0].evidence_ids == ["ev_gsc"]
    assert input_model.sections[0].claim_ids == ["claim_allowed"]
    assert input_model.sections[0].source_material_ids == ["material_1"]
    assert input_model.sections[0].knowledge_card_ids == ["card_1"]
