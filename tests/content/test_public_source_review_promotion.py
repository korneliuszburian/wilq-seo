from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.knowledge.public_source_reviews import (
    ContentPublicSourceReviewCommand,
    PublicSourceReviewStore,
    public_source_fact_digest,
)
from wilq.content.knowledge.source_facts import (
    ekologus_seed_source_facts,
    ekologus_source_facts,
)

SOURCE_ID = "ekologus_public_training_offer_2026_07_01"
TARGET_CARD_ID = "ekologus_service_environmental_training"


def _command(candidate_digest: str) -> ContentPublicSourceReviewCommand:
    return ContentPublicSourceReviewCommand(
        source_id=SOURCE_ID,
        expected_source_fact_digest=candidate_digest,
        target_card_id=TARGET_CARD_ID,
        decision="approve",
        reviewer="Korneliusz Burian",
        notes=(
            "Zatwierdzono dokładny publiczny zakres szkoleń; ceny, terminy, "
            "dostępność, certyfikaty i gwarancje pozostają zablokowane."
        ),
        source_trace_clear=True,
        blocked_claims_reviewed=True,
    )


def test_approved_public_review_projects_exact_approved_service_fact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(database))
    candidate = next(
        fact for fact in ekologus_seed_source_facts() if fact.source_id == SOURCE_ID
    )
    command = _command(public_source_fact_digest(candidate))
    store = PublicSourceReviewStore(database)

    response = store.record(command, candidates=ekologus_seed_source_facts())
    replay = store.record(command, candidates=ekologus_seed_source_facts())

    assert response.status == "approved"
    assert replay.status == "idempotent"
    assert replay.review.review_id == response.review.review_id
    ekologus_content_knowledge_cards.cache_clear()
    facts = ekologus_source_facts()
    assert SOURCE_ID not in {fact.source_id for fact in facts}
    approved_fact = next(
        fact for fact in facts if fact.source_id == response.approved_source_fact_id
    )
    assert approved_fact.review_status == "approved"
    assert approved_fact.source_url_or_path == candidate.source_url_or_path
    assert approved_fact.evidence_ids == ["ev_content_service_profile_source_facts"]
    card = next(card for card in ekologus_content_knowledge_cards() if card.id == TARGET_CARD_ID)
    assert card.lifecycle_status == "approved_current"
    assert approved_fact.source_id in card.source_fact_ids
    ekologus_content_knowledge_cards.cache_clear()


def test_public_review_fails_closed_when_exact_source_fact_changes(tmp_path: Path) -> None:
    candidate = next(
        fact for fact in ekologus_seed_source_facts() if fact.source_id == SOURCE_ID
    )

    with pytest.raises(ValueError, match="public_source_fact_changed"):
        PublicSourceReviewStore(tmp_path / "state.sqlite3").record(
            _command("0" * 64),
            candidates=ekologus_seed_source_facts(),
        )

    assert public_source_fact_digest(candidate) != "0" * 64


def test_public_source_review_route_persists_a_typed_approved_projection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The public API route must expose the same exact-review authority as the store."""

    database = tmp_path / "state.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(database))
    candidate = next(
        fact for fact in ekologus_seed_source_facts() if fact.source_id == SOURCE_ID
    )
    command = _command(public_source_fact_digest(candidate))

    ekologus_content_knowledge_cards.cache_clear()
    response = TestClient(app).post(
        "/api/content/public-source-reviews",
        json=command.model_dump(mode="json"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved"
    assert payload["review"]["source_id"] == SOURCE_ID
    assert payload["review"]["target_card_id"] == TARGET_CARD_ID
    assert payload["approved_source_fact_id"].startswith("public_source_review_fact_")
    ekologus_content_knowledge_cards.cache_clear()
