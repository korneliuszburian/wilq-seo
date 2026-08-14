from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest

from wilq.content.drafts import (
    codex_section_proposal_turn as proposal_turn,
)
from wilq.content.drafts import (
    fact_selection,
)
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningSourceFact
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.contracts.contracts import ContentWorkItemWorkflowSnapshotResponse
from wilq.content.workflow.decisions.planning import ContentPlanningSection
from wilq.content.workflow.documents.revisions import (
    ContentDraftRevision,
    ContentDraftRevisionSection,
)

_SERVICE_CARD_ID = "ekologus_service_bdo_reporting"
_DIRECT_HEADING = "Jak wygląda proces?"
_FALLBACK_HEADING = "Jak przygotować firmę?"
_REGULATORY_HEADING = "Kiedy mija termin?"


@pytest.fixture
def section_repair_context(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    ContentPlanningInput,
    ContentWorkItemWorkflowSnapshotResponse,
    ContentDraftRevision,
]:
    source_facts = _source_facts()
    registry_facts = [
        *source_facts,
        _approved_fact(
            "non_allowlisted_records_fact",
            target_card_id="ekologus_evidence_unrelated",
            buyer_problem_terms=["ewidencja odpadów"],
        ),
    ]
    monkeypatch.setattr(
        fact_selection,
        "ekologus_source_facts",
        lambda: tuple(registry_facts),
    )
    monkeypatch.setattr(
        proposal_turn,
        "proposal_output_schema",
        lambda *_args, **_kwargs: {},
    )
    planning_input = _planning_input(source_facts)
    sections = _planning_sections()
    return planning_input, _snapshot(sections), _revision(sections)


def _source_facts() -> list[ContentSourceFact]:
    return [
        _approved_fact(
            "direct_records_fact",
            target_card_id="ekologus_evidence_bdo_records",
            buyer_problem_terms=["ewidencja odpadów"],
        ),
        _approved_fact(
            "service_fallback_fact",
            target_card_id=_SERVICE_CARD_ID,
            target_card_type="service",
            service_fit_terms=["pakiet abonamentowy"],
        ),
        _approved_fact(
            "other_service_fact",
            target_card_id="ekologus_service_other",
            target_card_type="service",
            service_fit_terms=["audyt instalacji"],
        ),
        _approved_fact(
            "same_id_non_service_fact",
            target_card_id=_SERVICE_CARD_ID,
            service_fit_terms=["rekultywacja terenu"],
        ),
        _approved_fact(
            "official_reporting_fact",
            target_card_id="ekologus_requirement_bdo_reporting",
            service_fit_terms=["termin sprawozdania"],
            official_source=True,
        ),
    ]


def _planning_input(source_facts: list[ContentSourceFact]) -> ContentPlanningInput:
    return ContentPlanningInput.model_construct(
        work_item_id="content_work_item_bdo",
        planning_input_digest="a" * 64,
        confirmed_service_card_id=_SERVICE_CARD_ID,
        source_facts=[
            ContentPlanningSourceFact(
                fact_id=f"planning_{fact.source_id}",
                summary=fact.extracted_fact,
                source_connector=fact.source_connectors[0],
                evidence_ids=fact.evidence_ids,
                source_fact_ids=[fact.source_id],
            )
            for fact in source_facts
        ],
        regulatory_coverage=ContentRegulatoryCoverage(
            source_facts=[next(fact for fact in source_facts if fact.official_source)]
        ),
    )


def _planning_sections() -> list[ContentPlanningSection]:
    return [
        ContentPlanningSection(
            section_id="section_records",
            heading=_DIRECT_HEADING,
            purpose="Opisuje kolejne działania.",
            reader_question="Co należy zrobić?",
            query_terms=["EWIDENCJA ODPADÓW W BDO"],
        ),
        ContentPlanningSection(
            section_id="section_preparation",
            heading=_FALLBACK_HEADING,
            purpose="Porządkuje dalsze kroki przedsiębiorcy.",
            reader_question="Od czego zacząć?",
            query_terms=["Czy BDO ma związek z PIT, VAT i ZUS?"],
        ),
        ContentPlanningSection(
            section_id="section_reporting",
            heading=_REGULATORY_HEADING,
            purpose="Wyjaśnia termin wynikający z wymogu.",
            reader_question="Jaki termin obowiązuje?",
            query_terms=["termin sprawozdania"],
            regulatory_requirement_ids=["reporting"],
        ),
    ]


