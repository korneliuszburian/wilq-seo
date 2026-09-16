from __future__ import annotations

from wilq.content.drafts.draft_plan_preparation import (
    DraftPlanBlocked,
    PreparedDraftPlan,
    prepare_draft_plan,
)
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningSourceFact
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.decisions.planning import (
    ContentPlanningProposal,
    ContentPlanningSection,
)


def _source_snapshot(*source_facts: ContentPlanningSourceFact) -> ContentPlanningInput:
    return ContentPlanningInput.model_construct(
        work_item_id="content_work_item_draft_plan",
        planning_input_digest="a" * 64,
        content_kind="service",
        confirmed_service_card_id="service_bdo",
        source_facts=list(source_facts),
        regulatory_coverage=ContentRegulatoryCoverage(),
    )


def _source_fact(*, fact_id: str = "source_fact_exact") -> ContentPlanningSourceFact:
    return ContentPlanningSourceFact(
        fact_id=f"planning_{fact_id}",
        summary="Zatwierdzony fakt dotyczący zakresu usługi.",
        source_connector="public_site",
        evidence_ids=["ev_source_fact"],
        source_fact_ids=[fact_id],
        source_material_ids=["material_exact"],
    )


def _candidate(*sections: ContentPlanningSection) -> ContentPlanningProposal:
    return ContentPlanningProposal.model_construct(
        work_item_id="content_work_item_draft_plan",
        planning_digest="b" * 64,
        planning_input_digest="a" * 64,
        sections=list(sections),
    )


def test_inventory_only_body_target_is_blocked_before_draft_preparation() -> None:
    candidate = _candidate(
        ContentPlanningSection(
            section_id="section_inventory_only",
            heading="Sekcja z inventory",
            purpose="Przepisz znalezioną sekcję.",
            inventory_disposition="rewrite",
            evidence_ids=["ev_wordpress_inventory"],
        )
    )
    snapshot = _source_snapshot(_source_fact())

    result = prepare_draft_plan(candidate, snapshot)

    assert isinstance(result, DraftPlanBlocked)
    assert result.blocker.code == "draft_plan_source_support_missing"
    assert result.blocker.reason
    assert "source fact" in result.blocker.reason


def test_exact_source_fact_support_yields_a_prepared_draft_plan() -> None:
    candidate = _candidate(
        ContentPlanningSection(
            section_id="section_exact",
            heading="Sekcja ze źródłem",
            purpose="Wyjaśnij potwierdzony zakres.",
            inventory_disposition="rewrite",
            evidence_ids=["ev_source_fact"],
            source_material_ids=["material_exact"],
        )
    )
    snapshot = _source_snapshot(_source_fact())

    result = prepare_draft_plan(candidate, snapshot)

    assert isinstance(result, PreparedDraftPlan)
    assert list(result.body_targets) == candidate.sections


def test_missing_or_mismatched_exact_input_digest_blocks_fail_closed() -> None:
    candidate = _candidate(
        ContentPlanningSection(
            section_id="section_exact",
            heading="Sekcja ze źródłem",
            purpose="Wyjaśnij potwierdzony zakres.",
            inventory_disposition="rewrite",
            evidence_ids=["ev_source_fact"],
        )
    )
    snapshot = _source_snapshot(_source_fact())

    for invalid_candidate in (
        candidate.model_copy(update={"planning_input_digest": None}),
        candidate.model_copy(update={"planning_input_digest": "A" * 64}),
        candidate.model_copy(update={"work_item_id": "other_work_item"}),
    ):
        result = prepare_draft_plan(invalid_candidate, snapshot)
        assert isinstance(result, DraftPlanBlocked)
        assert result.blocker.code == "draft_plan_source_support_missing"


