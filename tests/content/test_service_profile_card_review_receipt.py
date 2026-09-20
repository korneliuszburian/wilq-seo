from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from apps.api.wilq_api.main import app
from wilq.content.knowledge.cards import ekologus_content_knowledge_cards
from wilq.content.knowledge.service_profile.core import content_service_profile_response
from wilq.content.knowledge.service_profile.review_receipts import (
    ContentServiceCardReviewCommand,
    ContentServiceCardReviewStore,
    service_profile_source_fact_digest,
    service_profile_source_set_digest,
)
from wilq.content.knowledge.source_facts import ekologus_source_facts
from wilq.content.workflow.source_fact_authority import (
    build_content_source_fact_authority_candidate_projection,
)

TARGET_CARD_ID = "ekologus_service_environmental_training"
IDENTITY_BINDING_ID = "content_delivery_identity_5239259909e4eab21cfb2f71"
ACTION_ID = f"service_profile_review_card_{TARGET_CARD_ID}"


def _authority_inputs() -> tuple[SimpleNamespace, SimpleNamespace]:
    identity = SimpleNamespace(
        binding_id=IDENTITY_BINDING_ID,
        binding_digest="a" * 64,
        status="exact_current",
        current_work_item_id="content_work_item_environmental_training",
        canonical_path="/oferta/szkolenia",
        public_url="https://www.ekologus.pl/oferta/szkolenia/",
        classification_run_id="classification_training",
        classification_run_digest="b" * 64,
        classification_decision_set_digest="c" * 64,
        classification_source_row_digest="d" * 64,
        inventory_evidence_ids=("ev_inventory_training",),
        final_disposition="keep",
    )
    classification = SimpleNamespace(
        run_id=identity.classification_run_id,
        run_digest=identity.classification_run_digest,
        decision_set_digest=identity.classification_decision_set_digest,
        freshness=SimpleNamespace(requires_refresh=False, state="fresh"),
        row=SimpleNamespace(
            current_work_item_id=identity.current_work_item_id,
            canonical_path=identity.canonical_path,
            public_url=identity.public_url,
            source_packet_row_digest=identity.classification_source_row_digest,
            primary_evidence_ids=identity.inventory_evidence_ids,
        ),
    )
    return identity, classification


def test_service_profile_approval_receipt_unlocks_only_exact_card_and_candidates(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state.sqlite3"))
    ekologus_content_knowledge_cards.cache_clear()
    facts = tuple(ekologus_source_facts())
    card = next(card for card in ekologus_content_knowledge_cards() if card.id == TARGET_CARD_ID)

    identity, classification = _authority_inputs()
    baseline_projection = build_content_source_fact_authority_candidate_projection(
        IDENTITY_BINDING_ID,
        identity=identity,
        classification=classification,
        facts=facts,
        cards=tuple(ekologus_content_knowledge_cards()),
        checked_at=datetime(2026, 9, 20, tzinfo=UTC),
    )
    assert card.lifecycle_status == "source_backed_review_required"
    assert baseline_projection.status == "evidence_acquisition_needed"
    assert baseline_projection.eligible_candidates == ()
    assert baseline_projection.review_required_candidates
    assert all(
        not candidate.selectable
        for candidate in baseline_projection.review_required_candidates
    )

    card_facts = tuple(fact for fact in facts if fact.source_id in card.source_fact_ids)
    source_fact_ids = tuple(sorted(fact.source_id for fact in card_facts))
    source_fact_digests = tuple(
        sorted(service_profile_source_fact_digest(fact) for fact in card_facts)
    )
    source_set_digest = service_profile_source_set_digest(
        source_fact_ids,
        source_fact_digests,
    )
    registry_digest = __import__(
        "wilq.content.workflow.source_pack_binding",
        fromlist=["source_fact_registry_digest"],
    ).source_fact_registry_digest(facts)
    command = ContentServiceCardReviewCommand(
        action_id=ACTION_ID,
        card_id=TARGET_CARD_ID,
        source_fact_registry_digest=registry_digest,
        source_fact_ids=source_fact_ids,
        source_fact_digests=source_fact_digests,
        source_set_digest=source_set_digest,
        decision="approve",
        reviewer="Wilku",
        notes="Sprawdzono exact zakres oferty i pozostawiono blokady claimów.",
        source_trace_clear=True,
        blocked_claims_reviewed=True,
    )

    client = TestClient(app)
    response = client.post(
        "/api/content/service-profile/card-reviews",
        json=command.model_dump(mode="json"),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "approved"
    assert payload["receipt"]["action_id"] == ACTION_ID
    assert payload["receipt"]["card_id"] == TARGET_CARD_ID
    assert payload["receipt"]["source_fact_registry_digest"] == registry_digest
    assert payload["receipt"]["source_fact_ids"] == list(command.source_fact_ids)
    assert payload["receipt"]["reviewer"] == "Wilku"
    assert payload["receipt"]["source_trace_clear"] is True
    assert payload["receipt"]["blocked_claims_reviewed"] is True

    profile = content_service_profile_response()
    section = next(item for item in profile.service_sections if item.card_id == TARGET_CARD_ID)
    assert section.status == "approved_current"
    assert section.source_lineage_labels == ["https://www.ekologus.pl/oferta/szkolenia/"]
    assert section.forbidden_claims
    assert section.claims_needing_review == []
    assert profile.coverage_summary.approved_current_count >= 2

    projection = build_content_source_fact_authority_candidate_projection(
        IDENTITY_BINDING_ID,
        identity=identity,
        classification=classification,
        facts=facts,
        cards=tuple(ekologus_content_knowledge_cards()),
        checked_at=datetime(2026, 9, 20, tzinfo=UTC),
    )
    assert projection.status == "eligible"
    assert projection.eligible_candidates
    assert all(
        "service_card_review_required" not in candidate.reasons
        for candidate in projection.eligible_candidates
    )

    replay = client.post(
        "/api/content/service-profile/card-reviews",
        json=command.model_dump(mode="json"),
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["status"] == "idempotent"
    assert replay.json()["receipt"]["receipt_id"] == payload["receipt"]["receipt_id"]

    conflict = client.post(
        "/api/content/service-profile/card-reviews",
        json=command.model_copy(update={"reviewer": "other-reviewer"}).model_dump(mode="json"),
    )
    assert conflict.status_code == 409

    readback = client.get(f"/api/content/service-profile/card-reviews/{ACTION_ID}")
    assert readback.status_code == 200, readback.text
    assert readback.json() == payload["receipt"]
    reopened = ContentServiceCardReviewStore(tmp_path / "state.sqlite3").load(ACTION_ID)
    assert reopened is not None
    assert reopened.receipt_digest == payload["receipt"]["receipt_digest"]

    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "state-no-set.sqlite3"))
    ekologus_content_knowledge_cards.cache_clear()
    no_set_command = command.model_copy(update={"source_set_digest": None})
    no_set = client.post(
        "/api/content/service-profile/card-reviews",
        json=no_set_command.model_dump(mode="json"),
    )
    assert no_set.status_code == 200, no_set.text
    assert no_set.json()["status"] == "approved"
    no_set_replay = client.post(
        "/api/content/service-profile/card-reviews",
        json=no_set_command.model_dump(mode="json"),
    )
    assert no_set_replay.status_code == 200, no_set_replay.text
    assert no_set_replay.json()["status"] == "idempotent"
