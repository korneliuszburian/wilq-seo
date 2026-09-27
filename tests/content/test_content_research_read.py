from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.content_research_read import (
    register_content_research_read_routes,
)
from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.intake import (
    ContentIntakeFieldProvenance,
    ContentIntakeQueueItem,
)

_FRESHNESS = {
    "google_search_console": "stale",
    "google_analytics_4": "stale",
    "ahrefs": "missing",
    "wordpress_ekologus": "fresh",
}


def _approved_fact(path: str = "/candidates") -> ContentSourceFact:
    return ContentSourceFact(
        source_id="synthetic_official_fact",
        source_type="legal_update",
        privacy_class="commit_safe",
        source_url_or_path="https://example.gov/exact-source",
        extracted_fact="Synthetic approved fact for the exact page.",
        scope="claim_policy",
        freshness_date="2026-09-24",
        confidence=0.9,
        review_status="approved",
        reviewer="synthetic_wilku",
        evidence_ids=["ev_official_fact"],
        source_connectors=["official_regulatory_review"],
        target_card_id="synthetic_profile",
        target_card_type="regulatory_source",
        target_card_title="Synthetic profile",
        official_source=True,
        regulatory_profile_id="synthetic_profile",
        regulatory_profile_version="synthetic-v1",
        regulatory_requirement_ids=["requirement_exact"],
        applicable_canonical_paths=[path],
    )


def _pending_fact(path: str = "/candidates") -> ContentSourceFact:
    return _approved_fact(path).model_copy(
        update={
            "source_id": "synthetic_pending_fact",
            "review_status": "review_required",
            "reviewer": None,
            "applicable_canonical_paths": [path],
        }
    )


def _exact_page_card() -> ContentKnowledgeCard:
    return ContentKnowledgeCard(
        id="synthetic_profile",
        card_type="service",
        title="Synthetic exact service card",
        summary="Exact page binding for scope validation.",
        service_binding_urls=["https://www.ekologus.pl/candidates/"],
        source_fact_ids=["synthetic_official_fact"],
        evidence_ids=["ev_service_card"],
        source_connectors=["synthetic_card_connector"],
        lifecycle_status="approved_current",
        confidence=0.9,
        freshness="2026-09-24",
    )


def _queue_item(candidates: tuple[str, ...] = ("wi_candidates",)) -> ContentIntakeQueueItem:
    return ContentIntakeQueueItem(
        queue_id="content_intake_test_queue",
        request_id=UUID("00000000-0000-4000-8000-000000000200"),
        input_digest="a" * 64,
        status="queued",
        ask="artykuł o kandydatach",
        provenance=(
            ContentIntakeFieldProvenance(
                field="ask",
                provenance="user_input",
                detail="Synthetic test request.",
            ),
        ),
        candidate_work_item_ids=candidates,
        candidate_paths=tuple(f"/path-{index}" for index in range(len(candidates))),
        candidate_public_urls=tuple(
            f"https://www.ekologus.pl/path-{index}/" for index in range(len(candidates))
        ),
        safe_next_step="Otwórz stronę.",
        created_at=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
    )


class _FakeStore:
    def __init__(self, item: ContentIntakeQueueItem | None) -> None:
        self.item = item

    def load_content_intake_request(self, queue_id: str) -> ContentIntakeQueueItem | None:
        if self.item is None or self.item.queue_id != queue_id:
            return None
        return self.item


def _evidence() -> CurrentPageEvidenceResponse:
    return CurrentPageEvidenceResponse(
        status="observed_material_current",
        decision="Dokładny bieżący odczyt.",
        work_item_id="wi_candidates",
        page_url="https://www.ekologus.pl/candidates/",
        material_meaning_digest="a" * 64,
        current_evidence_ids=["ev_current_page"],
        catalog_evidence_ids=["ev_catalog"],
        safe_next_step="Sprawdź zatwierdzone źródła.",
    )


