"""Public ActionObject review of one immutable exact v2 research packet."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.actions import create_actions_router
from tests.content.test_material_review_action_v2 import _configure_local_action_runtime
from tests.content.test_research_packet_v2_preview import _ready_inputs
from wilq.content.workflow.research_packet_v2_preview import (
    ResearchPacketV2Preview,
    ResearchPacketV2PreviewBlocker,
    build_research_packet_v2_preview,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore


def _client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[TestClient, ContentWorkflowStore, str, dict[str, ResearchPacketV2Preview]]:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    source_pack, planning_input = _ready_inputs()
    preview = build_research_packet_v2_preview(
        "wi_exact", source_pack=source_pack, planning_input=planning_input
    )
    assert preview.status == "ready" and preview.preview_hash is not None
    current = {"preview": preview}
    app = FastAPI()
    route_path = (
        Path(__file__).resolve().parents[2]
        / "apps/api/wilq_api/routers/content_research_packet_v2_action.py"
    )
    if route_path.is_file():
        module = importlib.import_module(
            "apps.api.wilq_api.routers.content_research_packet_v2_action"
        )
        module.register_content_research_packet_v2_action_routes(
            app.router,
            store_factory=lambda: store,
            preview_loader=lambda _work_item_id: current["preview"],
        )
    app.include_router(create_actions_router(lambda: None))
    monkeypatch.setenv("WILQ_STATE_DB", str(store.path))
    _configure_local_action_runtime(monkeypatch, store, audit_store)
    return TestClient(app), store, preview.preview_hash, current


def _approve_action(
    client: TestClient, action_id: str, *, checked_items: list[str] | None = None
) -> dict[str, object]:
    validated = client.post(f"/api/actions/{action_id}/validate")
    assert validated.status_code == 200, validated.text
    assert validated.json()["valid"] is True
    assert client.post(f"/api/actions/{action_id}/preview", json={}).status_code == 200
    review = client.post(
        f"/api/actions/{action_id}/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "synthetic-reviewer",
            "notes": "Synthetic full exact packet review.",
            "checked_items": ["reviewed_full_packet"] if checked_items is None else checked_items,
        },
    )
    assert review.status_code == 200, review.text
    assert (
        client.post(
            f"/api/actions/{action_id}/confirm",
            json={
                "confirmed_by": "synthetic-reviewer",
                "notes": "Exact.",
                "preview_acknowledged": True,
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/actions/{action_id}/impact-check",
            json={"checked_by": "synthetic-reviewer", "notes": "Local only."},
        ).status_code
        == 200
    )
    applied = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic-reviewer"},
    )
    assert applied.status_code in {200, 409}, applied.text
    payload = applied.json()
    return dict(payload.get("detail", payload))


def test_public_packet_v2_action_reviews_exact_snapshot_and_records_local_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, preview_hash, current = _client(tmp_path, monkeypatch)
    prepared = client.post("/api/content/work-items/wi_exact/research-packet-v2-action/preview")
    assert prepared.status_code == 200, prepared.text
    action_id = prepared.json()["action_id"]
    assert action_id == f"act_content_research_packet_v2_{preview_hash}"
    assert prepared.json()["generation_allowed"] is False
    assert prepared.json()["external_write_attempted"] is False
    from wilq.content.workflow.research_packet_v2_action import (
        validate_research_packet_v2_action_payload,
    )

    malformed = dict(prepared.json()["action"]["payload"])
    malformed["payload_preview"] = [None]
    assert validate_research_packet_v2_action_payload(malformed)

    applied = _approve_action(client, action_id)
    assert applied["applied"] is True, applied
    result = applied["adapter_result"]
    assert isinstance(result, dict)
    assert result["external_write_attempted"] is False
    assert result["generation_allowed"] is False
    receipt = store.load_research_packet_v2_approval_receipt(result["packet_id"])
    assert receipt is not None
    assert receipt.packet_digest == preview_hash
    assert receipt.action_id == action_id
    assert receipt.review_audit_event_id == result["review_audit_event_id"]
    readback = client.get(f"/api/content/research-packets-v2/{receipt.packet_id}")
    assert readback.status_code == 200, readback.text
    assert readback.json()["currentness_status"] == "current"
    assert readback.json()["generation_allowed"] is False

    current["preview"] = ResearchPacketV2Preview(
        status="blocked",
        work_item_id="wi_exact",
        blocker=ResearchPacketV2PreviewBlocker(
            code="material_meaning_changed",
            owner="WILQ content workflow",
            evidence_ids=("ev_current",),
            safe_next_step="Przejrzyj nowy dokładny materiał.",
        ),
    )
    stale = client.get(f"/api/content/research-packets-v2/{receipt.packet_id}")
    assert stale.status_code == 200
    assert stale.json()["currentness_status"] == "blocked"
    assert stale.json()["blocker"]["code"] == "material_meaning_changed"
    assert stale.json()["generation_allowed"] is False

    def unavailable_current(_work_item_id: str) -> ResearchPacketV2Preview:
        raise HTTPException(status_code=404, detail="current_work_item_missing")

    from apps.api.wilq_api.routers.content_research_packet_v2_action import (
        register_content_research_packet_v2_action_routes,
    )

    unavailable_app = FastAPI()
    register_content_research_packet_v2_action_routes(
        unavailable_app.router,
        store_factory=lambda: store,
        preview_loader=unavailable_current,
    )
    unavailable = TestClient(unavailable_app).get(
        f"/api/content/research-packets-v2/{receipt.packet_id}"
    )
    assert unavailable.status_code == 200, unavailable.text
    assert unavailable.json()["currentness_status"] == "blocked"
    assert unavailable.json()["blocker"]["code"] == "research_packet_v2_current_read_unavailable"


def test_packet_v2_action_requires_full_packet_attestation_before_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, preview_hash, _current = _client(tmp_path, monkeypatch)
    prepared = client.post("/api/content/work-items/wi_exact/research-packet-v2-action/preview")
    assert prepared.status_code == 200
    applied = _approve_action(
        client, prepared.json()["action_id"], checked_items=["reviewed_url_only"]
    )
    assert applied["applied"] is False
    assert (
        store.load_research_packet_v2_approval_receipt(
            f"content_research_packet_v2_{preview_hash[:24]}"
        )
        is None
    )


def test_packet_v2_action_preview_preserves_current_typed_blocker() -> None:
    app = FastAPI()
    from apps.api.wilq_api.routers.content_research_packet_v2_action import (
        register_content_research_packet_v2_action_routes,
    )

    blocked = ResearchPacketV2Preview(
        status="blocked",
        work_item_id="wi_blocked",
        blocker=ResearchPacketV2PreviewBlocker(
            code="material_review_missing_or_stale",
            owner="WILQ content workflow",
            evidence_ids=("ev_current_page",),
            safe_next_step="Przejrzyj pełny materiał.",
        ),
    )
    register_content_research_packet_v2_action_routes(
        app.router, preview_loader=lambda _work_item_id: blocked
    )
    response = TestClient(app).post(
        "/api/content/work-items/wi_blocked/research-packet-v2-action/preview"
    )
    assert response.status_code == 409
    assert response.json()["blocker_code"] == "material_review_missing_or_stale"
    assert response.json()["blocker_owner"] == "WILQ content workflow"
    assert response.json()["evidence_ids"] == ["ev_current_page"]
    assert response.json()["safe_next_step"]
    assert response.json()["generation_allowed"] is False

    def unavailable_current(_work_item_id: str) -> ResearchPacketV2Preview:
        raise HTTPException(status_code=404, detail="current_work_item_missing")

    unavailable_app = FastAPI()
    register_content_research_packet_v2_action_routes(
        unavailable_app.router, preview_loader=unavailable_current
    )
    unavailable = TestClient(unavailable_app).post(
        "/api/content/work-items/wi_blocked/research-packet-v2-action/preview"
    )
    assert unavailable.status_code == 409
    assert unavailable.json()["blocker_code"] == "research_packet_v2_preview_unavailable"
    assert unavailable.json()["blocker_owner"] == "WILQ content workflow"
