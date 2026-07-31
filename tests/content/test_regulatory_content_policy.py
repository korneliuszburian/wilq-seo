from __future__ import annotations

from datetime import date

from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.regulatory.planning import regulatory_planning_source_facts
from wilq.content.regulatory.policy import (
    ContentRegulatoryProfile,
    ContentRegulatoryRequirement,
    regulatory_content_coverage,
    regulatory_content_profile,
)


def _profile() -> ContentRegulatoryProfile:
    return ContentRegulatoryProfile(
        id="water_permit",
        version="2026-07",
        service_card_ids=["service_water_permit"],
        official_source_hosts=["gov.example"],
        max_source_age_days=90,
        requirements=[
            ContentRegulatoryRequirement(
                id="water_permit_scope",
                label="zakres operatu",
                reason="Zakres wymaga aktualnego źródła urzędowego.",
            ),
            ContentRegulatoryRequirement(
                id="water_permit_deadlines",
                label="terminy i tryb",
                reason="Terminy wymagają aktualnego źródła urzędowego.",
            ),
        ],
    )


def _official_fact(
    *,
    requirement_ids: list[str],
    service_card_ids: list[str] | None = None,
    version: str = "2026-07",
    freshness_date: str = "2026-07-15",
    approved: bool = True,
) -> ContentSourceFact:
    return ContentSourceFact(
        source_id="official_water_permit_test",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://gov.example/water-permit",
        extracted_fact="Oficjalny serwis opisuje obowiązki wymagające weryfikacji.",
        scope="claim_policy",
        freshness_date=freshness_date,
        confidence=1,
        review_status="approved" if approved else "review_required",
        reviewer="wilku" if approved else None,
        evidence_ids=["ev_official_water_permit"] if approved else [],
        source_connectors=["official_regulator"],
        target_card_id="regulatory_water_permit",
        target_card_type="regulatory_source",
        target_card_title="Oficjalne źródło operatu wodnoprawnego",
        official_source=True,
        regulatory_profile_id="water_permit",
        regulatory_profile_version=version,
        regulatory_requirement_ids=requirement_ids,
        applicable_service_card_ids=service_card_ids or ["service_water_permit"],
    )


def test_coverage_is_exactly_bound_to_profile_version_service_and_evidence() -> None:
    profile = _profile()
    fact = _official_fact(
        requirement_ids=["water_permit_scope", "water_permit_deadlines"],
    )

    coverage = regulatory_content_coverage(
        service_card_id="service_water_permit",
        source_facts=(fact,),
        profiles=(profile,),
        as_of=date(2026, 7, 31),
    )

    assert coverage.complete
    assert coverage.profile_id == "water_permit"
    assert coverage.profile_version == "2026-07"
    assert coverage.source_fact_ids == ["official_water_permit_test"]
    assert coverage.evidence_ids == ["ev_official_water_permit"]
    assert [item.requirement_id for item in coverage.requirement_coverage] == [
        "water_permit_scope",
        "water_permit_deadlines",
    ]
    planning_facts = regulatory_planning_source_facts(
        coverage,
        knowledge_card_ids=["service_water_permit"],
        source_material_ids=["material_water_permit"],
    )
    assert len(planning_facts) == 1
    assert planning_facts[0].evidence_ids == ["ev_official_water_permit"]
    assert planning_facts[0].regulatory_requirement_ids == [
        "water_permit_deadlines",
        "water_permit_scope",
    ]


def test_coverage_fails_closed_for_wrong_service_version_or_stale_source() -> None:
    profile = _profile()
    requirements = ["water_permit_scope", "water_permit_deadlines"]
    invalid_facts = (
        _official_fact(requirement_ids=requirements, service_card_ids=["other_service"]),
        _official_fact(requirement_ids=requirements, version="2026-06"),
        _official_fact(requirement_ids=requirements, freshness_date="2025-01-01"),
    )

    for fact in invalid_facts:
        coverage = regulatory_content_coverage(
            service_card_id="service_water_permit",
            source_facts=(fact,),
            profiles=(profile,),
            as_of=date(2026, 7, 31),
        )

        assert not coverage.complete
        assert coverage.source_fact_ids == []
        assert coverage.evidence_ids == []


def test_bdo_is_an_explicit_data_profile_not_a_planner_branch() -> None:
    profile = regulatory_content_profile(
        service_card_id="ekologus_service_bdo_reporting"
    )

    assert profile is not None
    assert profile.id == "bdo"
    assert profile.version == "2026-07"
    assert profile.official_source_hosts == ["bdo.mos.gov.pl"]
    assert [requirement.id for requirement in profile.requirements] == [
        "bdo_scope",
        "bdo_registration_and_updates",
        "bdo_records_and_kpo",
        "bdo_reporting",
        "bdo_access_and_account",
        "bdo_risks_and_sanctions",
    ]