def _snapshot(
    sections: list[ContentPlanningSection],
) -> ContentWorkItemWorkflowSnapshotResponse:
    return cast(
        ContentWorkItemWorkflowSnapshotResponse,
        SimpleNamespace(
            structured_generation=SimpleNamespace(
                structured_generation_result=SimpleNamespace(
                    contract=SimpleNamespace(
                        model_input=SimpleNamespace(model_dump=lambda *, mode: {})
                    )
                )
            ),
            revision_workspace=SimpleNamespace(latest_review=None),
            planning_workspace=SimpleNamespace(
                proposal=SimpleNamespace(
                    service_card_id=_SERVICE_CARD_ID,
                    sections=sections,
                )
            ),
        ),
    )


def _revision(sections: list[ContentPlanningSection]) -> ContentDraftRevision:
    evidence_by_heading = {
        _DIRECT_HEADING: ["ev_direct_records_fact"],
        _FALLBACK_HEADING: ["ev_service_fallback_fact"],
        _REGULATORY_HEADING: [
            "ev_official_reporting_fact",
            "ev_service_fallback_fact",
        ],
    }
    return ContentDraftRevision(
        revision_id="content_revision_bdo",
        work_item_id="content_work_item_bdo",
        revision_number=1,
        content_digest="b" * 64,
        draft_package_id="content_draft_package_bdo",
        draft_package_digest="c" * 64,
        service_card_id=_SERVICE_CARD_ID,
        final_canonical_url="https://www.ekologus.pl/bdo/",
        title="BDO dla przedsiębiorcy",
        sections=[
            ContentDraftRevisionSection(
                section_id=section.section_id,
                heading=section.heading,
                body_markdown=(
                    "Ta sekcja wyjaśnia konkretne kroki i pomaga przedsiębiorcy "
                    "uporządkować dalsze działania."
                ),
                evidence_ids=evidence_by_heading[section.heading],
            )
            for section in sections
        ],
        created_by="test",
        created_at=datetime(2026, 8, 13, tzinfo=UTC),
    )


def test_selected_query_match_is_exposed_as_approved_source_fact(
    section_repair_context: tuple[
        ContentPlanningInput,
        ContentWorkItemWorkflowSnapshotResponse,
        ContentDraftRevision,
    ],
) -> None:
    planning_input, snapshot, revision = section_repair_context

    request = proposal_turn.codex_turn_request(
        snapshot=snapshot,
        selected_headings=[_DIRECT_HEADING],
        base_revision=revision,
        planning_input=planning_input,
    )

    context = json.loads(request.untrusted_context)
    assert context["approved_source_facts_for_selected_sections"] == [
        {
            "source_fact_id": "direct_records_fact",
            "summary": "Konkretny zatwierdzony fakt: direct_records_fact.",
            "evidence_ids": ["ev_direct_records_fact"],
        }
    ]
    assert "approved_source_facts_for_selected_sections" in request.instruction
    assert "informacje zamiast ogólników" in request.instruction


def test_selected_section_without_match_gets_service_card_fallback_fact(
    section_repair_context: tuple[
        ContentPlanningInput,
        ContentWorkItemWorkflowSnapshotResponse,
        ContentDraftRevision,
    ],
) -> None:
    planning_input, snapshot, revision = section_repair_context

    request = proposal_turn.codex_turn_request(
        snapshot=snapshot,
        selected_headings=[_FALLBACK_HEADING],
        base_revision=revision,
        planning_input=planning_input,
    )

    context = json.loads(request.untrusted_context)
    assert context["approved_source_facts_for_selected_sections"] == [
        {
            "source_fact_id": "service_fallback_fact",
            "summary": "Konkretny zatwierdzony fakt: service_fallback_fact.",
            "evidence_ids": ["ev_service_fallback_fact"],
            "service_label": "Usługa service_fallback_fact",
        }
    ]


