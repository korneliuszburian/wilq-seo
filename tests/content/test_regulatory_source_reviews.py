from __future__ import annotations

from datetime import UTC, datetime
from urllib.error import HTTPError

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

import wilq.content.knowledge.source_facts as source_facts_module
import wilq.content.regulatory.source_reviews as source_reviews_module
import wilq.content.regulatory.source_snapshots as source_snapshots_module
from apps.api.wilq_api.routers.content_regulatory_source_reviews import (
    register_content_regulatory_source_review_routes,
)
from wilq.content.knowledge.cards import compile_source_facts_to_knowledge_cards
from wilq.content.regulatory.policy import regulatory_content_coverage, regulatory_source_candidates
from wilq.content.regulatory.source_reviews import (
    ContentRegulatorySourceReviewCommand,
    RegulatorySourceReviewStore,
)
from wilq.content.regulatory.source_snapshots import (
    ContentRegulatorySourceSnapshot,
    RegulatorySourceSnapshotStore,
)
from wilq.evidence.registry import list_evidence_by_ids


def _command(
    *,
    candidate_id: str | None = None,
    snapshot: ContentRegulatorySourceSnapshot,
    decision: str = "accepted",
    requirement_ids: list[str] | None = None,
) -> ContentRegulatorySourceReviewCommand:
    candidate = next(
        item
        for item in regulatory_source_candidates()
        if candidate_id is None or item.candidate_id == candidate_id
    )
    return ContentRegulatorySourceReviewCommand(
        candidate_id=candidate.candidate_id,
        expected_source_url=candidate.source_url,
        expected_profile_version=candidate.profile_version,
        expected_source_snapshot_id=snapshot.snapshot_id,
        expected_source_snapshot_digest=snapshot.content_digest,
        reviewed_fact=(
            "Zatwierdzony reviewer potwierdził zakres informacji tylko dla wskazanego "
            "oficjalnego źródła i przypisanych wymagań profilu BDO."
        ),
        covered_requirement_ids=requirement_ids or [candidate.requirement_ids[0]],
        decision=decision,  # type: ignore[arg-type]
        reviewer="Wilku",
    )


def _snapshot(
    path,
    candidate_id: str,
    *,
    now: datetime | None = None,
) -> ContentRegulatorySourceSnapshot:
    return RegulatorySourceSnapshotStore(path).capture(
        candidate_id,
        reader=lambda _: (b"<html>official source snapshot</html>", "text/html"),
        now=now or datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
    )


def test_accepted_review_projects_exact_source_fact_and_resolvable_evidence(
    tmp_path, monkeypatch
) -> None:
    store = RegulatorySourceReviewStore(tmp_path / "wilq.sqlite3")
    snapshot = _snapshot(store.path, regulatory_source_candidates()[0].candidate_id)
    review = store.record(
        _command(snapshot=snapshot),
        snapshot_store=RegulatorySourceSnapshotStore(store.path),
        now=datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
    )

    monkeypatch.setattr(source_reviews_module, "regulatory_source_review_store", lambda: store)
    facts = source_facts_module.ekologus_source_facts()
    source_fact_id = f"regulatory_source_fact_{review.review_id}"
    fact = next(item for item in facts if item.source_id == source_fact_id)
    evidence = list_evidence_by_ids(fact.evidence_ids)

    assert fact.official_source is True
    assert fact.regulatory_profile_id == review.profile_id
    assert fact.regulatory_profile_version == review.profile_version
    assert fact.regulatory_requirement_ids == review.covered_requirement_ids
    assert fact.source_url_or_path == review.source_url
    assert [item.source_id for item in evidence] == [fact.source_id]
    assert [item.raw_ref for item in evidence] == [review.source_url]

    cards = compile_source_facts_to_knowledge_cards((fact,))
    assert len(cards) == 1
    assert cards[0].card_type == "regulatory_source"
    assert cards[0].source_fact_ids == [fact.source_id]