def test_unresolved_merge_is_not_a_body_target() -> None:
    candidate = _candidate(
        ContentPlanningSection(
            section_id="section_merge",
            heading="Scal tę sekcję",
            purpose="Przenieś do innego adresu.",
            inventory_disposition="merge",
            evidence_ids=["ev_source_fact"],
        )
    )

    result = prepare_draft_plan(candidate, _source_snapshot(_source_fact()))

    assert isinstance(result, DraftPlanBlocked)
    assert result.blocker.code == "draft_plan_merge_target_missing"


def test_merge_with_exact_inventory_identity_still_requires_destination_contract() -> None:
    candidate = _candidate(
        ContentPlanningSection(
            section_id="section_merge",
            heading="Scal tę sekcję",
            purpose="Scal potwierdzoną informację.",
            inventory_disposition="merge",
            inventory_section_id="inventory_section_01",
            evidence_ids=["ev_source_fact"],
        )
    )

    result = prepare_draft_plan(candidate, _source_snapshot(_source_fact()))

    assert isinstance(result, DraftPlanBlocked)
    assert result.blocker.code == "draft_plan_merge_target_missing"
    assert result.blocker.source_codes == ["section_merge"]


def test_historical_bdo_v9_sections_10_to_12_block_without_exact_source_support() -> None:
    supported = [
        ContentPlanningSection(
            section_id=f"section_{index:02d}",
            heading=f"Obsługiwana sekcja {index}",
            purpose="Odpowiedz na pytanie z exact source fact.",
            inventory_disposition="rewrite",
            evidence_ids=["ev_source_fact"],
        )
        for index in range(1, 10)
    ]
    historical = [
        ContentPlanningSection(
            section_id=f"section_{index:02d}",
            heading=f"Historyczna sekcja {index}",
            purpose="Tylko inventory albo popyt, bez source fact.",
            inventory_disposition="rewrite",
            inventory_section_id=f"inventory_section_{index:02d}",
            evidence_ids=["ev_wordpress_inventory"],
        )
        for index in range(10, 13)
    ]
    candidate = _candidate(*supported, *historical).model_copy(update={"proposal_version": 9})

    result = prepare_draft_plan(candidate, _source_snapshot(_source_fact()))

    assert isinstance(result, DraftPlanBlocked)
    assert result.blocker.code == "draft_plan_source_support_missing"
    assert result.blocker.source_codes == [
        "section_10",
        "section_11",
        "section_12",
    ]
    assert "source" in result.blocker.next_step.lower()


def test_current_bdo_v10_compiles_eight_exact_supported_targets_without_merge() -> None:
    sections = [
        ContentPlanningSection(
            section_id=f"section_{index:02d}",
            heading=f"Aktualna sekcja {index}",
            purpose="Odpowiedz na pytanie z exact source fact.",
            inventory_disposition="rewrite",
            evidence_ids=["ev_source_fact"],
        )
        for index in range(1, 9)
    ]
    candidate = _candidate(*sections).model_copy(update={"proposal_version": 10})

    result = prepare_draft_plan(candidate, _source_snapshot(_source_fact()))

    assert isinstance(result, PreparedDraftPlan)
    assert len(result.body_targets) == 8


def test_remove_and_defer_sections_are_not_body_targets() -> None:
    candidate = _candidate(
        ContentPlanningSection(
            section_id="section_remove",
            heading="Usuń tę sekcję",
            purpose="Pozostaw poza draftem.",
            inventory_disposition="remove_review_required",
        ),
        ContentPlanningSection.model_construct(
            section_id="section_defer",
            heading="Odłóż tę sekcję",
            purpose="Pozostaw do osobnego review.",
            inventory_disposition="defer",
        ),
        ContentPlanningSection(
            section_id="section_exact",
            heading="Sekcja ze źródłem",
            purpose="Wyjaśnij potwierdzony zakres.",
            inventory_disposition="rewrite",
            evidence_ids=["ev_source_fact"],
        ),
    )

    result = prepare_draft_plan(candidate, _source_snapshot(_source_fact()))

    assert isinstance(result, PreparedDraftPlan)
    assert [section.section_id for section in result.body_targets] == ["section_exact"]
