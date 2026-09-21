"""Parent-safe observer for dropping unsupported draft-plan body targets."""

from __future__ import annotations

import json

from wilq.codex.prompts import resolve_prompt_template
from wilq.content.drafts import initial_full_draft
from wilq.content.drafts.draft_plan_preparation import PreparedDraftPlan, prepare_draft_plan
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
    ContentInitialDraftSectionOutput,
)
from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_turn_request
from wilq.content.drafts.structured_generation import (
    StructuredDraftGenerationContract,
    StructuredDraftGenerationInput,
    planning_section_inputs,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningSourceFact
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.decisions.planning import (
    ContentPlanningPageAssets,
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionPageAssets


def _source_snapshot() -> ContentPlanningInput:
    return ContentPlanningInput.model_construct(
        work_item_id="content_work_item_draft_plan_change_contract",
        planning_input_digest="a" * 64,
        content_kind="service",
        confirmed_service_card_id="service_operat",
        source_facts=[
            ContentPlanningSourceFact(
                fact_id="planning_exact_source_fact",
                summary="Potwierdzony fakt dotyczący zakresu usługi.",
                source_connector="official_source",
                evidence_ids=["ev_exact"],
                source_fact_ids=["source_exact"],
                source_material_ids=["material_exact"],
            )
        ],
        regulatory_coverage=ContentRegulatoryCoverage(),
    )


def _candidate(
    supported: ContentPlanningSection,
    unsupported: ContentPlanningSection,
) -> ContentPlanningProposal:
    return ContentPlanningProposal.model_construct(
        work_item_id="content_work_item_draft_plan_change_contract",
        planning_digest="b" * 64,
        planning_input_digest="a" * 64,
        sections=[supported, unsupported],
    )


def _draft_turn_candidate(
    supported: ContentPlanningSection,
    unsupported: ContentPlanningSection,
) -> ContentPlanningProposal:
    return ContentPlanningProposal.model_construct(
        work_item_id="content_work_item_draft_plan_change_contract",
        proposal_id="proposal_draft_plan_change_contract",
        planning_digest="b" * 64,
        planning_input_digest="a" * 64,
        page_assets=ContentPlanningPageAssets(title="Tytuł szkicu"),
        cta_direction="CTA szkicu",
        sections=[supported, unsupported],
        faq=[],
        cta_blocks=[],
        internal_links=[],
    )


def test_supported_target_survives_and_unsupported_target_is_recorded() -> None:
    supported = ContentPlanningSection(
        section_id="section_supported",
        heading="Obsługiwana sekcja",
        purpose="Wyjaśnij potwierdzony zakres.",
        inventory_disposition="rewrite",
        evidence_ids=["ev_exact"],
    )
    unsupported = ContentPlanningSection(
        section_id="section_inventory_only",
        heading="Sekcja tylko z inventory",
        purpose="Nie ma exact source support.",
        inventory_disposition="rewrite",
        evidence_ids=["ev_inventory"],
    )

    result = prepare_draft_plan(
        _candidate(supported, unsupported),
        _source_snapshot(),
    )

    assert isinstance(
        result,
        PreparedDraftPlan,
    ), "a mixed supported/unsupported plan must remain writable"
    assert [section.section_id for section in result.body_targets] == ["section_supported"]
    assert [section.section_id for section in result.draftable_proposal.sections] == [
        "section_supported"
    ]
    dropped_targets = getattr(result, "dropped_targets", None)
    assert dropped_targets is not None, "unsupported targets must be recorded"
    assert [
        (target.section_id, target.heading, tuple(target.source_codes))
        for target in dropped_targets
    ] == [("section_inventory_only", "Sekcja tylko z inventory", ("section_inventory_only",))]


def test_prepared_plan_turn_exposes_supported_generation_targets_only() -> None:
    supported = ContentPlanningSection(
        section_id="section_supported",
        heading="Obsługiwana sekcja",
        purpose="Wyjaśnij potwierdzony zakres.",
        inventory_disposition="rewrite",
        evidence_ids=["ev_exact"],
    )
    unsupported = ContentPlanningSection(
        section_id="section_inventory_only",
        heading="Sekcja tylko z inventory",
        purpose="Nie ma exact source support.",
        inventory_disposition="rewrite",
        evidence_ids=["ev_inventory"],
    )
    planning_input = _source_snapshot()
    proposal = _draft_turn_candidate(supported, unsupported)
    prepared_plan = prepare_draft_plan(proposal, planning_input)

    assert isinstance(prepared_plan, PreparedDraftPlan)
    generation_contract = StructuredDraftGenerationContract.model_construct(
        model_input=StructuredDraftGenerationInput.model_construct(
            work_item_id=proposal.work_item_id,
            planning_input_digest=planning_input.planning_input_digest,
            title="Tytuł bazowy",
            cta_direction="CTA bazowe",
            sections=planning_section_inputs(proposal),
        )
    )
    request = initial_full_draft_turn_request(
        planning_input=planning_input,
        proposal=proposal,
        generation_contract=generation_contract,
        prepared_plan=prepared_plan,
    )

    context = json.loads(request.untrusted_context)
    assert (
        context["generation_constraints"]["planning_input_digest"]
        == planning_input.planning_input_digest
    )
    assert [
        section["section_id"] for section in context["generation_constraints"]["sections"]
    ] == [supported.section_id]
    assert unsupported.section_id not in json.dumps(context["generation_constraints"])
    assert context["document_scope"]["included_section_ids"] == [supported.section_id]
    section_schema = request.output_schema["$defs"]["ContentInitialDraftSectionOutput"]
    assert section_schema["properties"]["section_id"]["enum"] == [supported.section_id]
    assert unsupported.section_id not in json.dumps(request.output_schema)


def test_initial_draft_v2_prompt_preserves_copy_and_source_fact_rules() -> None:
    template = resolve_prompt_template("content_initial_draft@v2")

    instruction = template.render(regulatory_draft_directive=" REGULATORY_DIRECTIVE")

    for planning_field in (
        "target_reader",
        "buyer_problem",
        "buyer_trigger",
        "search_intent",
        "angle",
        "value_proposition",
        "reader_question",
        "cta_direction",
        "baseline_cta_direction",
    ):
        assert planning_field in instruction
    assert "Source facts służą wyłącznie do ustalenia treści" in instruction
    assert "approved_source_facts_by_section" in instruction
    assert "co najmniej jeden konkretny fakt" in instruction
    assert "Nie dodawaj faktów" in instruction
    assert "nie powtarzaj tego samego twierdzenia" in instruction
    assert instruction.endswith("REGULATORY_DIRECTIVE")


def test_enrich_benefit_sections_skips_link_bearing_source_fact() -> None:
    safe_fact = "Terminowy nadzór formalno-prawny ogranicza ryzyko opóźnień."
    planning_input = ContentPlanningInput.model_construct(
        source_facts=[
            ContentPlanningSourceFact(
                fact_id="planning_link_benefit_fact",
                summary="Koszt opisano przy [usłudze](https://example.com).",
                source_connector="public_site",
                evidence_ids=["ev_link_benefit"],
            ),
            ContentPlanningSourceFact(
                fact_id="planning_safe_benefit_fact",
                summary=safe_fact,
                source_connector="public_site",
                evidence_ids=["ev_safe_benefit"],
            ),
        ]
    )
    output = ContentInitialDraftModelOutput(
        page_assets=ContentDraftRevisionPageAssets(
            wordpress_title="Korzyści outsourcingu",
            meta_title="Korzyści outsourcingu środowiskowego",
            meta_description="Korzyści stałej obsługi środowiskowej dla firmy.",
            h1="Korzyści outsourcingu środowiskowego",
            lead="Praktyczny opis stałego wsparcia środowiskowego dla firmy.",
        ),
        sections=[
            ContentInitialDraftSectionOutput(
                section_id="benefit_missing",
                heading="Co daje outsourcing?",
                body_markdown="Może obejmować nadzór nad dokumentacją.",
            )
        ],
    )

    enriched = initial_full_draft._enrich_benefit_sections(output, planning_input)

    assert safe_fact in enriched.sections[0].body_markdown
    assert "https://example.com" not in enriched.sections[0].body_markdown
