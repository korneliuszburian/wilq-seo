from datetime import date
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from wilq.content.drafts.draft_assurance import regulatory_draft_assurance_profile
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import ContentPlanningSourceAssessment
from wilq.content.planning.input_summary import content_planning_input_summary
from wilq.content.regulatory.policy import (
    ContentRegulatoryCoverage,
    ContentRegulatoryProfile,
    ContentRegulatoryRequirement,
    regulatory_content_coverage,
    regulatory_content_profile,
    regulatory_coverage_gap,
    regulatory_requirement_assertion_errors,
    regulatory_review_candidates,
    regulatory_source_candidates,
)
from wilq.content.regulatory.source_snapshots import RegulatorySourceSnapshotStore

CANONICAL_PATH = "/analiza-pozwolen-zintegrowanych"
REACH_CLP_PATH = (
    "/obowiazki-przedsiebiorstw-w-zakresie-rozporzadzenia-reach-i-clp-"
    "ze-szczegolnym-uwzglednieniem-zmian-w-kartach-charakterystyki"
)


def test_integrated_permit_article_has_exact_required_profile() -> None:
    profile = regulatory_content_profile(
        service_card_id=None,
        canonical_path=CANONICAL_PATH,
    )
    coverage = regulatory_content_coverage(
        service_card_id=None,
        canonical_path=CANONICAL_PATH,
        source_facts=(),
        as_of=date(2026, 8, 31),
    )

    assert profile is not None
    assert profile.id == "integrated_permit_editorial"
    assert coverage.applicability_status == "required"
    assert coverage.profile_id == profile.id
    assert coverage.canonical_path == CANONICAL_PATH
    assert {item.id for item in coverage.missing_requirements} == {
        "integrated_permit_distinct_decisions",
        "integrated_permit_initial_report",
        "integrated_permit_case_scope",
    }
    assert regulatory_coverage_gap(coverage) is not None


def test_integrated_permit_article_exposes_current_official_review_candidates() -> None:
    coverage = regulatory_content_coverage(
        service_card_id=None,
        canonical_path=CANONICAL_PATH,
        source_facts=(),
        as_of=date(2026, 8, 31),
    )
    candidates = regulatory_review_candidates(
        service_card_id=None,
        canonical_path=CANONICAL_PATH,
        coverage=coverage,
        as_of=date(2026, 8, 31),
    )

    assert {item.candidate_id for item in candidates} == {
        "integrated_permit_oos_eli_2026_08_30_r1",
        "integrated_permit_pos_eli_2026_08_31_r1",
        "integrated_permit_ekoportal_2026_08_30_r1",
    }
    ekoportal = next(
        item
        for item in candidates
        if item.candidate_id == "integrated_permit_ekoportal_2026_08_30_r1"
    )
    assert ekoportal.requirement_ids == ["integrated_permit_initial_report"]


def test_reach_clp_article_has_exact_editorial_profile_and_official_candidates() -> None:
    profile = regulatory_content_profile(
        service_card_id=None,
        canonical_path=REACH_CLP_PATH,
    )
    coverage = regulatory_content_coverage(
        service_card_id=None,
        canonical_path=REACH_CLP_PATH,
        source_facts=(),
        as_of=date(2026, 9, 1),
    )
    candidates = regulatory_review_candidates(
        service_card_id=None,
        canonical_path=REACH_CLP_PATH,
        coverage=coverage,
        as_of=date(2026, 9, 1),
    )

    assert profile is not None
    assert profile.id == "reach_clp_editorial"
    assert coverage.applicability_status == "required"
    assert {item.id for item in coverage.missing_requirements} == {
        "reach_clp_distinct_scope",
        "reach_registration_scope",
        "reach_authorisation_scope",
        "reach_restriction_scope",
        "reach_sds_scope",
        "clp_classification_labelling",
    }
    assert {item.candidate_id for item in candidates} == {
        "reach_scope_gov_pl_2026_09_01_r1",
        "reach_registration_gov_pl_2026_09_01_r1",
        "reach_authorisation_gov_pl_2026_09_01_r1",
        "reach_restrictions_gov_pl_2026_09_01_r1",
        "reach_sds_gov_pl_2026_09_01_r1",
        "clp_gov_pl_2026_09_01_r1",
    }


@pytest.mark.parametrize(
    ("requirement_id", "insufficient_text"),
    [
        ("reach_clp_distinct_scope", "Informacje o REACH."),
        ("reach_registration_scope", "Importer przekracza 1 tonę rocznie."),
        ("reach_authorisation_scope", "Substancja znajduje się w załączniku XIV."),
        ("reach_restriction_scope", "Sprawdź warunki ograniczenia."),
        ("reach_sds_scope", "Zaktualizuj kartę charakterystyki."),
        ("clp_classification_labelling", "Producent odpowiada za opakowanie."),
    ],
)
def test_reach_clp_profile_rejects_partial_regulatory_phrases(
    requirement_id: str,
    insufficient_text: str,
) -> None:
    profile = regulatory_content_profile(
        service_card_id=None,
        canonical_path=REACH_CLP_PATH,
    )
    assert profile is not None
    requirement = next(item for item in profile.requirements if item.id == requirement_id)

    assert regulatory_requirement_assertion_errors(
        requirement=requirement,
        text=insufficient_text,
    )


