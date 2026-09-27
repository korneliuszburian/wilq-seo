from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.content_request_workflow import (
    register_content_request_workflow_routes,
)
from wilq.content.knowledge.cards import ContentKnowledgeCard
from wilq.content.knowledge.source_facts import ContentSourceFact
from wilq.content.workflow.current_page_evidence import CurrentPageEvidenceResponse
from wilq.content.workflow.intake import (
    ContentIntakeFieldProvenance,
    ContentIntakeQueueItem,
)
from wilq.content.workflow.store.store import ContentWorkflowStore

QUEUE_ID = "content_request_workflow_test"
_ROUTE = f"/api/content/intake-requests/{QUEUE_ID}/workflow"
_FRESHNESS = {
    "google_search_console": "stale",
    "google_analytics_4": "stale",
    "ahrefs": "missing",
    "wordpress_ekologus": "fresh",
}


def _queue_item() -> ContentIntakeQueueItem:
    return ContentIntakeQueueItem(
        queue_id=QUEUE_ID,
        request_id=UUID("00000000-0000-4000-8000-000000000300"),
        input_digest="a" * 64,
        status="queued",
        ask="artykuł o kandydatach",
        provenance=(
            ContentIntakeFieldProvenance(
                field="ask",
                provenance="user_input",
                detail="Synthetic workflow request.",
            ),
        ),
        candidate_work_item_ids=("wi_candidates",),
        candidate_paths=("/candidates",),
        candidate_public_urls=("https://www.ekologus.pl/candidates/",),
        safe_next_step="Otwórz stronę.",
        created_at=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
    )


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


def _store(tmp_path: Path) -> ContentWorkflowStore:
    store = ContentWorkflowStore(tmp_path / "request-workflow.sqlite3")
    store.create_content_intake_request(_queue_item())
    return store


def _client(
    store: ContentWorkflowStore,
    *,
    facts: tuple[ContentSourceFact, ...] = (),
) -> TestClient:
    router = APIRouter()
    register_content_request_workflow_routes(
        router,
        store_factory=lambda: store,
        evidence_loader=lambda work_item_id: _evidence(),
        source_facts_loader=lambda: facts,
        cards_loader=lambda: (_exact_page_card(),),
        freshness_loader=lambda: _FRESHNESS,
    )
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _post_event(
    client: TestClient,
    key: str,
    event_type: str,
    *,
    note: str = "Synthetic workflow event.",
    gate_code: str | None = None,
    gate_status: str | None = None,
    owner: str | None = None,
) -> object:
    payload: dict[str, object] = {
        "idempotency_key": key,
        "event_type": event_type,
        "note": note,
    }
    if gate_code is not None:
        payload["gate_code"] = gate_code
    if gate_status is not None:
        payload["gate_status"] = gate_status
    if owner is not None:
        payload["owner"] = owner
    return client.post(f"{_ROUTE}/events", json=payload)


def test_request_workflow_event_idempotency_and_conflict(tmp_path: Path) -> None:
    client = _client(_store(tmp_path))

    first = _post_event(client, "event-1", "intake_accepted")
    second = _post_event(client, "event-1", "intake_accepted")
    conflict = _post_event(client, "event-1", "intake_accepted", note="Zmieniona treść.")

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert first.json()["event_id"] == second.json()["event_id"]
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["detail"] == "request_workflow_idempotency_conflict"


def test_request_workflow_resumes_with_same_lineage_and_pending_gate(
    tmp_path: Path,
) -> None:
    client = _client(_store(tmp_path), facts=(_approved_fact(),))
    _post_event(client, "event-1", "intake_accepted")
    _post_event(
        client,
        "event-2",
        "human_gate_requested",
        gate_code="target",
        owner="Wilku",
    )

    first = client.get(_ROUTE)
    second = client.get(_ROUTE)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["lineage_event_ids"] == second.json()["lineage_event_ids"]
    state = first.json()
    assert state["current_step"] == "human_review"
    assert state["status"] in {"in_progress", "blocked"}
    pending = [gate for gate in state["gates"] if gate["status"] == "pending"]
    assert pending and pending[0]["code"] == "target"
    assert pending[0]["owner"] == "Wilku"
    assert state["event_count"] == 2


