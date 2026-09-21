"""Parent-safe observer for one critic turn carrying all constraints."""

from __future__ import annotations

from types import SimpleNamespace

from wilq.content.drafts.initial_full_draft_contracts import ContentInitialDraftSectionOutput
from wilq.content.regulatory.policy import (
    ContentRegulatoryProfile,
    ContentRegulatoryRequirement,
)


def _profile() -> ContentRegulatoryProfile:
    return ContentRegulatoryProfile(
        id="assurance_batching_contract",
        version="2026-09-21",
        service_card_ids=["service_assurance_batching_contract"],
        official_source_hosts=["example.gov.pl"],
        max_source_age_days=30,
        requirements=[
            ContentRegulatoryRequirement(
                id=f"requirement_{index}",
                label=f"Wymóg {index}",
                reason="Kontrakt obserwatora.",
            )
            for index in range(2)
        ],
    )


def _turn_requests():
    try:
        from wilq.content.drafts.draft_assurance import draft_assurance_turn_requests
    except ImportError:  # pragma: no cover - parent tree may lack the seam
        return None
    return draft_assurance_turn_requests


def test_regulatory_assurance_batches_all_constraints_in_one_turn() -> None:
    turn_requests = _turn_requests()
    assert turn_requests is not None, "draft assurance request compiler is required"

    profile = _profile()
    requests = turn_requests(
        planning_input=SimpleNamespace(
            work_item_id="work_item_assurance_batching_contract",
            planning_input_digest="a" * 64,
            confirmed_service_card_id="service_assurance_batching_contract",
            regulatory_coverage=SimpleNamespace(evidence_ids=[]),
        ),
        proposal=SimpleNamespace(
            sections=[
                SimpleNamespace(
                    section_id="section_assurance_batching_contract",
                    regulatory_requirement_ids=[
                        "requirement_0",
                        "requirement_1",
                    ],
                )
            ]
        ),
        output=SimpleNamespace(
            sections=[
                ContentInitialDraftSectionOutput(
                    section_id="section_assurance_batching_contract",
                    heading="Sekcja kontraktu",
                    body_markdown="Treść kontraktu.",
                )
            ]
        ),
        profile=profile,
        prepared_plan=SimpleNamespace(target_supports=[]),
    )

    assert len(requests) == 1
