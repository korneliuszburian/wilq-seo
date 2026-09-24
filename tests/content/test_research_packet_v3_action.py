"""Public ActionObject approval of one exact v3 research packet."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from apps.api.wilq_api.routers.actions import create_actions_router
from tests.content.test_material_review_action_v2 import _configure_local_action_runtime
from tests.content.test_research_packet_v3_preview import _pack, _planning_result
from wilq.content.workflow.decisions.production import canonical_json_digest
from wilq.content.workflow.research_packet_v3_preview import (
    ResearchPacketV3Preview,
    build_research_packet_v3_preview,
)
from wilq.content.workflow.store.store import ContentWorkflowStore
from wilq.storage.local_state import LocalStateStore


def _client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[TestClient, ContentWorkflowStore, dict[str, ResearchPacketV3Preview]]:
    store = ContentWorkflowStore(tmp_path / "workflow.sqlite3")
    audit_store = LocalStateStore(tmp_path / "audit.sqlite3")
    preview = build_research_packet_v3_preview(
        "wi_exact", source_pack=_pack(), planning_result=_planning_result()
    )
    assert preview.status == "ready" and preview.preview_hash is not None
    current = {"preview": preview}
    app = FastAPI()
    route_path = Path(__file__).resolve().parents[2] / (
        "apps/api/wilq_api/routers/content_research_packet_v3_action.py"
    )
    if route_path.is_file():
        module = importlib.import_module(
            "apps.api.wilq_api.routers.content_research_packet_v3_action"
        )
        module.register_content_research_packet_v3_action_routes(
            app.router,
            store_factory=lambda: store,
            preview_loader=lambda _work_item_id: current["preview"],
        )
    app.include_router(create_actions_router(lambda: None))
    monkeypatch.setenv("WILQ_STATE_DB", str(store.path))
    _configure_local_action_runtime(monkeypatch, store, audit_store)
    preview_module = importlib.import_module(
        "apps.api.wilq_api.routers.content_research_packet_v3_preview"
    )
    monkeypatch.setattr(
        preview_module,
        "read_current_research_packet_v3_preview",
        lambda _work_item_id: current["preview"],
        raising=False,
    )
    return TestClient(app), store, current


def _apply(client: TestClient, action_id: str) -> dict[str, object]:
    assert client.post(f"/api/actions/{action_id}/validate").json()["valid"] is True
    assert client.post(f"/api/actions/{action_id}/preview", json={}).status_code == 200
    assert client.post(
        f"/api/actions/{action_id}/review",
        json={
            "outcome": "approved_for_prepare",
            "reviewed_by": "synthetic-reviewer",
            "notes": "Reviewed full exact v3 packet.",
            "checked_items": ["reviewed_full_packet"],
        },
    ).status_code == 200
    assert client.post(
        f"/api/actions/{action_id}/confirm",
        json={
            "confirmed_by": "synthetic-reviewer",
            "notes": "Exact local receipt.",
            "preview_acknowledged": True,
        },
    ).status_code == 200
    assert client.post(
        f"/api/actions/{action_id}/impact-check",
        json={"checked_by": "synthetic-reviewer", "notes": "Local only."},
    ).status_code == 200
    response = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic-reviewer"},
    )
    return dict(response.json().get("detail", response.json()))


def _with_semantic_cta_change(preview: ResearchPacketV3Preview) -> ResearchPacketV3Preview:
    provisional = preview.model_copy(update={"cta_direction": "Umów konsultację."})
    changed = provisional.model_dump(mode="python")
    digest = canonical_json_digest(provisional.semantic_payload())
    return ResearchPacketV3Preview.model_validate(
        changed
        | {
            "preview_hash": digest,
            "preview_id": f"content_research_packet_v3_{digest[:24]}",
        }
    )


def test_v3_action_keeps_first_snapshot_and_records_fresh_lineage_but_blocks_semantic_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, current = _client(tmp_path, monkeypatch)
    prepared = client.post("/api/content/work-items/wi_exact/research-packet-v3-action/preview")
    assert prepared.status_code == 200, prepared.text
    apply_responses = client.app.openapi()["paths"]["/api/actions/{action_id}/apply"]["post"][
        "responses"
    ]
    assert "409" in apply_responses
    action_id = prepared.json()["action_id"]
    initial = prepared.json()["preview"]
    assert action_id == f"act_content_research_packet_v3_{initial['preview_hash']}"
    assert prepared.json()["generation_allowed"] is False
    assert prepared.json()["external_write_attempted"] is False

    rotated = current["preview"].model_copy(
        update={
            "verification_evidence_ids": ("ev_rotated", "ev_official_fact"),
            "verification_evidence_digest": "1" * 64,
            "planning_input_digest": "2" * 64,
        }
    )
    current["preview"] = rotated
    second_prepare = client.post(
        "/api/content/work-items/wi_exact/research-packet-v3-action/preview"
    )
    assert second_prepare.status_code == 200, second_prepare.text
    assert second_prepare.json()["preview"] == initial

    result = _apply(client, action_id)
    assert result["applied"] is True, result
    adapter_result = result["adapter_result"]
    assert isinstance(adapter_result, dict)
    receipt = store.load_research_packet_v3_approval_receipt(adapter_result["packet_id"])
    assert receipt is not None
    assert receipt.verification_evidence_ids == rotated.verification_evidence_ids
    assert receipt.verification_evidence_digest == rotated.verification_evidence_digest
    assert adapter_result["external_write_attempted"] is False
    assert adapter_result["generation_allowed"] is False

    current["preview"] = current["preview"].model_copy(update={
        "verification_evidence_ids": ("ev_again", "ev_official_fact"),
        "verification_evidence_digest": "3" * 64,
    })
    retry = client.post(
        f"/api/actions/{action_id}/apply",
        json={"confirm": True, "confirmed_by": "synthetic-reviewer"},
    )
    retry_payload = retry.json().get("detail", retry.json())
    assert retry_payload["applied"] is True, retry_payload
    assert retry_payload["adapter_result"]["receipt_digest"] == receipt.receipt_digest
    assert retry_payload["adapter_result"]["verification_evidence_ids"] == list(
        receipt.verification_evidence_ids
    )
    readback = client.get(f"/api/content/research-packets-v3/{receipt.packet_id}")
    assert readback.status_code == 200, readback.text
    assert readback.json()["currentness_status"] == "current"
    assert readback.json()["receipt"]["receipt_digest"] == receipt.receipt_digest
    current["preview"] = _with_semantic_cta_change(current["preview"])
    stale_readback = client.get(f"/api/content/research-packets-v3/{receipt.packet_id}")
    assert stale_readback.status_code == 200, stale_readback.text
    assert stale_readback.json()["currentness_status"] == "blocked"
    assert stale_readback.json()["blocker"]["code"] == "research_packet_v3_current_drift"

    client, store, current = _client(tmp_path / "drift", monkeypatch)
    prepared = client.post("/api/content/work-items/wi_exact/research-packet-v3-action/preview")
    action_id = prepared.json()["action_id"]
    current["preview"] = _with_semantic_cta_change(current["preview"])
    drift_result = _apply(client, action_id)
    assert drift_result["applied"] is False
    assert drift_result["adapter_result"]["code"] == "research_packet_v3_current_drift"
    assert drift_result["typed_blocker"]["code"] == "research_packet_v3_current_drift"
    assert drift_result["adapter_result"]["owner"] == "WILQ content workflow"
    assert drift_result["adapter_result"]["safe_next_step"]
    assert store.load_research_packet_v3_approval_receipt(
        f"content_research_packet_v3_{prepared.json()['preview']['preview_hash'][:24]}"
    ) is None


def test_v3_action_current_preview_unavailable_blocks_before_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, store, _current = _client(tmp_path, monkeypatch)
    prepared = client.post("/api/content/work-items/wi_exact/research-packet-v3-action/preview")
    action_id = prepared.json()["action_id"]
    preview_module = importlib.import_module(
        "apps.api.wilq_api.routers.content_research_packet_v3_preview"
    )

    def unavailable(_work_item_id: str) -> ResearchPacketV3Preview:
        raise HTTPException(status_code=404, detail="current_work_item_missing")

    monkeypatch.setattr(preview_module, "read_current_research_packet_v3_preview", unavailable)
    result = _apply(client, action_id)
    assert result["applied"] is False
    assert result["adapter_result"]["code"] == "research_packet_v3_current_read_unavailable"
    assert result["adapter_result"]["owner"] == "WILQ content workflow"
    assert result["adapter_result"]["safe_next_step"]
    assert store.load_research_packet_v3_approval_receipt(
        f"content_research_packet_v3_{prepared.json()['preview']['preview_hash'][:24]}"
    ) is None
