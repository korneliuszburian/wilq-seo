"""Preflight and deterministic repair must share one approved fact source.

Live BDO: preflight accepted ``bdo_exemptions:bdo_paper_records_rule`` because
an approved official fact grounds it, yet the deterministic repair found no fact
for the section and left the draft blocked with ``document_scope_mismatch``. The
prepared plan binds facts to one writable section; the requirement-wide approved
set is the same source preflight already validated.
"""

from __future__ import annotations

from wilq.content.drafts.draft_plan_preparation import (
    PreparedDraftPlan,
    PreparedDraftTarget,
    PreparedSourceFact,
)
from wilq.content.drafts.initial_full_draft_contracts import (
    ContentInitialDraftModelOutput,
    ContentInitialDraftSectionOutput,
)
from wilq.content.drafts.regulatory_repair import ground_unmet_regulatory_assertions
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryDocumentAssertion,
    ContentRegulatoryRequirement,
    regulatory_requirement_assertion_errors,
)
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)
from wilq.content.workflow.documents.revisions import ContentDraftRevisionPageAssets

_REQUIREMENT_ID = "bdo_exemptions"
_ASSERTION_ID = "bdo_paper_records_rule"
_TERMS = ["nie upoważnia", "papierowych"]


def _requirement() -> ContentRegulatoryRequirement:
    return ContentRegulatoryRequirement(
        id=_REQUIREMENT_ID,
        label="wyłączenia z wpisu lub ewidencji",
        reason="Treść nie może sugerować identycznego wpisu ani ewidencji.",
        document_assertions=[
            ContentRegulatoryDocumentAssertion(
                id=_ASSERTION_ID,
                label="zasady dokumentacji papierowej",
                required_any_of=_TERMS,
            )
        ],
    )


def _official_fact() -> ContentSourceFact:
    return ContentSourceFact.model_construct(
        source_id="regulatory_source_fact_paper_records",
        extracted_fact=(
            "Oficjalne źródło BDO wskazuje, że brak Internetu lub energii nie jest "
            "awarią BDO i nie upoważnia do wystawiania papierowych dokumentów ewidencji. "
            "Wymaga weryfikacji przez człowieka."
        ),
        review_status="approved",
        official_source=True,
        evidence_ids=["ev_paper_records"],
        source_connectors=["official_regulatory_review"],
        regulatory_requirement_ids=[_REQUIREMENT_ID],
    )


def test_grounding_falls_back_to_requirement_wide_approved_facts() -> None:
    requirement = _requirement()
    section = ContentPlanningSection(
        section_id="section_bdo_exemptions",
        heading="Wyłączenia i ewidencja",
        purpose="Wyjaśnij warunki i zasady dokumentacji.",
        evidence_ids=["ev_paper_records"],
        regulatory_requirement_ids=[_REQUIREMENT_ID],
    )
    planning_input = ContentPlanningInput.model_construct(
        work_item_id="work_regulatory_fallback",
        planning_input_digest="a" * 64,
        source_facts=[],
        regulatory_coverage=ContentRegulatoryCoverage.model_construct(
            requirements=[requirement],
            source_facts=[_official_fact()],
        ),
    )
    proposal = ContentPlanningProposal.model_construct(
        work_item_id="work_regulatory_fallback",
        planning_input_digest="a" * 64,
        sections=[section],
    )
    prepared_plan = PreparedDraftPlan(
        candidate=proposal,
        exact_source_snapshot=planning_input,
        body_targets=(section,),
        target_supports=(PreparedDraftTarget(section=section, source_facts=()),),
    )
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
                section_id=section.section_id,
                heading=section.heading,
                body_markdown="Wprowadzenie bez wymaganej frazy.",
            )
        ],
    )

    grounded = ground_unmet_regulatory_assertions(
        output,
        planning_input=planning_input,
        proposal=proposal,
        missing_codes=[
            f"regulatory_document_assertion:{_REQUIREMENT_ID}:{_ASSERTION_ID}"
        ],
        prepared_plan=prepared_plan,
    )

    body = grounded.sections[0].body_markdown
    assert regulatory_requirement_assertion_errors(requirement=requirement, text=body) == []
    assert "nie upoważnia" in body


def test_grounding_falls_back_when_prepared_fact_is_not_document_safe() -> None:
    requirement = _requirement()
    section = ContentPlanningSection(
        section_id="section_bdo_exemptions",
        heading="Wyłączenia i ewidencja",
        purpose="Wyjaśnij warunki i zasady dokumentacji.",
        evidence_ids=["ev_paper_records"],
        regulatory_requirement_ids=[_REQUIREMENT_ID],
    )
    planning_input = ContentPlanningInput.model_construct(
        work_item_id="work_regulatory_unsafe_prepared",
        planning_input_digest="a" * 64,
        source_facts=[],
        regulatory_coverage=ContentRegulatoryCoverage.model_construct(
            requirements=[requirement],
            source_facts=[_official_fact()],
        ),
    )
    proposal = ContentPlanningProposal.model_construct(
        work_item_id="work_regulatory_unsafe_prepared",
        planning_input_digest="a" * 64,
        sections=[section],
    )
    unsafe_prepared = PreparedSourceFact(
        fact_id="prepared_unsafe",
        summary=(
            "Źródło podaje, że nie upoważnia to do papierowych dokumentów "
            "[zobacz](https://example.com)."
        ),
        source_connector="official_regulatory_review",
        evidence_ids=("ev_paper_records",),
        knowledge_card_ids=(),
        source_fact_ids=("regulatory_source_fact_paper_records",),
        source_material_ids=(),
        regulatory_requirement_ids=(_REQUIREMENT_ID,),
    )
    prepared_plan = PreparedDraftPlan(
        candidate=proposal,
        exact_source_snapshot=planning_input,
        body_targets=(section,),
        target_supports=(
            PreparedDraftTarget(section=section, source_facts=(unsafe_prepared,)),
        ),
    )
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
                section_id=section.section_id,
                heading=section.heading,
                body_markdown="Wprowadzenie bez wymaganej frazy.",
            )
        ],
    )

    grounded = ground_unmet_regulatory_assertions(
        output,
        planning_input=planning_input,
        proposal=proposal,
        missing_codes=[
            f"regulatory_document_assertion:{_REQUIREMENT_ID}:{_ASSERTION_ID}"
        ],
        prepared_plan=prepared_plan,
    )

    body = grounded.sections[0].body_markdown
    assert regulatory_requirement_assertion_errors(requirement=requirement, text=body) == []
    assert "nie upoważnia" in body
    assert "example.com" not in body
