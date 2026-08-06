from __future__ import annotations

from pathlib import Path

import pytest

from wilq.content.knowledge.cards import (
    ekologus_content_knowledge_cards,
)
from wilq.content.knowledge.private_source_reviews import (
    ContentPrivateSourceReviewCommand,
    PrivateSourceReviewStore,
    private_source_fact_digest,
)
from wilq.content.knowledge.source_facts import (
    ekologus_seed_source_facts,
    ekologus_source_facts,
)

SOURCE_ID = "ekologus_ai_kb003_audyt_zgodnosci_review_candidate_2026_07_01"
TARGET_CARD_ID = "ekologus_service_environmental_compliance_audit"


def test_approved_private_review_projects_exact_approved_service_fact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite3"
    monkeypatch.setenv("WILQ_STATE_DB", str(database))
    candidate = next(
        fact for fact in ekologus_seed_source_facts() if fact.source_id == SOURCE_ID
    )
    command = ContentPrivateSourceReviewCommand(
        source_id=SOURCE_ID,
        expected_source_fact_digest=private_source_fact_digest(candidate),
        target_card_id=TARGET_CARD_ID,
        decision="approve",
        reviewer="Wilku / owner oferty Ekologus",
        notes="Zatwierdzono redacted opis usługi; bez gwarancji wyniku ani porady prawnej.",
        retention_decision="short_window_only",
        source_trace_clear=True,
        blocked_claims_reviewed=True,
        data_classes_confirmed=True,
        source_block_refs_confirmed=True,
        freshness_status_confirmed=True,
        audience_scope_confirmed=True,
        deletion_path_confirmed=True,
        eval_gates_confirmed=True,
    )

    response = PrivateSourceReviewStore(database).record(
        command,
        candidates=ekologus_seed_source_facts(),
    )
    replay = PrivateSourceReviewStore(database).record(
        command,
        candidates=ekologus_seed_source_facts(),
    )

    assert response.status == "approved"
    assert replay.status == "idempotent"
    assert replay.review.review_id == response.review.review_id

    ekologus_content_knowledge_cards.cache_clear()
    facts = ekologus_source_facts()
    assert SOURCE_ID not in {fact.source_id for fact in facts}
    approved_fact = next(
        fact
        for fact in facts
        if fact.source_id == response.approved_source_fact_id
    )
    assert approved_fact.review_status == "approved"
    assert approved_fact.source_connectors == ["reviewed_internal"]
    assert approved_fact.source_url_or_path == f"private-source-review:{response.review.review_id}"
    card = next(card for card in ekologus_content_knowledge_cards() if card.id == TARGET_CARD_ID)
    assert card.lifecycle_status == "approved_current"
    assert approved_fact.source_id in card.source_fact_ids
    ekologus_content_knowledge_cards.cache_clear()


def test_private_review_fails_closed_when_the_exact_source_fact_changes(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite3"
    candidate = next(
        fact for fact in ekologus_seed_source_facts() if fact.source_id == SOURCE_ID
    )
    command = ContentPrivateSourceReviewCommand(
        source_id=SOURCE_ID,
        expected_source_fact_digest="0" * 64,
        target_card_id=TARGET_CARD_ID,
        decision="approve",
        reviewer="Wilku / owner oferty Ekologus",
        notes="Nie powinno dojść do zatwierdzenia zmienionego źródła.",
        retention_decision="short_window_only",
        source_trace_clear=True,
        blocked_claims_reviewed=True,
        data_classes_confirmed=True,
        source_block_refs_confirmed=True,
        freshness_status_confirmed=True,
        audience_scope_confirmed=True,
        deletion_path_confirmed=True,
        eval_gates_confirmed=True,
    )

    assert command.expected_source_fact_digest != private_source_fact_digest(candidate)
    with pytest.raises(ValueError, match="private_source_fact_changed"):
        PrivateSourceReviewStore(database).record(
            command,
            candidates=ekologus_seed_source_facts(),
        )
