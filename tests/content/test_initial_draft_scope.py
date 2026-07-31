from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ValidationError

from wilq.content.drafts import initial_full_draft
from wilq.content.drafts.initial_full_draft import _document_scope_errors, _planning_input_blocker
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftCtaOutput,
    ContentInitialDraftFaqOutput,
    ContentInitialDraftModelOutput,
    ContentInitialDraftRequest,
    ContentInitialDraftSectionOutput,
)
from wilq.content.drafts.initial_full_draft_scope import draftable_planning_sections
from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_output_schema
from wilq.content.planning.dynamic_input import (
    ContentPlanningInputBlocker,
    ContentPlanningInputBuildResult,
)
from wilq.content.workflow.planning import ContentPlanningProposal, ContentPlanningSection
from wilq.content.workflow.revisions import ContentDraftRevisionPageAssets


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            ContentInitialDraftSectionOutput,
            {"section_id": "section", "heading": "Nagłówek", "body_markdown": "   "},
        ),
        (
            ContentInitialDraftFaqOutput,
            {"question": "Pytanie", "answer_markdown": "   "},
        ),
        (ContentInitialDraftCtaOutput, {"body_markdown": "   "}),
    ],
)
def test_initial_draft_model_output_rejects_whitespace_only_content(
    model: type[BaseModel], payload: dict[str, str]
) -> None:
    with pytest.raises(ValidationError, match="cannot be blank"):
        model.model_validate(payload)


def _proposal_with_review_required_inventory() -> ContentPlanningProposal:
    return ContentPlanningProposal(
        work_item_id="content_work_item_scope",
        planning_digest="a" * 64,
        proposal_id="content_planning_proposal_scope",
        proposal_version=1,
        generation_status="codex_generated",
        planning_input_digest="b" * 64,
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


def test_initial_draft_preserves_the_first_actionable_planning_blocker() -> None:
    blocker = _planning_input_blocker([
        ContentPlanningInputBlocker(
            code="missing_approved_service_fact",
            label="Brakuje zatwierdzonego faktu usługi",
            reason="Karta wskazuje nieznany source fact.",
            next_step="Uzupełnij approved source fact.",
        ),
        ContentPlanningInputBlocker(
            code="stale_planning_sources",
            label="Źródła są nieświeże",
            reason="Odśwież dane.",
            next_step="Uruchom refresh.",
        ),
    ])

    assert blocker.code == "missing_approved_service_fact"
    assert blocker.label == "Brakuje zatwierdzonego faktu usługi"
    assert blocker.reason == "Karta wskazuje nieznany source fact."
    assert blocker.next_step == "Uzupełnij approved source fact."
    assert blocker.source_codes == [
        "missing_approved_service_fact",
        "stale_planning_sources",
    ]


def test_initial_draft_preserves_source_material_review_blocker() -> None:
    blocker = _planning_input_blocker(
        [
            ContentPlanningInputBlocker(
                code="wordpress_material_review_required",
                label="Materiał strony wymaga potwierdzenia",
                reason="Rendered the_content needs source review.",
                next_step="Potwierdź materiał REST/ACF.",
            )
        ]
    )

    assert blocker.code == "wordpress_material_review_required"
    assert blocker.next_step == "Potwierdź materiał REST/ACF."


def test_initial_draft_reuses_exact_service_binding_from_generated_plan(
    monkeypatch,
) -> None:
    proposal = _proposal_with_review_required_inventory()
    source_snapshot = SimpleNamespace(
        planning_workspace=SimpleNamespace(
            section_map_current=True,
            proposal=proposal,
        ),
        revision_workspace=SimpleNamespace(latest_revision=None, context_current=True),
        preflight=SimpleNamespace(item=SimpleNamespace(id=proposal.work_item_id)),
    )
    selected_snapshot = object()
    captured: dict[str, object] = {}

    def select_exact_service(snapshot, service_card_id: str):
        captured["selection_snapshot"] = snapshot
        captured["service_card_id"] = service_card_id
        return selected_snapshot

    def build_input(snapshot, *, service_card_id: str):
        captured["input_snapshot"] = snapshot
        captured["input_service_card_id"] = service_card_id
        return ContentPlanningInputBuildResult(
            blockers=[
                ContentPlanningInputBlocker(
                    code="service_card_not_approved",
                    label="Usługa wymaga potwierdzenia",
                    reason="Focused sentinel stops before runtime setup.",
                    next_step="Sprawdź usługę.",
                )
            ]
        )

    monkeypatch.setattr(
        initial_full_draft,
        "with_explicit_content_service_selection",
        select_exact_service,
    )
    monkeypatch.setattr(initial_full_draft, "build_content_planning_input", build_input)

    response = initial_full_draft._prepare_inputs(
        source_snapshot,
        ContentInitialDraftRequest(
            expected_proposal_id=proposal.proposal_id,
            expected_planning_digest=proposal.planning_digest,
            expected_planning_input_digest=proposal.planning_input_digest,
            requested_by="wilku",
        ),
    )

    assert response.status == "blocked"
    assert captured == {
        "selection_snapshot": source_snapshot,
        "service_card_id": proposal.service_card_id,
        "input_snapshot": selected_snapshot,
        "input_service_card_id": proposal.service_card_id,
    }