def test_request_workflow_source_change_invalidates_an_approved_gate(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    ready_client = _client(store, facts=(_approved_fact(),))
    _post_event(ready_client, "r1", "research_ready")
    _post_event(ready_client, "g1", "human_gate_requested", gate_code="target", owner="Wilku")
    _post_event(
        ready_client,
        "g2",
        "human_gate_answered",
        gate_code="target",
        gate_status="approved",
        owner="Wilku",
    )

    approved = ready_client.get(_ROUTE).json()
    assert approved["status"] == "in_progress"
    assert approved["gates"][0]["status"] == "approved"

    stale_client = _client(store, facts=())
    stale = stale_client.get(_ROUTE).json()

    assert stale["status"] == "blocked"
    assert stale["blocker_code"] == "request_workflow_source_changed"
    assert stale["gates"][0]["status"] == "stale"
    assert stale["lineage_event_ids"] == approved["lineage_event_ids"]


def test_request_workflow_is_ready_for_brief_with_live_research(tmp_path: Path) -> None:
    client = _client(_store(tmp_path), facts=(_approved_fact(),))
    _post_event(client, "r1", "research_ready")
    _post_event(client, "b1", "brief_ready")

    response = client.get(_ROUTE)

    assert response.status_code == 200, response.text
    state = response.json()
    assert state["status"] == "ready_for_brief"
    assert state["current_step"] == "brief_ready"
    assert state["generation_allowed"] is False
    assert state["blocker_code"] is None


def test_request_workflow_failed_event_returns_a_failed_state(tmp_path: Path) -> None:
    client = _client(_store(tmp_path), facts=(_approved_fact(),))

    response = _post_event(client, "f1", "failed", note="Krok nieudany.")

    assert response.status_code == 201, response.text
    state = client.get(_ROUTE).json()
    assert state["status"] == "failed"
    assert state["current_step"] == "failed"
    assert state["blocker_code"] == "request_workflow_failed"


def test_request_workflow_rejected_gate_blocks(tmp_path: Path) -> None:
    client = _client(_store(tmp_path), facts=(_approved_fact(),))
    _post_event(client, "g1", "human_gate_requested", gate_code="target", owner="Wilku")
    _post_event(
        client,
        "g2",
        "human_gate_answered",
        gate_code="target",
        gate_status="rejected",
        owner="Wilku",
    )

    state = client.get(_ROUTE).json()

    assert state["status"] == "blocked"
    assert state["blocker_code"] == "request_workflow_gate_rejected"
    assert state["gates"][0]["status"] == "rejected"


def test_request_workflow_re_request_after_answer_stops_again(tmp_path: Path) -> None:
    client = _client(_store(tmp_path), facts=(_approved_fact(),))
    _post_event(client, "g1", "human_gate_requested", gate_code="target", owner="Wilku")
    _post_event(
        client,
        "g2",
        "human_gate_answered",
        gate_code="target",
        gate_status="approved",
        owner="Wilku",
    )
    _post_event(client, "g3", "human_gate_requested", gate_code="target", owner="Wilku")

    state = client.get(_ROUTE).json()

    assert state["current_step"] == "human_review"
    assert state["gates"][0]["status"] == "pending"


def test_request_workflow_claim_gate_stales_on_stale_freshness(tmp_path: Path) -> None:
    client = _client(_store(tmp_path), facts=(_approved_fact(),))
    _post_event(client, "c1", "human_gate_requested", gate_code="claim", owner="Wilku")
    _post_event(
        client,
        "c2",
        "human_gate_answered",
        gate_code="claim",
        gate_status="approved",
        owner="Wilku",
    )
    _post_event(client, "t1", "human_gate_requested", gate_code="target", owner="Wilku")
    _post_event(
        client,
        "t2",
        "human_gate_answered",
        gate_code="target",
        gate_status="approved",
        owner="Wilku",
    )

    state = client.get(_ROUTE).json()
    gates = {gate["code"]: gate["status"] for gate in state["gates"]}

    assert gates["claim"] == "stale"
    assert gates["target"] == "approved"
    assert state["current_step"] == "human_review"


def test_request_workflow_rejects_an_invalid_gate_event(tmp_path: Path) -> None:
    client = _client(_store(tmp_path))

    response = client.post(
        f"{_ROUTE}/events",
        json={
            "idempotency_key": "invalid-1",
            "event_type": "human_gate_requested",
            "note": "Brak ownera.",
            "gate_code": "target",
        },
    )

    assert response.status_code == 422, response.text


def test_request_workflow_non_claim_gate_stays_approved(tmp_path: Path) -> None:
    client = _client(_store(tmp_path), facts=(_approved_fact(),))
    _post_event(client, "d1", "human_gate_requested", gate_code="disclaimer", owner="Wilku")
    _post_event(
        client,
        "d2",
        "human_gate_answered",
        gate_code="disclaimer",
        gate_status="approved",
        owner="Wilku",
    )

    state = client.get(_ROUTE).json()

    assert state["gates"][0]["status"] == "approved"


def test_request_workflow_unknown_queue_is_typed_404(tmp_path: Path) -> None:
    client = _client(_store(tmp_path))

    response = client.get("/api/content/intake-requests/missing_queue/workflow")

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "intake_queue_item_missing"
