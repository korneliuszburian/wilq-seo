"""Parent-safe observer for the single existing-page body projection."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from wilq.content.drafts.initial_full_draft_turn import initial_full_draft_turn_request
from wilq.content.planning.dynamic_input import ContentPlanningInput
from wilq.content.planning.input_sources import (
    ContentPlanningInventory,
    ContentPlanningInventorySection,
)
from wilq.content.regulatory.policy import ContentRegulatoryCoverage
from wilq.content.workflow.decisions.demand_evidence import ContentSearchDemandEvidence
from wilq.content.workflow.decisions.planning import ContentPlanningProposal


@pytest.mark.parametrize("existing_content_text", ["SENTINEL_REFRESH_BODY", ""])
def test_initial_draft_turn_sends_existing_body_once_only_for_refresh(
    existing_content_text: str,
) -> None:
    sentinel_body = "SENTINEL_REFRESH_BODY"
    content_summary = "Skrót istniejącej strony."
    inventory = ContentPlanningInventory(
        status="available",
        content_status="available",
        title_or_h1="Istniejąca strona",
        content_summary=content_summary,
        content_text=sentinel_body,
        sections=[
            ContentPlanningInventorySection(
                section_id="inventory_section_01",
                heading="Zachowany nagłówek",
                evidence_ids=["ev_inventory_section"],
            )
        ],
        evidence_ids=["ev_inventory"],
        source_connectors=["wordpress_ekologus"],
    )
    planning_input = ContentPlanningInput.model_construct(
        work_item_id="content_work_item_existing_body_once",
        planning_input_digest="a" * 64,
        final_canonical_url="https://www.ekologus.pl/istniejaca-strona/",
        confirmed_service_card_id="service_existing_body_once",
        service_label="Istniejąca usługa",
        inventory=inventory,
        target_reader="Przedsiębiorca",
        buyer_problem="Brak uporządkowanej dokumentacji.",
        buyer_trigger="Zbliża się termin.",
        search_intent="istniejąca strona",
        source_facts=[],
        source_assessments=[],
        regulatory_coverage=ContentRegulatoryCoverage(),
        query_portfolio=ContentSearchDemandEvidence(
            status="missing",
            optional_ads_status="not_exactly_mapped",
            safe_next_step="Brak exact zapytań.",
        ),
        measurement_observation_rule="Porównaj zamknięte okresy.",
        measurement_success_claim_rule="Nie claimuj bez dowodu.",
        baseline_cta_direction="Opisz sytuację firmy.",
    )
    proposal = ContentPlanningProposal.model_construct(
        work_item_id=planning_input.work_item_id,
        proposal_id="proposal_existing_body_once",
        planning_digest="b" * 64,
        planning_input_digest=planning_input.planning_input_digest,
        final_canonical_url=planning_input.final_canonical_url,
        service_card_id=planning_input.confirmed_service_card_id,
        service_label=planning_input.service_label,
        target_reader=planning_input.target_reader,
        buyer_problem=planning_input.buyer_problem,
        buyer_trigger=planning_input.buyer_trigger,
        search_intent=planning_input.search_intent,
        cta_direction=planning_input.baseline_cta_direction,
        sections=[],
        faq=[],
        cta_blocks=[],
        internal_links=[],
    )
    generation_contract = SimpleNamespace(
        model_input=SimpleNamespace(
            existing_content_text=existing_content_text,
            model_dump=lambda mode: {"existing_content_text": existing_content_text},
        )
    )

    request = initial_full_draft_turn_request(
        planning_input=planning_input,
        proposal=proposal,
        generation_contract=generation_contract,
    )

    context = json.loads(request.untrusted_context)
    context_inventory = context["planning_input"]["inventory"]
    assert context["generation_constraints"]["existing_content_text"] == existing_content_text
    assert context_inventory["evidence_ids"] == ["ev_inventory"]
    assert context_inventory["sections"] == [
        {
            "section_id": "inventory_section_01",
            "heading": "Zachowany nagłówek",
            "recommended_disposition": "preserve",
            "evidence_ids": ["ev_inventory_section"],
        }
    ]
    if existing_content_text:
        assert request.untrusted_context.count(sentinel_body) == 1
        assert "content_text" not in context_inventory
        assert "content_summary" not in context_inventory
    else:
        assert context_inventory["content_text"] == sentinel_body
        assert context_inventory["content_summary"] == content_summary
    assert planning_input.inventory.content_text == sentinel_body
    assert planning_input.inventory.content_summary == content_summary


def _body_stripper():
    try:
        from wilq.content.planning.compact_projections import (
            strip_existing_content_from_initial_draft_planning_input,
        )
    except (AttributeError, ImportError):  # pragma: no cover - parent-safe guard
        return None
    return strip_existing_content_from_initial_draft_planning_input


def test_initial_draft_projection_drops_only_duplicate_inventory_body() -> None:
    strip_body = _body_stripper()
    assert strip_body is not None, "initial-draft body projection seam is required"

    original = {
        "inventory": {
            "content_text": "SENTINEL_REFRESH_BODY",
            "content_summary": "Skrót istniejącej strony.",
            "evidence_ids": ["ev_inventory"],
            "sections": [{"heading": "Zachowany nagłówek"}],
        },
        "evidence_ids": ["ev_planning"],
    }

    projected = strip_body(original, "SENTINEL_REFRESH_BODY")

    assert projected is not original
    assert projected["inventory"] == {
        "evidence_ids": ["ev_inventory"],
        "sections": [{"heading": "Zachowany nagłówek"}],
    }
    assert projected["evidence_ids"] == ["ev_planning"]
    assert original["inventory"]["content_text"] == "SENTINEL_REFRESH_BODY"
    assert original["inventory"]["content_summary"] == "Skrót istniejącej strony."
