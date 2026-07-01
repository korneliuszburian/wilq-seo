from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.content_workflow import router
from wilq.content.knowledge.cards import (
    content_knowledge_card_blockers,
    content_knowledge_cards_response,
    ekologus_content_knowledge_cards,
    match_content_knowledge_cards,
    required_content_knowledge_card_ids,
)
from wilq.content.workflow.models import ContentWorkItem


def _item(**overrides: object) -> ContentWorkItem:
    payload: dict[str, Any] = {
        "id": "content_work_item_bdo",
        "topic": "BDO dla firm",
        "source_public_url": "https://ekologus.pl/bdo/",
        "final_canonical_url": "https://ekologus.pl/bdo/",
        "intended_final_url": "https://ekologus.pl/bdo/",
        "preview_url": "https://ekologus.dev.proudsite.pl/bdo/",
        "evidence_ids": ["ev_gsc_bdo", "ev_wp_bdo"],
        "source_connectors": ["google_search_console", "wordpress_ekologus"],
        "inventory_status": "resolved",
        "canonical_status": "resolved",
        "duplicate_status": "checked",
    }
    payload.update(overrides)
    return ContentWorkItem.model_validate(payload)


def test_ekologus_content_knowledge_cards_are_typed_and_seeded() -> None:
    cards = ekologus_content_knowledge_cards()

    assert {card.id for card in cards} >= {
        "ekologus_service_environmental_compliance",
        "ekologus_cta_consultation_without_guarantee",
        "ekologus_evidence_live_connector_requirement",
    }
    service_card = next(card for card in cards if card.card_type == "service")
    assert service_card.confidence >= 0.8
    assert service_card.source_lineage
    assert service_card.claims_needing_review
    assert service_card.forbidden_claims
    assert service_card.measurement_sensitive_claims
    assert "bdo" in service_card.service_fit_terms


def test_knowledge_cards_response_exposes_lineage_without_replacing_evidence() -> None:
    response = content_knowledge_cards_response()

    assert response.card_count == len(response.cards)
    assert "docs/goals/archive/004-goal.md" in response.source_lineage
    evidence_card = next(
        card for card in response.cards if card.id == "ekologus_evidence_live_connector_requirement"
    )
    assert any(
        "Brak evidence ID" in requirement
        for requirement in evidence_card.evidence_requirements
    )
    assert any("nie zastępuje" in note for note in evidence_card.usage_notes)


def test_work_item_matches_required_service_cta_claim_and_evidence_cards() -> None:
    match = match_content_knowledge_cards(_item())

    assert match.blockers == []
    assert match.service_card is not None
    assert match.cta_cards
    assert match.claim_policy_cards
    assert match.evidence_requirement_cards
    assert required_content_knowledge_card_ids(match) == [
        "ekologus_service_environmental_compliance",
        "ekologus_cta_consultation_without_guarantee",
        "ekologus_evidence_live_connector_requirement",
    ]


def test_unknown_topic_blocks_required_service_and_cta_cards() -> None:
    match = match_content_knowledge_cards(
        _item(
            topic="Neutralny temat bez dopasowania",
            source_public_url="https://ekologus.pl/neutralny-temat/",
            final_canonical_url="https://ekologus.pl/neutralny-temat/",
            intended_final_url="https://ekologus.pl/neutralny-temat/",
            evidence_ids=["ev_neutral"],
        )
    )

    blocker_codes = {blocker.code for blocker in content_knowledge_card_blockers(match)}
    assert {"missing_service_card", "missing_cta_card"} <= blocker_codes
    assert "missing_claim_policy_card" not in blocker_codes
    assert "missing_evidence_requirement_card" not in blocker_codes


def test_content_knowledge_cards_endpoint_exposes_typed_cards() -> None:
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/api/content/knowledge-cards")

    assert response.status_code == 200
    payload = response.json()
    assert payload["card_count"] >= 3
    assert {card["id"] for card in payload["cards"]} >= {
        "ekologus_service_environmental_compliance",
        "ekologus_cta_consultation_without_guarantee",
        "ekologus_evidence_live_connector_requirement",
    }
    assert "docs/goals/archive/004-goal.md" in payload["source_lineage"]