def _client(
    store: _FakeStore,
    *,
    facts: tuple[ContentSourceFact, ...],
    cards: tuple[ContentKnowledgeCard, ...] = (),
) -> TestClient:
    router = APIRouter()
    register_content_research_read_routes(
        router,
        store_factory=lambda: store,
        evidence_loader=lambda work_item_id: _evidence(),
        source_facts_loader=lambda: facts,
        cards_loader=lambda: cards,
        freshness_loader=lambda: _FRESHNESS,
    )
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_research_read_returns_approved_facts_with_lineage_and_claim_gates() -> None:
    client = _client(
        _FakeStore(_queue_item()),
        facts=(_approved_fact(), _pending_fact()),
        cards=(_exact_page_card(),),
    )

    response = client.get(
        "/api/content/intake-requests/content_intake_test_queue/research"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["generation_allowed"] is False
    assert payload["research_packet_created"] is False
    assert payload["action_created"] is False
    assert [fact["source_fact_id"] for fact in payload["facts"]] == [
        "synthetic_official_fact"
    ]
    fact = payload["facts"][0]
    assert fact["source_url"] == "https://example.gov/exact-source"
    assert fact["evidence_ids"] == ["ev_official_fact"]
    assert fact["freshness_date"] == "2026-09-24"
    assert fact["scope"] == "claim_policy"
    assert fact["authority"] == "official"
    assert payload["blocked_sources"] == [
        {
            "source_fact_id": "synthetic_pending_fact",
            "review_status": "review_required",
            "source_url": "https://example.gov/exact-source",
            "evidence_ids": ["ev_official_fact"],
            "reason_code": "source_fact_review_required",
            "blocker_owner": "Wilku",
            "safe_next_step": (
                "Zatwierdź exact fakt źródłowy dla tej strony przed briefem."
            ),
        }
    ]
    gates = {gate["claim"]: gate for gate in payload["claim_gates"]}
    assert gates["demand"]["allowed"] is False
    assert gates["competitor"]["allowed"] is False


def test_research_read_keeps_an_unverified_source_blocked() -> None:
    client = _client(_FakeStore(_queue_item()), facts=(_pending_fact(),))

    response = client.get(
        "/api/content/intake-requests/content_intake_test_queue/research"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["facts"] == []
    assert payload["blockers"][0]["code"] == "source_fact_review_required"
    assert payload["blockers"][0]["owner"] == "Wilku"
    assert payload["blocked_sources"][0]["review_status"] == "review_required"


def test_research_read_keeps_a_normalized_unverified_source_blocked() -> None:
    client = _client(
        _FakeStore(_queue_item()),
        facts=(_approved_fact("/candidates"), _pending_fact("/Candidates/")),
        cards=(_exact_page_card(),),
    )

    response = client.get(
        "/api/content/intake-requests/content_intake_test_queue/research"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ready"
    assert [item["source_fact_id"] for item in payload["blocked_sources"]] == [
        "synthetic_pending_fact"
    ]


def test_research_read_keeps_a_card_bound_unverified_source_blocked() -> None:
    pending = _pending_fact().model_copy(update={"applicable_canonical_paths": []})
    client = _client(
        _FakeStore(_queue_item()),
        facts=(_approved_fact(), pending),
        cards=(_exact_page_card(),),
    )

    response = client.get(
        "/api/content/intake-requests/content_intake_test_queue/research"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ready"
    assert [item["source_fact_id"] for item in payload["blocked_sources"]] == [
        "synthetic_pending_fact"
    ]


def test_research_read_keeps_a_service_card_scoped_unverified_source_blocked() -> None:
    pending = _pending_fact().model_copy(
        update={
            "applicable_canonical_paths": [],
            "target_card_id": "other_card",
            "applicable_service_card_ids": ["synthetic_profile"],
        }
    )
    client = _client(
        _FakeStore(_queue_item()),
        facts=(_approved_fact(), pending),
        cards=(_exact_page_card(),),
    )

    response = client.get(
        "/api/content/intake-requests/content_intake_test_queue/research"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ready"
    assert [item["source_fact_id"] for item in payload["blocked_sources"]] == [
        "synthetic_pending_fact"
    ]


def test_research_read_uses_one_registry_snapshot() -> None:
    calls: list[int] = []

    def facts_loader() -> tuple[ContentSourceFact, ...]:
        calls.append(1)
        return (_approved_fact(),)

    router = APIRouter()
    register_content_research_read_routes(
        router,
        store_factory=lambda: _FakeStore(_queue_item()),
        evidence_loader=lambda work_item_id: _evidence(),
        source_facts_loader=facts_loader,
        cards_loader=lambda: (_exact_page_card(),),
        freshness_loader=lambda: _FRESHNESS,
    )
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).get(
        "/api/content/intake-requests/content_intake_test_queue/research"
    )

    assert response.status_code == 200, response.text
    assert calls == [1]


def test_research_read_blocks_a_non_exact_identity() -> None:
    mismatched = _evidence().model_copy(update={"work_item_id": "wi_other"})
    router = APIRouter()
    register_content_research_read_routes(
        router,
        store_factory=lambda: _FakeStore(_queue_item()),
        evidence_loader=lambda work_item_id: mismatched,
        source_facts_loader=lambda: (_approved_fact(),),
        cards_loader=lambda: (_exact_page_card(),),
        freshness_loader=lambda: _FRESHNESS,
    )
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).get(
        "/api/content/intake-requests/content_intake_test_queue/research"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["facts"] == []
    assert payload["blockers"]


def test_research_read_blocks_an_ambiguous_request_target() -> None:
    client = _client(_FakeStore(_queue_item(("wi_candidates", "wi_other"))), facts=())

    response = client.get(
        "/api/content/intake-requests/content_intake_test_queue/research"
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["blockers"][0]["code"] == "research_target_ambiguous"


def test_research_read_returns_typed_missing_for_unknown_queue() -> None:
    client = _client(_FakeStore(None), facts=())

    response = client.get(
        "/api/content/intake-requests/content_intake_missing/research"
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "intake_queue_item_missing"