def test_rejected_review_never_projects_to_source_fact_or_coverage(tmp_path, monkeypatch) -> None:
    store = RegulatorySourceReviewStore(tmp_path / "wilq.sqlite3")
    snapshot = _snapshot(store.path, regulatory_source_candidates()[0].candidate_id)
    review = store.record(
        _command(snapshot=snapshot, decision="rejected"),
        snapshot_store=RegulatorySourceSnapshotStore(store.path),
    )
    monkeypatch.setattr(source_reviews_module, "regulatory_source_review_store", lambda: store)

    facts = source_facts_module.ekologus_source_facts()
    coverage = regulatory_content_coverage(
        service_card_id="ekologus_service_bdo_reporting",
        source_facts=facts,
    )

    assert all(review.review_id not in fact.source_id for fact in facts)
    assert not coverage.complete
    assert coverage.source_fact_ids == []


def test_direct_review_rejects_a_superseded_snapshot_and_hides_old_fact(
    tmp_path, monkeypatch
) -> None:
    store = RegulatorySourceReviewStore(tmp_path / "wilq.sqlite3")
    candidate_id = regulatory_source_candidates()[0].candidate_id
    first = _snapshot(store.path, candidate_id, now=datetime(2026, 7, 31, tzinfo=UTC))
    store.record(_command(snapshot=first), snapshot_store=RegulatorySourceSnapshotStore(store.path))
    second = _snapshot(store.path, candidate_id, now=datetime(2026, 8, 2, tzinfo=UTC))

    with pytest.raises(ValueError, match="stale"):
        store.record(
            _command(snapshot=first),
            snapshot_store=RegulatorySourceSnapshotStore(store.path),
        )

    monkeypatch.setattr(source_reviews_module, "regulatory_source_review_store", lambda: store)
    facts = source_facts_module.ekologus_source_facts()
    assert not any(fact.source_id.startswith("regulatory_source_fact_") for fact in facts)
    assert second.snapshot_id != first.snapshot_id


def test_source_snapshot_stays_bounded_without_persisting_source_body(tmp_path) -> None:
    from wilq.content.regulatory.source_snapshots import _MAX_SNAPSHOT_BYTES

    store = RegulatorySourceSnapshotStore(tmp_path / "wilq.sqlite3")

    with pytest.raises(ValueError, match="exceeds the safe snapshot size"):
        store.capture(
            "bdo_system_definition_2026_07_31_r2",
            reader=lambda _: (b"x" * (_MAX_SNAPSHOT_BYTES + 1), "application/pdf"),
        )

    assert not store.path.exists()


def test_source_snapshot_rejects_a_redirect_outside_the_official_allowlist(tmp_path) -> None:
    store = RegulatorySourceSnapshotStore(tmp_path / "wilq.sqlite3")

    with pytest.raises(ValueError, match="outside the allowlist"):
        store.capture(
            "bdo_system_definition_2026_07_31_r2",
            reader=lambda _: (
                b"<html><main>untrusted body</main></html>",
                "text/html",
                "https://not-official.example/regulatory-source",
            ),
        )

    assert not store.path.exists()


def test_official_reader_stops_before_a_redirect_target_is_requested(monkeypatch) -> None:
    candidate = regulatory_source_candidates()[0]
    redirected_to = "https://not-official.example/return-to-source"
    requested_urls: list[str] = []

    class _RedirectingOpener:
        def __init__(self, handler) -> None:
            self.handler = handler

        def open(self, request, *, timeout):
            requested_urls.append(request.full_url)
            return self.handler.redirect_request(
                request, None, 302, "Found", None, redirected_to
            )

    monkeypatch.setattr(
        source_snapshots_module,
        "build_opener",
        lambda handler: _RedirectingOpener(handler),
    )

    with pytest.raises(HTTPError, match="redirects are not allowed"):
        source_snapshots_module._read_official_source(candidate.source_url)
    assert requested_urls == [candidate.source_url]