def test_selected_sections_cap_approved_source_facts_per_section(
    section_repair_context: tuple[
        ContentPlanningInput,
        ContentWorkItemWorkflowSnapshotResponse,
        ContentDraftRevision,
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, snapshot, revision = section_repair_context
    direct_facts = [
        _approved_fact(
            f"direct_records_fact_{index}",
            target_card_id="ekologus_evidence_bdo_records",
            buyer_problem_terms=["ewidencja odpadów"],
        )
        for index in range(1, 6)
    ]
    fallback_facts = [
        _approved_fact(
            "service_fallback_unrelated",
            target_card_id=_SERVICE_CARD_ID,
            target_card_type="service",
            service_fit_terms=["audyt instalacji"],
        ),
        _approved_fact(
            "service_fallback_overlap_one",
            target_card_id=_SERVICE_CARD_ID,
            target_card_type="service",
            service_fit_terms=["zus nip"],
        ),
        _approved_fact(
            "service_fallback_overlap_two",
            target_card_id=_SERVICE_CARD_ID,
            target_card_type="service",
            service_fit_terms=["vat bdo"],
        ),
        _approved_fact(
            "service_fallback_overlap_two_tie",
            target_card_id=_SERVICE_CARD_ID,
            target_card_type="service",
            buyer_problem_terms=["pit zus"],
        ),
        _approved_fact(
            "service_fallback_overlap_three",
            target_card_id=_SERVICE_CARD_ID,
            target_card_type="service",
            buyer_problem_terms=["vat pit bdo"],
        ),
        _approved_fact(
            "service_fallback_overlap_four",
            target_card_id=_SERVICE_CARD_ID,
            target_card_type="service",
            service_fit_terms=["vat pit bdo czy"],
        ),
    ]
    official_fact = next(fact for fact in _source_facts() if fact.official_source)
    source_facts = [*direct_facts, *fallback_facts, official_fact]
    monkeypatch.setattr(
        fact_selection,
        "ekologus_source_facts",
        lambda: tuple(source_facts),
    )
    planning_input = _planning_input(source_facts)

    request = proposal_turn.codex_turn_request(
        snapshot=snapshot,
        selected_headings=[_DIRECT_HEADING, _FALLBACK_HEADING],
        base_revision=revision,
        planning_input=planning_input,
    )

    context = json.loads(request.untrusted_context)
    assert _source_fact_ids(context) == [
        "direct_records_fact_1",
        "direct_records_fact_2",
        "direct_records_fact_3",
        "direct_records_fact_4",
        "service_fallback_overlap_four",
        "service_fallback_overlap_three",
        "service_fallback_overlap_two",
        "service_fallback_overlap_two_tie",
    ]


def test_missing_planning_input_exposes_no_approved_source_facts(
    section_repair_context: tuple[
        ContentPlanningInput,
        ContentWorkItemWorkflowSnapshotResponse,
        ContentDraftRevision,
    ],
) -> None:
    _, snapshot, revision = section_repair_context

    request = proposal_turn.codex_turn_request(
        snapshot=snapshot,
        selected_headings=[_DIRECT_HEADING],
        base_revision=revision,
        planning_input=None,
    )

    context = json.loads(request.untrusted_context)
    assert context["approved_source_facts_for_selected_sections"] == []


def test_official_regulatory_fact_is_not_duplicated_as_approved_source_fact(
    section_repair_context: tuple[
        ContentPlanningInput,
        ContentWorkItemWorkflowSnapshotResponse,
        ContentDraftRevision,
    ],
) -> None:
    planning_input, snapshot, revision = section_repair_context

    request = proposal_turn.codex_turn_request(
        snapshot=snapshot,
        selected_headings=[_REGULATORY_HEADING],
        base_revision=revision,
        planning_input=planning_input,
    )

    context = json.loads(request.untrusted_context)
    assert _source_fact_ids(context) == ["service_fallback_fact"]
    assert [
        fact["source_fact_id"]
        for fact in context["approved_regulatory_facts_for_selected_sections"]
    ] == ["official_reporting_fact"]


def _source_fact_ids(context: dict[str, object]) -> list[str]:
    facts = cast(
        list[dict[str, object]],
        context["approved_source_facts_for_selected_sections"],
    )
    return [str(fact["source_fact_id"]) for fact in facts]


def _approved_fact(
    source_id: str,
    *,
    target_card_id: str,
    target_card_type: str = "evidence_requirement",
    service_fit_terms: list[str] | None = None,
    buyer_problem_terms: list[str] | None = None,
    official_source: bool = False,
) -> ContentSourceFact:
    return ContentSourceFact(
        source_id=source_id,
        source_type="legal_update" if official_source else "public_site",
        privacy_class="commit_safe",
        source_url_or_path=f"https://www.ekologus.pl/{source_id}/",
        extracted_fact=f"Konkretny zatwierdzony fakt: {source_id}.",
        scope="service",
        freshness_date="2026-08-13",
        confidence=1,
        review_status="approved",
        reviewer="wilku",
        evidence_ids=[f"ev_{source_id}"],
        source_connectors=["official_source" if official_source else "public_site"],
        target_card_id=target_card_id,
        target_card_type=target_card_type,
        target_card_title=(
            f"Usługa {source_id}" if target_card_type == "service" else f"Materiał {source_id}"
        ),
        service_fit_terms=service_fit_terms or [],
        buyer_problem_terms=buyer_problem_terms or [],
        official_source=official_source,
        regulatory_profile_id="bdo" if official_source else None,
        regulatory_profile_version="2026-08" if official_source else None,
        regulatory_requirement_ids=["reporting"] if official_source else [],
        applicable_service_card_ids=[_SERVICE_CARD_ID] if official_source else [],
    )
