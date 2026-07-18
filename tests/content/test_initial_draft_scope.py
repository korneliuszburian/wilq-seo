from wilq.content.drafts.initial_full_draft import _document_scope_errors
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
    ContentInitialDraftSectionOutput,
)
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_output_schema
from wilq.content.workflow.planning import ContentPlanningProposal, ContentPlanningSection
from wilq.content.workflow.revisions import ContentDraftRevisionPageAssets


def _proposal_with_review_required_inventory() -> ContentPlanningProposal:
    return ContentPlanningProposal(
        work_item_id="content_work_item_scope",
        planning_digest="a" * 64,
        proposal_id="content_planning_proposal_scope",
        proposal_version=1,
        generation_status="codex_generated",
        final_canonical_url="https://www.ekologus.pl/strona/",
        service_card_id="ekologus_service_bdo_reporting",
        service_label="BDO",
        service_selection_confirmed=True,
        target_reader="przedsiębiorca",
        buyer_problem="Nie wie, co sprawdzić.",
        buyer_trigger="Przed decyzją.",
        search_intent="informacyjna",
        cta_direction="Skontaktuj się.",
        sections=[
            ContentPlanningSection(
                section_id="section_keep",
                heading="Sekcja do tekstu",
                purpose="Odpowiedz.",
                reader_question="Co sprawdzić?",
                inventory_disposition="rewrite",
                evidence_ids=["ev_scope"],
            ),
            ContentPlanningSection(
                section_id="section_remove",
                heading="Stary element do review",
                purpose="Nie przenoś automatycznie.",
                reader_question="Czy zachować?",
                inventory_disposition="remove_review_required",
                evidence_ids=["ev_scope"],
            ),
        ],
        search_demand={
            "status": "available",
            "optional_ads_status": "not_exactly_mapped",
            "safe_next_step": "Review",
        },
    )


def test_full_draft_schema_excludes_remove_review_required_sections() -> None:
    proposal = _proposal_with_review_required_inventory()

    assert [item.section_id for item in draftable_planning_sections(proposal.sections)] == [
        "section_keep"
    ]

    schema = initial_full_draft_output_schema(proposal)
    sections = schema["properties"]["sections"]
    section_definition = schema["$defs"]["ContentInitialDraftSectionOutput"]

    assert sections["minItems"] == 1
    assert sections["maxItems"] == 1
    assert section_definition["properties"]["section_id"]["enum"] == ["section_keep"]
    assert section_definition["properties"]["heading"]["enum"] == ["Sekcja do tekstu"]


def test_document_scope_accepts_the_same_excluded_section_projection() -> None:
    proposal = _proposal_with_review_required_inventory()
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Tytuł",
            meta_title="Meta",
            meta_description="Opis",
            h1="Nagłówek",
            lead="Lead",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="section_keep",
                heading="Sekcja do tekstu",
                body_markdown="Odpowiedź.",
            )
        ],
        publish_ready=False,
    )

    assert _document_scope_errors(proposal, output) == []