def test_full_bdo_candidate_review_set_unlocks_exact_coverage_only_after_acceptance(
    tmp_path, monkeypatch
) -> None:
    store = RegulatorySourceReviewStore(tmp_path / "wilq.sqlite3")
    for candidate in regulatory_source_candidates():
        snapshot = _snapshot(store.path, candidate.candidate_id)
        store.record(
            _command(
                candidate_id=candidate.candidate_id,
                snapshot=snapshot,
                requirement_ids=candidate.requirement_ids,
            ),
            snapshot_store=RegulatorySourceSnapshotStore(store.path),
        )
    monkeypatch.setattr(source_reviews_module, "regulatory_source_review_store", lambda: store)

    coverage = regulatory_content_coverage(
        service_card_id="ekologus_service_bdo_reporting",
        source_facts=source_facts_module.ekologus_source_facts(),
    )

    assert coverage.complete
    assert {
        requirement.id for requirement in coverage.requirements
    } == set(coverage.covered_requirement_ids)
    assert len(coverage.evidence_ids) == len(
        [candidate for candidate in regulatory_source_candidates() if candidate.profile_id == "bdo"]
    )


def test_review_rejects_changed_candidate_or_unassigned_requirement(tmp_path) -> None:
    store = RegulatorySourceReviewStore(tmp_path / "wilq.sqlite3")
    snapshot = _snapshot(store.path, regulatory_source_candidates()[0].candidate_id)
    changed = _command(snapshot=snapshot).model_copy(
        update={"expected_source_url": "https://bdo.mos.gov.pl/other"}
    )
    with pytest.raises(ValueError, match="candidate changed"):
        store.record(changed, snapshot_store=RegulatorySourceSnapshotStore(store.path))

    outside_requirement = _command(
        snapshot=snapshot,
        requirement_ids=["bdo_risks_and_sanctions"],
    )
    with pytest.raises(ValueError, match="outside its candidate"):
        store.record(
            outside_requirement,
            snapshot_store=RegulatorySourceSnapshotStore(store.path),
        )


def test_public_source_review_route_persists_only_human_decision(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WILQ_STATE_DB", str(tmp_path / "wilq.sqlite3"))
    app = FastAPI()
    router = APIRouter()
    register_content_regulatory_source_review_routes(router)
    app.include_router(router)
    client = TestClient(app)
    monkeypatch.setattr(
        source_snapshots_module,
        "_read_official_source",
        lambda _: (b"<html>official source snapshot</html>", "text/html"),
    )
    snapshot_response = client.get(
        "/api/content/regulatory-source-candidates/bdo_registration_scope_2026_07_31_r2/snapshot"
    )
    snapshot = ContentRegulatorySourceSnapshot.model_validate(snapshot_response.json()["snapshot"])
    payload = _command(
        candidate_id="bdo_registration_scope_2026_07_31_r2", snapshot=snapshot
    ).model_dump(mode="json")
    missing_snapshot_payload = {
        **payload,
        "expected_source_snapshot_id": "regulatory_snapshot_missing",
    }

    before = client.get("/api/content/regulatory-source-reviews")
    missing_snapshot = client.post(
        "/api/content/regulatory-source-reviews",
        json=missing_snapshot_payload,
    )
    recorded = client.post("/api/content/regulatory-source-reviews", json=payload)
    after = client.get("/api/content/regulatory-source-reviews")

    assert before.status_code == 200
    assert before.json() == {"reviews": []}
    assert snapshot_response.status_code == 200
    assert snapshot_response.json()["status"] == "captured"
    assert missing_snapshot.status_code == 409
    assert missing_snapshot.json()["code"] == "source_snapshot_missing"
    assert recorded.status_code == 200
    assert recorded.json()["decision"] == "accepted"
    assert recorded.json()["source_url"] == payload["expected_source_url"]
    assert after.status_code == 200
    assert [item["review_id"] for item in after.json()["reviews"]] == [
        recorded.json()["review_id"]
    ]