def test_unprofiled_editorial_scope_does_not_invent_a_regulatory_gate() -> None:
    coverage = regulatory_content_coverage(
        service_card_id=None,
        canonical_path="/artykul-bez-oceny-regulacyjnej",
        source_facts=(),
        as_of=date(2026, 8, 31),
    )

    gap = regulatory_coverage_gap(coverage)
    assert coverage.applicability_status == "not_required"
    assert coverage.complete is True
    assert gap is None


def test_editorial_draft_assurance_resolves_profile_without_service_card() -> None:
    coverage = regulatory_content_coverage(
        service_card_id=None,
        canonical_path=CANONICAL_PATH,
        source_facts=(),
        as_of=date(2026, 8, 31),
    )
    planning_input = ContentPlanningInput.model_construct(
        work_item_id="content_work_item_integrated_permit",
        planning_input_digest="a" * 64,
        content_kind="editorial",
        confirmed_service_card_id=None,
        regulatory_coverage=coverage,
    )

    profile = regulatory_draft_assurance_profile(planning_input)
    assert profile is not None
    assert profile.id == "integrated_permit_editorial"


def test_mixed_service_and_canonical_subjects_are_rejected() -> None:
    requirement = ContentRegulatoryRequirement(id="scope", label="Zakres", reason="Test")
    profiles = (
        ContentRegulatoryProfile(
            id="profile_a",
            version="v1",
            service_card_ids=["service_a"],
            canonical_paths=["/path-a"],
            official_source_hosts=["a.gov.pl"],
            max_source_age_days=30,
            requirements=[requirement],
        ),
        ContentRegulatoryProfile(
            id="profile_b",
            version="v1",
            service_card_ids=["service_b"],
            canonical_paths=["/path-b"],
            official_source_hosts=["b.gov.pl"],
            max_source_age_days=30,
            requirements=[requirement],
        ),
    )

    with pytest.raises(ValueError, match="different profiles"):
        regulatory_content_profile(
            service_card_id="service_a",
            canonical_path="/path-b",
            profiles=profiles,
        )


def test_explicit_not_required_cannot_hide_regulatory_payload() -> None:
    with pytest.raises(ValidationError, match="cannot carry regulatory payload"):
        ContentRegulatoryCoverage(
            applicability_status="not_required",
            profile_id="regulated",
            profile_version="v1",
            requirements=[
                ContentRegulatoryRequirement(id="scope", label="Zakres", reason="Test")
            ],
        )


def test_editorial_summary_exposes_regulatory_candidates() -> None:
    coverage = regulatory_content_coverage(
        service_card_id=None,
        canonical_path=CANONICAL_PATH,
        source_facts=(),
        as_of=date(2026, 8, 31),
    )
    planning_input = SimpleNamespace(
        goal="refresh_existing",
        final_canonical_url="https://www.ekologus.pl" + CANONICAL_PATH + "/",
        proposed_ia_location=None,
        content_kind="editorial",
        service_label=None,
        inventory=SimpleNamespace(
            status="available",
            content_status="available",
            acf_section_status="missing",
        ),
        source_assessments=[
            ContentPlanningSourceAssessment(
                source=source,
                status="not_applicable",
                reason="Testowy stan źródła.",
            )
            for source in (
                "wordpress", "service_profile", "gsc", "ga4", "google_ads", "ahrefs",
                "keyword_planner", "merchant", "localo", "social",
            )
        ],
        source_facts=[],
        query_portfolio=SimpleNamespace(gsc_query_rows=[]),
        regulatory_coverage=coverage,
        confirmed_service_card_id=None,
        evidence_ids=[],
        knowledge_card_ids=[],
        measurement_metrics=[],
        metric_comparisons=[],
    )

    summary = content_planning_input_summary(planning_input)
    assert summary.regulatory_applicability_status == "required"
    assert len(summary.regulatory_review_candidates) == 3


def test_bare_eli_metadata_page_is_not_a_reviewable_source(tmp_path) -> None:
    candidate = next(
        item
        for item in regulatory_source_candidates()
        if item.candidate_id == "integrated_permit_oos_eli_2026_08_30_r1"
    ).model_copy(update={"source_url": "https://eli.gov.pl/eli/DU/2026/670/ogl"})

    with pytest.raises(ValueError, match="allowlisted official HTTPS source"):
        RegulatorySourceSnapshotStore(tmp_path / "state.sqlite3").capture(
            candidate.candidate_id,
            candidates=(candidate,),
            reader=lambda _url: (b"metadata only", "text/html"),
        )
