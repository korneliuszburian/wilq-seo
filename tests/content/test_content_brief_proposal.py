from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.content_brief_proposal import (
    register_content_brief_proposal_routes,
)
from tests.content.test_request_workflow import (
    _FRESHNESS,
    _approved_fact,
    _evidence,
    _exact_page_card,
)
from wilq.content.workflow.intake import (
    ContentIntakeFieldProvenance,
    ContentIntakeQueueItem,
)
from wilq.content.workflow.request_workflow import build_content_request_workflow_event
from wilq.content.workflow.store.store import ContentWorkflowStore

QUEUE_ID = "content_brief_test"
_ROUTE = f"/api/content/intake-requests/{QUEUE_ID}/brief"


def _queue_item(
    candidates: tuple[str, ...] = ("wi_candidates",),
) -> ContentIntakeQueueItem:
    return ContentIntakeQueueItem(
        queue_id=QUEUE_ID,
        request_id=UUID("00000000-0000-4000-8000-000000000400"),
        input_digest="a" * 64,
        status="queued",
        ask="artykuł o kandydatach",
        provenance=(
            ContentIntakeFieldProvenance(
                field="ask",
                provenance="user_input",
                detail="Synthetic brief request.",
            ),
            ContentIntakeFieldProvenance(
                field="target_path",
                provenance="evidence" if candidates else "unknown",
                detail="Synthetic target match.",
                evidence_ids=("ev_wp_run",) if candidates else (),
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


def _store(
    tmp_path: Path,
    candidates: tuple[str, ...] = ("wi_candidates",),
) -> ContentWorkflowStore:
    store = ContentWorkflowStore(tmp_path / "brief.sqlite3")
    store.create_content_intake_request(_queue_item(candidates))
    return store


def _append(
    store: ContentWorkflowStore,
    key: str,
    event_type: str,
    **kwargs: object,
) -> None:
    store.append_content_request_workflow_event(
        build_content_request_workflow_event(
            queue_id=QUEUE_ID,
            idempotency_key=key,
            event_type=event_type,
            note="Synthetic brief workflow event.",
            **kwargs,
        )
    )


def _client(
    store: ContentWorkflowStore,
    *,
    facts: tuple[object, ...] = (),
    freshness: dict[str, str] | None = None,
) -> TestClient:
    router = APIRouter()
    register_content_brief_proposal_routes(
        router,
        store_factory=lambda: store,
        evidence_loader=lambda work_item_id: _evidence(),
        source_facts_loader=lambda: facts,
        cards_loader=lambda: (_exact_page_card(),),
        freshness_loader=lambda: freshness if freshness is not None else _FRESHNESS,
    )
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_brief_is_ready_for_an_existing_page_with_provenance(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _append(store, "r1", "research_ready")
    _append(store, "b1", "brief_ready")
    client = _client(store, facts=(_approved_fact(),))

    response = client.get(_ROUTE)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["route"] == "existing_page"
    assert payload["target_work_item_id"] == "wi_candidates"
    assert payload["planning_proposal_created"] is False
    assert payload["action_created"] is False
    assert payload["generation_allowed"] is False
    fields = {field["field"]: field for field in payload["fields"]}
    assert fields["topic"]["provenance"] == "user_input"
    assert fields["target"]["provenance"] == "evidence"
    assert fields["target"]["value"] == payload["target_path"]
    assert fields["target"]["evidence_ids"] == ["ev_wp_run"]
    assert fields["source_facts"]["provenance"] == "evidence"
    assert fields["audience"]["provenance"] == "unknown"
    assert fields["cta"]["provenance"] == "unknown"
    assert fields["demand"]["provenance"] == "unknown"
    assert fields["competition"]["provenance"] == "unknown"
    assert fields["source_facts"]["evidence_ids"] == ["ev_official_fact"]


def test_brief_derives_claim_copy_from_the_live_read(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _append(store, "r1", "research_ready")
    _append(store, "b1", "brief_ready")
    fresh = {
        "google_search_console": "fresh",
        "google_analytics_4": "fresh",
        "ahrefs": "fresh",
        "wordpress_ekologus": "fresh",
    }
    client = _client(store, facts=(_approved_fact(),), freshness=fresh)

    payload = client.get(_ROUTE).json()
    fields = {field["field"]: field for field in payload["fields"]}

    assert payload["status"] == "ready"
    assert "Brak świeżych danych popytu" not in fields["demand"]["detail"]
    assert "Brak świeżych danych konkurencji" not in fields["competition"]["detail"]


def test_brief_stops_at_a_pending_human_gate(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _append(store, "i1", "intake_accepted")
    _append(store, "g1", "human_gate_requested", gate_code="target", owner="Wilku")
    client = _client(store, facts=(_approved_fact(),))

    payload = client.get(_ROUTE).json()

    assert payload["status"] == "blocked"
    assert payload["blockers"][0]["code"] == "brief_workflow_not_ready"
    assert payload["blockers"][0]["owner"] == "Wilku"


def test_brief_routes_a_new_page_to_the_owner_discovery_decision(tmp_path: Path) -> None:
    client = _client(_store(tmp_path, candidates=()))

    payload = client.get(_ROUTE).json()

    assert payload["status"] == "blocked"
    assert payload["route"] == "new_page"
    assert payload["blockers"][0]["code"] == "new_topic_discovery_source_unavailable"
    assert payload["blockers"][0]["owner"] == "Wilku"
    fields = {field["field"]: field for field in payload["fields"]}
    assert fields["target"]["provenance"] == "unknown"
    assert fields["source_facts"]["provenance"] == "unknown"


def test_brief_returns_typed_ambiguity_for_multiple_targets(tmp_path: Path) -> None:
    client = _client(_store(tmp_path, candidates=("wi_a", "wi_b")))

    payload = client.get(_ROUTE).json()

    assert payload["status"] == "blocked"
    assert payload["route"] == "ambiguous"
    assert payload["blockers"][0]["code"] == "brief_route_ambiguous"


def test_brief_keeps_an_unsupported_source_claim_blocked(tmp_path: Path) -> None:
    client = _client(_store(tmp_path))

    payload = client.get(_ROUTE).json()

    assert payload["status"] == "blocked"
    assert payload["route"] == "existing_page"
    assert payload["blockers"][0]["code"] == "approved_source_fact_candidate_missing"


def test_brief_returns_typed_missing_for_unknown_queue(tmp_path: Path) -> None:
    client = _client(_store(tmp_path))

    response = client.get("/api/content/intake-requests/missing_queue/brief")

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "intake_queue_item_missing"
